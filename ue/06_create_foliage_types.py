"""STEP 10 (in editor): create the FoliageType assets the plan needs.

For every mesh in work/engine/xf_<tag>.json (or in ARGS['meshes']) creates, if missing,
  <foliage_type_folder>/FT_<mesh name[:60]>   (FoliageType_InstancedStaticMesh, mesh set, collision OFF)
and saves it. Existing FTs are left untouched, so it is safe to re-run. Chunked: stops after ~90 s, call again
until left == [].
NOTE: this writes into the shared tree library folder (FoliageTypes) - on a PC where another project already
created them nothing happens.
Origin: Zaliniy calls #245/#281/#322/#390.
ARGS: tag (default config.engine.tag), meshes (optional list), budget (s, default 90)
"""
import json
import os
import sys
import time

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
import ue_common as U  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(tag=U.CFG['engine']['tag'], meshes=None, budget=90))


def main():
    U.editor_world()
    if A['meshes']:
        meshes = list(A['meshes'])
    else:
        X = json.load(open(U.W('engine', 'xf_%s.json' % A['tag'])))
        meshes = sorted(set(r['mesh'] for v in X.values() for r in v))
    folder = U.CFG['foliage_type_folder'].rstrip('/')
    at = unreal.AssetToolsHelpers.get_asset_tools(); eal = unreal.EditorAssetLibrary
    made, bad = [], []
    t = time.time()
    for m in meshes:
        if time.time() - t > float(A['budget']):
            break
        path = U.C.ft_path(m)
        if eal.does_asset_exist(path):
            continue
        sm = unreal.load_asset(m)
        if sm is None:
            bad.append(m); continue
        ft = at.create_asset(path.split('/')[-1], folder, unreal.FoliageType_InstancedStaticMesh,
                             unreal.FoliageType_InstancedStaticMeshFactory())
        ft.set_editor_property('mesh', sm)
        try:
            bi = ft.get_editor_property('body_instance')
            bi.set_editor_property('collision_enabled', unreal.CollisionEnabled.NO_COLLISION)
            ft.set_editor_property('body_instance', bi)
        except Exception:
            pass
        eal.save_loaded_asset(ft)
        made.append(path.split('/')[-1])
        del ft, sm
        if len(made) % 5 == 0:          # heavy Nanite trees: free memory often, stop before RAM runs out
            unreal.SystemLibrary.collect_garbage()
            if U.mem()['phys_free_gb'] < 8:
                break
    left = [m for m in meshes if not eal.does_asset_exist(U.C.ft_path(m))]
    unreal.SystemLibrary.collect_garbage()
    return dict(meshes=len(meshes), made=made, missing_meshes=bad, left=left)


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
