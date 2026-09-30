"""Site data + per-bed geometry/context features and the bed-typology classifier (v3)."""
import os, json, numpy as np, cv2
from scipy import ndimage as ndi
import env
from env import SP, CFG

J = lambda n: os.path.join(SP, n)
GRID = json.load(open(J('grid.json')))
X0, Y0, RES = GRID['x0'], GRID['y0'], GRID['res']
PX = 0.25  # m per 0.25-m pixel
GRASS, ROAD, PAVE, PLAY, WATER, BLD, LOW, OTHER = 1, 2, 3, 4, 5, 6, 7, 8
MARGIN = 56  # px (14 m) context margin around each bed crop


lot_level_name = env.lot_level_name   # 'LOT_4' -> 'FOL_4', '34-1+34-2' -> 'FOL_34x1_34x2'
GROUND_Z = float(CFG['ground_z_cm'])   # fallback planting z when a bed has no traced grass z


class Site:
    def __init__(self):
        self.cls1 = np.load(J('cls1_fixed.npy'))
        self.z1 = np.load(J('z1.npy'))
        self.g4 = np.load(J('group4.npy'))
        self.names = {int(k): v for k, v in json.load(open(J('group4_names.json'))).items()}
        self.beds = np.load(J('beds_lab025.npy'))
        self.lab = np.load(J('label025.npy'), mmap_mode='r')
        self.bedinfo = {b['id']: b for b in json.load(open(J('beds_st1.json')))}
        self.slices = ndi.find_objects(self.beds)
        self.H, self.W = self.beds.shape

    # ---- coordinates ------------------------------------------------------------------------
    @staticmethod
    def world(R, C):
        """continuous 0.25-m pixel coords (row, col) -> world cm"""
        return X0 + C * RES, Y0 + R * RES

    @staticmethod
    def pix(x, y):
        return (y - Y0) / RES, (x - X0) / RES

    def cls_at(self, R, C):
        return self.cls1[np.clip(np.asarray(R, int) // 4, 0, self.cls1.shape[0] - 1),
                         np.clip(np.asarray(C, int) // 4, 0, self.cls1.shape[1] - 1)]

    def crop(self, bid, margin=MARGIN):
        sl = self.slices[bid - 1]
        r0 = max(sl[0].start - margin, 0); r1 = min(sl[0].stop + margin, self.H)
        c0 = max(sl[1].start - margin, 0); c1 = min(sl[1].stop + margin, self.W)
        return r0, r1, c0, c1


def dist_m(mask):
    """distance (m) of every pixel to the nearest True pixel of mask"""
    if not mask.any():
        return np.full(mask.shape, 1e3, np.float32)
    return cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) * PX


class Bed:
    """Geometry + context of one lawn bed in its own 0.25-m crop."""

    def __init__(self, site, bid):
        self.site, self.id = site, bid
        self.info = site.bedinfo.get(bid, {})
        r0, r1, c0, c1 = site.crop(bid)
        self.r0, self.c0 = r0, c0
        lab = site.beds[r0:r1, c0:c1]
        self.m = lab == bid
        rr, cc = np.mgrid[r0:r1, c0:c1]
        cls = site.cls_at(rr, cc)
        self.cls = cls
        grass_any = np.asarray(site.lab[r0:r1, c0:c1]) > 0
        self.grass = grass_any
        self.dt = cv2.distanceTransform(self.m.astype(np.uint8), cv2.DIST_L2, 5) * PX  # inside depth (m)
        hard = (~self.m) & (~grass_any)
        self.d_bld = dist_m((cls == BLD) & ~grass_any)
        self.d_road = dist_m((cls == ROAD) & ~grass_any)
        self.d_pave = dist_m(((cls == PAVE) | (cls == OTHER) | (cls == LOW) | (cls == 0)) & ~grass_any & ~self.m)
        self.d_play = dist_m((cls == PLAY) & ~grass_any)
        self.d_hard = dist_m(hard)
        self.d_lowobj = dist_m(((cls == LOW) | (cls == BLD)) & self.m & (self.dt > 1.25))  # obstacles inside the lawn
        self.d_cut = dist_m(grass_any & ~self.m)       # lawn that belongs to another bed / lot (no hedge there)
        self.d_out = dist_m(~self.m)
        # local thickness: 2 x the largest inscribed radius within 3 m / 8 m
        k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
        k8 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (65, 65))
        self.W3 = np.where(self.m, 2 * cv2.dilate(self.dt, k3), 0)
        self.W8 = np.where(self.m, 2 * cv2.dilate(self.dt, k8), 0)
        R1 = np.clip(np.arange(r0, r1) // 4, 0, site.cls1.shape[0] - 1)
        C1 = np.clip(np.arange(c0, c1) // 4, 0, site.cls1.shape[1] - 1)
        z = site.z1[np.ix_(R1, C1)]
        ok = self.m & (cls == GRASS) & np.isfinite(z)
        self.zmed = float(np.median(z[ok])) if ok.any() else GROUND_Z
        self.z = z
        self.features()

    def zat(self, r, c):
        """planting z (cm) at crop coords"""
        i, j = int(r), int(c)
        v = self.z[i, j]
        if self.cls[i, j] == GRASS and np.isfinite(v) and abs(v - self.zmed) < 60:
            return float(v) - 3.0
        return self.zmed - 3.0

    def inside(self, r, c):
        i, j = int(r), int(c)
        return 0 <= i < self.m.shape[0] and 0 <= j < self.m.shape[1] and self.m[i, j]

    # ---- features ---------------------------------------------------------------------------
    def features(self):
        m, dt = self.m, self.dt
        n = int(m.sum()); self.A = n * PX * PX
        self.maxr = float(dt.max())
        mx = ndi.maximum_filter(dt, size=3)
        ridge = m & (dt >= mx - 1e-3) & (dt > 0.2)
        w = 2 * dt[ridge] if ridge.any() else np.array([2 * self.maxr])
        self.Wmed, self.Wmin, self.Wmax = float(np.median(w)), float(np.percentile(w, 10)), float(np.percentile(w, 95))
        pts = np.argwhere(m)[:, ::-1].astype(np.float32)
        (cx, cy), (a, b), ang = cv2.minAreaRect(pts)
        self.rectL, self.rectW = max(a, b) * PX, min(a, b) * PX
        self.axis_ang = np.deg2rad(ang if a >= b else ang + 90)   # long axis angle in crop pixel coords (x=col, y=row)
        self.elong = self.A / max(self.Wmed, 0.5) ** 2
        hull = cv2.convexHull(pts)
        self.convex = self.A / max(cv2.contourArea(hull) * PX * PX, 1e-3)
        cnts, hier = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        self.holes = int(sum(1 for h in hier[0] if h[3] >= 0)) if hier is not None else 0
        self.perim = float(sum(cv2.arcLength(c, True) for c in cnts)) * PX
        # context in a 0-2 m ring outside the bed
        ring = (~m) & (dist_m(m) <= 2.0)
        cls = self.cls[ring]; g = self.grass[ring]
        tot = max(ring.sum(), 1)
        self.ctx = dict(bld=float(((cls == BLD) & ~g).sum() / tot), road=float(((cls == ROAD) & ~g).sum() / tot),
                        pave=float((((cls == PAVE) | (cls == OTHER) | (cls == 0) | (cls == LOW)) & ~g).sum() / tot),
                        play=float(((cls == PLAY) & ~g).sum() / tot), grass=float(g.sum() / tot),
                        water=float((cls == WATER).sum() / tot))
        inb = m
        self.fac_frac = float((self.d_bld[inb] <= 3.0).sum() / max(n, 1))   # share of the bed within 3 m of a facade
        self.min_bld = float(self.d_bld[inb].min())
        self.road_frac = float((self.d_road[inb] <= 2.5).sum() / max(n, 1))
        self.play_near = float(self.d_play[inb].min())
        ys, xs = np.nonzero(m)
        self.cR, self.cC = ys.mean() + self.r0 + 0.5, xs.mean() + self.c0 + 0.5
        self.classify()

    def classify(self):
        A, W, c = self.A, self.Wmed, self.ctx
        hard_ring = c['pave'] + c['play'] + c['road']
        if W < 1.5:
            t = 'T1'
        elif self.fac_frac > 0.25 and W <= 6.0 and self.elong > 3 and self.min_bld < 3.0:
            t = 'T2'
        elif hard_ring > 0.8 and c['bld'] < 0.05 and self.holes > 0 and A < 1500:
            t = 'T6'
        elif A > 400:
            t = 'T11' if (self.convex >= 0.6 and self.elong < 6) else 'TX'
        elif c['road'] > 0.25 and self.elong > 4:
            t = 'T3'
        elif c['play'] > 0.12 and A >= 25:
            t = 'T4'
        elif hard_ring > 0.8 and c['bld'] < 0.05:
            t = 'T5'
        elif A < 300 and self.convex < 0.72 and self.elong < 6:
            t = 'T7'
        elif A < 80 and self.elong < 4:
            t = 'T8'
        elif self.elong > 4 and self.convex < 0.6:
            t = 'T9'
        elif self.elong > 4:
            t = 'T9s'   # straight band between paths (same family as T9 but tree row on the axis)
        elif A <= 400:
            t = 'T10'
        else:
            t = 'T11'
        self.type = t
        return t

    def summary(self):
        return dict(id=self.id, lot=self.info.get('lot'), type=self.type, A=round(self.A, 1), Wmed=round(self.Wmed, 2),
                    Wmin=round(self.Wmin, 2), Wmax=round(self.Wmax, 2), maxr=round(self.maxr, 2),
                    elong=round(self.elong, 2), convex=round(self.convex, 2), holes=self.holes,
                    fac=round(self.fac_frac, 2), min_bld=round(self.min_bld, 1), ctx={k: round(v, 2) for k, v in self.ctx.items()},
                    perim=round(self.perim, 1))
