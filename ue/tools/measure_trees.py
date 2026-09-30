"""TOOL (in editor): geometric measurement of tree meshes -> work/tree_geo.json (the engine reads data/tree_geo.json).

Only needed for NEW meshes. Per mesh: bbox, height, trunk base / DBH / stem profile from bark cross-sections,
crown width x/y (2-98 percentile of leaf vertices), crown base. Leaf vs bark sections are told apart by the
MF_Season_Leaf / MF_Season_Bark function used by the base material (fallback: material name).
Needs work/tree_meta.json or data/tree_meta.json. Loads one mesh at a time; stops when free RAM < ARGS min_free_gb.
ARGS: paths (list; default every mesh of tree_meta), budget (s), min_free_gb (14).
Copy the new entries into data/tree_geo.json and give them a role/base scale in offline/lib/species6.py.
Origin: tree_geo.py of the Zaliniy session.
"""
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import builtins, json, time  # noqa: E402
import numpy as np  # noqa: E402
import unreal  # noqa: E402

OUT = U.W('tree_geo.json')
ar = unreal.AssetRegistryHelpers.get_asset_registry()
opt = unreal.AssetRegistryDependencyOptions()
store = builtins.__dict__.setdefault('_uefol_tgeo', {})   # plain dicts only
_kind_cache = {}


_tm = U.W('tree_meta.json') if os.path.exists(U.W('tree_meta.json')) else U.D('tree_meta.json')
_TMETA = json.load(open(_tm))


def kind(mat_meta):
    """bark / leaf / none — by which season function the base material uses."""
    if not mat_meta:
        return 'none'
    b = mat_meta['base']
    if b not in _kind_cache:
        deps = [str(d) for d in (ar.get_dependencies(b, opt) or [])]
        if any(d.endswith('MF_Season_Bark') for d in deps):
            k = 'bark'
        elif any(d.endswith('MF_Season_Leaf') for d in deps):
            k = 'leaf'
        else:
            n = (mat_meta['name'] + b).lower()
            k = 'leaf' if any(s in n for s in ('leaf', 'needle', 'petal', 'foliage')) else 'bark'
        _kind_cache[b] = k
    return _kind_cache[b]


def section(sm, s):
    v, t, *_ = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, s)
    if not v:
        return np.zeros((0, 3), np.float64), np.zeros((0, 3), np.int64)
    return np.array([[p.x, p.y, p.z] for p in v], dtype=np.float64), np.array(t, dtype=np.int64).reshape(-1, 3)


def cross_section(V, T, z):
    """Intersect triangles with plane Z=z. Returns list of loops: dict(area, cx, cy, w)."""
    tz = V[T][:, :, 2] - z
    s = np.sign(tz); s[s == 0] = 1e-9
    cross = ~((s > 0).all(1) | (s < 0).all(1))
    if not cross.any():
        return []
    TT = T[cross]; P = V[TT]; D = tz[cross]
    # consistent orientation: segment runs from the edge crossing upward (below->above)
    # to the edge crossing downward (above->below), following triangle winding
    up_pt = np.zeros((len(D), 2)); dn_pt = np.zeros((len(D), 2))
    n_up = np.zeros(len(D), int); n_dn = np.zeros(len(D), int)
    for (a, b) in ((0, 1), (1, 2), (2, 0)):
        da, db = D[:, a], D[:, b]
        m = (da * db) < 0
        t = np.where(m, da / np.where(m, da - db, 1), 0)
        pt = P[:, a, :2] + t[:, None] * (P[:, b, :2] - P[:, a, :2])
        up = m & (da < 0); dn = m & (da > 0)
        up_pt[up] = pt[up]; dn_pt[dn] = pt[dn]; n_up += up; n_dn += dn
    ok = (n_up == 1) & (n_dn == 1)
    p1 = up_pt[ok]; p2 = dn_pt[ok]
    # union-find on rounded endpoints (0.05 cm)
    k1 = np.round(p1 * 20).astype(np.int64); k2 = np.round(p2 * 20).astype(np.int64)
    keys = np.vstack([k1, k2])
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel(); n = len(p1)
    a_id, b_id = inv[:n], inv[n:]
    parent = np.arange(inv.max() + 1)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i in range(n):
        ra, rb = find(a_id[i]), find(b_id[i])
        if ra != rb:
            parent[ra] = rb
    comp = np.array([find(x) for x in a_id])
    loops = []
    cr = p1[:, 0] * p2[:, 1] - p2[:, 0] * p1[:, 1]
    for c in np.unique(comp):
        m = comp == c
        if m.sum() < 3:
            continue
        area = abs(cr[m].sum()) / 2
        q = np.vstack([p1[m], p2[m]])
        # closed loop: every endpoint key used exactly twice
        ids = np.concatenate([a_id[m], b_id[m]])
        _, cnt = np.unique(ids, return_counts=True)
        loops.append(dict(area=float(area), cx=float(q[:, 0].mean()), cy=float(q[:, 1].mean()),
                          w=float((np.ptp(q[:, 0]) + np.ptp(q[:, 1])) / 2), n=int(m.sum()),
                          closed=bool((cnt == 2).all())))
    return loops


