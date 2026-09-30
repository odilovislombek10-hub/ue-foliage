"""Geometry helpers on 0.25-m crops: offset contours, edge labelling, runs, vertex-preserving resampling, skeleton."""
import numpy as np, cv2
from lsite import PX

EDGE_NAMES = ('bld', 'road', 'pave', 'play', 'cut')


def offset_contours(bed, d):
    """closed contours of {dt >= d}; each as float (N,2) array of crop (row, col) pixel-centre coords"""
    mask = (bed.dt >= d).astype(np.uint8)
    cnts, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cnts:
        if len(c) < 8:
            continue
        p = c[:, 0, ::-1].astype(np.float64) + 0.5
        out.append(p)
    return out


def edge_labels(bed, pts, d, smooth=9):
    """label each contour point by what lies just beyond the bed edge (0 bld,1 road,2 pave,3 play,4 cut/none)"""
    i = np.clip(pts[:, 0].astype(int), 0, bed.m.shape[0] - 1)
    j = np.clip(pts[:, 1].astype(int), 0, bed.m.shape[1] - 1)
    D = np.stack([bed.d_bld[i, j], bed.d_road[i, j], bed.d_pave[i, j], bed.d_play[i, j], bed.d_cut[i, j]], 1)
    lab = D.argmin(1)
    lab[D.min(1) > d + 1.75] = 4
    if smooth and len(lab) > smooth:
        n = len(lab); h = smooth // 2
        idx = (np.arange(n)[:, None] + np.arange(-h, h + 1)[None, :]) % n
        votes = np.stack([(lab[idx] == k).sum(1) for k in range(5)], 1)
        lab = votes.argmax(1)
    return lab


def runs(mask_bool):
    """contiguous True runs of a circular boolean array -> list of index arrays (in order)"""
    n = len(mask_bool)
    if mask_bool.all():
        return [np.arange(n)], True
    if not mask_bool.any():
        return [], False
    start = int(np.argmin(mask_bool))  # a False position
    order = (np.arange(n) + start) % n
    out, cur = [], []
    for k in order:
        if mask_bool[k]:
            cur.append(k)
        elif cur:
            out.append(np.array(cur)); cur = []
    if cur:
        out.append(np.array(cur))
    return out, False


def arclen(p, closed=False):
    if len(p) < 2:
        return 0.0
    q = np.vstack([p, p[:1]]) if closed else p
    return float(np.sqrt((np.diff(q, axis=0) ** 2).sum(1)).sum()) * PX


def simplify(p, closed, eps=0.7):
    a = cv2.approxPolyDP(p[:, ::-1].astype(np.float32).reshape(-1, 1, 2), eps, closed)[:, 0, ::-1].astype(np.float64)
    if not closed:
        # approxPolyDP keeps the ends for open curves
        pass
    return a


def resample_vertices(v, closed, spacing_m, min_gap_m=None):
    """resample a polyline so every vertex keeps a plant and each segment is split evenly (spacing ~ spacing_m)"""
    sp = spacing_m / PX
    pts, tans = [], []
    V = np.vstack([v, v[:1]]) if closed else v
    for a, b in zip(V[:-1], V[1:]):
        seg = b - a; L = np.hypot(*seg)
        if L < 1e-6:
            continue
        n = max(1, int(round(L / sp)))
        t = seg / L
        for k in range(n):
            pts.append(a + seg * k / n); tans.append(t)
    if not closed:
        pts.append(V[-1]); tans.append(tans[-1] if tans else np.array([0, 1.0]))
    pts, tans = np.array(pts), np.array(tans)
    if min_gap_m and len(pts) > 1:
        keep = [0]
        g = min_gap_m / PX
        for k in range(1, len(pts)):
            if np.hypot(*(pts[k] - pts[keep[-1]])) >= g:
                keep.append(k)
        if closed and len(keep) > 2 and np.hypot(*(pts[keep[-1]] - pts[keep[0]])) < g:
            keep.pop()
        pts, tans = pts[keep], tans[keep]
    return pts, tans


def resample_even(p, closed, spacing_m, offset_m=0.0):
    """points every spacing_m along a dense polyline (no vertex preservation) + unit tangents"""
    q = np.vstack([p, p[:1]]) if closed else p
    seg = np.diff(q, axis=0); L = np.hypot(seg[:, 0], seg[:, 1])
    s = np.concatenate([[0], np.cumsum(L)]) * PX
    tot = s[-1]
    if tot < 1e-6:
        return np.zeros((0, 2)), np.zeros((0, 2))
    ts = np.arange(offset_m, tot + 1e-6, spacing_m)
    out, tan = [], []
    for t in ts:
        k = min(np.searchsorted(s, t, side='right') - 1, len(seg) - 1)
        f = (t - s[k]) / max(s[k + 1] - s[k], 1e-9)
        out.append(q[k] + f * seg[k]); tan.append(seg[k] / max(L[k], 1e-9))
    return np.array(out), np.array(tan)


