"""Coverage / empty-lawn metrics computed from a world-space xf file only (any version).
covered  = lawn inside a tree crown disc or a shrub disc (D * s / 2)
empty    = connected lawn patches > 30 m2 whose every pixel is > 4 m from any plant footprint."""
import env
import os, sys, json, collections, numpy as np, cv2
from lsite import SP, X0, Y0, RES
import species6 as SPC

F = 2                      # 0.25-m label grid downsampled by 2 -> 0.5 m pixels
PXM = 0.25 * F
TREE_MESH = {v[0] for k, v in SPC.LIB.items() if SPC.role(k) in 'LMSPC'}
# v3 meshes are all in LIB (Autumn_pear etc.)


class Lots:
    def __init__(self):
        self.beds = np.load(os.path.join(SP, 'beds_lab025.npy'), mmap_mode='r')
        info = json.load(open(os.path.join(SP, 'beds_st1.json')))
        self.bedinfo = {b['id']: b for b in info}
        self.by = collections.defaultdict(list)
        for b in info:
            if b.get('lot'):
                self.by[b['lot']].append(b['id'])
        from scipy import ndimage as ndi
        self.B = np.asarray(self.beds[::F, ::F])
        self.sl = ndi.find_objects(self.B)

    def box(self, bids, m=30):
        s = [self.sl[b - 1] for b in bids if b - 1 < len(self.sl) and self.sl[b - 1] is not None]
        r0 = max(min(x[0].start for x in s) - m, 0); r1 = min(max(x[0].stop for x in s) + m, self.B.shape[0])
        c0 = max(min(x[1].start for x in s) - m, 0); c1 = min(max(x[1].stop for x in s) + m, self.B.shape[1])
        return r0, r1, c0, c1


def level_of(lot):
    return env.lot_level_name(lot)


def lot_metrics(L, lot, pts, far=4.0, min_patch=30.0):
    bids = L.by[lot]
    r0, r1, c0, c1 = L.box(bids)
    bl = L.B[r0:r1, c0:c1]
    lawn = np.isin(bl, bids)
    can = np.zeros(bl.shape, np.uint8); shr = np.zeros(bl.shape, np.uint8)
    for p in pts:
        R = (p['y'] - Y0) / RES / F - r0; C = (p['x'] - X0) / RES / F - c0
        d = SPC.MESH_D.get(p['mesh'], 1.0) * p['s']
        rad = max(1, int(round(d / 2 / PXM)))
        cv2.circle(can if p['mesh'] in TREE_MESH else shr, (int(C), int(R)), rad, 1, -1)
    can = can.astype(bool); shr = shr.astype(bool)
    foot = can | shr
    A = lawn.sum()
    dist = cv2.distanceTransform((~foot).astype(np.uint8), cv2.DIST_L2, 5) * PXM
    far_m = lawn & (dist > far)
    n, lab, st, cen = cv2.connectedComponentsWithStats(far_m.astype(np.uint8), connectivity=8)
    patches = []
    for k in range(1, n):
        a = st[k, cv2.CC_STAT_AREA] * PXM * PXM
        if a > min_patch:
            ys, xs = np.nonzero(lab == k)
            bid = collections.Counter(bl[ys, xs].tolist()).most_common(1)[0][0]
            cx = X0 + (cen[k][0] + c0) * F * RES; cy = Y0 + (cen[k][1] + r0) * F * RES
            patches.append(dict(area=round(float(a), 1), bed=int(bid), x=round(float(cx)), y=round(float(cy)),
                                bedA=L.bedinfo.get(int(bid), {}).get('area')))
    return dict(lawn_m2=round(float(A * PXM * PXM)), canopy=round(float((can & lawn).sum() / max(A, 1)), 3),
                shrub_only=round(float((shr & ~can & lawn).sum() / max(A, 1)), 3),
                covered=round(float((foot & lawn).sum() / max(A, 1)), 3),
                within4m=round(float((lawn & (dist <= far)).sum() / max(A, 1)), 3),
                far_m2=round(float(far_m.sum() * PXM * PXM)),
                patches=sorted(patches, key=lambda p: -p['area']), n_inst=len(pts))


def run(xf_path, out_path=None):
    L = Lots()
    xf = json.load(open(xf_path))
    res = {}
    for lot in sorted(L.by):
        lvl = level_of(lot)
        if lvl not in xf:
            continue
        res[lvl] = lot_metrics(L, lot, xf[lvl])
    if out_path:
        json.dump(res, open(out_path, 'w'), indent=1)
    tot_l = sum(v['lawn_m2'] for v in res.values())
    print('%-20s %7s %6s %6s %6s %6s %5s %7s' % ('level', 'lawn', 'canopy', 'shrub', 'cover', 'in4m', 'npat', 'patchm2'))
    for k, v in res.items():
        print('%-20s %7d %6.2f %6.2f %6.2f %6.2f %5d %7d' % (k, v['lawn_m2'], v['canopy'], v['shrub_only'], v['covered'],
              v['within4m'], len(v['patches']), sum(p['area'] for p in v['patches'])))
    w = lambda key: sum(v[key] * v['lawn_m2'] for v in res.values()) / tot_l
    print('TOTAL lawn %d canopy %.3f cover %.3f within4m %.3f patches %d (%.0f m2) inst %d' % (
        tot_l, w('canopy'), w('covered'), w('within4m'), sum(len(v['patches']) for v in res.values()),
        sum(p['area'] for v in res.values() for p in v['patches']), sum(v['n_inst'] for v in res.values())))
    return res


if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
