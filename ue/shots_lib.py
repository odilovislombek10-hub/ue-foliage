"""Tick-driven screenshot tools (import inside Unreal). Files land in <Project>/Saved/Screenshots/WindowsEditor/.

Why tick-driven: a Python call blocks the editor, so nothing streams / renders while it runs. Every tool here
registers a slate post-tick callback, returns at once, and moves the camera -> WAITS (Nanite / textures / Lumen
must settle; the client complained when shots were taken after 1-2 s) -> shoots -> next.
Before every shot the foliage season MPC is forced to summer (config.mpc_seasons).

  queue(shots, prefix, wait)   shots = [(name, (x,y,z), (roll,pitch,yaw), fov)] via a temporary CameraActor
  cine(name, wait)             through the level's CineCameraActor (config.screenshots.cine_camera_label) - the
                               camera is only piloted, never modified (it must stay default: no PP overrides)
  settle(steps, min_wait, max_wait)   steps = [(name, {cvar: value})]: apply cvars, wait >= min_wait s AND until
                               frame time is stable (3 s windows within 15 %), shoot through the CineCamera, log fps
  shotset(prefix)              fixed audit set from work/shots/shotset.json: aerials + eye-level + CINE (7 shots on Zaliniy)
  status() / stop()
State lives in builtins['_uefol_shots' | '_uefol_cine' | '_uefol_settle' | '_uefol_chain'] (our own names only).
Origin: shots.py, cineshot.py, settleshot.py, shotset.py, topset.py of the Zaliniy session.
"""
import builtins
import json
import math
import os
import sys
import time

import unreal

_d = os.path.dirname(os.path.abspath(__file__))
if _d not in sys.path:
    sys.path.insert(0, _d)
import ue_common as U  # noqa: E402

SC = U.CFG['screenshots']
MPC = U.CFG['mpc_seasons']


def _summer(w):
    try:
        unreal.MaterialLibrary.set_vector_parameter_value(w, unreal.load_asset(MPC['path']), MPC['param'],
                                                          unreal.LinearColor(*MPC['summer']))
    except Exception:
        pass


def _cine_cam(w):
    cams = [c for c in unreal.GameplayStatics.get_all_actors_of_class(w, unreal.CineCameraActor)
            if c.get_actor_label() == SC['cine_camera_label']]
    if not cams:
        raise RuntimeError('no CineCameraActor labelled %s in the level' % SC['cine_camera_label'])
    return cams[0]


def queue(shots, prefix, wait=None, summer=True, then=None):
    """then: optional callable run when the queue finishes (e.g. lambda: cine(...))"""
    wait = float(wait if wait is not None else SC['wait_s'])
    builtins._uefol_shots = dict(q=[tuple(s) for s in shots], state='next', t=0, cam=None, done=[], prefix=prefix,
                                 wait=wait, summer=summer, then=then)

    def tick(dt):
        # re-entrancy guard: take_high_res_screenshot can pump Slate while the editor is busy (mesh builds),
        # which re-entered this callback recursively -> EXCEPTION_STACK_OVERFLOW crash on 2026-09-30.
        if getattr(builtins, '_shot_tick_busy', False):
            return
        builtins._shot_tick_busy = True
        try:
            _tick(dt)
        finally:
            builtins._shot_tick_busy = False

    def _tick(dt):
        Q = builtins._uefol_shots
        eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if w is None:
            return
        if Q['state'] == 'next':
            if not Q['q']:
                if Q['cam']:
                    eas.destroy_actor(Q['cam']); Q['cam'] = None
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).eject_pilot_level_actor()
                unreal.unregister_slate_post_tick_callback(Q['cb']); Q['state'] = 'finished'
                if Q.get('then'):
                    f = Q['then']; Q['then'] = None; f()
                return
            n, l, r, f = Q['q'].pop(0)
            if Q['cam'] is None:
                Q['cam'] = eas.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(*l), unreal.Rotator(*r))
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).pilot_level_actor(Q['cam'])
            Q['cam'].set_actor_location_and_rotation(unreal.Vector(*l), unreal.Rotator(*r), False, False)
            Q['cam'].camera_component.set_editor_property('field_of_view', f)
            Q['cur'] = n; Q['t'] = time.time(); Q['state'] = 'wait'
        elif Q['state'] == 'wait' and time.time() - Q['t'] > Q['wait']:
            if Q['summer']:
                _summer(w)
            unreal.AutomationLibrary.take_high_res_screenshot(SC['width'], SC['height'], Q['prefix'] + Q['cur'] + '.png', Q['cam'])
            Q['t'] = time.time(); Q['state'] = 'save'
        elif Q['state'] == 'save' and time.time() - Q['t'] > SC['save_s']:
            Q['done'].append(Q['cur']); Q['state'] = 'next'

    builtins._uefol_shots['cb'] = unreal.register_slate_post_tick_callback(tick)
    return [s[0] for s in shots]


