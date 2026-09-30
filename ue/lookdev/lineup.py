"""LOOKDEV TEST (in editor): tree line-up for per-species material checks (Zaliniy calls #541-#547, #560).

  ARGS action='spawn'   place one StaticMeshActor per mesh (ARGS meshes, default: every tree/shrub of the engine
                        library that is used in work/engine/xf_<tag>.json) in rows of 8, 18 m apart, on the water
                        plane far from the site (ARGS origin, Zaliniy: 260000, -20000, -300), labels ZZ_LINEUP_<nn>_<name>
  ARGS action='shoot'   one screenshot per species (prefix TS_), camera in front at ~1.25x its height, 45 deg FOV,
                        plus the material dump work/lookdev/lineup_mats.json (all scalar/vector/texture params per slot)
  ARGS action='remove'  delete every ZZ_LINEUP actor (do this before saving the level!)
Level-only, temporary actors. Compare TS_ shots before/after a material change (offline/tools/*).
"""
import json
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import shots_lib as S  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(action='spawn', meshes=None, origin=[260000, -20000, -300], tag=U.CFG['engine']['tag'], prefix='TS_'))
MEL = unreal.MaterialEditingLibrary


def lineup_actors():
    return sorted([a for a in unreal.EditorLevelLibrary.get_all_level_actors() if a.get_actor_label().startswith('ZZ_LINEUP')],
                  key=lambda a: a.get_actor_label())


def spawn():
    meshes = A['meshes']
    if not meshes:
        X = json.load(open(U.W('engine', 'xf_%s.json' % A['tag'])))
        meshes = sorted(set(r['mesh'] for v in X.values() for r in v))
    for a in lineup_actors():
        a.destroy_actor()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    ox, oy, oz = A['origin']; placed = []
    for k, p in enumerate(meshes):
        sm = unreal.load_asset(p)
        if sm is None:
            continue
        r, i = divmod(k, 8)
        a = eas.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(ox + i * 1800, oy + r * 9000, oz))
        a.static_mesh_component.set_static_mesh(sm)
        a.set_actor_label('ZZ_LINEUP_%02d_%s' % (k, p.split('/')[-1][:30]))
        placed.append(p.split('/')[-1]); del a, sm
        if len(placed) % 5 == 0 and U.mem()['phys_free_gb'] < 8:    # heavy Nanite trees: never run out of RAM
            return dict(placed=len(placed), stopped='low memory - pass fewer ARGS meshes')
    return dict(placed=len(placed))


def shoot():
    sh, out = [], {}
    for a in lineup_actors():
        o, e = a.get_actor_bounds(False)
        h = max(e.z * 2, 300); dist = h * 1.25 + e.y
        loc = a.get_actor_location()
        sh.append((a.get_actor_label()[10:], (loc.x, loc.y - dist, loc.z + h * 0.55), (0, -4, 90), 45))
        sm = a.static_mesh_component.static_mesh
        mats = []
        for s in sm.static_materials:
            m = s.material_interface
            if not m:
                continue
            b = m.get_base_material()
            inst = isinstance(m, unreal.MaterialInstance)
            e_ = dict(mat=m.get_path_name().split('.')[0], master=b.get_path_name().split('.')[0], scal={}, vec={}, tex={})
            for n in MEL.get_scalar_parameter_names(b):
                n = str(n)
                e_['scal'][n] = round(MEL.get_material_instance_scalar_parameter_value(m, n) if inst else MEL.get_material_default_scalar_parameter_value(m, n), 3)
            for n in MEL.get_vector_parameter_names(b):
                n = str(n)
                c = MEL.get_material_instance_vector_parameter_value(m, n) if inst else MEL.get_material_default_vector_parameter_value(m, n)
                e_['vec'][n] = [round(c.r, 3), round(c.g, 3), round(c.b, 3)]
            for n in MEL.get_texture_parameter_names(b):
                n = str(n)
                t = MEL.get_material_instance_texture_parameter_value(m, n) if inst else MEL.get_material_default_texture_parameter_value(m, n)
                e_['tex'][n] = t.get_path_name().split('.')[0] if t else None
            mats.append(e_)
        out[a.get_actor_label()[10:]] = dict(mesh=sm.get_path_name().split('.')[0], materials=mats)
    json.dump(out, open(U.W('lookdev', 'lineup_mats.json'), 'w'), indent=1)
    return dict(started=S.queue(sh, A['prefix'], wait=8))


def main():
    U.editor_world()
    if A['action'] == 'spawn':
        return spawn()
    if A['action'] == 'shoot':
        return shoot()
    if A['action'] == 'remove':
        n = 0
        for a in lineup_actors():
            a.destroy_actor(); n += 1
        return dict(removed=n)
    return dict(err='action = spawn | shoot | remove')


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
