"""STEP 4 (offline): lots. Every lot becomes one FOL_ streaming sublevel.

  python 04_lots.py propose      automatic proposal
      * lots from the PDF plan if 03_plan_register.py was run (work/lotUE.npy + reg2lot.json) -> 'LOT_<name>'
      * all other lawn: blocks closed by the road network (asphalt opened by road_open_m, closed by road_close_m)
        -> 'KV_nn' (west -> east); small blocks (< min_kvartal_grass_m2 lawn) merge into the nearest block;
        small blocks mostly inside a plan lot (+15 m) are absorbed by that lot
      * big blocks are split (config.lots.split = lanes | complexes | split_kv) -> 'KV_nn_k'
      Writes group3.npy, group3_names.json, lots_proposed.json (area, lawn, centre of every group),
      lots_proposed.png (labelled map) and, if missing, a lots.json template.
  (manual) edit work/lots.json with the user (who decides which groups belong together and which are stage 1).
  python 04_lots.py apply        lots.json -> group4.npy, group4_names.json, lots_resolved.json, lots_final.png

lots.json format (example: data/examples/lots.zaliniy.json):
  {"merge": [["LOT_20", "LOT_21"], ["LOT_12", "KV_34"], ...],   groups (group3 names) that form one lot;
                                                                  final name = parts joined by '+', 'LOT_' dropped,
                                                                  'KV_' -> 'K' (e.g. '12+K34'); single groups keep
                                                                  their name ('LOT_4')
   "spill_pairs":  [["LOT_38", "LOT_37"], ...]   road-closed blocks where dst has >= 50 % of the lawn and src < 30 %
                                                  are given to dst (fixes plan slivers that spill over a road)
   "absorb_pairs": [["38+38-1", "LOT_37"]]       raw road-split blocks where dst has >= 50 %: every src cell -> dst
   "stage": "auto" | "all" | [final names]       lots to plant now ('auto' = every group containing a plan lot)
   "palettes": {"20+21": "sage", ...}            fresh | sage | deep | blossom (missing stage lots get one automatically,
                                                  cycling west -> east so neighbours differ)
   "parks": ["LOT_128"]}                          public parks: one deliberate glade per large bed is allowed
Origin: Zaliniy calls #213-#239 (kvartals, stage-1 absorb, group1, lanes.py, MERGE list, spill fixes).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

import lotsplit  # noqa: E402

J = env.W
LC = env.CFG['lots']
GROUPS_ORDER = ['deep', 'fresh', 'sage', 'blossom']


def road_net(R):
    road = (R == 2).astype(np.uint8)
    k1, k2 = int(LC['road_open_m']), int(LC['road_close_m'])
    wide = cv2.morphologyEx(road, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k1, k1)))
    return cv2.morphologyEx(wide, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k2, k2)))


def nearest_fill(lab):
    """every 0 cell gets the label of the nearest labelled cell"""
    _, idx = cv2.distanceTransformWithLabels((lab == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(lab > 0)
    lut = np.zeros(idx.max() + 1, np.int32); lut[1:] = lab[ys, xs][:idx.max()]
    return lut[idx]


def render(R, G, names, lawn, path):
    site = (R != 0) & (R != 2)
    img = np.full(R.shape + (3,), 30, np.uint8); img[R == 2] = (70, 70, 70)
    rng = np.random.default_rng(21); pal = np.zeros((G.max() + 1, 3), np.uint8)
    for i in range(1, G.max() + 1):
        pal[i] = rng.integers(60, 235, 3)
    m = site & (G > 0); img[m] = pal[G[m]]
    b = R == 6; img[b] = (img[b].astype(np.int32) * 0.35 + 255 * 0.65).astype(np.uint8)
    ed = cv2.morphologyEx(G.astype(np.float32), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    img[ed & site] = (20, 20, 20)
    for i, nm in names.items():
        ys, xs = np.nonzero((G == i) & site)
        if not len(xs):
            continue
        t = nm.replace('LOT_', '').replace('KV_', 'K'); p = (int(np.median(xs)) - 4 * len(t), int(np.median(ys)) + 5)
        cv2.putText(img, t, p, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, t, p, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    ys, xs = np.nonzero(lawn)
    if len(ys):
        img = img[max(ys.min() - 50, 0):ys.max() + 50, max(xs.min() - 50, 0):xs.max() + 50]
    cv2.imwrite(path, img)
    cv2.imwrite(path.replace('.png', '_small.png'), cv2.resize(img, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))


def propose():
    R = np.load(J('cls1_fixed.npy')); S = np.load(J('size1.npy'))
    H, Wd = R.shape
    have_plan = os.path.exists(J('lotUE.npy')) and os.path.exists(J('reg2lot.json'))
    lotUE = np.load(J('lotUE.npy'))[:H, :Wd] if have_plan else np.zeros(R.shape, np.int32)
    r2l = json.load(open(J('reg2lot.json'))) if have_plan else {}
    g_all = S > 0
    # kvartals: blocks closed by the road network (call #217)
    net = road_net(R)
    free = ((net == 0) & (R != 0) & (lotUE == 0)).astype(np.uint8)
    n, kv, st, cen = cv2.connectedComponentsWithStats(free, 4)
    kvf = nearest_fill(kv)
    g = g_all & (lotUE == 0)
    u, c = np.unique(kvf[g], return_counts=True)
    mn = int(LC['min_kvartal_grass_m2'])
    big = [int(a) for a, b in zip(u, c) if b >= mn and a > 0]
    remap = {}
    if big:
        bc = np.array([cen[b] for b in big])
        for a, b in zip(u, c):
            if a > 0 and b < mn:
                remap[int(a)] = big[int(np.argmin(((bc - cen[a]) ** 2).sum(1)))]
    kvm = kvf.copy()
    for a, b in remap.items():
        kvm[kvf == a] = b
    # small blocks lying mostly inside the plan lots (+15 m) are absorbed by the nearest lot (call #218)
    final_lot = lotUE.copy(); final_kv = kvm.copy(); final_kv[lotUE > 0] = 0; absorbed = []
    if have_plan:
        stage1 = cv2.dilate((lotUE > 0).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))) > 0
        nearlot = nearest_fill(lotUE)
        for k in big:
            m = (kvm == k) & g_all & (lotUE == 0)
            a = int(m.sum())
            if a == 0:
                continue
            if float((m & stage1).sum()) / a > 0.6 and a < 2500:
                sel = (kvm == k) & (lotUE == 0) & (nearlot > 0) & stage1
                final_lot[sel] = nearlot[sel]; final_kv[(kvm == k) & stage1] = 0; absorbed.append(k)
    # group raster: plan lots first, then blocks west -> east (call #219)
    ks = [int(k) for k in np.unique(final_kv[g_all & (final_lot == 0)]) if k > 0]
    cx = {k: float(np.nonzero((final_kv == k) & g_all)[1].mean()) for k in ks}
    order = sorted(ks, key=lambda k: cx[k])
    G = np.zeros(R.shape, np.int32); names = {}; gid = 0
    for l in sorted(np.unique(final_lot[final_lot > 0])):
        gid += 1; G[final_lot == l] = gid; names[gid] = 'LOT_' + r2l.get(str(int(l)), str(int(l)))
    for i, k in enumerate(order):
        gid += 1; G[(final_kv == k) & (final_lot == 0)] = gid; names[gid] = 'KV_%02d' % (i + 1)
    np.save(J('group1.npy'), G); json.dump({str(k): v for k, v in names.items()}, open(J('group1_names.json'), 'w'), indent=0)
    # split big blocks
    method = LC.get('split', 'lanes')
    fn = dict(lanes=lotsplit.lanes, complexes=lotsplit.complexes, split_kv=lotsplit.split_kv)[method]
    G3, names3, rep = fn(R, G, names)
    np.save(J('group3.npy'), G3)
    json.dump({str(k): v for k, v in names3.items()}, open(J('group3_names.json'), 'w'), indent=0)
    grid = json.load(open(J('grid.json'))); r1 = grid['res'] * 4
    rows = []
    for i, nm in sorted(names3.items()):
        m = G3 == i
        if not m.any():
            continue
        ys, xs = np.nonzero(m & g_all) if (m & g_all).any() else np.nonzero(m)
        rows.append(dict(name=nm, site_m2=int((m & (R != 0)).sum()), lawn_m2=int((m & g_all).sum()),
                         x=round(grid['x0'] + (xs.mean() + 0.5) * r1), y=round(grid['y0'] + (ys.mean() + 0.5) * r1)))
    json.dump(rows, open(J('lots_proposed.json'), 'w'), indent=1)
    render(R, G3, names3, g_all, J('lots_proposed.png'))
    if not os.path.exists(J('lots.json')):
        json.dump(dict(merge=[], spill_pairs=[], absorb_pairs=[], stage='auto' if have_plan else 'all',
                       palettes={}, parks=[]), open(J('lots.json'), 'w'), indent=1)
    print(json.dumps(dict(plan_lots=len(set(np.unique(lotUE[lotUE > 0]).tolist())), kvartals=len(order),
                          absorbed_small_blocks=len(absorbed), split=method, split_report=rep, groups=len(rows)), indent=1))
    print('look at', J('lots_proposed.png'), '- then edit', J('lots.json'), 'and run: 04_lots.py apply')


def _blocks(R, raw=False):
    if raw:
        road = (R == 2).astype(np.uint8)
        _, blk = cv2.connectedComponents(((road == 0) & (R != 0)).astype(np.uint8), connectivity=4)
    else:
        _, blk = cv2.connectedComponents(((road_net(R) == 0) & (R != 0)).astype(np.uint8), connectivity=4)
    return blk


def is_stage_auto(v):
    return not v.startswith('KV_') and not re.fullmatch(r'(K[\d_]+\+?)+', v)


def apply():
    R = np.load(J('cls1_fixed.npy')); S = np.load(J('size1.npy'))
    G = np.load(J('group3.npy'))
    n = {int(k): v for k, v in json.load(open(J('group3_names.json'))).items()}
    L = json.load(open(J('lots.json'), encoding='utf-8'))
    inv = {v: k for k, v in n.items()}
    missing = [x for grp in L.get('merge', []) for x in grp if x not in inv]
    if missing:
        sys.exit('unknown group names in lots.json merge: %s (see lots_proposed.json)' % missing)
    lut = np.arange(G.max() + 1); newname = dict(n)
    for grp in L.get('merge', []):
        ids = [inv[x] for x in grp]; t = ids[0]
        for i in ids[1:]:
            lut[i] = t; newname.pop(i, None)
        newname[t] = '+'.join(x.replace('LOT_', '').replace('KV_', 'K') for x in grp) if len(grp) > 1 else grp[0]
    G4 = lut[G]
    byfinal = {v: k for k, v in newname.items()}

    def gidof(nm):
        if nm in byfinal:
            return byfinal[nm]
        if nm in inv:
            return int(lut[inv[nm]])
        sys.exit('unknown name %s' % nm)
    g = S > 0; moved = []
    if L.get('spill_pairs'):
        blk = _blocks(R)
        for src, dst in L['spill_pairs']:
            s, d = gidof(src), gidof(dst)
            for b in np.unique(blk[(G4 == s) & g]):
                if b == 0:
                    continue
                m = (blk == b) & g; tot = m.sum()
                cs = ((G4 == s) & m).sum(); cd = ((G4 == d) & m).sum()
                if cd / tot >= 0.5 and cs / tot < 0.3:
                    G4[(blk == b) & (G4 == s)] = d; moved.append((src, dst, int(cs)))
    if L.get('absorb_pairs'):
        blk = _blocks(R, raw=True)
        for src, dst in L['absorb_pairs']:
            s, d = gidof(src), gidof(dst)
            for b in np.unique(blk[(G4 == d) & g]):
                if b == 0:
                    continue
                m = (blk == b) & g; tot = m.sum(); cd = ((G4 == d) & m).sum(); cs = ((G4 == s) & m).sum()
                if cd / tot >= 0.5 and cs > 0:
                    G4[(blk == b) & (G4 == s)] = d; moved.append((src, dst, int(cs)))
    np.save(J('group4.npy'), G4)
    final = {k: v for k, v in newname.items() if (G4 == k).any()}
    json.dump({str(k): v for k, v in final.items()}, open(J('group4_names.json'), 'w'), indent=0)
    st = L.get('stage', 'auto')
    if st == 'auto':
        stage = [v for v in final.values() if is_stage_auto(v)]
    elif st == 'all':
        stage = list(final.values())
    else:
        stage = list(st)
        bad = [s for s in stage if s not in final.values()]
        if bad:
            sys.exit('stage names not found after merge: %s' % bad)
    pal = dict(L.get('palettes', {}))
    cx = {}
    for k, v in final.items():
        if v in stage and v not in pal:
            xs = np.nonzero((G4 == k) & g)[1]
            cx[v] = float(xs.mean()) if len(xs) else 0.0
    for i, v in enumerate(sorted(cx, key=lambda v: cx[v])):
        pal[v] = GROUPS_ORDER[i % len(GROUPS_ORDER)]
    res = dict(stage=sorted(stage), palettes={k: pal[k] for k in sorted(stage) if k in pal},
               parks=[p for p in L.get('parks', []) if p in stage],
               levels={k: env.lot_level_name(k) for k in sorted(stage)})
    json.dump(res, open(J('lots_resolved.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    render(R, G4, final, g, J('lots_final.png'))
    print(json.dumps(dict(groups=len(final), stage_lots=len(stage), moved=moved, auto_palettes=len(cx)), indent=1))
    print('stage levels:', ', '.join(res['levels'].values()))
    print('look at', J('lots_final.png'))


if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ('propose', 'apply'):
        print(__doc__); sys.exit(1)
    propose() if sys.argv[1] == 'propose' else apply()
