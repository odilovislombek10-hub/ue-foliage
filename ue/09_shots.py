"""STEP 13 (in editor): screenshots for visual verification. Returns immediately; shots are taken on editor ticks.

ARGS action:
  'lots'    review shots of every planted lot (work/shots/lot_shots.json from offline/09_camplan.py);
            ARGS levels=[...] limits to some FOL_ levels. prefix default 'LOT_'
  'set'     fixed audit set (work/shots/shotset.json, example data/examples/shotset.zaliniy.json) + CINE
  'top'     top-down set: shotset.json 'top_target' from 150 / 400 / 800 m, then CINE
  'cine'    one shot through the level CineCameraActor (ARGS name)
  'list'    ARGS shots=[[name,[x,y,z],[roll,pitch,yaw],fov], ...]
  'settle'  ARGS steps=[[name, {cvar: value}], ...] - change, wait until the editor has settled, shoot
  'status' / 'stop'
Common ARGS: prefix, wait (s, default config.screenshots.wait_s)
Files: <Project>/Saved/Screenshots/WindowsEditor/<prefix><name>.png - open them (Read tool) and judge.
Wait until the shaders are compiled (no ShaderCompileWorker running) before shooting.
"""
import json
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _d)
import ue_common as U  # noqa: E402
import shots_lib as S  # noqa: E402

A = U.args(dict(action='status', prefix='', wait=None, levels=None, name='CINE', shots=None, steps=None,
                min_wait=None, max_wait=None))


def main():
    U.editor_world()
    act = A['action']
    if act == 'status':
        return S.status()
    if act == 'stop':
        return S.stop()
    if act == 'lots':
        sh = json.load(open(U.W('shots', 'lot_shots.json')))
        if A['levels']:
            sh = [s for s in sh if any(s[0].startswith(l + '_') for l in A['levels'])]
        return dict(started=S.queue(sh, A['prefix'] or 'LOT_', A['wait']))
    if act == 'set':
        return dict(started=S.shotset(A['prefix'] or 'SET_'))
    if act == 'top':
        cfg = json.load(open(U.W('shots', 'shotset.json')))
        tx, ty = cfg['top_target']
        pre = A['prefix'] or 'TOP_'
        sh = [S.aerial('H%d' % (d // 100), (tx, ty), 33, d, pit, None, fov) for d, pit, fov in
              ((15000, 55, 60), (40000, 50, 55), (80000, 45, 50))]
        return dict(started=S.queue(sh, pre, 20, then=lambda: S.cine(pre + 'CINE', wait=20)))
    if act == 'cine':
        return dict(started=S.cine(A['name'], wait=A['wait'] or 20))
    if act == 'list':
        return dict(started=S.queue(A['shots'], A['prefix'], A['wait']))
    if act == 'settle':
        return dict(started=S.settle(A['steps'], A['min_wait'], A['max_wait']))
    return dict(err='unknown action ' + str(act))


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
