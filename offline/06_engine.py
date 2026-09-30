"""STEP 6 (offline): planting engine v6 (coverage-driven, mixed species) - the algorithm used on Zaliniy stage 1.

Usage:  python 06_engine.py [FOL_level ...] [--tag v6]
Inputs (work dir): grid.json, cls1_fixed.npy, z1.npy, label025.npy, group4.npy, group4_names.json,
                   beds_lab025.npy, beds_st1.json, lots_resolved.json (palettes / parks); data/tree_geo.json.
Outputs (work/engine): xf_<tag>.json  {FOL_level: [{mesh,x,y,z,roll,pitch,yaw,s}, ...]}  (world cm / degrees)
                       meta_<tag>.pkl (roles, rows, groups, beds - for verify/preview), engine_stats_<tag>.json
With level names given, only those lots are designed and the tag becomes 'part'.

Order per lot:
 1 street rows (mixed large / mixed columnar, constant spacing, gap repair)
 2 playground shade (every playground, S+W sides first, then the other sides sparser)
 3 path-framing rows along long paving edges of wide lawns + axis rows in band-shaped beds (no roll-back)
 4 conifer groups (deep palette)
 5 coverage fill: greedy tree clusters (3-4 species of the lot's harmony group, merged crowns) until the
   bed's canopy target is met; partial clusters are kept (no roll-back); class falls back L -> M -> S
 6 shrub skirts (2-4 species, layered back/middle/front) on the path-facing side of tree bases
 7 rhythmic facade masses + strip groups for beds too narrow for trees
 8 context-aware empty-patch repair: tree-poor lawns get structure; tree-heavy/facade/strip beds get
   layered shrub masses first (parks keep one deliberate glade per large bed)
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json, math, time, collections, pickle, argparse, numpy as np, cv2  # noqa: E402
from lsite import Site, Bed, PX, lot_level_name, SP, X0, Y0, RES
import geom as G
import species6 as SPC

EDGE_OFF, FACADE_OFF, ROAD_OFF = SPC.EDGE_OFF, SPC.FACADE_OFF, SPC.ROAD_OFF
ARCHVIZ = {
    # A shifted/repaired row position must still keep this share of its nominal spacing.  This prevents
    # partially-overlapping offset contours from interleaving into a visually doubled street row.
    'row_spacing_factor': 0.78,
    'row_min_spacing_m': 4.0,
    'unrelated_tree_min_m': 4.0,
    # Underplanting is rhythmic rather than a ring around every trunk (visual hierarchy + performance).
    'skirt_gap_m': 7.5,
    'street_skirt_step': 2,
    # Building edges receive designed masses with breathing intervals, not a continuous hedge.
    'facade_drift_period_m': 13.0,
    'facade_drift_min_run_m': 7.0,
    # Once a bed already has enough tree structure, repair bare patches with shrubs before adding trees.
    'tree_heavy_per_100m2': 3.5,
    'tree_heavy_canopy': 0.52,
}
ARCHVIZ.update(env.CFG.get('engine', {}).get('archviz', {}))
SKIRT_GAP = float(ARCHVIZ['skirt_gap_m'])
BLD, ROAD, PAVE, PLAY, CUT = 0, 1, 2, 3, 4
role, D, is_tree, tone = SPC.role, SPC.D, SPC.is_tree, SPC.tone
OUT = os.path.dirname(env.W('engine', 'x'))
STATS = collections.Counter()


class Hash:
    def __init__(self, cell=40.0):
        self.cell = cell; self.d = collections.defaultdict(list)

    def add(self, R, C, item):
        self.d[(int(R // self.cell), int(C // self.cell))].append((R, C, item))

    def near(self, R, C, rad_px):
        k = int(rad_px // self.cell) + 1
        ci, cj = int(R // self.cell), int(C // self.cell)
        r2 = rad_px * rad_px
        for di in range(-k, k + 1):
            for dj in range(-k, k + 1):
                for (r, c, it) in self.d.get((ci + di, cj + dj), ()):
                    if (r - R) ** 2 + (c - C) ** 2 <= r2:
                        yield r, c, it

    def remove(self, R, C):
        cell = self.d[(int(R // self.cell), int(C // self.cell))]
        cell[:] = [t for t in cell if not (t[0] == R and t[1] == C)]


def wchoice(rng, mix, exclude=()):
    ks = [k for k, w in mix if k not in exclude] or [k for k, w in mix]
    ws = np.array([w for k, w in mix if k in ks], float)
    return ks[int(rng.choice(len(ks), p=ws / ws.sum()))]


def mixed_seq(rng, mix, n):
    """species sequence for a row: weighted, never the same model twice in a row (when >1 species)."""
    out = []
    for i in range(n):
        ex = tuple(k for k, w in mix if out and SPC.mesh(k) == SPC.mesh(out[-1])) if len(mix) > 1 else ()
        out.append(wchoice(rng, mix, ex))
    return out


class Planter:
    def __init__(self, lot, group, seed):
        self.lot, self.gname = lot, group
        self.grp = SPC.GROUPS[group]
        self.rng = np.random.default_rng(seed)
        self.recs = []
        self.trees = Hash(); self.shrubs = Hash()
        self.gid = 0
        self.combos = list(SPC.LOT_COMBOS[group])
        self.rng.shuffle(self.combos)

    def new_group(self):
        self.gid += 1
        return self.gid

    def scale(self, key, mul=1.0):
        j = SPC.jit(key)
        return float(SPC.base(key) * mul * self.rng.uniform(1 - j, 1 + j))

    # ---- spacing checks -------------------------------------------------------------------
    def tree_free(self, R, C, key, s, gid=None, f=0.62, min_m=0.0):
        Dk = D(key, s); cl = role(key); tn = tone(key)
        for r, c, it in self.trees.near(R, C, max(14.0, min_m) / PX):
            d = math.hypot(r - R, c - C) * PX
            same = gid is not None and it['gid'] == gid
            ff = 0.5 if same else f
            visual_min = min_m if same else max(min_m, float(ARCHVIZ['unrelated_tree_min_m']))
            if d < visual_min or d < ff * (Dk + it['D']) / 2 or \
                    d < (2.2 if cl in 'LM' and it['cls'] in 'LM' else 1.6) or (not same and d < 3.2):
                return False
            if (cl == 'C') != (it['cls'] == 'C') and d < 8.0:
                other = tn if it['cls'] == 'C' else it['tone']
                if other in ('G', 'Y'):
                    return False
            if {tn, it['tone']} == {'D', 'Y'} and d < 8.0:
                return False
        for r, c, it in self.shrubs.near(R, C, 1.5 / PX):
            if math.hypot(r - R, c - C) * PX < 0.6 + it['r']:
                return False
        return True

    def shrub_free(self, R, C, rad, f=0.85):
        for r, c, it in self.shrubs.near(R, C, 2.0 / PX):
            if math.hypot(r - R, c - C) * PX < f * (rad + it['r']):
                return False
        for r, c, it in self.trees.near(R, C, 1.2 / PX):
            if math.hypot(r - R, c - C) * PX < 0.75:
                return False
        return True

    # ---- add / remove ---------------------------------------------------------------------
    def add_tree(self, bed, r, c, key, s, rl, gid, row=None, idx=None):
        R, C = r + bed.r0, c + bed.c0
        lean = self.rng.uniform(0, 1.5); az = self.rng.uniform(0, 2 * math.pi)
        rec = dict(key=key, R=R, C=C, s=round(s, 3), yaw=float(self.rng.uniform(0, 360)),
                   pitch=float(lean * math.cos(az)), roll=float(lean * math.sin(az)), z=bed.zat(r, c),
                   role=rl, bed=bed.id, gid=gid, btype=bed.type, row=row, idx=idx)
        self.recs.append(rec)
        self.trees.add(R, C, dict(D=D(key, s), cls=role(key), tone=tone(key), gid=gid, key=key, role=rl, rec=rec))
        if self.canvas is not None:
            self.canvas.draw(R, C, D(key, s) / 2, True)
        return rec

    def add_shrub(self, bed, r, c, key, s, rl, gid, combo=None):
        R, C = r + bed.r0, c + bed.c0
        rec = dict(key=key, R=R, C=C, s=round(s, 3), yaw=float(self.rng.uniform(0, 360)), pitch=0.0, roll=0.0,
                   z=bed.zat(r, c), role=rl, bed=bed.id, gid=gid, btype=bed.type, combo=combo)
        self.recs.append(rec)
        self.shrubs.add(R, C, dict(r=D(key, s) / 2, key=key, gid=gid))
        if self.canvas is not None:
            self.canvas.draw(R, C, D(key, s) / 2, False)
        return rec

    def remove(self, recs):
        ids = {id(r) for r in recs}
        self.recs = [r for r in self.recs if id(r) not in ids]
        for rec in recs:
            (self.trees if is_tree(rec['key']) else self.shrubs).remove(rec['R'], rec['C'])
        if recs and self.canvas is not None:
            self.canvas.redraw(self.recs)

    canvas = None


class Canvas:
    """lot-wide footprint rasters (0.25 m): canopy discs and shrub discs"""

    def __init__(self, beds):
        self.R0 = min(b.r0 for b in beds); self.C0 = min(b.c0 for b in beds)
        self.R1 = max(b.r0 + b.m.shape[0] for b in beds); self.C1 = max(b.c0 + b.m.shape[1] for b in beds)
        self.can = np.zeros((self.R1 - self.R0, self.C1 - self.C0), np.uint8)
        self.shr = np.zeros_like(self.can)

    def draw(self, R, C, rad_m, tree):
        cv2.circle(self.can if tree else self.shr, (int(round(C - self.C0)), int(round(R - self.R0))),
                   max(1, int(round(rad_m / PX))), 1, -1)

    def redraw(self, recs):
        self.can[:] = 0; self.shr[:] = 0
        for r in recs:
            self.draw(r['R'], r['C'], D(r['key'], r['s']) / 2, is_tree(r['key']))

    def crop(self, bed, which='foot'):
        a = self.can if which == 'can' else (self.can | self.shr)
        r0 = bed.r0 - self.R0; c0 = bed.c0 - self.C0
        return a[r0:r0 + bed.m.shape[0], c0:c0 + bed.m.shape[1]].astype(bool)


# ================================= site tests ================================================
def tree_ok(bed, r, c, key, extra_edge=0.0):
    i, j = int(r), int(c)
    if not (0 <= i < bed.m.shape[0] and 0 <= j < bed.m.shape[1]) or not bed.m[i, j]:
        return False
    cl = role(key)
    if bed.dt[i, j] < EDGE_OFF[cl] + extra_edge:
        STATS['rej_edge'] += 1; return False
    if bed.d_bld[i, j] < FACADE_OFF[cl]:
        STATS['rej_facade'] += 1; return False
    if bed.d_road[i, j] < ROAD_OFF[cl]:
        STATS['rej_road'] += 1; return False
    if bed.d_play[i, j] < (15.0 if cl == 'C' else 2.5) or bed.d_lowobj[i, j] < 2.5:
        STATS['rej_play'] += 1; return False
    return bed.site.lab[bed.r0 + i, bed.c0 + j] > 0


def low_only(bed):
    """distance to LOW-class obstacles inside the lawn (lawn under a building/canopy mask is shrub-plantable)"""
    if not hasattr(bed, '_dlow'):
        from lsite import dist_m, LOW
        bed._dlow = dist_m((bed.cls == LOW) & bed.m & (bed.dt > 1.25))
    return bed._dlow


def shrub_ok(bed, r, c, key, s):
    i, j = int(r), int(c)
    if not (0 <= i < bed.m.shape[0] and 0 <= j < bed.m.shape[1]) or not bed.m[i, j]:
        return False
    rad = D(key, s) / 2
    if bed.dt[i, j] < rad + 0.12:            # never overhang paving / neighbouring surfaces
        return False
    if low_only(bed)[i, j] < 0.6 or bed.d_bld[i, j] < rad + 0.2:
        return False
    if key in SPC.NO_PLAY and bed.d_play[i, j] < 10:
        return False
    if not bed.site.lab[bed.r0 + i, bed.c0 + j] > 0:
        return False
    # the whole crown disc must lie on lawn (no overhang over paving)
    rp = (rad + 0.05) / PX
    for a in range(0, 360, 30):
        ii = int(r + rp * math.sin(math.radians(a))); jj = int(c + rp * math.cos(math.radians(a)))
        if not bed.site.lab[bed.r0 + ii, bed.c0 + jj] > 0:
            return False
    return True


def valid_mask(bed, cl):
    return bed.m & (bed.dt >= EDGE_OFF[cl]) & (bed.d_bld >= FACADE_OFF[cl]) & (bed.d_road >= ROAD_OFF[cl]) & \
        (bed.d_play >= (15.0 if cl == 'C' else 2.5)) & (bed.d_lowobj >= 2.5)


def try_tree(P, bed, r, c, cands, rl, gid, f=0.62, row=None, idx=None, min_m=0.0):
    """place the first species of `cands` that fits at (r,c); returns rec or None"""
    for key in cands:
        s = P.scale(key)
        if tree_ok(bed, r, c, key) and P.tree_free(r + bed.r0, c + bed.c0, key, s, gid, f=f, min_m=min_m):
            return P.add_tree(bed, r, c, key, s, rl, gid, row=row, idx=idx)
    return None


def class_list(P, cl):
    return [k for k, w in P.grp[cl]]


def cands_for(P, pref, classes=('L', 'M', 'S')):
    """preferred species first, then the rest of its class (mixed), then smaller classes"""
    out = [pref] if pref else []
    for cl in classes:
        mix = P.grp[cl]
        ks = [k for k, w in sorted(mix, key=lambda kw: -kw[1] * P.rng.uniform(0.5, 1.5))]
        out += [k for k in ks if k not in out]
    return out


# ================================= rows =======================================================
def _row_points(seg, spacing, margin):
    L = G.arclen(seg)
    if L < 2 * margin:
        if L >= 3.0:
            p, _ = G.resample_even(seg, False, max(L / 2, 0.5), L / 2)
            return p[:1]
        return np.zeros((0, 2))
    k = int((L - 2 * margin) // spacing) + 1
    start = (L - (k - 1) * spacing) / 2
    p, _ = G.resample_even(seg, False, spacing, start)
    return p[:k]


def plant_row(P, bed, pts, mix, rl, fallback_classes=('M', 'S'), f=0.5, tan=None, min_spacing=0.0):
    """Mixed row with gap repair; shifted/fallback trees still obey a real minimum centre spacing."""
    seq = mixed_seq(P.rng, mix, len(pts))
    gid = P.new_group(); row = gid
    if tan is None and len(pts) > 1:
        dp = np.gradient(np.asarray(pts, float), axis=0)
        tan = dp / np.maximum(np.hypot(dp[:, 0], dp[:, 1])[:, None], 1e-6)
    got = []
    prev = None
    for n, ((r, c), key) in enumerate(zip(pts, seq)):
        pm = SPC.mesh(prev) if prev else None
        opts = [k for k in [key] + [k for k, w in mix if k != key] if SPC.mesh(k) != pm]
        rec = try_tree(P, bed, r, c, opts, rl, gid, f=f, row=row, idx=n, min_m=min_spacing)
        if rec is None and tan is not None:
            t = tan[n] if len(tan) > n else tan[-1]
            for sh in (1.5, -1.5):
                rr, cc = r + t[0] * sh / PX, c + t[1] * sh / PX
                rec = try_tree(P, bed, rr, cc, opts, rl, gid, f=f, row=row, idx=n, min_m=min_spacing)
                if rec:
                    break
        if rec is None:
            for cl in fallback_classes:
                ks = [k for k in class_list(P, cl) if SPC.mesh(k) != pm]
                P.rng.shuffle(ks)
                rec = try_tree(P, bed, r, c, ks, rl, gid, f=f, row=row, idx=n, min_m=min_spacing)
                if rec:
                    STATS['row_repair_smaller'] += 1
                    break
        if rec is not None:
            got.append(rec); prev = rec['key']
        else:
            STATS['row_gap'] += 1
    return got


def street_rows(P, bed):
    """mixed allee along road edges (axis at half the verge width, >= 1.5 m from the curb)."""
    def street(cnt, off):
        lab = G.edge_labels(bed, cnt, off)
        i = np.clip(cnt[:, 0].astype(int), 0, bed.m.shape[0] - 1); j = np.clip(cnt[:, 1].astype(int), 0, bed.m.shape[1] - 1)
        return (lab == ROAD) | ((lab == PAVE) & (bed.d_road[i, j] <= off + 4.0))

    from scipy.spatial import cKDTree
    n = 0
    for cnt in G.offset_contours(bed, 1.5):
        rs, closed = G.runs(street(cnt, 1.5))
        for idx in rs:
            seg = cnt[idx]
            if G.arclen(seg) < 12:
                continue
            i = np.clip(seg[:, 0].astype(int), 0, bed.m.shape[0] - 1); j = np.clip(seg[:, 1].astype(int), 0, bed.m.shape[1] - 1)
            Wr = float(np.median(bed.W8[i, j]))
            if Wr >= 5.0:
                mix, off, sp, fb = SPC.STREET_WIDE, (3.0 if Wr >= 6.5 else max(2.5, Wr / 2)), 9.0, ('M',)
            elif Wr >= 3.0:
                mix, off, sp, fb = SPC.STREET_NARROW, max(1.4, min(Wr / 2, 2.2)), 5.5, ()
            else:
                continue
            for cnt2 in G.offset_contours(bed, off):
                rs2, _ = G.runs(street(cnt2, off))
                for idx2 in rs2:
                    s2 = cnt2[idx2]
                    d, _ = cKDTree(seg).query(s2)
                    s2 = s2[d * PX <= off + 0.5]
                    if len(s2) < 8:
                        continue
                    pts = _row_points(s2, sp, 4.0)
                    if not len(pts):
                        continue
                    # Do not discard a whole partly-overlapping segment: the per-position spacing guard keeps
                    # the existing part and repairs only genuinely free gaps.  This fixes both doubled rows and
                    # long skipped strip fragments.
                    min_sp = max(float(ARCHVIZ['row_min_spacing_m']), sp * float(ARCHVIZ['row_spacing_factor']))
                    got = plant_row(P, bed, pts, mix, 'street', fallback_classes=fb, tan=None,
                                    min_spacing=min_sp)
                    if not got:
                        STATS['street_overlap_segments_skipped'] += 1
                    n += len(got)
    return n


def play_shade(P, bed):
    """shade trees 3 m outside every playground on the S and W sides (+X north, +Y east), then N/E sparser."""
    if bed.d_play[bed.m].min() > 4.5:
        return 0
    iso = (bed.d_play <= 3.4).astype(np.uint8)
    cnts, _ = cv2.findContours(iso, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    gy, gx = np.gradient(bed.d_play)
    mix = P.grp['L'] + [(k, w * 0.6) for k, w in P.grp['M']]
    n = 0
    for sw in (True, False):
        for c in cnts:
            p = c[:, 0, ::-1].astype(float) + 0.5
            i = np.clip(p[:, 0].astype(int), 0, bed.m.shape[0] - 1); j = np.clip(p[:, 1].astype(int), 0, bed.m.shape[1] - 1)
            side = (gx[i, j] < -0.25) | (gy[i, j] < -0.25)
            ok = bed.m[i, j] & (side if sw else ~side)
            rs, _ = G.runs(ok)
            for idx in rs:
                seg = p[idx]
                if G.arclen(seg) < 5:
                    continue
                pts = _row_points(seg, 7.5 if sw else 10.0, 2.0)
                min_sp = max(float(ARCHVIZ['row_min_spacing_m']), (7.5 if sw else 10.0) *
                             float(ARCHVIZ['row_spacing_factor']))
                n += len(plant_row(P, bed, pts, mix, 'play', fallback_classes=('M', 'S'), f=0.55,
                                   min_spacing=min_sp))
    return n


_SK = {}


def skeleton(bed):
    if bed.id not in _SK:
        sm = cv2.morphologyEx(bed.m.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        sk = G.zhang_suen(sm, max_iter=60) & (bed.dt > 0.3)
        _SK[bed.id] = G.skeleton_branches(sk)
    return _SK[bed.id]


def axis_rows(P, bed, wband=(3.0, 12.0), min_len=8.0):
    """tree row on the medial axis of band-shaped parts; class by local width; no fragment roll-back."""
    n = 0
    for br in sorted(skeleton(bed), key=len, reverse=True):
        p = br.astype(float) + 0.5
        i, j = br[:, 0], br[:, 1]
        ok = (bed.W3[i, j] >= wband[0]) & (bed.W3[i, j] <= wband[1])
        rs, _ = G.runs(np.r_[ok, False])
        for idx in rs:
            idx = idx[idx < len(p)]
            seg = p[idx]
            L = G.arclen(seg)
            if L < min_len:
                continue
            Wm = float(np.median(bed.W3[br[idx, 0], br[idx, 1]]))
            fb = float(np.median(bed.d_bld[br[idx, 0], br[idx, 1]]))
            if Wm >= 5.0 and fb >= FACADE_OFF['L']:
                mix, sp, fbc = P.grp['L'], 9.0, ('M',)
            elif Wm >= 3.6 and fb >= FACADE_OFF['M']:
                mix, sp, fbc = P.grp['M'], 6.5, ('S',)
            else:
                mix, sp, fbc = P.grp['S'], 6.0, ()
            pts = _row_points(seg, sp, 2.0)
            busy = [any(True for _ in P.trees.near(r + bed.r0, c + bed.c0, 4.5 / PX)) for r, c in pts]
            if len(pts) and sum(busy) > 0.5 * len(pts):
                continue
            pts = np.array([p for p, b in zip(pts, busy) if not b]).reshape(-1, 2)
            min_sp = max(float(ARCHVIZ['row_min_spacing_m']), sp * float(ARCHVIZ['row_spacing_factor']))
            n += len(plant_row(P, bed, pts, mix, 'row', fallback_classes=fbc, f=0.55,
                               min_spacing=min_sp))
    return n


def path_frame_rows(P, bed, min_run=24.0):
    """rows along long paving edges of wide lawns (path framing); mixed L of the lot group."""
    off = 3.0
    n = 0
    for cnt in G.offset_contours(bed, off):
        lab = G.edge_labels(bed, cnt, off)
        i = np.clip(cnt[:, 0].astype(int), 0, bed.m.shape[0] - 1); j = np.clip(cnt[:, 1].astype(int), 0, bed.m.shape[1] - 1)
        good = (lab == PAVE) & (bed.W8[i, j] >= 11.0) & (bed.d_bld[i, j] >= FACADE_OFF['L']) & (bed.d_play[i, j] >= 4)
        rs, closed = G.runs(good)
        for idx in rs:
            seg = cnt[idx]
            if G.arclen(seg) < min_run:
                continue
            pts = _row_points(seg, 9.5, 3.0)
            min_sp = max(float(ARCHVIZ['row_min_spacing_m']), 9.5 * float(ARCHVIZ['row_spacing_factor']))
            n += len(plant_row(P, bed, pts, P.grp['L'], 'frame', fallback_classes=('M',), f=0.55,
                               min_spacing=min_sp))
    return n


# ================================= clusters ===================================================
TEMPL = {1: [(0, 0)], 2: [(-0.5, 0), (0.5, 0.05)], 3: [(0, 0), (1.0, 0.12), (0.48, 0.86)],
         4: [(0, 0), (1.0, 0.1), (0.45, 0.88), (1.5, 0.95)],
         5: [(0, 0), (1.0, 0.1), (2.05, -0.05), (0.5, 0.9), (1.55, 0.95)]}


def cluster_at(P, bed, r, c, n, cls_pref='L'):
    """irregular group of n trees mixing 2-3 species of the lot group; keeps whatever fits."""
    mixL = P.grp[cls_pref]
    dom = wchoice(P.rng, mixL)
    sec = wchoice(P.rng, mixL, (dom,))
    keys = [dom if P.rng.random() < 0.6 else sec for _ in range(n)]
    if n >= 3 and len(set(keys)) < 2:
        keys[-1] = sec
    if n >= 4 and len(P.grp[cls_pref]) >= 3 and P.rng.random() < 0.5:
        keys[-2] = wchoice(P.rng, mixL, (dom, sec))
    Dm = np.mean([SPC.D(k, SPC.base(k)) for k in keys])
    a = 0.66 * Dm / PX
    T = np.array(TEMPL[n], float)
    T -= T.mean(0)
    th = P.rng.uniform(0, 2 * math.pi)
    rot = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
    T = T @ rot.T
    gid = P.new_group(); got = []
    for (x, y), key in zip(T, keys):
        placed = None
        for shrink in (1.0, 0.8, 0.6):
            rr = r + a * shrink * x + P.rng.normal(0, 0.05 * a); cc = c + a * shrink * y + P.rng.normal(0, 0.05 * a)
            opts = [key] + [k for k, w in mixL if k != key]
            placed = try_tree(P, bed, rr, cc, opts, 'cluster', gid, f=0.62)
            if placed:
                break
        if placed is None:
            smaller = {'L': ('M', 'S'), 'M': ('S',), 'S': ()}[cls_pref]
            for cl in smaller:
                ks = class_list(P, cl); P.rng.shuffle(ks)
                rr = r + a * 0.8 * x; cc = c + a * 0.8 * y
                placed = try_tree(P, bed, rr, cc, ks, 'cluster', gid, f=0.62)
                if placed:
                    break
        if placed:
            got.append(placed)
    return got


def disk(rad_px):
    k = int(math.ceil(rad_px))
    yy, xx = np.mgrid[-k:k + 1, -k:k + 1]
    return ((yy * yy + xx * xx) <= rad_px * rad_px).astype(np.float32)


def fill_clusters(P, bed, target, glades=()):
    """greedy coverage: put the next group where it covers the most still-bare lawn."""
    if bed.A < 20:
        return 0
    vS = valid_mask(bed, 'S')
    if not vS.any():
        return 0
    vM = valid_mask(bed, 'M'); vL = valid_mask(bed, 'L')
    lawn = bed.m.copy()
    for (gr, gc, grad) in glades:
        yy, xx = np.ogrid[:bed.m.shape[0], :bed.m.shape[1]]
        lawn &= ((yy - gr) ** 2 + (xx - gc) ** 2) * PX * PX > grad ** 2
    A = lawn.sum()
    n_added = 0
    k6 = disk(6.0)
    k3 = disk(3.0)
    k9 = disk(9.0)
    fails = 0
    W8c = bed.W8[2::4, 2::4]
    for it in range(600):
        phase = 'big' if it < 300 and not getattr(bed, '_bigdone', False) else 'any'
        can = P.canvas.crop(bed, 'can')
        cov = (can & bed.m).sum() / max(bed.m.sum(), 1)
        if cov >= target:
            break
        un = (lawn & ~can).astype(np.float32)
        # 1 m grid
        H, W = un.shape
        h1, w1 = H // 4, W // 4
        if h1 < 1 or w1 < 1:
            break
        u1 = un[:h1 * 4, :w1 * 4].reshape(h1, 4, w1, 4).mean((1, 3))
        g6 = cv2.filter2D(u1, -1, k6, borderType=cv2.BORDER_CONSTANT)
        g3 = cv2.filter2D(u1, -1, k3, borderType=cv2.BORDER_CONSTANT)
        cL = vL[2:h1 * 4:4, 2:w1 * 4:4]; cM = vM[2:h1 * 4:4, 2:w1 * 4:4]; cS = vS[2:h1 * 4:4, 2:w1 * 4:4]
        if phase == 'big':
            g9 = cv2.filter2D(u1, -1, k9, borderType=cv2.BORDER_CONSTANT)
            score = np.where(cL & (W8c[:h1, :w1] >= 12), g9, -1)
        else:
            score = np.where(cL, g6, np.where(cM, g6 * 0.8, np.where(cS, g3 * 0.9, -1)))
        score += np.random.default_rng(it).uniform(0, 0.5, score.shape)
        blocked = getattr(bed, '_blocked', None)
        if blocked is not None:
            score[blocked[:h1, :w1]] = -1
        k = int(np.argmax(score))
        i1, j1 = divmod(k, w1)
        best = score[i1, j1]
        if phase == 'big' and best < 160.0:   # no more room for a merged group of 3-5
            bed._bigdone = True; continue
        if best < 6.0:          # less than ~6 m2 of bare lawn gained
            break
        r, c = i1 * 4 + 2.0, j1 * 4 + 2.0
        W8 = bed.W8[int(r), int(c)]
        cl = 'L' if cL[i1, j1] else ('M' if cM[i1, j1] else 'S')
        if phase == 'big':
            nn = 5 if W8 >= 20 else (4 if W8 >= 15 else 3)
        elif cl == 'L':
            nn = 5 if (W8 >= 22 and g6[i1, j1] > 80) else (4 if W8 >= 17 else (3 if W8 >= 12 else (2 if W8 >= 8 else 1)))
        elif cl == 'M':
            nn = 3 if W8 >= 10 else (2 if W8 >= 6.5 else 1)
        else:
            nn = 3 if W8 >= 7 else (2 if W8 >= 4.5 else 1)
        got = cluster_at(P, bed, r, c, nn, cl)
        if not got:
            if blocked is None:
                bed._blocked = blocked = np.zeros((h1 + 1, w1 + 1), bool)
            blocked[max(i1 - 1, 0):i1 + 2, max(j1 - 1, 0):j1 + 2] = True
            fails += 1
            if fails > 60:
                break
            continue
        n_added += len(got)
    return n_added


def conifer_group(P, bed):
    if not P.grp.get('C'):
        return []
    cand = valid_mask(bed, 'C') & (bed.W8 >= 14) & (bed.dt >= 3) & (bed.dt <= 7) & (bed.d_bld >= 9) & \
        (bed.d_road >= 6)
    ys, xs = np.nonzero(cand)
    if not len(ys):
        return []
    for o in P.rng.permutation(len(ys))[:40]:
        r, c = ys[o] + 0.5, xs[o] + 0.5
        if any(True for _ in P.trees.near(r + bed.r0, c + bed.c0, 10 / PX)):
            continue
        gid = P.new_group(); got = []
        T = np.array(TEMPL[5], float); T -= T.mean(0)
        th = P.rng.uniform(0, 2 * math.pi)
        T = T @ np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]).T
        keys = ['pine650', 'pine550', 'pine650', 'pine450', 'pine550']
        for (x, y), key in zip(T, keys):
            rr, cc = r + 3.6 / PX * x, c + 3.6 / PX * y
            rec = try_tree(P, bed, rr, cc, [key, 'pine650', 'pine450'], 'conifer', gid, f=0.55)
            if rec:
                got.append(rec)
        if len(got) >= 3:
            # vertical accents in front (juniper / hach pine)
            ctr = np.mean([[g['R'] - bed.r0, g['C'] - bed.c0] for g in got], 0)
            for q in range(3):
                a = th + q * 0.7
                rr, cc = ctr[0] + math.sin(a) * 5.5 / PX, ctr[1] + math.cos(a) * 5.5 / PX
                try_tree(P, bed, rr, cc, ['junip', 'hach'] if q % 2 == 0 else ['hach', 'junip'], 'conifer', gid, f=0.5)
            return got
        P.remove(got)
    return []


# ================================= shrubs =====================================================
def combo_rows(P, combo, play=False):
    back, mids, front = SPC.COMBOS[combo]
    if play and back in SPC.NO_PLAY:
        back = 'montra2'
    return back, list(mids), front


def pick_combo(P, bed, salt=0):
    return P.combos[(bed.id * 7 + salt) % len(P.combos)]


def skirt(P, bed, tree, toward, combo, span=(40, 58, 72), full=False):
    """layered shrub skirt at a tree base: back row hugging the trunk, middle (1-2 species in blocks), front."""
    back, mids, front = combo_rows(P, combo, play=bed.d_play[int(tree['R'] - bed.r0), int(tree['C'] - bed.c0)] < 10
                                   if 0 <= int(tree['R'] - bed.r0) < bed.m.shape[0] and 0 <= int(tree['C'] - bed.c0) < bed.m.shape[1] else False)
    r0, c0 = tree['R'] - bed.r0, tree['C'] - bed.c0
    a0 = math.atan2(toward[0], toward[1]) if toward is not None else 0.0
    sK = P.scale(back); sE = [P.scale(k) for k in mids]; sF = P.scale(front)
    dK = D(back, sK); dE = max(D(k, s) for k, s in zip(mids, sE)); dF = D(front, sF)
    rK = 0.95 + dK / 2
    rE = rK + 0.85 * (dK + dE) / 2
    rF = rE + 0.85 * (dE + dF) / 2
    rows = [(rK, [back], span[0]), (rE, mids, span[1]), (rF, [front], span[2])]
    if full:
        rows = [(rK, [back], 180), (rE, mids, 180)]
    gid = P.new_group(); out = []
    for ri, (rad, keys, sp) in enumerate(rows):
        spc = {0: dK, 1: dE, 2: dF}[ri] * 0.92
        arc = 2 * math.radians(sp) * rad
        k = max(1, int(round(arc / spc)) + 1) if sp < 180 else max(3, int(2 * math.pi * rad / spc))
        for q in range(k):
            if sp >= 180:
                a = a0 + 2 * math.pi * q / k + ri * 0.3
                frac = q / k
            else:
                a = a0 + (math.radians(-sp) + 2 * math.radians(sp) * q / max(k - 1, 1) if k > 1 else 0.0)
                frac = q / max(k - 1, 1)
            key = keys[min(int(frac * len(keys)), len(keys) - 1)] if len(keys) > 1 else keys[0]
            mul = {0: 1.05, 1: 1.0, 2: 0.95}[ri]
            s = P.scale(key, mul)
            rr, cc = r0 + math.sin(a) * rad / PX, c0 + math.cos(a) * rad / PX
            if shrub_ok(bed, rr, cc, key, s) and P.shrub_free(rr + bed.r0, cc + bed.c0, D(key, s) / 2):
                out.append(P.add_shrub(bed, rr, cc, key, s, 'skirt', gid, combo))
    if len(out) < 4 or len({o['key'] for o in out}) < 2:
        P.remove(out); STATS['skirt_small_removed'] += 1
        return []
    return out


def path_dir(bed, r, c, field='pave', maxd=8.0):
    f = {'pave': bed.d_pave, 'play': bed.d_play, 'hard': bed.d_hard}[field]
    i, j = int(r), int(c)
    if not (0 <= i < f.shape[0] and 0 <= j < f.shape[1]) or f[i, j] > maxd:
        return None
    gy, gx = np.gradient(f[max(i - 3, 0):i + 4, max(j - 3, 0):j + 4])
    ii, jj = min(i, 3), min(j, 3)
    v = -np.array([gy[ii, jj], gx[ii, jj]])
    n = np.hypot(*v)
    return v / n if n > 1e-6 else None


def edge_dir(bed, r, c):
    """Direction from a tree towards its nearest bed edge (fallback when no path gradient is readable)."""
    if not hasattr(bed, '_edge_grad'):
        bed._edge_grad = np.gradient(bed.dt)
    i, j = int(r), int(c)
    if not (0 <= i < bed.m.shape[0] and 0 <= j < bed.m.shape[1]):
        return np.array([1.0, 0.0])
    gy, gx = bed._edge_grad
    v = -np.array([gy[i, j], gx[i, j]])
    n = np.hypot(*v)
    return v / n if n > 1e-6 else np.array([1.0, 0.0])


def skirts_for_lot(P, beds_by_id):
    """one skirt per group on the tree nearest a path/playground; rows every 2nd tree; singles all."""
    trees = [r for r in P.recs if is_tree(r['key']) and role(r['key']) != 'C']
    skirt_hash = Hash()
    by_gid = collections.defaultdict(list)
    for t in trees:
        by_gid[t['gid']].append(t)
    n = 0
    for gid, ts in by_gid.items():
        rl = ts[0]['role']
        if rl in ('street', 'row', 'frame', 'play'):
            ts = sorted(ts, key=lambda t: t['idx'] if t['idx'] is not None else 0)
            step = int(ARCHVIZ['street_skirt_step']) if rl == 'street' else 2
            step = max(step, 1)
            pick = ts[P.rng.integers(0, step)::step] if len(ts) > 1 else ts
        else:
            pick = None
        cand = []
        for t in ts:
            bed = beds_by_id[t['bed']]
            r, c = t['R'] - bed.r0, t['C'] - bed.c0
            v = path_dir(bed, r, c, 'pave', 8.0)
            fld = 'pave'
            if v is None:
                v = path_dir(bed, r, c, 'play', 9.0); fld = 'play'
            if v is None:
                v = path_dir(bed, r, c, 'hard', 7.0); fld = 'hard'
            d = {'pave': bed.d_pave, 'play': bed.d_play, 'hard': bed.d_hard}[fld][int(r), int(c)] if v is not None else 99
            cand.append((d, t, v, bed))
        if pick is None:
            cand.sort(key=lambda x: x[0])
            chosen = cand[:1] if len(ts) < 4 else cand[:2]
        else:
            ids = {id(t) for t in pick}
            chosen = [x for x in cand if id(x[1]) in ids]
        for d, t, v, bed in chosen:
            if any(True for _ in skirt_hash.near(t['R'], t['C'], SKIRT_GAP / PX)):
                continue
            if v is None:
                v = edge_dir(bed, t['R'] - bed.r0, t['C'] - bed.c0)
            got = skirt(P, bed, t, v, pick_combo(P, bed, t['gid'] % 3))
            if got:
                skirt_hash.add(t['R'], t['C'], 1)
            n += len(got)
    return n


def drift_at(P, bed, r, c, combo, length=5.0, rows=3, gid=None):
    """edge drift centred on the bed edge nearest (r,c): front row at the edge, taller rows behind;
    rows parallel to the edge, tapered ends, middle row split into 1-2 species blocks."""
    back, mids, front = combo_rows(P, combo, play=bed.d_play[int(r), int(c)] < 10)
    i, j = int(r), int(c)
    # nearest edge point direction = -grad(dt)
    gy, gx = np.gradient(bed.dt)
    nrm = np.array([gy[i, j], gx[i, j]]); nn = np.hypot(*nrm)
    if nn < 1e-6:
        nrm = np.array([1.0, 0.0])
    else:
        nrm = nrm / nn
    tan = np.array([-nrm[1], nrm[0]])
    depth = bed.dt[i, j]
    base = np.array([r, c]) - nrm * depth / PX       # point on the edge
    bi, bj = int(np.clip(base[0], 0, bed.m.shape[0] - 1)), int(np.clip(base[1], 0, bed.m.shape[1] - 1))
    fshift = 0.6 if bed.d_bld[bi, bj] < 1.0 else 0.0   # facade base: keep the front row off the wall
    sF = P.scale(front); sE = [P.scale(k) for k in mids]; sK = P.scale(back)
    dF = D(front, sF); dE = max(D(k, s) for k, s in zip(mids, sE)); dK = D(back, sK)
    offs = [(front, [front], fshift + dF / 2 + 0.15), (None, mids, fshift + dF / 2 + 0.15 + 0.85 * (dF + dE) / 2)]
    offs.append((back, [back], offs[1][2] + 0.85 * (dE + dK) / 2))
    offs = offs[:rows]
    gid = gid or P.new_group(); out = []
    for ri, (_, keys, off) in enumerate(offs):
        dd = {0: dF, 1: dE, 2: dK}[ri]
        Lr = max(length - ri * 1.2 * dd, dd)
        k = max(1, int(round(Lr / (dd * 0.92))))
        for q in range(k):
            t = (q - (k - 1) / 2) * dd * 0.92 + (dd * 0.46 if ri % 2 else 0)
            key = keys[min(int(q / k * len(keys)), len(keys) - 1)]
            s = P.scale(key, {0: 0.95, 1: 1.0, 2: 1.05}[ri])
            p = base + nrm * off / PX + tan * t / PX
            # follow the edge: re-project onto the offset line using local dt
            ii, jj = int(p[0]), int(p[1])
            if 0 <= ii < bed.m.shape[0] and 0 <= jj < bed.m.shape[1] and bed.m[ii, jj]:
                err = off - bed.dt[ii, jj]
                g = np.array([gy[ii, jj], gx[ii, jj]]); gn = np.hypot(*g)
                if gn > 1e-6 and abs(err) < 1.5:
                    p = p + g / gn * err / PX
            if shrub_ok(bed, p[0], p[1], key, s) and P.shrub_free(p[0] + bed.r0, p[1] + bed.c0, D(key, s) / 2):
                out.append(P.add_shrub(bed, p[0], p[1], key, s, 'drift', gid, combo))
    if len(out) < 3 or len({o['key'] for o in out}) < 2:
        P.remove(out)
        return []
    return out


def facade_drifts(P, bed):
    """Rhythmic layered masses along true building edges, with deliberate gaps between compositions."""
    if bed.A < 10 or bed.min_bld > 2.5:
        return 0
    period = max(8.0, float(ARCHVIZ['facade_drift_period_m']))
    min_run = max(4.0, float(ARCHVIZ['facade_drift_min_run_m']))
    n = 0
    for cnt in G.offset_contours(bed, 1.1):
        lab = G.edge_labels(bed, cnt, 1.1)
        i = np.clip(cnt[:, 0].astype(int), 0, bed.m.shape[0] - 1)
        j = np.clip(cnt[:, 1].astype(int), 0, bed.m.shape[1] - 1)
        good = (lab == BLD) & (bed.d_play[i, j] >= 1.5) & (low_only(bed)[i, j] >= 0.8)
        for idx in G.runs(good)[0]:
            seg = cnt[idx]
            length = G.arclen(seg)
            if length < min_run:
                continue
            pts = _row_points(seg, period, min(2.0, length * 0.2))
            for q, (r, c) in enumerate(pts):
                R, C = r + bed.r0, c + bed.c0
                if any(True for _ in P.shrubs.near(R, C, period * 0.42 / PX)):
                    continue
                mass_len = min(7.5, max(4.5, length * 0.32))
                got = drift_at(P, bed, r, c, pick_combo(P, bed, q), length=mass_len, rows=3)
                if got:
                    n += len(got)
                    STATS['facade_masses'] += 1
    return n


def strip_groups(P, bed, period=7.5, glen=3.6):
    """beds too narrow for trees: rhythmic mixed groups along the medial axis (never a lone ball)."""
    n = 0
    combo = pick_combo(P, bed)
    back, mids, front = combo_rows(P, combo, play=False)
    for br in skeleton(bed):
        p = br.astype(float) + 0.5
        L = G.arclen(p)
        if L < 1.5:
            continue
        v = G.simplify(p, False, 0.8)
        pts, tans = G.resample_even(v, False, 0.45, 0.2)
        if not len(pts):
            continue
        ss = np.arange(len(pts)) * 0.45
        ph = P.rng.uniform(0, period - glen) if L > period else max((L - glen) / 2, 0)
        gid = None; cur = -1
        for (q, t, s0) in zip(pts, tans, ss):
            pos = (s0 - ph) % period
            if pos > glen or s0 < ph - 1e-6:
                continue
            if any(True for _ in P.trees.near(q[0] + bed.r0, q[1] + bed.c0, 4.0 / PX)):
                continue
            g = int((s0 - ph) // period)
            if g != cur:
                cur = g; gid = P.new_group()
            i, j = int(q[0]), int(q[1])
            w = bed.W3[i, j] if (0 <= i < bed.m.shape[0] and 0 <= j < bed.m.shape[1]) else 0
            nrm = np.array([t[1], -t[0]])
            # choose row layout by local width
            if w >= 3.2:
                lanes = [(-0.9, front), (0.0, mids[0]), (0.9, back)]
            elif w >= 2.2:
                lanes = [(-0.45, front), (0.45, mids[-1])]
            else:
                lanes = [(0.0, mids[0] if int(pos / 1.0) % 2 == 0 else front)]
            for li, (off, key) in enumerate(lanes):
                s = P.scale(key)
                dd = D(key, s)
                if w and dd + 0.25 > w:
                    # narrow strip: two small species that fit, alternating in pairs (never one model only)
                    fit = [k for k in (front, 'box072', 'rosv2', 'rosf05', 'box071', 'montra1', 'lavanda')
                           if D(k, SPC.base(k) * 1.1) + 0.25 <= w]
                    fit = list(dict.fromkeys(fit))
                    if len(fit) >= 2:
                        key = fit[(int(pos / 1.4) + li) % 2]; s = P.scale(key)
                        if D(key, s) + 0.25 > w:
                            s = (w - 0.25) / SPC.DIM[key][0]
                    else:
                        key = ('box071', 'box072')[int(pos / 1.4) % 2]
                        s = max(0.75, (w - 0.3) / SPC.DIM[key][0])
                qq = q + nrm * off / PX
                if shrub_ok(bed, qq[0], qq[1], key, s) and P.shrub_free(qq[0] + bed.r0, qq[1] + bed.c0, D(key, s) / 2, f=0.9):
                    P.add_shrub(bed, qq[0], qq[1], key, s, 'strip', gid, combo); n += 1
    return n


# ================================= repair =====================================================
def far_patches(P, bed, far=4.0, min_area=30.0, exclude=None):
    foot = P.canvas.crop(bed, 'foot')
    dist = cv2.distanceTransform((~foot).astype(np.uint8), cv2.DIST_L2, 5) * PX
    fm = bed.m & (dist > far)
    if exclude is not None:
        fm &= ~exclude
    n, lab, st, _ = cv2.connectedComponentsWithStats(fm.astype(np.uint8), connectivity=8)
    out = []
    for k in range(1, n):
        a = st[k, cv2.CC_STAT_AREA] * PX * PX
        if a > min_area:
            comp = lab == k
            dd = np.where(comp, dist, 0)
            i, j = np.unravel_index(np.argmax(dd), dd.shape)
            out.append((a, i + 0.5, j + 0.5, comp))
    return out


def bed_tree_profile(P, bed):
    trees = [r for r in P.recs if r['bed'] == bed.id and is_tree(r['key'])]
    can = P.canvas.crop(bed, 'can')
    canopy = float((can & bed.m).sum() / max(bed.m.sum(), 1))
    return len(trees), len(trees) * 100.0 / max(bed.A, 1.0), canopy


def repair_tree(P, bed, comp, r, c):
    """Add one structural tree at the best valid point of a bare patch, then underplant it."""
    ys, xs = np.nonzero(comp)
    order = np.argsort((ys - r) ** 2 + (xs - c) ** 2)
    placed = None
    for cl in ('L', 'M', 'S'):
        vm = valid_mask(bed, cl)
        sel = [o for o in order[:4000:7] if vm[ys[o], xs[o]]]
        for o in sel[:40]:
            ks = cands_for(P, None, (cl,))
            placed = try_tree(P, bed, ys[o] + 0.5, xs[o] + 0.5, ks, 'fill', P.new_group(),
                              f=0.6, min_m=float(ARCHVIZ['row_min_spacing_m']))
            if placed:
                break
        if placed:
            break
    if placed:
        rr, cc = placed['R'] - bed.r0, placed['C'] - bed.c0
        v = path_dir(bed, rr, cc, 'hard', 12.0)
        skirt(P, bed, placed, v if v is not None else edge_dir(bed, rr, cc), pick_combo(P, bed, 1))
    return placed


def repair_shrubs(P, bed, comp, r, c, edge_first=False):
    """Build one mixed, layered shrub composition; return its records or an empty list."""
    ys, xs = np.nonzero(comp)
    order = np.argsort((ys - r) ** 2 + (xs - c) ** 2)

    def edge_mass():
        for trial in range(6):
            o = order[min(trial * 37, len(order) - 1)]
            rr, cc = ys[o] + 0.5, xs[o] + 0.5
            got = drift_at(P, bed, rr, cc, pick_combo(P, bed, trial),
                           length=P.rng.uniform(4.5, 7.0), rows=3)
            if got:
                return got
        return []

    if edge_first:
        got = edge_mass()
        return got or lens_group(P, bed, comp) or ridge_group(P, bed, comp)
    got = lens_group(P, bed, comp) or ridge_group(P, bed, comp)
    return got or edge_mass()


def repair_bed(P, bed, glade_mask=None, rounds=16):
    added = 0
    for rnd in range(rounds):
        ps = far_patches(P, bed, 3.6, 20.0 if rnd < rounds - 3 else 10.0, glade_mask)
        if not ps:
            break
        progress = False
        for a, r, c, comp in sorted(ps, key=lambda x: -x[0]):
            before = len(P.recs)
            nt, density, canopy = bed_tree_profile(P, bed)
            tree_heavy = density >= float(ARCHVIZ['tree_heavy_per_100m2']) or \
                canopy >= float(ARCHVIZ['tree_heavy_canopy'])
            edge_context = bed.fac_frac >= 0.08 or bed.type in ('T2', 'T3', 'T9', 'T9s') or bed.elong > 4
            shrub_first = tree_heavy or edge_context
            if shrub_first:
                STATS['repair_shrub_first'] += 1
                got = repair_shrubs(P, bed, comp, r, c, edge_first=edge_context)
                if not got:
                    repair_tree(P, bed, comp, r, c)
            else:
                STATS['repair_tree_first'] += 1
                placed = repair_tree(P, bed, comp, r, c)
                if not placed:
                    repair_shrubs(P, bed, comp, r, c, edge_first=bed.fac_frac >= 0.08)
            delta = len(P.recs) - before
            if delta:
                progress = True
                added += delta
        if not progress:
            break
    return added


def lens_group(P, bed, comp, length=4.0):
    """mixed shrub group centred on the deepest point of a bare patch, long axis along the patch"""
    ys, xs = np.nonzero(comp)
    dd = bed.dt[ys, xs]
    k = int(np.argmax(dd)); r, c = ys[k] + 0.5, xs[k] + 0.5
    pts = np.stack([ys, xs], 1).astype(float)
    cov = np.cov((pts - pts.mean(0)).T) if len(pts) > 3 else np.eye(2)
    w, v = np.linalg.eigh(cov)
    ax = v[:, -1]; nrm = np.array([-ax[1], ax[0]])
    combo = pick_combo(P, bed, 2)
    back, mids, front = combo_rows(P, combo, play=bed.d_play[int(r), int(c)] < 10)
    wloc = 2 * bed.dt[int(r), int(c)]
    if wloc >= 3.2:
        lanes = [(-0.95, front), (0.0, None), (0.95, back)]
    elif wloc >= 2.1:
        lanes = [(-0.45, front), (0.45, None)]
    else:
        lanes = [(0.0, None)]
    gid = P.new_group(); out = []
    for li, (off, key0) in enumerate(lanes):
        n = max(3, int(length / 0.9))
        for q in range(n):
            t = (q - (n - 1) / 2) * 0.9 + (0.45 if li % 2 else 0)
            key = key0 or (mids[0] if q < n / 2 or len(mids) == 1 else mids[-1])
            if key0 is None and len(lanes) == 1 and q % 3 == 2:
                key = front
            s = P.scale(key)
            if D(key, s) + 0.2 > wloc:
                key = ('box071', 'box072')[q % 2]
                s = min(P.scale(key), max(0.75, (wloc - 0.25) / SPC.DIM[key][0]))
            p = np.array([r, c]) + ax * t / PX + nrm * off / PX
            if shrub_ok(bed, p[0], p[1], key, s) and P.shrub_free(p[0] + bed.r0, p[1] + bed.c0, D(key, s) / 2, f=0.9):
                out.append(P.add_shrub(bed, p[0], p[1], key, s, 'group', gid, combo))
    if len(out) < 3 or len({o['key'] for o in out}) < 2:
        P.remove(out); return []
    return out


def ridge_group(P, bed, comp):
    """last resort for thin strips: small mixed balls on the ridge (medial) pixels of the bare patch"""
    from scipy import ndimage as ndi
    mx = ndi.maximum_filter(bed.dt, size=5)
    ridge = comp & (bed.dt >= mx - 1e-3)
    ys, xs = np.nonzero(ridge)
    if not len(ys):
        return []
    order = np.lexsort((xs, ys))
    pts = np.stack([ys[order], xs[order]], 1).astype(float) + 0.5
    gid = P.new_group(); out = []; q = 0
    for p in pts:
        if any(math.hypot(p[0] - (o['R'] - bed.r0), p[1] - (o['C'] - bed.c0)) * PX < 0.8 for o in out[-6:]):
            continue
        key = ('box071', 'box072', 'rosv2')[q % 3]
        w = 2 * bed.dt[int(p[0]), int(p[1])]
        s = min(P.scale(key), max(0.7, (w - 0.25) / SPC.DIM[key][0]))
        if shrub_ok(bed, p[0], p[1], key, s) and P.shrub_free(p[0] + bed.r0, p[1] + bed.c0, D(key, s) / 2, f=0.9):
            out.append(P.add_shrub(bed, p[0], p[1], key, s, 'group', gid, 'ridge')); q += 1
        if len(out) >= 5:
            break
    if len(out) < 3 or len({o['key'] for o in out}) < 2:
        P.remove(out); return []
    return out


def island_group(P, bed, r, c):
    combo = pick_combo(P, bed, 2)
    back, mids, front = combo_rows(P, combo, play=bed.d_play[int(r), int(c)] < 10)
    gid = P.new_group(); out = []
    ring = [(0, 0, back)] + [(1.0, a, mids[k % len(mids)]) for k, a in enumerate(np.linspace(0, 2 * math.pi, 6, endpoint=False))] + \
        [(1.9, a + 0.3, front) for a in np.linspace(0, 2 * math.pi, 9, endpoint=False)]
    for rad, a, key in ring:
        s = P.scale(key)
        rr, cc = r + math.sin(a) * rad / PX, c + math.cos(a) * rad / PX
        if shrub_ok(bed, rr, cc, key, s) and P.shrub_free(rr + bed.r0, cc + bed.c0, D(key, s) / 2):
            out.append(P.add_shrub(bed, rr, cc, key, s, 'island', gid, combo))
    if len(out) < 4 or len({o['key'] for o in out}) < 2:
        P.remove(out); return []
    return out


# ================================= driver =====================================================
def glades_for(P, bed):
    """parks only: one deliberate glade (r = 8 m) per 3000 m2 of large lawn, at the deepest points"""
    if P.lot not in SPC.PARK_LOTS or bed.A < 1500 or bed.maxr < 11:
        return []
    out = []
    dt = bed.dt.copy()
    for _ in range(max(1, int(bed.A // 3000))):
        i, j = np.unravel_index(np.argmax(dt), dt.shape)
        if dt[i, j] < 11:
            break
        out.append((i + 0.5, j + 0.5, 8.0))
        yy, xx = np.ogrid[:dt.shape[0], :dt.shape[1]]
        dt[((yy - i) ** 2 + (xx - j) ** 2) * PX * PX < 30 ** 2] = 0
    return out


def glade_mask(bed, glades, rad_extra=0.0):
    if not glades:
        return None
    yy, xx = np.ogrid[:bed.m.shape[0], :bed.m.shape[1]]
    m = np.zeros(bed.m.shape, bool)
    for (r, c, rad) in glades:
        m |= ((yy - r) ** 2 + (xx - c) ** 2) * PX * PX <= (rad + rad_extra) ** 2
    return m


def diversify_groups(P):
    """tree groups of >= 3 must mix species: swap one member to a same-class, same-tone companion"""
    g = collections.defaultdict(list)
    for r in P.recs:
        if is_tree(r['key']) and r['role'] in ('cluster',):
            g[r['gid']].append(r)
    for v in g.values():
        if len(v) >= 3 and len({SPC.mesh(r['key']) for r in v}) < 2:
            k0 = v[0]['key']; cl = role(k0)
            alts = [k for k, w in P.grp.get(cl, []) if SPC.mesh(k) != SPC.mesh(k0) and tone(k) == tone(k0)] or                    [k for k, w in P.grp.get(cl, []) if SPC.mesh(k) != SPC.mesh(k0) and {tone(k), tone(k0)} != {'D', 'Y'}]
            if alts:
                rec = v[len(v) // 2]
                rec['key'] = alts[0]
                rec['s'] = round(SPC.base(alts[0]) * P.rng.uniform(0.9, 1.1), 3)
                for _, _, it in P.trees.near(rec['R'], rec['C'], 0.5):
                    if it.get('rec') is rec:
                        it.update(key=rec['key'], D=D(rec['key'], rec['s']), tone=tone(rec['key']))
                STATS['group_species_swapped'] += 1


def cleanup_small_groups(P):
    g = collections.defaultdict(list)
    for r in P.recs:
        if not is_tree(r['key']):
            g[r['gid']].append(r)
    bad = [r for v in g.values() if len(v) < 3 or len({x['key'] for x in v}) < 2 for r in v]
    STATS['small_shrub_groups_removed'] += len(bad)
    if bad:
        P.remove(bad)


def is_podium(b):
    """lawn islands enclosed by the building mask (roof / podium gardens with no ground z): not planted"""
    return b.ctx['bld'] >= 0.8 and float(b.d_bld[b.m].max()) < 5.0


def design_lot(S, lot, beds, seed=0):
    group = SPC.LOT_GROUP.get(lot, 'fresh')
    P = Planter(lot, group, seed)
    B = [Bed(S, bid) for bid in beds]
    B = [b for b in B if b.A >= 1.0]
    P.podium = [b.summary() for b in B if is_podium(b)]
    B = [b for b in B if not is_podium(b)]
    by_id = {b.id: b for b in B}
    P.canvas = Canvas(B)
    glades = {b.id: glades_for(P, b) for b in B}
    # 1-2 structure
    for b in B:
        street_rows(P, b)
    for b in B:
        play_shade(P, b)
    # 3 path framing + band rows
    for b in sorted(B, key=lambda b: -b.A):
        if b.A >= 250 and b.Wmax >= 14:
            path_frame_rows(P, b)
    for b in B:
        if b.type in ('T9', 'T9s', 'T3', 'T2', 'TX', 'T11') or b.elong > 4:
            axis_rows(P, b, wband=(3.0, 11.0) if b.type not in ('TX', 'T11') else (3.4, 10.0),
                      min_len=6.0 if b.type not in ('TX', 'T11') else 14.0)
    # 4 conifers
    if P.grp.get('C'):
        done = 0
        for b in sorted(B, key=lambda b: -b.A)[:4]:
            if conifer_group(P, b):
                done += 1
            if done >= (2 if sum(x.A for x in B) > 8000 else 1):
                break
    # 5 coverage fill
    for b in sorted(B, key=lambda b: -b.A):
        tgt = 0.55 if P.lot in SPC.PARK_LOTS else 0.66
        fill_clusters(P, b, tgt, glades=glades[b.id])
    diversify_groups(P)
    P.canvas.redraw(P.recs)
    # 6 skirts
    skirts_for_lot(P, by_id)
    # 7 designed facade masses, then narrow-bed rhythm
    for b in B:
        facade_drifts(P, b)
    for b in B:
        if b.Wmed < 4.0:
            strip_groups(P, b)
    # no lone balls: shrub groups cut down to 1-2 plants (by trees nearby) are removed
    cleanup_small_groups(P)
    # 8 repair loop
    for b in sorted(B, key=lambda b: -b.A):
        repair_bed(P, b, glade_mask(b, glades[b.id], -0.5))
    return P, B, glades


def to_world(P):
    out = []
    for r in P.recs:
        x, y = X0 + r['C'] * RES, Y0 + r['R'] * RES
        out.append(dict(mesh=SPC.mesh(r['key']), x=round(float(x), 1), y=round(float(y), 1), z=round(float(r['z']), 1),
                        roll=round(float(r['roll']), 3), pitch=round(float(r['pitch']), 3), yaw=round(float(r['yaw']) % 360, 2),
                        s=round(float(r['s']), 3)))
    return out


def lot_beds(S):
    by = collections.defaultdict(list)
    for bid, info in S.bedinfo.items():
        if info.get('lot'):
            by[info['lot']].append(bid)
    return by


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('levels', nargs='*', help='only these FOL_ levels (default: every lot in beds_st1.json)')
    ap.add_argument('--tag', default=env.CFG['engine']['tag'], help='output tag (default from config.engine.tag)')
    a = ap.parse_args()
    t0 = time.time()
    S = Site()
    by = lot_beds(S)
    only = a.levels
    xf, meta = {}, {}
    salt = int(env.CFG['engine'].get('seed_salt', 7919))
    for lot, beds in sorted(by.items()):
        lvl = lot_level_name(lot)
        if only and lvl not in only:
            continue
        P, B, gl = design_lot(S, lot, beds, seed=sum(map(ord, lot)) * salt % 100003)
        xf[lvl] = to_world(P)
        meta[lvl] = dict(lot=lot, palette=P.gname, recs=P.recs, podium=P.podium, glades={k: v for k, v in gl.items() if v},
                         beds=[dict(b.summary(), r0=b.r0, c0=b.c0) for b in B])
        nt = sum(1 for r in P.recs if is_tree(r['key']))
        print('%-22s %-8s beds=%3d inst=%5d trees=%4d shrubs=%5d  %.0fs' % (lvl, P.gname, len(B), len(P.recs), nt,
              len(P.recs) - nt, time.time() - t0), flush=True)
    tag = 'part' if only else a.tag
    json.dump(xf, open(os.path.join(OUT, 'xf_%s.json' % tag), 'w'))
    pickle.dump(meta, open(os.path.join(OUT, 'meta_%s.pkl' % tag), 'wb'))
    json.dump(STATS, open(os.path.join(OUT, 'engine_stats_%s.json' % tag), 'w'), indent=1)
    print('total', sum(len(v) for v in xf.values()), 'trees', sum(1 for m in meta.values() for r in m['recs'] if is_tree(r['key'])),
          '%.0fs' % (time.time() - t0))
    print(dict(STATS))
    print('written', os.path.join(OUT, 'xf_%s.json' % tag))
