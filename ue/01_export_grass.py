"""STEP 1 (in editor): find every lawn mesh (grass material) in the open persistent level, split it into
triangle islands and rasterize them at 0.25 m.

Open the persistent level first (config.persistent_level). Read-only for the scene.
Outputs (work dir):
  label025.npy       int32 [H,W]  0 = no lawn, k = island k (1-based, index into islands_raw.json)
  grid.json          {x0, y0, W, H, res}: world cm of pixel (col c, row r) = (x0 + c*res, y0 + r*res)
  islands_raw.json   per island: comp index, actor label, z/zmin/zmax, mesh area, triangle count
  grass_comps.json   one row per grass component (actor, mesh, transform) for auditing
Origin: zones.py step1 of the Zaliniy session (+ the inline component collection, call #109).
"""
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

A = U.args(dict(roof_z_cm=U.CFG['raster']['roof_z_cm'], res_cm=U.CFG['raster']['res_cm'],
                margin_cm=U.CFG['raster']['margin_cm']))
GRASS = set(U.CFG['grass_materials'])


def world_tris(c):
    """world-space triangles (N,3,3) of the grass sections of one StaticMeshComponent"""
    sm = c.get_editor_property('static_mesh')
    if sm is None:
        return np.zeros((0, 3, 3))
    mats = c.get_materials()
    xf = c.get_world_transform(); q_ = xf.rotation
    R = np.array([[ax.x, ax.y, ax.z] for ax in (q_.get_axis_x(), q_.get_axis_y(), q_.get_axis_z())]).T
    M = R @ np.diag([xf.scale3d.x, xf.scale3d.y, xf.scale3d.z])
    tr = np.array([xf.translation.x, xf.translation.y, xf.translation.z])
    out = []
    for s, m in enumerate(mats):
        if not (m and m.get_path_name() in GRASS) or s >= sm.get_num_sections(0):
            continue
        v, t, *_ = unreal.ProceduralMeshLibrary.get_section_from_static_mesh(sm, 0, s)
        if not v:
            continue
        va = np.array([[p.x, p.y, p.z] for p in v]) @ M.T + tr
        out.append(va[np.array(t).reshape(-1, 3)])
    return np.vstack(out) if out else np.zeros((0, 3, 3))


def islands_of(tris):
    """connected triangle groups (shared welded vertex, 1 cm)"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    P = tris.reshape(-1, 3)
    _, vid = np.unique(np.round(P).astype(np.int64), axis=0, return_inverse=True)
    vid = vid.ravel().reshape(-1, 3)
    n = vid.max() + 1
    r = np.concatenate([vid[:, 0], vid[:, 1]]); c = np.concatenate([vid[:, 1], vid[:, 2]])
    g = coo_matrix((np.ones(len(r)), (r, c)), shape=(n, n))
    _, lab = connected_components(g, directed=False)
    return lab[vid[:, 0]]


def main():
    t0 = time.time()
    U.editor_world()
    res = float(A['res_cm']); roof = float(A['roof_z_cm']); margin = float(A['margin_cm'])
    rows, isl, tri_store = [], [], []
    ci = -1
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            mats = c.get_materials()
            if not any(m and m.get_path_name() in GRASS for m in mats):
                continue
            ci += 1
            sm = c.get_editor_property('static_mesh'); t = c.get_world_transform(); r = t.rotation.rotator()
            rows.append(dict(i=ci, actor=a.get_actor_label(), comp=c.get_name(), ctype=type(c).__name__,
                             mesh=sm.get_path_name() if sm else None,
                             level=a.get_outer().get_path_name().split('/')[-1],
                             loc=[round(t.translation.x), round(t.translation.y), round(t.translation.z)],
                             rot=[round(r.roll, 2), round(r.pitch, 2), round(r.yaw, 2)],
                             scl=[round(t.scale3d.x, 3), round(t.scale3d.y, 3), round(t.scale3d.z, 3)]))
            tr = world_tris(c)
            if not len(tr) or tr[:, :, 2].min() > roof:      # roof gardens are skipped
                continue
            lab = islands_of(tr)
            for k in np.unique(lab):
                tk = tr[lab == k]
                p0, p1, p2 = tk[:, 0], tk[:, 1], tk[:, 2]
                area = float(np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1).sum() / 2 / 1e4)
                isl.append(dict(comp=ci, actor=a.get_actor_label(), z=float(tk[:, :, 2].mean()),
                                zmin=float(tk[:, :, 2].min()), zmax=float(tk[:, :, 2].max()), area_mesh=area,
                                ntri=int(len(tk))))
                tri_store.append(tk)
    if not tri_store:
        return dict(err='no grass triangles found - check config.grass_materials and the open level', comps=len(rows))
    allp = np.vstack([t.reshape(-1, 3) for t in tri_store])
    x0, y0 = allp[:, 0].min() - margin, allp[:, 1].min() - margin
    x1, y1 = allp[:, 0].max() + margin, allp[:, 1].max() + margin
    Wd = int(np.ceil((x1 - x0) / res)); Hd = int(np.ceil((y1 - y0) / res))
    Wd += (-Wd) % 4; Hd += (-Hd) % 4          # multiple of 4 so the 1 m grid is exactly /4
    label = np.zeros((Hd, Wd), np.int32)
    for idx in np.argsort([d['z'] for d in isl]):    # lower islands first so stacked (upper) ones win
        tk = tri_store[idx]
        pts = np.stack([(tk[:, :, 0] - x0) / res, (tk[:, :, 1] - y0) / res], -1)
        pts = np.round(pts * 4).astype(np.int32)      # shift=2 -> quarter-pixel precision
        cv2.fillPoly(label, list(pts), int(idx + 1), lineType=cv2.LINE_8, shift=2)
    np.save(U.W('label025.npy'), label)
    json.dump(dict(x0=float(x0), y0=float(y0), W=Wd, H=Hd, res=res), open(U.W('grid.json'), 'w'))
    json.dump(isl, open(U.W('islands_raw.json'), 'w'), indent=0)
    json.dump(rows, open(U.W('grass_comps.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    del tri_store, allp
    return dict(level=U.world_name(), comps=len(rows), islands=len(isl), grid=[Wd, Hd],
                sec=round(time.time() - t0, 1), mem=U.mem())


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
