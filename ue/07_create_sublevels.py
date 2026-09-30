"""STEP 11 (in editor): one streaming sublevel per lot, added to the persistent level.

Loads config.persistent_level if it is not the open map, then for every level in work/engine/xf_<tag>.json
(or ARGS['levels']) that is not yet part of the world:
    EditorLevelUtils.create_new_streaming_level(<streaming_class>, <foliage_level_folder>/<FOL_x>, False)
sets streaming flags (config.streaming_initially_loaded / _visible, if the class exposes them), makes the
persistent level current again and saves all dirty packages (persistent map + new FOL maps).
Existing levels are kept (re-run safe). Origin: Zaliniy calls #246/#281/#282.
ARGS: tag, levels (optional list)
"""
import json
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
import ue_common as U  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(tag=U.CFG['engine']['tag'], levels=None))


def main():
    pers = U.CFG['persistent_level']
    if U.world_name() != U.short(pers):
        if not U.load_level(pers):
            return dict(err='cannot load ' + pers)
    w = U.editor_world()
    if A['levels']:
        levels = list(A['levels'])
    else:
        levels = sorted(json.load(open(U.W('engine', 'xf_%s.json' % A['tag']))).keys())
    have = [l.get_path_name().split('/')[-1].split('.')[0] for l in unreal.EditorLevelUtils.get_levels(w)]
    cls = getattr(unreal, U.CFG.get('streaming_class', 'LevelStreamingDynamic'))
    folder = U.CFG['foliage_level_folder'].rstrip('/')
    new, flags = [], {}
    for lvl in levels:
        if lvl in have:
            continue
        sl = unreal.EditorLevelUtils.create_new_streaming_level(cls, folder + '/' + lvl, False)
        new.append(lvl)
        for prop, key in (('initially_loaded', 'streaming_initially_loaded'), ('initially_visible', 'streaming_initially_visible')):
            try:
                sl.set_editor_property(prop, bool(U.CFG.get(key, True)))
                flags[prop] = 'ok'
            except Exception as e:
                flags[prop] = 'not available: %s' % str(e)[:60]
        del sl
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name(U.short(pers))
    del w
    saved = U.save_dirty()
    return dict(levels=len(levels), created=new, streaming_flags=flags, **saved)


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