def stem_at(V, T, z, axis, max_dist):
    """Largest loop whose centre is within max_dist of axis."""
    L = [l for l in cross_section(V, T, z) if np.hypot(l['cx'] - axis[0], l['cy'] - axis[1]) <= max_dist and l['w'] > 0.3]
    if not L:
        return None, 0
    best = max(L, key=lambda l: l['w'])
    big = sum(1 for l in L if l['w'] >= 0.5 * best['w'])
    return best, big


def analyze(p):
    meta = _TMETA[p]
    sm = unreal.load_asset(p)
    kinds = [kind(m) for m in meta['mats']]
    BV = []; BT = []; L = []; off = 0
    for s, k in enumerate(kinds):
        if s >= sm.get_num_sections(0):
            continue
        V, T = section(sm, s)
        if k == 'leaf':
            L.append(V)
        else:
            BV.append(V); BT.append(T + off); off += len(V)
    BV = np.vstack(BV) if BV else np.zeros((0, 3)); BT = np.vstack(BT) if BT else np.zeros((0, 3), np.int64)
    L = np.vstack(L) if L else np.zeros((0, 3))
    A = np.vstack([BV, L])
    bb = sm.get_bounding_box()
    r = dict(kinds=kinds, n_bark=int(len(BV)), n_leaf=int(len(L)),
             zmin=float(A[:, 2].min()), zmax=float(A[:, 2].max()),
             xmin=float(A[:, 0].min()), xmax=float(A[:, 0].max()),
             ymin=float(A[:, 1].min()), ymax=float(A[:, 1].max()),
             bbox=[round(bb.min.x), round(bb.min.y), round(bb.min.z), round(bb.max.x), round(bb.max.y), round(bb.max.z)])
    H = r['zmax']
    if len(BT):
        zb = float(BV[:, 2].min())
        # base: largest loop 30 cm above lowest bark point, near the bark median
        axis0 = np.median(BV[BV[:, 2] <= zb + 60][:, :2], axis=0)
        base, _ = stem_at(BV, BT, zb + 30, axis0, 200)
        if base:
            axis = np.array([base['cx'], base['cy']]); c0 = axis.copy()
            r['trunk_base_z'] = zb
            r['trunk_base_xy'] = [base['cx'], base['cy']]
            r['d_base30'] = base['w']
            prev_d = r['d_base30']
            stems = {}
            heights = sorted(set([130.0, 0.25 * H, 0.5 * H, 0.75 * H]))
            # walk up in 20 cm steps to track the axis and find where the stem splits
            split = None; z = zb + 50; pts = {}
            while z < H * 0.9:
                st, nbig = stem_at(BV, BT, z, axis, max(prev_d, 10))
                if st is None:
                    split = split or z; break
                d = st['w']
                if split is None and (nbig >= 2 or d < 0.55 * prev_d):
                    split = z
                axis = np.array([st['cx'], st['cy']]); prev_d = d
                pts[round(z)] = (d, axis.copy(), nbig)
                z += 20
            r['stem_split_z'] = split
            for h in heights:
                if not pts:
                    break
                zz = min(pts, key=lambda k: abs(k - h))
                if abs(zz - h) <= 20:
                    d, ax, nb = pts[zz]
                    stems[f'd_{int(round(h))}'] = round(d, 1)
                    if h == 130.0:
                        r['dbh'] = d
                        r['lean_deg'] = float(np.degrees(np.arctan2(np.hypot(*(ax - c0)), 130 - zb)))
            r['stem_profile'] = stems
            # all stems at 1.3 m (multi-stem trees / shrubs): equivalent diameter sqrt(sum d^2)
            if H > 140:
                cand = [l for l in cross_section(BV, BT, 130.0)
                        if np.hypot(l['cx'] - c0[0], l['cy'] - c0[1]) <= 150
                        and l['w'] >= max(0.25 * r['d_base30'], 1.0)]
                r['stems_130'] = len(cand)
                r['dbh_eq'] = float(np.sqrt(sum(l['w'] ** 2 for l in cand))) if cand else None
    C = L if len(L) else A
    if len(C):
        r['crown_base'] = float(np.percentile(C[:, 2], 2))
        r['crown_w_x'] = float(np.percentile(C[:, 0], 98) - np.percentile(C[:, 0], 2))
        r['crown_w_y'] = float(np.percentile(C[:, 1], 98) - np.percentile(C[:, 1], 2))
        cc = np.median(C[:, :2], axis=0)
        r['crown_centre_xy'] = [float(cc[0]), float(cc[1])]
    del sm
    return r


def run(paths, budget=90, min_free_gb=14):
    t0 = time.time(); done = []
    for p in paths:
        if p in store:
            continue
        if time.time() - t0 > budget:
            break
        m = U.mem()
        if m['phys_free_gb'] < min_free_gb:
            done.append(('STOP_low_mem', m)); break
        t = time.time()
        try:
            store[p] = analyze(p)
        except Exception as e:
            import traceback
            store[p] = dict(err=traceback.format_exc()[-400:])
        unreal.SystemLibrary.collect_garbage()
        json.dump(store, open(OUT, 'w'), indent=0)
        done.append((p.split('/')[-1], round(time.time() - t, 1)))
    return dict(done=done, total=len(store), mem=U.mem())


if __name__ == '__main__':
    A = U.args(dict(paths=None, budget=90, min_free_gb=14))
    P = A['paths'] or sorted(k for k, v in _TMETA.items() if 'err' not in v)
    RESULT = run(P, A['budget'], A['min_free_gb'])
    print(RESULT)
