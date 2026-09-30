"""Automatic split of large road-closed blocks (KV_*) into lot proposals.

lanes()      (default, used on Zaliniy): cut a block along internal lanes that cross its whole width
             (>= 85 % hard surface across the section, >= 4 m wide); parts need >= 8000 m2 and >= 80 m2 of building.
complexes()  alternative: buildings closer than LINK m without a >= LANE m hard-surface run between them form one
             complex (one courtyard composition = one lot).
split_kv()   alternative: recursive split along through-lanes until parts are <= TARGET_MAX m2.
All work on the 1 m class raster R (cls1_fixed) and a group raster G with names {id: name}; only names starting
with 'KV' are split. Return (G3, names3, report). Origin: lanes.py / complexes.py / split_kv.py of the Zaliniy session.
"""
import cv2
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROAD, PAVE, TALL = 2, 3, 6


# ------------------------------------------------------------------ lanes (default)
THROUGH = 0.85     # share of the block's cross-section covered by hard surface
MIN_W = 4          # m: lane width
MIN_PART = 8000    # m2 site area; smaller parts merge into a neighbour
MIN_BLD = 80


def _lane_cuts(mr, hr, axis):
    width = mr.sum(axis=axis).astype(np.float32)
    hw = (mr & hr).sum(axis=axis).astype(np.float32)
    ok = (width > 20) & (hw / np.maximum(width, 1) >= THROUGH)
    cuts = []; i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j + 1 < len(ok) and ok[j + 1]:
                j += 1
            if j - i + 1 >= MIN_W:
                cuts.append((i, j))
            i = j + 1
        else:
            i += 1
    return cuts


