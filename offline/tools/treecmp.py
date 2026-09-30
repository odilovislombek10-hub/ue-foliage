"""Tree look comparison: stacks <tag>A / <tag>B shots of several versions under a reference photo and prints
the canopy colour bands (shade / mid / lit RGB, median saturation).

Usage:  python treecmp.py <reference.jpg> <tag1> [tag2 ...]      (e.g. TREE1_ TREE2_)
Writes work/compare/treecmp.png. Origin: treecmp.py."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
import env  # noqa: E402
import numpy as np
from PIL import Image
from skimage import color as skc
S = os.path.join(env.CFG['project_root'], 'Saved', 'Screenshots', 'WindowsEditor')


def bands(p):
    a = np.asarray(Image.open(p).convert('RGB').resize((960, 540))).astype(np.float32) / 255
    hsv = skc.rgb2hsv(a)
    H, Sa, V = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    fol = (H > 40) & (H < 150) & (Sa > 0.2) & (V > 0.04)
    L = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2])[fol]
    c = a[fol]
    out = {}
    for nm, lo, hi in (('shade', 0, 30), ('mid', 30, 70), ('lit', 70, 95)):
        m = (L >= np.percentile(L, lo)) & (L <= np.percentile(L, hi))
        out[nm] = [int(x) for x in c[m].mean(0) * 255]
    out['sat'] = round(float(np.median(Sa[fol])), 2)
    return out


if __name__ == '__main__':
    REF = sys.argv[1]
    tags = sys.argv[2:]
    print('REF', bands(REF))
    for t in tags:
        for v in 'AB':
            print(t, v, bands(os.path.join(S, t + v + '.png')))
    W = 640
    o = Image.new('RGB', (W * 2, 360 * (len(tags) + 1)))
    o.paste(Image.open(REF).convert('RGB').resize((360, 360)), (0, 0))
    for i, t in enumerate(tags):
        for j, v in enumerate('AB'):
            o.paste(Image.open(os.path.join(S, t + v + '.png')).convert('RGB').resize((W, 360)), (j * W, 360 * (i + 1)))
    o.save(env.W('compare', 'treecmp.png')); print('written', env.W('compare', 'treecmp.png'))
