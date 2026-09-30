"""LOOKDEV (in editor): level lighting / post-process state of the validated Zaliniy look (data/lookdev/lighting_state.json).

LEVEL-ONLY change (actors of the open map; nothing in the shared library). Open the persistent level first.
  * Ultra Dynamic Sky: 13:00, no time animation, warm sun colour, sun source angle x0.5, Sun Yaw 120, UDS exposure
    OFF (the PPV owns exposure), sky light 0.7 with warm day multiplier, fog density 0.0015 / falloff 0.2,
    warm fog colours (1, 0.88, 0.68)
  * Ultra Dynamic Weather manual state: clouds 1.5, fog 0.05, wind 1.0
  * UDS 'Sun' directional light: indirect 1.4, contact shadow length 0.02; height fog component; sky atmosphere
    aerial perspective scale 0
  * unbound PostProcessVolume 'PPV_Master_Runtime' (created if missing, priority 10): MANUAL exposure bias 2.1,
    WB 6500 / tint -0.02, shadow grading, local exposure 0.8 / 0.6, Lumen skylight leaking 0.1, final gather 2, ...
  * CineCameraActor: post-process settings reset to defaults (the client wants that camera untouched)
Then UDS/UDW construction scripts are re-run and the level is saved after a .umap.bak_YYYYMMDD backup.
ARGS: save (True), dry_run (False)
Values that are wrong for another project's sun/camera layout (Sun Yaw, exposure) - check with the shot set.
Origin: calls #379-#472, #550-#552, #584, #590, #596, #615, #617 of the Zaliniy session.
"""
import os
import shutil
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import json  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(save=True, dry_run=False))


def conv(old, v):
    """json value -> the type of the current property value"""
    if isinstance(old, unreal.LinearColor):
        return unreal.LinearColor(*[float(x) for x in (list(v) + [1.0])[:4]])
    if isinstance(old, unreal.Vector4):
        return unreal.Vector4(*[float(x) for x in (list(v) + [0.0])[:4]])
    if isinstance(v, str) and not isinstance(old, str):
        return getattr(type(old), v)
    if isinstance(old, bool):
        return bool(v)
    if isinstance(old, float):
        return float(v)
    return v


def setp(obj, name, v, log, tag, override=False):
    try:
        old = obj.get_editor_property(name)
        nv = conv(old, v)
        if not A['dry_run']:
            obj.set_editor_property(name, nv)
            if override:
                obj.set_editor_property('override_' + name, True)
        log.append((tag, name, str(old)[:48], str(v)))
    except Exception as e:
        log.append((tag, name, 'ERR ' + str(e)[:100]))


def main():
    w = U.editor_world()
    S = json.load(open(U.D('lookdev', 'lighting_state.json')))
    acts = unreal.GameplayStatics.get_all_actors_of_class(w, unreal.Actor)
    uds = [a for a in acts if a.get_class().get_name().startswith('Ultra_Dynamic_Sky')]
    udw = [a for a in acts if a.get_class().get_name().startswith('Ultra_Dynamic_Weather')]
    log = []
    if uds:
        u = uds[0]
        for k, v in S['uds'].items():
            setp(u, k, v, log, 'UDS')
        for c in u.get_components_by_class(unreal.DirectionalLightComponent):
            if c.get_name() == S['sun_component']['name']:
                for k, v in S['sun_component'].items():
                    if k != 'name':
                        setp(c, k, v, log, 'Sun')
        for c in u.get_components_by_class(unreal.ExponentialHeightFogComponent)[:1]:
            for k, v in S['height_fog_component'].items():
                setp(c, k, v, log, 'Fog')
        for c in u.get_components_by_class(unreal.SkyAtmosphereComponent)[:1]:
            for k, v in S['sky_atmosphere_component'].items():
                setp(c, k, v, log, 'SkyAtmosphere')
    else:
        log.append(('UDS', 'not found in level'))
    if udw:
        wa = udw[0]
        for k, v in S['udw'].items():
            setp(wa, k, v, log, 'UDW')
        try:
            ws = wa.get_editor_property('Manual Weather State')
            for k, v in S['udw_manual_weather_state'].items():
                setp(ws, k, v, log, 'UDW.state')
            if not A['dry_run']:
                wa.set_editor_property('Manual Weather State', ws)
        except Exception as e:
            log.append(('UDW', 'Manual Weather State', 'ERR ' + str(e)[:80]))
    P = S['ppv']
    label = U.CFG.get('lookdev', {}).get('ppv_label') or P['label']
    ppv = [a for a in acts if isinstance(a, unreal.PostProcessVolume) and a.get_actor_label() == label]
    if ppv:
        ppv = ppv[0]
    elif not A['dry_run']:
        ppv = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0))
        ppv.set_actor_label(label); log.append(('PPV', 'created', label))
    else:
        ppv = None
    if ppv is not None:
        if not A['dry_run']:
            ppv.set_editor_property('unbound', bool(P['unbound'])); ppv.set_editor_property('priority', float(P['priority']))
        s = ppv.get_editor_property('settings')
        for k, v in P['settings'].items():
            setp(s, k, v, log, 'PPV', override=True)
        if not A['dry_run']:
            ppv.set_editor_property('settings', s)
    cc = S.get('cine_camera', {})
    if cc.get('reset_post_process'):
        cams = [a for a in acts if a.get_actor_label() == cc['label'] and isinstance(a, unreal.CineCameraActor)]
        for cam in cams:
            if not A['dry_run']:
                cam.get_cine_camera_component().set_editor_property('post_process_settings', unreal.PostProcessSettings())
            log.append(('CineCamera', 'post_process_settings', 'reset to defaults'))
    for a in uds + udw:
        try:
            if not A['dry_run']:
                a.rerun_construction_scripts()
        except Exception:
            pass
    del acts, uds, udw, ppv
    saved = None
    if A['save'] and not A['dry_run']:
        f = U.asset_file(U.CFG['persistent_level']).replace('.uasset', '.umap')
        if os.path.exists(f) and not os.path.exists(f + U.today_suffix()):
            shutil.copy2(f, f + U.today_suffix())
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).set_current_level_by_name(U.short(U.CFG['persistent_level']))
        saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    del w
    return dict(saved=saved, errors=[l for l in log if len(l) > 2 and str(l[2]).startswith('ERR')], n=len(log))


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
