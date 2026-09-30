"""LOOKDEV (in editor, OPTIONAL): 'CTX_Water_Plane' - a huge water plane under the site so aerial shots do not show
the void around the model (Zaliniy call #491). LEVEL-ONLY change.

Spawns (replacing an existing one) a StaticMeshActor labelled CTX_Water_Plane: /Engine/BasicShapes/Plane scaled
8000 x 8000 (800 km), material /Game/StarterContent/Materials/M_Water_Lake, cast_shadow off, at ARGS location
(Zaliniy: 15000, -30000, -300 = 1 m under ground). Needs the StarterContent pack (its M_Water_Lake colour is also
darkened by apply_materials.py, scope 'project').
ARGS: location [x,y,z], scale (8000), material, remove (False = spawn, True = delete only), save (False)
"""
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(location=[15000, -30000, float(U.CFG['ground_z_cm']) - 100], scale=8000,
                material='/Game/StarterContent/Materials/M_Water_Lake', remove=False, save=False))


def main():
    U.editor_world()
    for a in unreal.EditorLevelLibrary.get_all_level_actors():
        if a.get_actor_label() == 'CTX_Water_Plane':
            a.destroy_actor()
    if A['remove']:
        return dict(removed=True)
    mat = unreal.load_asset(A['material'])
    if mat is None:
        return dict(err='material not found: ' + A['material'])
    a = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*A['location']))
    a.set_actor_label('CTX_Water_Plane')
    c = a.static_mesh_component
    c.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Plane'))
    a.set_actor_scale3d(unreal.Vector(float(A['scale']), float(A['scale']), 1))
    c.set_material(0, mat)
    c.set_editor_property('cast_shadow', False)
    lvl = a.get_level().get_outer().get_name()
    del a, c, mat
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level() if A['save'] else None
    return dict(spawned=True, level=lvl, saved=saved)


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
