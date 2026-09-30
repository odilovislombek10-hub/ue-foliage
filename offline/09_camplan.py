"""STEP 9 (offline): review cameras for every planted lot (used by ue/09_shots.py lots).

Usage:  python 09_camplan.py [tag]
Per level two shots from the engine output work/engine/xf_<tag>.json:
  <lvl>_aer  35 mm, pitch -50, looking along the lot's long axis, lot bbox ~80 % of the frame (camplan.py)
  <lvl>_mid  60 deg FOV, 35 m above ground, pitch -30, looking into the lot centre (call #338 'mid')
Writes work/shots/lot_shots.json: [[name, [x,y,z], [roll,pitch,yaw], fov], ...]
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402

HFOV = 54.4          # 35 mm on a 36 mm sensor
ASPECT = 16 / 9
GROUND_Z = float(env.CFG['ground_z_cm'])


def frame(cx, cy, w_along, w_across, yaw, pitch=-50.0, fill=0.8, hfov=HFOV):
    vfov = 2 * math.degrees(math.atan(math.tan(math.radians(hfov / 2)) / ASPECT))
    d_w = (w_across / fill) / (2 * math.tan(math.radians(hfov / 2)))
    p = math.radians(-pitch)
    d_h = (w_along * math.sin(p) / fill) / (2 * math.tan(math.radians(vfov / 2)))
    d = max(d_w, d_h, 6000.0)
    yr = math.radians(yaw)
    return [cx - d * math.cos(p) * math.cos(yr), cy - d * math.cos(p) * math.sin(yr), GROUND_Z + d * math.sin(p)], \
        [0.0, pitch, yaw], hfov


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else env.CFG['engine']['tag']
    X = json.load(open(env.W('engine', 'xf_%s.json' % tag)))
    out = []
    for lvl, recs in sorted(X.items()):
        if not recs:
            continue
        xs = [r['x'] for r in recs]; ys = [r['y'] for r in recs]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        wx, wy = x1 - x0, y1 - y0
        yaw, along, across = (90.0, wy, wx) if wx >= wy else (0.0, wx, wy)
        loc, rot, fov = frame(cx, cy, along, across, yaw)
        out.append([lvl + '_aer', [round(v, 1) for v in loc], rot, fov])
        ext = max(wx, wy); d2 = ext * 0.35; yw = 35.0 + 30.0
        out.append([lvl + '_mid', [round(cx - d2 * math.cos(math.radians(yw)), 1), round(cy - d2 * math.sin(math.radians(yw)), 1),
                                   GROUND_Z + 3500], [0.0, -30.0, yw], 60.0])
    json.dump(out, open(env.W('shots', 'lot_shots.json'), 'w'), indent=1)
    print(len(out), 'shots ->', env.W('shots', 'lot_shots.json'))


if __name__ == '__main__':
    main()