def cine(name, wait=20.0):
    builtins._uefol_cine = dict(state='pilot', t=time.time(), name=name, wait=float(wait))

    def tick(dt):
        # re-entrancy guard: take_high_res_screenshot can pump Slate while the editor is busy (mesh builds),
        # which re-entered this callback recursively -> EXCEPTION_STACK_OVERFLOW crash on 2026-09-30.
        if getattr(builtins, '_shot_tick_busy', False):
            return
        builtins._shot_tick_busy = True
        try:
            _tick(dt)
        finally:
            builtins._shot_tick_busy = False

    def _tick(dt):
        Q = builtins._uefol_cine
        wd = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if wd is None:
            return
        cam = _cine_cam(wd)
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        if Q['state'] == 'pilot':
            les.pilot_level_actor(cam); Q['t'] = time.time(); Q['state'] = 'wait'
        elif Q['state'] == 'wait' and time.time() - Q['t'] > Q['wait']:
            _summer(wd)
            unreal.AutomationLibrary.take_high_res_screenshot(SC['width'], SC['height'], Q['name'] + '.png', cam)
            Q['t'] = time.time(); Q['state'] = 'save'
        elif Q['state'] == 'save' and time.time() - Q['t'] > SC['save_s']:
            les.eject_pilot_level_actor()
            unreal.unregister_slate_post_tick_callback(Q['cb']); Q['state'] = 'finished'

    builtins._uefol_cine['cb'] = unreal.register_slate_post_tick_callback(tick)
    return name


def settle(steps, min_wait=None, max_wait=None):
    """validated test method: change -> wait until the editor has really settled -> shoot -> next"""
    min_wait = float(min_wait if min_wait is not None else SC['settle_min_s'])
    max_wait = float(max_wait if max_wait is not None else SC['settle_max_s'])
    builtins._uefol_settle = dict(q=[(n, dict(c)) for n, c in steps], state='next', t=0, dts=[], log=[],
                                  min_wait=min_wait, max_wait=max_wait)

    def tick(dt):
        # re-entrancy guard: take_high_res_screenshot can pump Slate while the editor is busy (mesh builds),
        # which re-entered this callback recursively -> EXCEPTION_STACK_OVERFLOW crash on 2026-09-30.
        if getattr(builtins, '_shot_tick_busy', False):
            return
        builtins._shot_tick_busy = True
        try:
            _tick(dt)
        finally:
            builtins._shot_tick_busy = False

    def _tick(dt):
        Q = builtins._uefol_settle
        w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if w is None:
            return
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        now = time.time()
        if Q['state'] == 'next':
            if not Q['q']:
                les.eject_pilot_level_actor()
                json.dump(Q['log'], open(U.W('shots', 'settle_log.json'), 'w'), indent=1)
                unreal.unregister_slate_post_tick_callback(Q['cb']); Q['state'] = 'finished'; return
            name, cv = Q['q'].pop(0)
            for k, v in cv.items():
                unreal.SystemLibrary.execute_console_command(w, '%s %s' % (k, v))
            les.pilot_level_actor(_cine_cam(w))
            Q.update(cur=name, t=now, dts=[], state='wait')
        elif Q['state'] == 'wait':
            Q['dts'].append((now, dt))
            el = now - Q['t']
            recent = [d for (t, d) in Q['dts'] if now - t < 3]
            prev = [d for (t, d) in Q['dts'] if 3 <= now - t < 6]
            stable = recent and prev and abs(sum(recent) / len(recent) - sum(prev) / len(prev)) < 0.15 * (sum(prev) / len(prev))
            if (el > Q['min_wait'] and stable) or el > Q['max_wait']:
                _summer(w)
                unreal.AutomationLibrary.take_high_res_screenshot(SC['width'], SC['height'], Q['cur'] + '.png', _cine_cam(w))
                Q['log'].append(dict(name=Q['cur'], waited=round(el, 1), fps=round(len(recent) / 3.0, 1)))
                Q['t'] = now; Q['state'] = 'save'
        elif Q['state'] == 'save' and now - Q['t'] > 8:
            Q['state'] = 'next'

    builtins._uefol_settle['cb'] = unreal.register_slate_post_tick_callback(tick)
    return [s[0] for s in steps]