def lanes(R, G, names):
    hard = np.isin(R, [ROAD, PAVE])
    bld = (R == TALL)
    G3 = G.copy(); nxt = int(G.max()) + 1; out = dict(names); rep = {}
    for gid, nm in names.items():
        if not nm.startswith('KV'):
            continue
        blk_all = (G == gid)
        blk = blk_all & (R != 0)
        if blk.sum() < 2 * MIN_PART:
            continue
        ys, xs = np.nonzero(blk)
        pad = 10
        y0, y1 = max(ys.min() - pad, 0), min(ys.max() + 1 + pad, R.shape[0])
        x0, x1 = max(xs.min() - pad, 0), min(xs.max() + 1 + pad, R.shape[1])
        mc = blk[y0:y1, x0:x1].astype(np.uint8)
        (cx, cy), (rw, rh), ang = cv2.minAreaRect(np.stack(np.nonzero(mc)[::-1], 1).astype(np.float32))
        if ang > 45:
            ang -= 90
        h, w = mc.shape; D = int(np.ceil(np.hypot(h, w))) + 4
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0); M[0, 2] += (D - w) / 2; M[1, 2] += (D - h) / 2
        rot = lambda a: cv2.warpAffine(a.astype(np.uint8), M, (D, D), flags=cv2.INTER_NEAREST).astype(bool)  # noqa: E731
        mr, hr, br = rot(mc), rot(hard[y0:y1, x0:x1]), rot(bld[y0:y1, x0:x1])
        vc = _lane_cuts(mr, hr, 0); hc = _lane_cuts(mr, hr, 1)
        cutmask = np.zeros_like(mr)
        for a, b in vc:
            cutmask[:, a:b + 1] = True
        for a, b in hc:
            cutmask[a:b + 1, :] = True
        free = (mr & ~cutmask).astype(np.uint8)
        n, cl, st, _ = cv2.connectedComponentsWithStats(free, 4)
        parts = [i for i in range(1, n) if st[i, 4] >= MIN_PART and (br & (cl == i)).sum() >= MIN_BLD]
        if len(parts) <= 1:
            rep[nm] = 1; continue
        seed = np.zeros((D, D), np.int32)
        for k, i in enumerate(parts):
            seed[cl == i] = k + 1
        _, idx = cv2.distanceTransformWithLabels((seed == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        yy, xx = np.nonzero(seed > 0); lut = np.zeros(idx.max() + 1, np.int32); lut[1:] = seed[yy, xx][:idx.max()]
        full = lut[idx]
        Mi = cv2.invertAffineTransform(M)
        back = cv2.warpAffine(full.astype(np.float32), Mi, (w, h), flags=cv2.INTER_NEAREST).astype(np.int32)
        ba = blk_all[y0:y1, x0:x1]
        if (ba & (back == 0)).any():
            _, idx2 = cv2.distanceTransformWithLabels((back == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
            yy, xx = np.nonzero(back > 0); lut2 = np.zeros(idx2.max() + 1, np.int32); lut2[1:] = back[yy, xx][:idx2.max()]
            back = np.where(back > 0, back, lut2[idx2])
        order = sorted(range(1, len(parts) + 1),
                       key=lambda c: float(np.nonzero(ba & (back == c))[1].mean()) if (ba & (back == c)).any() else 1e9)
        sub = G3[y0:y1, x0:x1]
        for r_, c in enumerate(order):
            if r_ == 0:
                out[gid] = f'{nm}_1'; continue
            sub[ba & (back == c)] = nxt; out[nxt] = f'{nm}_{r_ + 1}'; nxt += 1
        rep[nm] = len(parts)
    return G3, out, {k: v for k, v in rep.items() if v > 1}


# ------------------------------------------------------------------ complexes (alternative)
LINK = 35.0        # m: max gap between buildings of one composition
LANE = 7           # m: a continuous hard-surface run this long between them = separate complexes
MIN_BLD_C = 80     # m2: smaller tall objects are not buildings


def _longest_run(vals):
    best = cur = 0
    for v in vals:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


def complexes(R, G, names, link=LINK, lane=LANE):
    hard = np.isin(R, [ROAD, PAVE])
    n, bl, st, cen = cv2.connectedComponentsWithStats((R == TALL).astype(np.uint8), 8)
    G3 = G.copy(); nxt = int(G.max()) + 1; out = dict(names); rep = {}
    for gid, nm in names.items():
        if not nm.startswith('KV'):
            continue
        blk = (G == gid) & (R != 0)
        ids = [i for i in np.unique(bl[blk]) if i > 0 and st[i, 4] >= MIN_BLD_C]
        ids = [i for i in ids if (blk & (bl == i)).sum() >= 0.5 * st[i, 4]]
        if len(ids) <= 1:
            rep[nm] = len(ids); continue
        pts = {}
        for i in ids:
            c, _ = cv2.findContours((bl == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            p = np.vstack(c).reshape(-1, 2)
            pts[i] = p[::max(1, len(p) // 60)].astype(np.float32)
        rows, cols = [], []
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                A_, B_ = pts[ids[a]], pts[ids[b]]
                d2 = ((A_[:, None, :] - B_[None, :, :]) ** 2).sum(-1)
                k = np.unravel_index(np.argmin(d2), d2.shape)
                if float(np.sqrt(d2[k])) > link:
                    continue
                p0, p1 = A_[k[0]], B_[k[1]]
                L = int(max(abs(p1 - p0))) + 1
                xs = np.linspace(p0[0], p1[0], L).round().astype(int)
                ys = np.linspace(p0[1], p1[1], L).round().astype(int)
                if _longest_run(hard[ys, xs]) >= lane:
                    continue
                rows.append(a); cols.append(b)
        m = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(ids), len(ids)))
        nc, lab = connected_components(m, directed=False)
        rep[nm] = int(nc)
        if nc <= 1:
            continue
        seed = np.zeros(R.shape, np.int32)
        for j, i in enumerate(ids):
            seed[bl == i] = lab[j] + 1
        ys, xs = np.nonzero(blk)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        sd = seed[y0:y1, x0:x1]; bb = blk[y0:y1, x0:x1]
        _, idx = cv2.distanceTransformWithLabels((sd == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        yy, xx = np.nonzero(sd > 0); lut = np.zeros(idx.max() + 1, np.int32); lut[1:] = sd[yy, xx][:idx.max()]
        near = lut[idx]
        sub = G3[y0:y1, x0:x1]
        blk_all = (G[y0:y1, x0:x1] == gid)
        order = sorted(range(1, nc + 1),
                       key=lambda c: float(np.nonzero((near == c) & bb)[1].mean()) if ((near == c) & bb).any() else 1e9)
        for r_, c in enumerate(order):
            sel = blk_all & (near == c)
            if r_ == 0:
                out[gid] = f'{nm}_1'; continue
            sub[sel] = nxt; out[nxt] = f'{nm}_{r_ + 1}'; nxt += 1
    return G3, out, {k: v for k, v in rep.items() if v > 1}


# ------------------------------------------------------------------ split_kv (alternative)
TARGET_MAX = 60000   # m2 of site area: split while bigger
MIN_PART_KV = 20000  # m2: each part at least this big
THROUGH_KV = 0.8


def _candidates(mask, hard, axis):
    m = mask.astype(bool)
    width = m.sum(axis=axis).astype(np.float32)
    hw = (m & hard).sum(axis=axis).astype(np.float32)
    frac = np.where(width > 10, hw / np.maximum(width, 1), 0)
    ok = frac >= THROUGH_KV
    runs = []; i = 0
    while i < len(ok):
        if ok[i]:
            j = i
            while j + 1 < len(ok) and ok[j + 1]:
                j += 1
            runs.append(((i + j) / 2.0, j - i + 1))
            i = j + 1
        else:
            i += 1
    return runs


def _split_mask(mask, hard, depth=0):
    area = int(mask.sum())
    if area <= TARGET_MAX or depth > 6:
        return [mask]
    best = None
    ys, xs = np.nonzero(mask)
    for axis in (0, 1):
        coord = xs if axis == 0 else ys
        lo, hi = coord.min(), coord.max(); mid = (lo + hi) / 2
        for pos, wid in _candidates(mask, hard, axis):
            a = int((mask[:, :int(pos)] if axis == 0 else mask[:int(pos), :]).sum()); b = area - a
            if a < MIN_PART_KV or b < MIN_PART_KV:
                continue
            score = abs(pos - mid) / max(hi - lo, 1) - 0.002 * wid
            if best is None or score < best[0]:
                best = (score, axis, pos)
    if best is None:
        return [mask]
    _, axis, pos = best
    p = int(round(pos))
    m1 = mask.copy(); m2 = mask.copy()
    if axis == 0:
        m1[:, p:] = False; m2[:, :p] = False
    else:
        m1[p:, :] = False; m2[:p, :] = False
    return _split_mask(m1, hard, depth + 1) + _split_mask(m2, hard, depth + 1)


def split_kv(R, G, names):
    hardall = np.isin(R, [ROAD, PAVE])
    G2 = G.copy(); nxt = G.max() + 1; newnames = dict(names); report = {}
    for gid, nm in names.items():
        if not nm.startswith('KV'):
            continue
        m = (G == gid) & (R != 0)
        if m.sum() <= TARGET_MAX:
            continue
        ys, xs = np.nonzero(m)
        pad = 20
        y0p, x0p = max(ys.min() - pad, 0), max(xs.min() - pad, 0)
        y1p, x1p = min(ys.max() + 1 + pad, R.shape[0]), min(xs.max() + 1 + pad, R.shape[1])
        mc = m[y0p:y1p, x0p:x1p].astype(np.uint8); hc = hardall[y0p:y1p, x0p:x1p].astype(np.uint8)
        ys2, xs2 = np.nonzero(mc)
        (_, _), (_, _), ang = cv2.minAreaRect(np.stack([xs2, ys2], 1).astype(np.float32))
        if ang > 45:
            ang -= 90
        h, w = mc.shape; D = int(np.ceil(np.hypot(h, w))) + 4
        M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0); M[0, 2] += (D - w) / 2; M[1, 2] += (D - h) / 2
        mr = cv2.warpAffine(mc, M, (D, D), flags=cv2.INTER_NEAREST).astype(bool)
        hr = cv2.warpAffine(hc, M, (D, D), flags=cv2.INTER_NEAREST).astype(bool)
        parts = _split_mask(mr, hr)
        report[nm] = len(parts)
        if len(parts) <= 1:
            continue
        Mi = cv2.invertAffineTransform(M)
        lab = np.zeros((D, D), np.int32)
        for i, pm in enumerate(parts):
            lab[pm] = i + 1
        back = cv2.warpAffine(lab.astype(np.float32), Mi, (w, h), flags=cv2.INTER_NEAREST).astype(np.int32)
        blk = mc.astype(bool)
        miss = blk & (back == 0)
        if miss.any():
            _, idx = cv2.distanceTransformWithLabels((back == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
            yy, xx = np.nonzero(back > 0); lut = np.zeros(idx.max() + 1, np.int32); lut[1:] = back[yy, xx][:idx.max()]
            back[miss] = lut[idx[miss]]
        sub = G2[y0p:y1p, x0p:x1p]
        for i in range(1, len(parts) + 1):
            sel = blk & (back == i)
            if i == 1:
                newnames[gid] = f'{nm}_1'; continue
            sub[sel] = nxt; newnames[nxt] = f'{nm}_{i}'; nxt += 1
    return G2, newnames, {k: v for k, v in report.items() if v > 1}
