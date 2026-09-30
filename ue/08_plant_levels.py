"""STEP 12 (in editor): plant the engine output into the FOL_ sublevels.

InstancedFoliageActor.add_instances() ALWAYS writes into the PersistentLevel of the editor world, so each FOL_
level is opened as its own map, its old foliage actors are destroyed, the instances are added, the map is saved,
then the next one. At the end the persistent level is opened again.
Per call ARGS['max_levels'] levels (default 4) to keep each MCP call short; call again until left == [].
Transforms come straight from xf_<tag>.json (x, y, z in cm - z already = traced ground - 3 cm; roll/pitch/yaw in
degrees; uniform scale s). FoliageTypes must exist (06_create_foliage_types.py).
Origin: plant_level.py of the Zaliniy session.
ARGS: tag, levels (optional list), max_levels (4), reload_persistent (True)
"""
import gc
import json
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
import ue_common as U  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(tag=U.CFG['engine']['tag'], levels=None, max_levels=4, reload_persistent=True))


def plant(lvl, recs):
    folder = U.CFG['foliage_level_folder'].rstrip('/')
    if not U.load_level(folder + '/' + lvl):
        return dict(lvl=lvl, err='load failed (run 07_create_sublevels.py first)')
    w = U.editor_world()
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for a in unreal.EditorLevelLibrary.get_all_level_actors():      # remove anything planted before
        if isinstance(a, unreal.InstancedFoliageActor):
            eas.destroy_actor(a)
    by = {}
    for r in recs:
        by.setdefault(r['mesh'], []).append(unreal.Transform(unreal.Vector(r['x'], r['y'], r['z']),
                                                             unreal.Rotator(roll=r['roll'], pitch=r['pitch'], yaw=r['yaw']),
                                                             unreal.Vector(r['s'], r['s'], r['s'])))
    missing = []
    for m, trs in by.items():
        ft = unreal.load_asset(U.C.ft_path(m))
        if ft is None:
            missing.append(m); continue
        unreal.InstancedFoliageActor.add_instances(w, ft, trs)
        del ft
    n = sum(sum(c.get_instance_count() for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent))
            for a in unreal.EditorLevelLibrary.get_all_level_actors() if isinstance(a, unreal.InstancedFoliageActor))
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    del w, by, eas
    gc.collect()
    return dict(lvl=lvl, n=n, want=len(recs), saved=ok, missing_ft=missing)


def main():
    U.editor_world()
    X = json.load(open(U.W('engine', 'xf_%s.json' % A['tag'])))
    todo = list(A['levels']) if A['levels'] else sorted(X)
    done_file = U.W('engine', 'planted_%s.json' % A['tag'])
    done = json.load(open(done_file)) if os.path.exists(done_file) else {}
    if not A['levels']:
        todo = [l for l in todo if l not in done]
    res = []
    for lvl in todo[:int(A['max_levels'])]:
        r = plant(lvl, X[lvl])
        res.append(r)
        if r.get('saved') and r.get('n') == r.get('want'):
            done[lvl] = r['n']
            json.dump(done, open(done_file, 'w'), indent=1)
    del X
    if A['reload_persistent']:
        U.load_level(U.CFG['persistent_level'])
    left = [l for l in (A['levels'] or sorted(json.load(open(U.W('engine', 'xf_%s.json' % A['tag']))))) if l not in done]
    return dict(planted=res, left=left, world=U.world_name())


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
