"""STEP 3 (offline, OPTIONAL): register lots drawn in a PDF master plan onto the UE site raster.

Skip this step if there is no plan: 04_lots.py then proposes lots from the road network only.
Sub-commands (run in order, look at every PNG before going on):
  python 03_plan_register.py render    PDF page clip -> work/plan/plan.png           (config.plan_pdf.pdf/page/clip_rel/zoom)
  python 03_plan_register.py regions   lot outlines (lot_line_hsv) -> regions + label boxes (label_box_hsv)
                                       -> plan/lot_lab.npy, lot_regs.json, lot_boxes.png (numbered label boxes),
                                          lot_regions.png
  (manual)  read lot_boxes.png, write work/plan/plan_labels.json:
            {"box_to_lot": {"0": "7", "1": "40", ...}, "lot_area_m2": {"7": 5777, ...}}   (areas optional)
            example: data/examples/plan_labels.zaliniy.json
  python 03_plan_register.py label     -> plan/lot_lab2.npy, reg2lot.json, scale check against lot_area_m2
  python 03_plan_register.py compare   -> plan/compare.png (UE classes on top, plan scaled to 1 px = 1 m below);
                                          pick one landmark visible in both and set config.plan_pdf.anchor_plan_px
                                          (plan.png pixel, full resolution) and anchor_ue_px (cls1 1 m grid pixel)
  python 03_plan_register.py align     road-mask chamfer fit (rotation +-6 deg, scale +-3 %, shift +-80 m, refined)
                                       -> work/plan2ue_affine.npy, work/lotUE.npy (1 m grid lot ids), work/reg2lot.json,
                                          plan/overlay_lots.png, plan/overlay_roads.png  (lot edges must sit on roads)
Origin: Zaliniy calls #191-#212, #217 (birlashgani2.pdf).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

PC = env.CFG['plan_pdf']
P = lambda n: env.W('plan', n)  # noqa: E731


def cmd_render():
    import pymupdf
    d = pymupdf.open(PC['pdf'])
    p = d[int(PC['page'])]
    Wp, Hp = p.rect.width, p.rect.height
    a, b, c, e = PC['clip_rel']
    clip = pymupdf.Rect(Wp * a, Hp * b, Wp * c, Hp * e)
    z = float(PC['zoom'])
    pix = p.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip)
    pix.save(P('plan.png'))
    im = cv2.imread(P('plan.png'))
    cv2.imwrite(P('plan_small.png'), cv2.resize(im, None, fx=0.2, fy=0.2, interpolation=cv2.INTER_AREA))
    print('plan.png', pix.width, pix.height)


def cmd_regions():
    im = cv2.imread(P('plan.png'))
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    lo, hi = PC['lot_line_hsv']
    g = cv2.inRange(hsv, tuple(lo), tuple(hi))
    ylo, yhi = PC['label_box_hsv']
    y = cv2.inRange(hsv, tuple(ylo), tuple(yhi))
    g2 = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    g2 = cv2.dilate(g2, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    free = (g2 == 0).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(free, 4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())
    regs = [i for i in range(1, n) if i not in border and st[i, 4] > 3000]
    ny, ly, sy, cy = cv2.connectedComponentsWithStats(y, 8)
    boxes = [(int(sy[i, 0]), int(sy[i, 1]), int(sy[i, 2]), int(sy[i, 3])) for i in range(1, ny)
             if sy[i, 4] > 600 and 50 < sy[i, 2] < 400 and 30 < sy[i, 3] < 200]
    np.save(P('lot_lab.npy'), lab)
    json.dump(dict(regs=regs, areas={int(i): int(st[i, 4]) for i in regs}, boxes=boxes), open(P('lot_regs.json'), 'w'))
    vis = im.copy(); vis[g2 > 0] = (0, 0, 255)
    rng = np.random.default_rng(3); col = np.zeros((n, 3), np.uint8)
    for i in regs:
        col[i] = rng.integers(60, 255, 3)
    m = np.isin(lab, regs); vis[m] = (vis[m] * 0.4 + col[lab[m]] * 0.6).astype(np.uint8)
    for (bx, by, bw, bh) in boxes:
        cv2.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 0, 0), 3)
    cv2.imwrite(P('lot_regions.png'), cv2.resize(vis, None, fx=0.18, fy=0.18, interpolation=cv2.INTER_AREA))
    tiles, info = [], []
    for k, (x, yy, w, h) in enumerate(boxes):
        crop = cv2.resize(im[yy:yy + h, x:x + w], (260, max(1, int(260 * h / w))))
        t = np.full((140, 300, 3), 255, np.uint8); hh = min(crop.shape[0], 110); t[28:28 + hh, 20:280] = crop[:hh]
        cv2.putText(t, '#%d' % k, (4, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        tiles.append(t)
        info.append(dict(k=k, region=int(lab[yy + h // 2, x + w // 2]), cx=x + w // 2, cy=yy + h // 2))
    cols = 6; rows = max(1, (len(tiles) + cols - 1) // cols)
    sheet = np.full((rows * 140, cols * 300, 3), 255, np.uint8)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols); sheet[r * 140:(r + 1) * 140, c * 300:(c + 1) * 300] = t
    cv2.imwrite(P('lot_boxes.png'), sheet)
    json.dump(info, open(P('lot_boxinfo.json'), 'w'))
    print(dict(green_px=int((g > 0).sum()), regions=len(regs), boxes=len(boxes)))
    print('now write', P('plan_labels.json'), '(box index -> lot name, see lot_boxes.png)')


def cmd_label():
    im = cv2.imread(P('plan.png')); lab = np.load(P('lot_lab.npy'))
    R = json.load(open(P('lot_regs.json')))
    L = json.load(open(P('plan_labels.json'), encoding='utf-8'))
    K2LOT = {int(k): v for k, v in L['box_to_lot'].items()}
    info = json.load(open(P('lot_boxinfo.json')))
    reg2lot = {}
    for d in info:
        if d['k'] in K2LOT and d['region'] > 0:
            reg2lot.setdefault(d['region'], []).append((K2LOT[d['k']], d['cx'], d['cy']))
    lab2 = lab.copy(); nid = int(lab.max())
    for r in list(reg2lot):          # one region carrying two labels: split at the x mid-point between them
        l = reg2lot[r]
        if len(l) == 2:
            (a, ax, ay), (b, bx, by) = sorted(l, key=lambda t: t[1]); mid = (ax + bx) // 2
            nid += 1; m = (lab == r); xs = np.arange(lab.shape[1])[None, :]
            lab2[m & (xs >= mid)] = nid
            reg2lot[r] = [(a, ax, ay)]; reg2lot[nid] = [(b, bx, by)]; R['regs'].append(nid)
    unl = [r for r in R['regs'] if r not in reg2lot]
    np.save(P('lot_lab2.npy'), lab2)
    r2l = {str(r): v[0][0] for r, v in reg2lot.items()}
    json.dump(r2l, open(P('reg2lot.json'), 'w'))
    vis = cv2.resize(im, None, fx=0.18, fy=0.18, interpolation=cv2.INTER_AREA)
    small = cv2.resize(lab2, (vis.shape[1], vis.shape[0]), interpolation=cv2.INTER_NEAREST)
    for r in unl:
        vis[small == r] = (0, 0, 255)
    cv2.imwrite(P('lot_unlabeled.png'), vis)
    AREA = L.get('lot_area_m2') or {}
    cnt = np.bincount(lab2.ravel())
    s = [(l, (cnt[int(r)] / AREA[l]) ** 0.5) for r, l in r2l.items() if l in AREA]
    out = dict(labeled=len(reg2lot), unlabeled=[(r, int((lab2 == r).sum())) for r in unl])
    if s:
        v = np.array([x[1] for x in s]); med = float(np.median(v))
        out.update(px_per_m_median=round(med, 3), config_px_per_m=PC['px_per_m'],
                   outliers=[(l, round(x, 2)) for l, x in s if abs(x / med - 1) > 0.12])
    print(json.dumps(out, indent=1))


def _ue_classes():
    return np.load(env.W('cls1_fixed.npy'))


def cmd_compare():
    S = float(PC['px_per_m'])
    R = _ue_classes()
    ue = np.full(R.shape + (3,), 30, np.uint8)
    ue[R == 1] = (60, 140, 60); ue[R == 2] = (90, 90, 90); ue[R == 3] = (160, 160, 160); ue[R == 6] = (255, 255, 255)
    ue[R == 4] = (150, 110, 240); ue[R == 5] = (200, 120, 40)
    pl = cv2.resize(cv2.imread(P('plan.png')), None, fx=1 / S, fy=1 / S, interpolation=cv2.INTER_AREA)
    Wd = max(ue.shape[1], pl.shape[1])
    canvas = np.full((ue.shape[0] + pl.shape[0] + 20, Wd, 3), 255, np.uint8)
    canvas[:ue.shape[0], :ue.shape[1]] = ue
    canvas[ue.shape[0] + 20:, :pl.shape[1]] = pl
    cv2.imwrite(P('compare.png'), cv2.resize(canvas, None, fx=0.6, fy=0.6, interpolation=cv2.INTER_AREA))
    print('compare.png written (top = UE 1 m grid, bottom = plan at 1 px/m). Set anchor_plan_px / anchor_ue_px in config.')


def cmd_align():
    S = float(PC['px_per_m'])
    if not PC.get('anchor_plan_px') or not PC.get('anchor_ue_px'):
        sys.exit('set config.plan_pdf.anchor_plan_px (plan.png px) and anchor_ue_px (1 m grid px) first - see compare')
    im = cv2.imread(P('plan.png'))
    pl = cv2.resize(im, None, fx=1 / S, fy=1 / S, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(pl, cv2.COLOR_BGR2HSV)
    v0, v1 = PC['road_grey_v']
    road = ((hsv[..., 1] < PC['road_grey_s_max']) & (hsv[..., 2] > v0) & (hsv[..., 2] < v1)).astype(np.uint8)
    road = cv2.morphologyEx(road, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))     # thick bands (>= 5 m) only
    lab2 = np.load(P('lot_lab2.npy'))
    lots = cv2.resize((lab2 > 0).astype(np.uint8), (pl.shape[1], pl.shape[0]), interpolation=cv2.INTER_NEAREST)
    road = road * cv2.dilate(lots, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (201, 201)))
    cv2.imwrite(P('plan_road.png'), road * 255)
    R = _ue_classes()
    ur = (R == 2).astype(np.uint8)
    dt = np.minimum(cv2.distanceTransform(1 - ur, cv2.DIST_L2, 5), 30)
    near = cv2.dilate(lots, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41))) > 0
    ys, xs = np.nonzero((road > 0) & near)
    idx = np.random.default_rng(0).choice(len(xs), min(6000, len(xs)), replace=False)
    Pp = np.stack([xs[idx], ys[idx]], 1).astype(np.float64)
    pc = np.array(PC['anchor_plan_px'], float) / S
    uc = np.array(PC['anchor_ue_px'], float)
    H, Wd = dt.shape

    def score(ang, sc, tx, ty):
        a = np.radians(ang); Rm = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]) * sc
        Q = (Pp - pc) @ Rm.T + uc + [tx, ty]
        qi = np.round(Q).astype(int); ok = (qi[:, 0] >= 0) & (qi[:, 0] < Wd) & (qi[:, 1] >= 0) & (qi[:, 1] < H)
        v = np.full(len(Q), 30.0); v[ok] = dt[qi[ok, 1], qi[ok, 0]]
        return v.mean()
    t = time.time(); best = (1e9,)
    for ang in np.arange(-6, 6.01, 0.5):
        for sc in (0.97, 1.0, 1.03):
            for tx in range(-80, 81, 8):
                for ty in range(-80, 81, 8):
                    s_ = score(ang, sc, tx, ty)
                    if s_ < best[0]:
                        best = (s_, ang, sc, tx, ty)
    s0, a0, sc0, tx0, ty0 = best
    for ang in np.arange(a0 - 0.6, a0 + 0.61, 0.1):
        for sc in np.arange(sc0 - 0.02, sc0 + 0.021, 0.005):
            for tx in range(tx0 - 8, tx0 + 9, 2):
                for ty in range(ty0 - 8, ty0 + 9, 2):
                    s_ = score(ang, sc, tx, ty)
                    if s_ < best[0]:
                        best = (s_, ang, sc, tx, ty)
    _, ang, sc, tx, ty = best
    a = np.radians(ang); Rm = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]) * sc
    Mfull = np.zeros((2, 3)); Mfull[:, :2] = Rm / S; Mfull[:, 2] = uc + [tx, ty] - Rm @ pc   # plan full-res px -> UE 1 m px
    r2l = json.load(open(P('reg2lot.json')))
    keep = np.zeros(lab2.max() + 1, np.int32)
    for r in r2l:
        keep[int(r)] = int(r)
    lab3 = keep[lab2]
    lotUE = cv2.warpAffine(lab3.astype(np.float32), Mfull, (Wd, H), flags=cv2.INTER_NEAREST).astype(np.int32)
    np.save(env.W('lotUE.npy'), lotUE); np.save(env.W('plan2ue_affine.npy'), Mfull)
    json.dump(r2l, open(env.W('reg2lot.json'), 'w'))
    ue = np.full(R.shape + (3,), 30, np.uint8)
    ue[R == 1] = (60, 140, 60); ue[R == 2] = (90, 90, 90); ue[R == 3] = (160, 160, 160); ue[R == 6] = (255, 255, 255)
    ue[R == 4] = (150, 110, 240)
    ed = cv2.morphologyEx(lotUE.astype(np.float32), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    o1 = ue.copy(); o1[ed] = (0, 255, 255)
    Mr = Mfull.copy(); Mr[:, :2] *= S
    rw = cv2.warpAffine(road, Mr, (Wd, H))
    o2 = ue.copy(); o2[rw > 0] = (o2[rw > 0] * 0.4 + np.array([0, 0, 255]) * 0.6).astype(np.uint8)
    cv2.imwrite(P('overlay_lots.png'), o1); cv2.imwrite(P('overlay_roads.png'), o2)
    print(dict(fit_mean_dist_m=round(float(best[0]), 2), baseline=round(float(score(0, 1, 0, 0)), 2),
               angle=round(float(ang), 2), scale=round(float(sc), 3), shift=[int(tx), int(ty)],
               lots=int(len(np.unique(lotUE[lotUE > 0]))), sec=round(time.time() - t, 1)))


if __name__ == '__main__':
    cmds = dict(render=cmd_render, regions=cmd_regions, label=cmd_label, compare=cmd_compare, align=cmd_align)
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(1)
    cmds[sys.argv[1]]()
