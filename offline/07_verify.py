"""STEP 7 (offline): independent verification of the engine output (world data + meta).

Usage:  python 07_verify.py [tag] [--ref path/to/older_xf.json]
Checks: schema, every instance on lawn and inside a lot bed, clearance to edge/facade/road/playground per role,
oleander >= 10 m from playgrounds, rows never repeat one model > 2 times, groups mixed, yaw/scale variation,
tone rules (dark never next to yellow, conifers away from light broadleaf), coverage and empty lawn patches
(> 30 m2 farther than 4 m from any plant). Writes work/engine/verify_<tag>.json."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json, pickle, math, collections, argparse, numpy as np, cv2  # noqa: E402
from lsite import Site, SP, PX, X0, Y0, RES
import species6 as SPC
import metrics6

_ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument('tag', nargs='?', default=env.CFG['engine']['tag'])
_ap.add_argument('--ref', default=None, help='older xf json to compare the level list with (optional)')
_a = _ap.parse_args()
tag = _a.tag
D6 = os.path.join(SP, 'engine')
S = Site()
xf = json.load(open(os.path.join(D6, 'xf_%s.json' % tag)))
meta = pickle.load(open(os.path.join(D6, 'meta_%s.pkl' % tag), 'rb'))
ref = json.load(open(_a.ref)) if _a.ref else xf
rep = collections.OrderedDict()
MESH2KEYS = collections.defaultdict(set)
for k, v in SPC.LIB.items():
    MESH2KEYS[v[0]].add(k)

# 0 schema
rep['schema'] = dict(levels=len(xf), same_levels_as_ref=sorted(xf) == sorted(ref),
                     fields_ok=all(set(p) == {'mesh', 'x', 'y', 'z', 'roll', 'pitch', 'yaw', 's'} for v in xf.values() for p in v),
                     numeric_ok=all(all(isinstance(p[k], (int, float)) and math.isfinite(p[k]) for k in 'x y z roll pitch yaw s'.split())
                                    for v in xf.values() for p in v))

# rasters
lab = np.asarray(S.lab); grass = lab > 0
H, W = grass.shape
rr = np.clip(np.arange(H) // 4, 0, S.cls1.shape[0] - 1); cc = np.clip(np.arange(W) // 4, 0, S.cls1.shape[1] - 1)
cls = S.cls1[rr[:, None], cc[None, :]]
dist = lambda m: cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5) * PX
d_nonlawn = dist(~grass)
d_bld = dist((cls == 6) & ~grass)
d_road = dist((cls == 2) & ~grass)
d_play = dist((cls == 4) & ~grass)
del cls
lotbeds = {b['id'] for m in meta.values() for b in m['beds']}
podium = {p['id'] for m in meta.values() for p in m.get('podium', [])}

viol = collections.Counter(); off = 0; off_lot = 0; tot = 0; mins = collections.defaultdict(lambda: [99, 99, 99, 99])
zbad = 0
for lvl, pts in xf.items():
    recs = meta[lvl]['recs']
    assert len(pts) == len(recs)
    for p, r in zip(pts, recs):
        tot += 1
        assert SPC.mesh(r['key']) == p['mesh']
        cl = SPC.role(r['key'])
        R = (p['y'] - Y0) / RES; C = (p['x'] - X0) / RES
        i, j = int(R), int(C)
        if not (0 <= i < H and 0 <= j < W) or not grass[i, j]:
            off += 1; continue
        if S.beds[i, j] not in lotbeds:
            off_lot += 1
        if not (-400 < p['z'] < 200):
            zbad += 1
        dn, db, dr, dp = d_nonlawn[i, j], d_bld[i, j], d_road[i, j], d_play[i, j]
        mm = mins[cl]; mins[cl] = [min(mm[0], dn), min(mm[1], db), min(mm[2], dr), min(mm[3], dp)]
        t = 0.3
        if cl in 'LMSPC':
            if dn < SPC.EDGE_OFF[cl] - t: viol['tree_edge_' + cl] += 1
            if db < SPC.FACADE_OFF[cl] - t: viol['tree_facade_' + cl] += 1
            if dr < SPC.ROAD_OFF[cl] - t: viol['tree_road_' + cl] += 1
            if dp < (15 if cl == 'C' else 2.5) - t: viol['tree_play_' + cl] += 1
        else:
            rad = SPC.D(r['key'], p['s']) / 2
            if dn < rad - 0.05: viol['shrub_overhangs_paving'] += 1
            if r['key'] in SPC.NO_PLAY and dp < 10 - t: viol['oleander_near_play'] += 1
rep['lawn_test'] = dict(instances=tot, off_lawn=off, outside_lot_beds=off_lot, z_out_of_range=zbad)
rep['clearance_violations'] = dict(viol)
rep['clearance_min_m'] = {k: dict(edge=round(float(v[0]), 2), facade=round(float(v[1]), 2), road=round(float(v[2]), 2),
                                  play=round(float(v[3]), 2)) for k, v in sorted(mins.items())}

# species mix: rows, groups, shrub combos
rows = collections.defaultdict(list); groups = collections.defaultdict(list); sgroups = collections.defaultdict(list)
for lvl, m in meta.items():
    for r in m['recs']:
        if SPC.is_tree(r['key']):
            if r.get('row') is not None:
                rows[(lvl, r['row'])].append(r)
            groups[(lvl, r['gid'])].append(r)
        else:
            sgroups[(lvl, r['gid'])].append(r)
max_run = 0; bad_rows = []; row_species = collections.Counter()
for k, v in rows.items():
    v = sorted(v, key=lambda r: r['idx'])
    run = 1; best = 1
    for a, b in zip(v, v[1:]):
        run = run + 1 if SPC.mesh(a['key']) == SPC.mesh(b['key']) else 1
        best = max(best, run)
    max_run = max(max_run, best)
    if best > 2:
        bad_rows.append((k, best))
    if len(v) >= 4:
        row_species[min(len({SPC.mesh(r['key']) for r in v}), 4)] += 1
grp3 = [v for k, v in groups.items() if len(v) >= 3 and v[0]['role'] in ('cluster', 'conifer')]
mono_groups = sum(1 for v in grp3 if len({SPC.mesh(r['key']) for r in v}) < 2)
sg_sizes = [len(v) for v in sgroups.values()]
sg_mono = sum(1 for v in sgroups.values() if len({SPC.mesh(r['key']) for r in v}) < 2)
sg_small = sum(1 for v in sgroups.values() if len(v) < 3)
rep['species_mix'] = dict(rows=len(rows), rows_max_identical_run=max_run, rows_with_run_gt2=len(bad_rows),
                          rows_ge4_by_species_count=dict(sorted(row_species.items())),
                          tree_groups_ge3=len(grp3), tree_groups_ge3_single_species=mono_groups,
                          shrub_groups=len(sgroups), shrub_groups_single_species=sg_mono, shrub_groups_lt3=sg_small,
                          shrub_group_size_median=float(np.median(sg_sizes)) if sg_sizes else 0)
# yaw / scale jitter
yaws = np.array([p['yaw'] for v in xf.values() for p in v])
sc = collections.defaultdict(list)
for m in meta.values():
    for r in m['recs']:
        sc[r['key']].append(r['s'] / SPC.base(r['key']))
rep['variation'] = dict(yaw_hist_8bins=np.histogram(yaws, 8, (0, 360))[0].tolist(),
                        scale_rel_p5_p95={k: [round(float(np.percentile(v, 5)), 3), round(float(np.percentile(v, 95)), 3)]
                                          for k, v in sorted(sc.items()) if len(v) >= 20})
# tone checks
bad_c = bad_dy = 0
for m in meta.values():
    T = [r for r in m['recs'] if SPC.is_tree(r['key'])]
    P = np.array([[r['R'], r['C']] for r in T]) if T else np.zeros((0, 2))
    from scipy.spatial import cKDTree
    if len(T) < 2:
        continue
    for a, b in cKDTree(P).query_pairs(8.0 / PX):
        ka, kb = T[a]['key'], T[b]['key']
        if (SPC.role(ka) == 'C') != (SPC.role(kb) == 'C'):
            other = kb if SPC.role(ka) == 'C' else ka
            if SPC.tone(other) in 'GY': bad_c += 1
        if {SPC.tone(ka), SPC.tone(kb)} == {'D', 'Y'}: bad_dy += 1
rep['tone'] = dict(conifer_within_8m_of_light_broadleaf=bad_c, dark_next_to_yellow_within_8m=bad_dy)

# coverage + empty patches
M = metrics6.run(os.path.join(D6, 'xf_%s.json' % tag))
patches = []
for lvl, v in M.items():
    gl = {int(k) for k in meta[lvl].get('glades', {})}
    for p in v['patches']:
        why = 'PODIUM (lawn inside building mask, no ground z)' if p['bed'] in podium else (
            'deliberate park glade' if p['bed'] in gl else 'UNRESOLVED')
        patches.append(dict(level=lvl, **p, reason=why))
rep['coverage'] = {k: dict(lawn_m2=v['lawn_m2'], canopy=v['canopy'], covered=v['covered'], within4m=v['within4m'],
                           patches=len(v['patches'])) for k, v in M.items()}
rep['empty_patches_gt30m2_far4m'] = patches
rep['unresolved_patches'] = sum(1 for p in patches if p['reason'] == 'UNRESOLVED')
# totals
cnt = collections.Counter(p['mesh'] for v in xf.values() for p in v)
rep['totals'] = dict(instances=tot, trees=sum(n for m, n in cnt.items() if any(SPC.is_tree(k) for k in MESH2KEYS[m])),
                     meshes=len(cnt), per_mesh={m.split('/')[-1]: n for m, n in cnt.most_common()},
                     roles=dict(collections.Counter(r['role'] for m in meta.values() for r in m['recs']).most_common()),
                     podium_beds=len(podium), podium_m2=round(sum(p['A'] for m in meta.values() for p in m.get('podium', []))))
json.dump(rep, open(os.path.join(D6, 'verify_%s.json' % tag), 'w'), indent=1, default=float)
for k in ('schema', 'lawn_test', 'clearance_violations', 'clearance_min_m', 'species_mix', 'tone', 'unresolved_patches'):
    print(k, json.dumps(rep[k], default=float))
print('patches:')
for p in patches:
    print('  ', p['level'], p['area'], 'bed', p['bed'], p['reason'])
print('totals', rep['totals']['instances'], 'trees', rep['totals']['trees'], 'meshes', rep['totals']['meshes'])
print('roles', rep['totals']['roles'])
