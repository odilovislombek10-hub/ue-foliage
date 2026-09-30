"""STEP 2b (offline): lawn islands -> geometry stats, context, type, and the per-point tree-size field.

Usage:  python 02_zones.py
Inputs  (work dir, from ue/01 + ue/02): label025.npy, grid.json, islands_raw.json, cls1.npy
Outputs (work dir):
  cls1_fixed.npy   cls1 with thin "playground" strips (bike lanes, < bike_lane_open_m wide) turned into paving
  islands.json     per island: area, perimeter, mean/max width, compactness, centre, hidden flag, distance to
                   building/playground/road, ring shares (paving/road/playground/tall), type (D parterre,
                   C narrow strip, G general lawn, X tiny, - hidden)
  size1.npy        uint8 1 m grid: largest plant class allowed per lawn cell (4 large tree, 3 medium, 2 small,
                   1 shrub, 0 none) - used for lawn masks and the lot maps
  size_full.png    colour map of size1 (check it: big trees only in wide lawns far from facades/playgrounds)
Origin: zones.py stats + call #127 (bike lanes) + zones2.context/classify + zones3.retype/size_field.
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json  # noqa: E402
from collections import Counter  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

GRASS, ROAD, PAVE, PLAY, WATER, TALL, LOW, OTHER = 1, 2, 3, 4, 5, 6, 7, 8
# zones2 thresholds (metres) - tuned with the client on the first map
B_BUILD, B_PLAY = 15.0, 10.0
MIN_AREA = 3.0
# zones3: size class -> (min dist to lawn edge, to building, to playground), metres
SIZE_RULES = {4: (4.0, 12.0, 6.0), 3: (2.5, 7.0, 5.0), 2: (1.2, 5.0, 1.5), 1: (0.4, 1.5, 0.5)}
# parterre (formal plaza lawns): fully paved ring, no playground, many small islands close together
D_RING_PAVE, D_MAX_AREA, D_MAX_W, D_NEIGH, D_RADIUS = 0.8, 800.0, 14.0, 8, 60.0
C_MEAN_W = 4.0


def stats(label, isl, grid):
    """per-island geometry from the raster (zones.stats)"""
    RES = grid['res']
    objs = ndimage.find_objects(label)
    for i, d in enumerate(isl):
        sl = objs[i] if i < len(objs) else None
        if sl is None:
            d.update(area=0.0, hidden=True); continue
        m = (label[sl] == i + 1).astype(np.uint8)
        m = np.pad(m, 1)
        area = float(m.sum() * RES * RES / 1e4)
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        per = float(sum(cv2.arcLength(cc, True) for cc in cnts) * RES / 100)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        maxw = float(dt.max() * 2 * RES / 100)
        rect = cv2.minAreaRect(np.vstack(cnts)) if cnts else ((0, 0), (0, 0), 0)
        (rw, rh) = rect[1]
        ys, xs = np.nonzero(m)
        cx = grid['x0'] + (sl[1].start - 1 + xs.mean()) * RES
        cy = grid['y0'] + (sl[0].start - 1 + ys.mean()) * RES
        d.update(area=round(area, 1), perim=round(per, 1),
                 mean_w=round(2 * area / per, 2) if per > 0 else 0,
                 max_w=round(maxw, 2), compact=round(4 * np.pi * area / per ** 2, 3) if per > 0 else 0,
                 rect=[round(max(rw, rh) * RES / 100, 1), round(min(rw, rh) * RES / 100, 1)],
                 cx=round(float(cx)), cy=round(float(cy)),
                 hidden=area < 0.5 * d['area_mesh'])


def fix_bike_lanes(R0):
    """thin playground-coloured strips (bike lanes) -> paving; real playgrounds survive a morphological opening"""
    k = int(env.CFG.get('bike_lane_open_m', 4))
    play = (R0 == PLAY).astype(np.uint8)
    real = cv2.morphologyEx(play, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))) > 0
    lanes = (play > 0) & ~real
    R2 = R0.copy(); R2[lanes] = PAVE
    return R2, int(lanes.sum()), int(real.sum())


def dist_to(R, c):
    return cv2.distanceTransform((R != c).astype(np.uint8), cv2.DIST_L2, 5)   # metres (1 m grid)


def context(Z):
    """island context in a 3 m ring + distances (zones2.context)"""
    label, isl, R = Z['label'], Z['isl'], Z['cls1']
    objs = ndimage.find_objects(label)
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    H1, W1 = R.shape
    for i, d in enumerate(isl):
        sl = objs[i] if i < len(objs) else None
        if sl is None or d.get('hidden') or d.get('area', 0) <= 0:
            d['type'] = '-'; continue
        pad = 16
        y0, y1 = max(sl[0].start - pad, 0), min(sl[0].stop + pad, label.shape[0])
        x0, x1 = max(sl[1].start - pad, 0), min(sl[1].stop + pad, label.shape[1])
        m = (label[y0:y1, x0:x1] == i + 1).astype(np.uint8)
        ys, xs = np.nonzero(m)
        Y1, X1 = np.clip((ys + y0) // 4, 0, H1 - 1), np.clip((xs + x0) // 4, 0, W1 - 1)
        db = Z['d_build'][Y1, X1]; dp = Z['d_play'][Y1, X1]; dr = Z['d_road'][Y1, X1]
        ring = cv2.dilate(m, k5) & (1 - cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))))
        ry, rx = np.nonzero(ring)
        rc = R[np.clip((ry + y0) // 4, 0, H1 - 1), np.clip((rx + x0) // 4, 0, W1 - 1)]
        rc = rc[rc != GRASS]
        tot = max(len(rc), 1)
        d.update(d_build=round(float(db.min()), 1), near_build_frac=round(float((db < B_BUILD).mean()), 2),
                 d_play=round(float(dp.min()), 1), d_road=round(float(dr.min()), 1),
                 ring_pave=round(float(np.isin(rc, [PAVE]).sum() / tot), 2),
                 ring_road=round(float(np.isin(rc, [ROAD]).sum() / tot), 2),
                 ring_play=round(float(np.isin(rc, [PLAY]).sum() / tot), 2),
                 ring_tall=round(float(np.isin(rc, [TALL]).sum() / tot), 2))
        d['type'] = 'X' if d['area'] < MIN_AREA else 'M'


def retype(isl):
    """zones3.retype: D parterre / C narrow strip / G general lawn (size decided per point)"""
    for d in isl:
        d.pop('parter_neigh', None)
    cand = [i for i, d in enumerate(isl) if d.get('type') not in ('-', None) and d.get('area', 0) <= D_MAX_AREA
            and d.get('max_w', 99) <= D_MAX_W and d.get('ring_pave', 0) >= D_RING_PAVE and d.get('ring_play', 0) == 0]
    if cand:
        Cc = np.array([[isl[i]['cx'], isl[i]['cy']] for i in cand]) / 100
        n = cKDTree(Cc).query_ball_point(Cc, D_RADIUS, return_length=True)
        for i, k in zip(cand, n):
            isl[i]['parter_neigh'] = int(k) - 1
    for d in isl:
        t = d.get('type')
        if t in ('-', None, 'X'):
            continue
        if d.get('parter_neigh', 0) >= D_NEIGH:
            d['type'] = 'D'
        elif d['mean_w'] < C_MEAN_W:
            d['type'] = 'C'
        else:
            d['type'] = 'G'
    return dict(Counter(d.get('type') for d in isl))


def size_field(Z):
    H1, W1 = Z['cls1'].shape
    S = np.zeros((H1, W1), np.uint8)
    for k in (1, 2, 3, 4):
        e, b, p = SIZE_RULES[k]
        S[(Z['d_edge1'] >= e) & (Z['d_build'] >= b) & (Z['d_play'] >= p)] = k
    tl = np.array(['-'] + [d.get('type', '-') for d in Z['isl']])
    t = tl[Z['lab4']]
    S[(t == 'D') & (S > 3)] = 3          # parterre: medium and small trees
    S[(t == 'C') & (S > 2)] = 2          # narrow strips: small trees only
    m = (t == '-') | (t == 'X')
    S[m] = np.minimum(S[m], 1)
    S[Z['lab4'] == 0] = 0
    return S


SCOL = {1: (60, 160, 240), 2: (120, 230, 150), 3: (40, 170, 60), 4: (20, 90, 20)}  # BGR


def render(R, S, lab4, path):
    img = np.full(R.shape + (3,), 30, np.uint8)
    img[R == ROAD] = (70, 70, 70); img[R == PAVE] = (150, 150, 150)
    img[R == PLAY] = (150, 110, 240); img[R == TALL] = (235, 235, 235); img[R == WATER] = (200, 120, 40)
    img[lab4 > 0] = (40, 40, 110)
    for k, col in SCOL.items():
        img[S == k] = col
    items = [((20, 90, 20), 'Katta daraxt (12-21 m)'), ((40, 170, 60), 'Orta daraxt (6-10 m)'),
             ((120, 230, 150), 'Kichik daraxt (3-5.5 m)'), ((60, 160, 240), 'Buta / gul'),
             ((40, 40, 110), 'Maysa, ekilmaydi'), ((150, 110, 240), 'Bolalar maydonchasi'), ((235, 235, 235), 'Bino')]
    s = max(1.0, img.shape[1] / 2000)
    y = int(20 * s); h = int(26 * s)
    cv2.rectangle(img, (10, 8), (int(340 * s), int(20 * s) + h * len(items)), (20, 20, 20), -1)
    for col, txt in items:
        cv2.rectangle(img, (18, y), (18 + int(22 * s), y + int(16 * s)), col, -1)
        cv2.putText(img, txt, (int(50 * s), y + int(14 * s)), cv2.FONT_HERSHEY_SIMPLEX, 0.55 * s, (240, 240, 240),
                    max(1, int(s)), cv2.LINE_AA)
        y += h
    cv2.imwrite(path, img)


def main():
    J = env.W
    grid = json.load(open(J('grid.json')))
    label = np.load(J('label025.npy'))
    isl = json.load(open(J('islands_raw.json')))
    R0 = np.load(J('cls1.npy'))
    stats(label, isl, grid)
    R, nl, nr = fix_bike_lanes(R0)
    np.save(J('cls1_fixed.npy'), R)
    H1, W1 = R.shape
    Z = dict(label=label, isl=isl, cls1=R)
    Z['d_build'], Z['d_play'], Z['d_road'] = dist_to(R, TALL), dist_to(R, PLAY), dist_to(R, ROAD)
    context(Z)
    types = retype(isl)
    g = (label > 0).astype(np.uint8)
    Z['d_edge1'] = (cv2.distanceTransform(g, cv2.DIST_L2, 5)[::4, ::4] * 0.25)[:H1, :W1]
    Z['lab4'] = label[::4, ::4][:H1, :W1]
    S = size_field(Z)
    np.save(J('size1.npy'), S)
    json.dump(isl, open(J('islands.json'), 'w'), indent=0)
    render(R, S, Z['lab4'], J('size_full.png'))
    u, c = np.unique(S[Z['lab4'] > 0], return_counts=True)
    print(json.dumps(dict(islands=len(isl), types=types, bike_lane_cells=nl, playground_cells=nr,
                          size_ha={int(a): round(int(b) / 1e4, 2) for a, b in zip(u, c)}), indent=1))
    print('written', J('cls1_fixed.npy'), J('islands.json'), J('size1.npy'), J('size_full.png'))


if __name__ == '__main__':
    main()