def aerial(name, target_xy, yaw, dist=9000.0, pitch=32.0, ground_z=None, fov=55.0):
    """camera looking at target from `dist` cm away, `pitch` degrees down (shotset TA/TB, topset)"""
    gz = float(U.CFG['ground_z_cm'] if ground_z is None else ground_z)
    h, v = dist * math.cos(math.radians(pitch)), dist * math.sin(math.radians(pitch))
    px, py = target_xy
    return (name, (px - h * math.cos(math.radians(yaw)), py - h * math.sin(math.radians(yaw)), gz + v), (0, -pitch, yaw), fov)


def shotset(prefix, path=None):
    """fixed audit set (Zaliniy: TA, TB 90 m aerials of two dense courtyards, EYE0..3 at 1.65 m, then CINE).
    work/shots/shotset.json: {"aerials": [{"name","target":[x,y],"yaw","dist","pitch","fov"}],
                              "eyes": [{"name","pos":[x,y,z],"yaw","fov"}], "cine": true}"""
    cfg = json.load(open(path or U.W('shots', 'shotset.json')))
    sh = [aerial(a['name'], a['target'], a.get('yaw', 33), a.get('dist', 9000), a.get('pitch', 32), None, a.get('fov', 55))
          for a in cfg.get('aerials', [])]
    for e in cfg.get('eyes', []):
        sh.append((e['name'], tuple(e['pos']), (0, e.get('pitch', 4), e['yaw']), e.get('fov', 62)))
    then = (lambda: cine(prefix + 'CINE', wait=20)) if cfg.get('cine', True) else None
    return queue(sh, prefix, wait=SC['wait_s'], then=then)


def status():
    out = {}
    for k in ('_uefol_shots', '_uefol_cine', '_uefol_settle'):
        q = builtins.__dict__.get(k)
        if q:
            out[k] = dict(state=q.get('state'), cur=q.get('cur'), left=len(q.get('q', [])), done=q.get('done'),
                          log=q.get('log'))
    return out


def stop():
    """unregister every running queue and remove the temporary camera"""
    for k in ('_uefol_shots', '_uefol_cine', '_uefol_settle'):
        q = builtins.__dict__.get(k)
        if q and q.get('state') != 'finished' and q.get('cb') is not None:
            try:
                unreal.unregister_slate_post_tick_callback(q['cb'])
            except Exception:
                pass
            q['state'] = 'finished'
        if q and q.get('cam'):
            try:
                unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actor(q['cam'])
            except Exception:
                pass
            q['cam'] = None
    try:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).eject_pilot_level_actor()
    except Exception:
        pass
    return status()
