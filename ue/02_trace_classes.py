"""STEP 2 (in editor): classify the surroundings of every lawn with vertical line traces on a 1 m grid.

Needs step 1 (grid.json, label025.npy). Chunked: every call traces for ~chunk_seconds and returns progress;
call it again until done=True (state is kept in builtins['_uefol_trace'] as plain numpy only - no UObjects).
Pass ARGS={'reset': True} to start over.

Classes (uint8): 0 none/no hit, 1 grass, 2 road, 3 paving, 4 playground, 5 water, 6 tall (building, > ground+3 m),
                 7 low obstacle (> ground+0.3 m, not a ground material), 8 other.
Material -> class comes from config.material_classes (by material NAME).
Outputs (work dir):  cls1.npy (uint8, 1 m grid = label grid / 4), z1.npy (float32 hit z, cm, NaN = no hit),
                     env_mats.json (hits per material set: count, median height above ground, owners) - read it
                     for a new project and extend config.material_classes.
Origin: Zaliniy calls #114-#119 (trace_chunk + mclass), made resumable.
"""
import builtins
import json
import os
import sys
import time

import numpy as np

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
import ue_common as U  # noqa: E402
import unreal  # noqa: E402
import cv2  # noqa: E402

A = U.args(dict(reset=False, budget=U.CFG['raster']['chunk_seconds']))
GRASS, ROAD, PAVE, PLAY, WATER, TALL, LOW, OTHER, NONE = 1, 2, 3, 4, 5, 6, 7, 8, 0
MC = U.CFG['material_classes']
CLS_OF = (('grass', GRASS), ('road', ROAD), ('paving', PAVE), ('playground', PLAY), ('water', WATER))


def mclass(n):
    if n is None:
        return OTHER
    for key, c in CLS_OF:
        r = MC.get(key, {})
        if n in r.get('names', ()) or any(n.startswith(p) for p in r.get('prefixes', ())) \
                or any(s in n for s in r.get('contains', ())):
            return c
    return OTHER


def init():
    g = json.load(open(U.W('grid.json')))
    lab = np.load(U.W('label025.npy'))
    H1, W1 = g['H'] // 4, g['W'] // 4
    g1 = cv2.resize((lab > 0).astype(np.uint8), (W1, H1), interpolation=cv2.INTER_AREA)
    g1 = (g1 > 0).astype(np.uint8)
    k = 2 * int(U.CFG['raster']['near_grass_m']) + 1
    near = cv2.dilate(g1, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    ys, xs = np.nonzero(near)
    del lab
    return dict(xs=xs, ys=ys, hz=np.full(len(xs), np.nan, np.float32), cls=np.zeros(len(xs), np.uint8),
                key=np.full(len(xs), -1, np.int32), keys=[], kid={}, comp_cls={}, face_cls={},
                pos=0, H1=H1, W1=W1, x0=g['x0'], y0=g['y0'], res1=g['res'] * 4, owners={})


def comp_info(E, c):
    """(key index, single class or None) for a hit component, cached by its path name (string only)"""
    p = c.get_path_name()
    if p in E['comp_cls']:
        return E['comp_cls'][p]
    try:
        mats = [x.get_name() if x else None for x in c.get_materials()]
    except Exception:
        mats = [None]
    key = mats[0] if len(set(mats)) == 1 else 'MULTI:' + ','.join(sorted(set(str(x) for x in mats))[:4])
    if key not in E['kid']:
        E['kid'][key] = len(E['keys']); E['keys'].append(key)
    try:
        own = c.get_owner().get_actor_label()
    except Exception:
        own = '?'
    E['owners'].setdefault(key, set()).add(own)
    cs = set(mclass(n) for n in mats)
    v = (E['kid'][key], cs.pop() if len(cs) == 1 else None)
    E['comp_cls'][p] = v
    return v


def finish(E):
    G = float(U.CFG['ground_z_cm'])
    hz, cls = E['hz'], E['cls']
    tall = (hz - G) > float(U.CFG['tall_above_ground_cm'])
    low = ((hz - G) > float(U.CFG['low_above_ground_cm'])) & ~tall & ~np.isin(cls, [GRASS, ROAD, PAVE, PLAY, WATER])
    cls[tall] = TALL
    cls[low & (cls == OTHER)] = LOW
    cls[np.isnan(hz)] = NONE
    R = np.zeros((E['H1'], E['W1']), np.uint8); R[E['ys'], E['xs']] = cls
    Zr = np.full((E['H1'], E['W1']), np.nan, np.float32); Zr[E['ys'], E['xs']] = hz
    np.save(U.W('cls1.npy'), R); np.save(U.W('z1.npy'), Zr)
    rows = []
    for key, k in E['kid'].items():
        m = E['key'] == k
        n = int(m.sum())
        rows.append([key, n, float(np.nanmedian(hz[m]) - G) if n else None, sorted(E['owners'].get(key, ()))[:5]])
    rows.sort(key=lambda r: -r[1])
    json.dump(rows, open(U.W('env_mats.json'), 'w'), indent=0)
    u, c = np.unique(cls, return_counts=True)
    return {int(a): int(b) for a, b in zip(u, c)}


def main():
    w = U.editor_world()
    if A['reset'] or '_uefol_trace' not in builtins.__dict__:
        builtins._uefol_trace = init()
    E = builtins._uefol_trace
    TT = unreal.TraceTypeQuery.TRACE_TYPE_QUERY1; DN = unreal.DrawDebugTrace.NONE
    LT = unreal.SystemLibrary.line_trace_single
    top, bot = float(U.CFG['raster']['trace_top_cm']), float(U.CFG['raster']['trace_bottom_cm'])
    x0, y0, r1 = E['x0'], E['y0'], E['res1']
    xs, ys = E['xs'], E['ys']
    t = time.time(); i = E['pos']; n = len(xs)
    while i < n and time.time() - t < float(A['budget']):
        for _ in range(2000):
            if i >= n:
                break
            x = x0 + (xs[i] + 0.5) * r1; y = y0 + (ys[i] + 0.5) * r1
            h = LT(w, unreal.Vector(x, y, top), unreal.Vector(x, y, bot), TT, True, [], DN, True)
            if h:
                tp = h.to_tuple(); c = tp[10]
                E['hz'][i] = tp[4].z
                if c is not None:
                    k, single = comp_info(E, c)
                    E['key'][i] = k
                    if single is not None:
                        E['cls'][i] = single
                    else:
                        fk = (c.get_path_name(), int(tp[15]))
                        v = E['face_cls'].get(fk)
                        if v is None:
                            try:
                                mat, _sec = c.get_material_from_collision_face_index(int(tp[15]))
                                v = mclass(mat.get_name() if mat else None)
                            except Exception:
                                v = OTHER
                            E['face_cls'][fk] = v
                        E['cls'][i] = v
                    del c
                del tp
            del h
            i += 1
    E['pos'] = i
    del w
    out = dict(pos=i, of=n, pct=round(100.0 * i / max(n, 1), 1), materials=len(E['keys']), sec=round(time.time() - t, 1))
    if i >= n:
        out['counts'] = finish(E)
        out['done'] = True
        builtins.__dict__.pop('_uefol_trace', None)
    else:
        out['done'] = False
    return out


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