def zhang_suen(img, max_iter=48):
    img = (img > 0).astype(np.uint8).copy()
    for _ in range(max_iter):
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1)
            p2, p3, p4 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:]
            p5, p6, p7 = P[2:, 2:], P[2:, 1:-1], P[2:, :-2]
            p8, p9 = P[1:-1, :-2], P[:-2, :-2]
            seq = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            B = p2.astype(np.int16) + p3 + p4 + p5 + p6 + p7 + p8 + p9
            Acnt = sum(((seq[k] == 0) & (seq[k + 1] == 1)).astype(np.int16) for k in range(8))
            if step == 0:
                c = ((p2 * p4 * p6) == 0) & ((p4 * p6 * p8) == 0)
            else:
                c = ((p2 * p4 * p8) == 0) & ((p2 * p6 * p8) == 0)
            m = (img == 1) & (B >= 2) & (B <= 6) & (Acnt == 1) & c
            if m.any():
                img[m] = 0; changed = True
        if not changed:
            break
    return img.astype(bool)


NB8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def skeleton_branches(sk):
    """split a 1-px skeleton into ordered branches (list of (N,2) int arrays of (row, col))"""
    S = sk.astype(np.uint8)
    nb = cv2.filter2D(S, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT) - S
    nb = nb * S
    node = S.astype(bool) & (nb != 2)
    body = S.astype(bool) & ~node
    n, lab = cv2.connectedComponents(body.astype(np.uint8), connectivity=8)
    branches = []
    H, W = S.shape
    pix = {}
    ys, xs = np.nonzero(body)
    for y, x in zip(ys, xs):
        pix.setdefault(lab[y, x], []).append((y, x))
    for k, pl in pix.items():
        st = set(pl)
        # find an end: a pixel with <= 1 neighbour inside the branch
        start = pl[0]
        for (y, x) in pl:
            c = sum(((y + dy, x + dx) in st) for dy, dx in NB8)
            if c <= 1:
                start = (y, x); break
        order = [start]; seen = {start}
        cur = start
        while True:
            nxt = None
            for dy, dx in NB8:
                q = (cur[0] + dy, cur[1] + dx)
                if q in st and q not in seen:
                    nxt = q; break
            if nxt is None:
                break
            order.append(nxt); seen.add(nxt); cur = nxt
        branches.append(np.array(order))
    return branches


def resample_corners(v, closed, spacing_m, corner_deg=25.0, min_piece_m=0.0):
    """split a simplified polyline at true corners (turn > corner_deg); every corner gets a plant and each
    straight/curved piece between corners is divided evenly (spacing within a few % of spacing_m)."""
    v = np.asarray(v, float)
    n = len(v)
    if n < 2:
        return v, np.zeros_like(v)
    if closed:
        a = v - np.roll(v, 1, 0); b = np.roll(v, -1, 0) - v
    else:
        a = np.vstack([v[1:2] - v[0:1], v[1:-1] - v[:-2], v[-1:] - v[-2:-1]])
        b = np.vstack([v[1:2] - v[0:1], v[2:] - v[1:-1], v[-1:] - v[-2:-1]])
    ang = np.degrees(np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1))))
    corner = ang > corner_deg
    if not closed:
        corner[0] = corner[-1] = True
    idx = np.nonzero(corner)[0]
    pts, tans = [], []
    if len(idx) == 0:  # smooth closed loop
        p, t = resample_even(v, True, spacing_m)
        L = arclen(v, True); k = max(3, int(round(L / spacing_m)))
        p, t = resample_even(v, True, L / k)
        return _dedupe(p[:k], t[:k], True, 0.6 * spacing_m)
    pieces = []
    for q in range(len(idx) if closed else len(idx) - 1):
        s, e = idx[q], idx[(q + 1) % len(idx)]
        if closed and e <= s:
            piece = np.vstack([v[s:], v[:e + 1]])
        else:
            piece = v[s:e + 1]
        pieces.append(piece)
    for piece in pieces:
        L = arclen(piece)
        if L < 1e-6:
            continue
        k = max(1, int(round(L / spacing_m)))
        p, t = resample_even(piece, False, L / k)
        p, t = p[:k], t[:k]          # drop the end point (it is the next piece's start corner)
        pts += list(p); tans += list(t)
    if not closed:
        pts.append(v[-1]); tans.append(tans[-1] if tans else np.array([0, 1.0]))
    return _dedupe(np.array(pts), np.array(tans), closed, 0.6 * spacing_m)


def _dedupe(pts, tans, closed, gap_m):
    if len(pts) < 2:
        return pts, tans
    g = gap_m / PX
    keep = [0]
    for k in range(1, len(pts)):
        if np.hypot(*(pts[k] - pts[keep[-1]])) >= g:
            keep.append(k)
    if closed and len(keep) > 2 and np.hypot(*(pts[keep[-1]] - pts[keep[0]])) < g:
        keep.pop()
    return pts[keep], tans[keep]
