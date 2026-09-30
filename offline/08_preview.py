"""STEP 8 (offline): top-down plan previews (context colours, crowns coloured by species, legend).

Usage:  python 08_preview.py [tag] [FOL_level ...] [ov]
Writes work/engine/preview/<level>.png and OVERVIEW_stage1.png (+ left/right halves). Look at them before planting."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lib'))
import env  # noqa: E402
import pickle, collections, math, numpy as np, cv2  # noqa: E402
from lsite import Site, SP, PX
import species6 as SPC

OUT = os.path.join(SP, 'engine', 'preview')
os.makedirs(OUT, exist_ok=True)
CTX = {0: (225, 225, 220), 1: (185, 215, 160), 2: (95, 95, 100), 3: (215, 212, 205), 4: (205, 150, 215),
       5: (150, 190, 230), 6: (255, 255, 255), 7: (200, 195, 185), 8: (205, 200, 190)}
COL = {
    'hornbeam': (120, 205, 80), 'ash0202': (160, 180, 105), 'ash0521': (70, 160, 150), 'sbf3': (100, 160, 70),
    'sbf2': (135, 150, 95), 'leaf': (30, 90, 45), 'birch': (60, 110, 60), 'ashY': (200, 210, 90),
    'ash1': (50, 125, 70), 'leafsg': (40, 105, 95), 'pear': (175, 185, 70), 'ashYm': (215, 215, 120),
    'proxy137': (85, 115, 60), 'birch6': (150, 215, 150), 'birch6b': (140, 205, 160),
    'crataegus': (215, 85, 80), 'crat_m1': (230, 120, 100), 'crat_m2': (200, 110, 130), 'irga': (150, 75, 150),
    'sakura': (245, 150, 200), 'lager': (225, 90, 170), 'pot65': (110, 90, 60), 'dub': (170, 150, 60),
    'terak1': (60, 120, 210), 'terak2': (90, 150, 230), 'pearP': (130, 110, 220),
    'pine650': (15, 65, 55), 'pine550': (20, 80, 65), 'pine450': (25, 95, 75), 'hach': (10, 50, 40), 'junip': (60, 110, 130),
}
_shr = [k for k in SPC.LIB if SPC.role(k) in 'KEF']
for n, k in enumerate(_shr):   # shrubs: dark-ish distinct hues
    h = (n * 37) % 180
    c = cv2.cvtColor(np.uint8([[[h, 200, 150]]]), cv2.COLOR_HSV2RGB)[0, 0]
    COL[k] = tuple(int(v) for v in c)


def bgr(c):
    return (int(c[2]), int(c[1]), int(c[0]))


def render(S, m, title, box=None, scale=1.0, legend=True):
    recs = m['recs']
    beds = m['beds']
    if box is None:
        rr0 = min(S.slices[b['id'] - 1][0].start for b in beds); rr1 = max(S.slices[b['id'] - 1][0].stop for b in beds)
        cc0 = min(S.slices[b['id'] - 1][1].start for b in beds); cc1 = max(S.slices[b['id'] - 1][1].stop for b in beds)
        box = (max(rr0 - 60, 0), min(rr1 + 60, S.H), max(cc0 - 60, 0), min(cc1 + 60, S.W))
    R0, R1, C0, C1 = box
    rr, cc = np.mgrid[R0:R1, C0:C1]
    cls = S.cls_at(rr, cc)
    img = np.zeros(cls.shape + (3,), np.uint8)
    for k, v in CTX.items():
        img[cls == k] = bgr(v)
    grass = np.asarray(S.lab[R0:R1, C0:C1]) > 0
    img[grass] = bgr((170, 205, 140))
    bl = S.beds[R0:R1, C0:C1]
    inb = np.isin(bl, [b['id'] for b in beds])
    img[inb] = bgr((150, 200, 120))
    edge = cv2.morphologyEx(inb.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    img[edge & inb] = bgr((110, 160, 90))
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    f = scale
    trees = [r for r in recs if SPC.is_tree(r['key'])]
    shr = [r for r in recs if not SPC.is_tree(r['key'])]
    for r in shr:
        rad = max(1, int(round(SPC.D(r['key'], r['s']) / 2 / PX * f)))
        p = (int((r['C'] - C0) * f), int((r['R'] - R0) * f))
        cv2.circle(img, p, rad, bgr(COL[r['key']]), -1, cv2.LINE_AA)
        if f >= 0.6:
            cv2.circle(img, p, rad, (30, 30, 30), 1, cv2.LINE_AA)
    over = img.copy()
    for r in sorted(trees, key=lambda r: -SPC.D(r['key'], r['s'])):
        rad = max(2, int(round(SPC.D(r['key'], r['s']) / 2 / PX * f)))
        cv2.circle(over, (int((r['C'] - C0) * f), int((r['R'] - R0) * f)), rad, bgr(COL[r['key']]), -1, cv2.LINE_AA)
    img = cv2.addWeighted(over, 0.62, img, 0.38, 0)
    for r in trees:
        rad = max(2, int(round(SPC.D(r['key'], r['s']) / 2 / PX * f)))
        p = (int((r['C'] - C0) * f), int((r['R'] - R0) * f))
        cv2.circle(img, p, rad, bgr(tuple(max(0, v - 70) for v in COL[r['key']])), 1, cv2.LINE_AA)
        cv2.circle(img, p, max(1, int(2 * f)), (40, 40, 40), -1)
    for (bid, gl) in m.get('glades', {}).items():
        b = [x for x in beds if x['id'] == bid][0]
        for (gr, gc, rad) in gl:
            cv2.circle(img, (int((gc + b['c0'] - C0) * f), int((gr + b['r0'] - R0) * f)),
                       int(rad / PX * f), (0, 140, 255), 2, cv2.LINE_AA)
    if legend:
        cnt = collections.Counter(r['key'] for r in recs)
        pad = np.full((max(img.shape[0], 60 + 19 * len(cnt)), 330, 3), 255, np.uint8)
        cv2.putText(pad, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)
        y = 46
        for k, n in sorted(cnt.items(), key=lambda kv: ('LMSPCKEF'.index(SPC.role(kv[0])), -kv[1])):
            cv2.circle(pad, (18, y - 5), 7, bgr(COL[k]), -1)
            cv2.putText(pad, '%s %s  %d' % (k, SPC.role(k), n), (32, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
            y += 19
        cv2.putText(pad, 'bar 20 m', (8, y + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        cv2.line(pad, (8, y + 22), (8 + int(20 / PX * f), y + 22), (0, 0, 0), 3)
        if pad.shape[0] > img.shape[0]:
            img = np.vstack([img, np.full((pad.shape[0] - img.shape[0], img.shape[1], 3), 255, np.uint8)])
        img = np.hstack([img, pad[:img.shape[0]]])
    return img


def overview(S, meta, f=0.3):
    allb = [b for m in meta.values() for b in m['beds']]
    rr0 = min(S.slices[b['id'] - 1][0].start for b in allb) - 100; rr1 = max(S.slices[b['id'] - 1][0].stop for b in allb) + 100
    cc0 = min(S.slices[b['id'] - 1][1].start for b in allb) - 100; cc1 = max(S.slices[b['id'] - 1][1].stop for b in allb) + 100
    merged = dict(recs=[r for m in meta.values() for r in m['recs']], beds=allb)
    box = (max(rr0, 0), rr1, max(cc0, 0), cc1)
    img = render(S, merged, 'STAGE-1 v6', box=box, scale=f)
    for lvl, m in meta.items():
        Rs = [S.slices[b['id'] - 1][0].start for b in m['beds']]; Cs = [S.slices[b['id'] - 1][1].start for b in m['beds']]
        Re = [S.slices[b['id'] - 1][0].stop for b in m['beds']]; Ce = [S.slices[b['id'] - 1][1].stop for b in m['beds']]
        y = int(((min(Rs) + max(Re)) / 2 - box[0]) * f); x = int(((min(Cs) + max(Ce)) / 2 - box[2]) * f)
        t = lvl[4:] + ' ' + m['palette'][:2]
        cv2.putText(img, t, (x - 40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(img, t, (x - 40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return img


if __name__ == '__main__':
    if any(x in ('-h', '--help') for x in sys.argv[1:]):
        print(__doc__); sys.exit(0)
    tag = sys.argv[1] if len(sys.argv) > 1 else env.CFG['engine']['tag']
    S = Site()
    meta = pickle.load(open(os.path.join(SP, 'engine', 'meta_%s.pkl' % tag), 'rb'))
    lvls = [a for a in sys.argv[2:] if a != 'ov'] or list(meta)
    for lvl in lvls:
        img = render(S, meta[lvl], '%s (%s)' % (lvl, meta[lvl]['palette']))
        cv2.imwrite(os.path.join(OUT, '%s.png' % lvl), img)
        print(lvl, img.shape)
    if 'ov' in sys.argv[2:] or not sys.argv[2:]:
        img = overview(S, meta, 0.3)
        cv2.imwrite(os.path.join(OUT, 'OVERVIEW_stage1.png'), img)
        h, w = img.shape[:2]
        cv2.imwrite(os.path.join(OUT, 'OVERVIEW_left.png'), img[:, :w // 2 + 100])
        cv2.imwrite(os.path.join(OUT, 'OVERVIEW_right.png'), img[:, w // 2 - 100:])
