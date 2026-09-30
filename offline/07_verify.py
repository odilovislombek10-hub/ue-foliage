"""STEP 7 (offline): independent verification of the engine output (world data + meta).

Usage:  python 07_verify.py [tag] [--ref path/to/older_xf.json]
Checks: schema, every instance on lawn and inside a lot bed, clearance to edge/facade/road/playground per role,
oleander >= 10 m from playgrounds, rows never repeat one model > 2 times, groups mixed, yaw/scale variation,
tone rules, coverage/empty patches and archviz composition (real row spacing, unrelated tree crowding,
underplanted tree bases, facade masses and worst beds). Writes work/engine/verify_<tag>.json."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json, pickle, math, collections, argparse, numpy as np, cv2  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
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
ARCHVIZ = {'audit_underplant_m': 3.0, 'audit_crowded_tree_m': 4.0, 'audit_facade_min_fraction': 0.08,
           'tree_heavy_per_100m2': 3.5}
ARCHVIZ.update(env.CFG.get('engine', {}).get('archviz', {}))
UNDERPLANT_M = float(ARCHVIZ['audit_underplant_m'])
CROWDED_M = float(ARCHVIZ['audit_crowded_tree_m'])
FACADE_FRAC = float(ARCHVIZ['audit_facade_min_fraction'])
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
max_run = 0; bad_rows = []; row_species = collections.Counter(); row_dists = []; tight_rows = []
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
    if len(v) >= 2:
        ds = [math.hypot(a['R'] - b['R'], a['C'] - b['C']) * PX for a, b in zip(v, v[1:])]
        row_dists.extend(ds)
        if min(ds) < CROWDED_M:
            tight_rows.append(dict(level=k[0], row=k[1], role=v[0].get('role'), minimum=round(min(ds), 2)))
grp3 = [v for k, v in groups.items() if len(v) >= 3 and v[0]['role'] in ('cluster', 'conifer')]
mono_groups = sum(1 for v in grp3 if len({SPC.mesh(r['key']) for r in v}) < 2)
sg_sizes = [len(v) for v in sgroups.values()]
sg_mono = sum(1 for v in sgroups.values() if len({SPC.mesh(r['key']) for r in v}) < 2)
sg_small = sum(1 for v in sgroups.values() if len(v) < 3)
rep['species_mix'] = dict(rows=len(rows), rows_max_identical_run=max_run, rows_with_run_gt2=len(bad_rows),
                          row_spacing_min_m=round(min(row_dists), 2) if row_dists else None,
                          row_spacing_median_m=round(float(np.median(row_dists)), 2) if row_dists else None,
                          rows_with_spacing_lt_audit=len(tight_rows), tightest_rows=sorted(tight_rows, key=lambda x: x['minimum'])[:20],
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

# Archviz composition audit.  Designed members of one free-form cluster may merge crowns; unrelated trees
# and all structural rows are checked against the hard visual spacing threshold.
unresolved_by_bed = collections.defaultdict(float)
for p in patches:
    if p['reason'] == 'UNRESOLVED':
        unresolved_by_bed[(p['level'], int(p['bed']))] += float(p['area'])

audit_levels = collections.OrderedDict(); audit_total = collections.Counter(); worst = []
structural_roles = {'street', 'row', 'frame', 'play', 'fill'}
for lvl, m in meta.items():
    by_bed = collections.defaultdict(list)
    for r in m['recs']:
        by_bed[int(r['bed'])].append(r)
    level_counter = collections.Counter(); bed_report = collections.OrderedDict()
    for b in sorted(m['beds'], key=lambda x: x['id']):
        bid = int(b['id']); recs = by_bed[bid]
        trees_b = [r for r in recs if SPC.is_tree(r['key'])]
        broad = [r for r in trees_b if SPC.role(r['key']) != 'C']
        shrubs_b = [r for r in recs if not SPC.is_tree(r['key'])]
        tp = np.array([[r['R'] * PX, r['C'] * PX] for r in trees_b], float)
        bp = np.array([[r['R'] * PX, r['C'] * PX] for r in broad], float)
        sp = np.array([[r['R'] * PX, r['C'] * PX] for r in shrubs_b], float)
        if len(broad) and len(shrubs_b):
            d, _ = cKDTree(sp).query(bp, k=1)
            under = int((d > UNDERPLANT_M).sum())
        else:
            under = len(broad)
        crowded = 0; cluster_pairs = 0
        if len(trees_b) >= 2:
            for i, j in cKDTree(tp).query_pairs(CROWDED_M):
                a, z = trees_b[i], trees_b[j]
                if a.get('gid') != z.get('gid') or a.get('role') in structural_roles or z.get('role') in structural_roles:
                    crowded += 1
                else:
                    cluster_pairs += 1
        shrub_groups = collections.defaultdict(list)
        for r in shrubs_b:
            shrub_groups[r.get('gid')].append(r)
        masses = sum(1 for v in shrub_groups.values() if len(v) >= 3 and len({x['key'] for x in v}) >= 2)
        area = float(b.get('A', 0.0)); density = len(trees_b) * 100.0 / max(area, 1.0)
        facade = float(b.get('fac', 0.0)) >= FACADE_FRAC and area >= 10.0
        facade_missing = bool(facade and masses == 0)
        gap_m2 = round(unresolved_by_bed[(lvl, bid)], 1)
        high_density = bool(area >= 80 and density >= 2.0 * float(ARCHVIZ['tree_heavy_per_100m2']))
        issues = []
        if broad and under / len(broad) > 0.55:
            issues.append('tree_bases_underplanted')
        if crowded:
            issues.append('trees_overcrowded')
        if gap_m2:
            issues.append('large_uncomposed_gap')
        if facade_missing:
            issues.append('bare_facade_edge')
        if high_density:
            issues.append('tree_density_excess')
        score = gap_m2 / 30.0 + crowded * 1.5 + (under / max(len(broad), 1)) * 2.0 + \
            (2.0 if facade_missing else 0.0) + (2.0 if high_density else 0.0)
        d = dict(type=b.get('type'), area_m2=round(area, 1), trees=len(trees_b), shrubs=len(shrubs_b),
                 shrub_masses=masses, tree_per_100m2=round(density, 2), broadleaf_bases=len(broad),
                 underplanted_bases=under, crowded_unrelated_pairs=crowded,
                 designed_cluster_pairs_ignored=cluster_pairs, unresolved_gap_m2=gap_m2,
                 facade_bed=facade, issues=issues, score=round(score, 2))
        if issues:
            bed_report[str(bid)] = d
            worst.append(dict(level=lvl, bed=bid, **d))
        level_counter.update(trees=len(trees_b), shrubs=len(shrubs_b), broadleaf_bases=len(broad),
                             underplanted_bases=under, crowded_unrelated_pairs=crowded,
                             unresolved_gap_m2=gap_m2, facade_beds=int(facade),
                             facade_beds_without_mass=int(facade_missing), issue_beds=int(bool(issues)))
    audit_total.update(level_counter)
    audit_levels[lvl] = dict(summary=dict(level_counter), beds=bed_report)

rep['archviz_design'] = dict(
    thresholds=dict(underplant_m=UNDERPLANT_M, crowded_unrelated_tree_m=CROWDED_M,
                    facade_fraction=FACADE_FRAC,
                    high_tree_density_per_100m2=2.0 * float(ARCHVIZ['tree_heavy_per_100m2'])),
    totals=dict(audit_total), per_level=audit_levels,
    worst_beds=sorted(worst, key=lambda x: (-x['score'], -x['unresolved_gap_m2']))[:40])
# totals
cnt = collections.Counter(p['mesh'] for v in xf.values() for p in v)
rep['totals'] = dict(instances=tot, trees=sum(n for m, n in cnt.items() if any(SPC.is_tree(k) for k in MESH2KEYS[m])),
                     meshes=len(cnt), per_mesh={m.split('/')[-1]: n for m, n in cnt.most_common()},
                     roles=dict(collections.Counter(r['role'] for m in meta.values() for r in m['recs']).most_common()),
                     podium_beds=len(podium), podium_m2=round(sum(p['A'] for m in meta.values() for p in m.get('podium', []))))
json.dump(rep, open(os.path.join(D6, 'verify_%s.json' % tag), 'w'), indent=1, default=float)
for k in ('schema', 'lawn_test', 'clearance_violations', 'clearance_min_m', 'species_mix', 'tone', 'unresolved_patches'):
    print(k, json.dumps(rep[k], default=float))
print('archviz_design', json.dumps(rep['archviz_design']['totals'], default=float))
print('patches:')
for p in patches:
    print('  ', p['level'], p['area'], 'bed', p['bed'], p['reason'])
print('totals', rep['totals']['instances'], 'trees', rep['totals']['trees'], 'meshes', rep['totals']['meshes'])
print('roles', rep['totals']['roles'])
