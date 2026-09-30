"""STEP 5 (offline): lawn beds of the stage lots at 0.25 m.

A bed = one connected lawn component (4-connectivity) of label025 inside the stage lots, >= 4 m2.
Usage:  python 05_beds.py
Inputs  (work dir): label025.npy, grid.json, cls1_fixed.npy, group4.npy, group4_names.json, lots_resolved.json
Outputs (work dir): beds_lab025.npy (int32 bed id per 0.25 m pixel, 0 = none)
                    beds_st1.json   [{id, lot, area, maxw, meanw, L, W, ang, cx, cy, r_bld, r_pave, r_road, r_play,
                                      r_lawn}, ...]  (r_* = share of each class in a 1.5 m ring around the bed)
Origin: Zaliniy call #309 (the 'cov' field, which measured an older plan, is dropped).
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json  # noqa: E402

import cv2  # noqa: E402
import numpy as np  # noqa: E402

J = env.W


def main():
    G = np.load(J('group4.npy')); R = np.load(J('cls1_fixed.npy'))
    names = {int(k): v for k, v in json.load(open(J('group4_names.json'))).items()}
    stage = set(json.load(open(J('lots_resolved.json'), encoding='utf-8'))['stage'])
    st1 = [k for k, v in names.items() if v in stage]
    lab = np.load(J('label025.npy'))
    grid = json.load(open(J('grid.json')))
    G4 = cv2.resize(G.astype(np.float32), (lab.shape[1], lab.shape[0]), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    R4 = cv2.resize(R, (lab.shape[1], lab.shape[0]), interpolation=cv2.INTER_NEAREST)
    lawn = ((lab > 0) & np.isin(G4, st1)).astype(np.uint8)
    del lab
    n, bl, st, cen = cv2.connectedComponentsWithStats(lawn, 4)
    beds = []
    for i in range(1, n):
        a = st[i, 4] / 16.0
        if a < 4:
            continue
        x, y, w, h = st[i, :4]; pad = 24
        y0, y1, x0, x1 = max(y - pad, 0), min(y + h + pad, lawn.shape[0]), max(x - pad, 0), min(x + w + pad, lawn.shape[1])
        m = (bl[y0:y1, x0:x1] == i).astype(np.uint8)
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        maxw = float(dt.max()) * 2 / 4
        cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        per = float(sum(cv2.arcLength(c, True) for c in cnts)) / 4
        (rx, ry), (rw, rh), ang = cv2.minAreaRect(np.vstack(cnts))
        ring = cv2.dilate(m, np.ones((13, 13), np.uint8)) - m
        rc = R4[y0:y1, x0:x1][ring > 0]; tot = max(len(rc), 1)
        f = lambda c: round(float((rc == c).sum()) / tot, 2)  # noqa: E731
        gid = int(np.bincount(G4[y0:y1, x0:x1][m > 0]).argmax())
        beds.append(dict(id=i, lot=names[gid], area=round(a, 1), maxw=round(maxw, 1), meanw=round(2 * a / max(per, 1), 1),
                         L=round(float(max(rw, rh)) / 4, 1), W=round(float(min(rw, rh)) / 4, 1), ang=round(float(ang), 1),
                         cx=round(float(grid["x0"] + cen[i][0] * grid["res"])), cy=round(float(grid["y0"] + cen[i][1] * grid["res"])),
                         r_bld=f(6), r_pave=f(3), r_road=f(2), r_play=f(4), r_lawn=f(1)))
    json.dump(beds, open(J('beds_st1.json'), 'w'))
    np.save(J('beds_lab025.npy'), bl.astype(np.int32))
    A = np.array([b['area'] for b in beds]) if beds else np.zeros(1)
    from collections import Counter
    print(json.dumps(dict(beds=len(beds), lawn_ha=round(float(A.sum()) / 1e4, 1),
                          per_lot=dict(Counter(b['lot'] for b in beds))), indent=1))


if __name__ == '__main__':
    main()
