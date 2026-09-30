"""Reference vs render comparison panel: images, luminance histograms, colour swatches per region, CIE dE2000.

Usage:  python compare_panel.py panel.json
  panel.json = {"ref": "reference.jpg", "shots": [["label", "render.png"], ...], "out": "panel.png"}
Prints dE2000 per region (shadow, mid, highlight, foliage shade / lit, sky). Origin: compare_panel.py."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
import env  # noqa: E402
import json  # noqa: E402
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from skimage import color as skc

REGIONS = ('shadow', 'mid', 'highlight', 'fol_shade', 'fol_lit', 'sky')


def load(p, w=900):
    im = Image.open(p).convert('RGB')
    im = im.resize((w, int(im.height * w / im.width)))
    return np.asarray(im).astype(np.float32) / 255.0


def regions(a):
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    hsv = skc.rgb2hsv(a)
    H, S, V = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    fol = (H > 35) & (H < 150) & (S > 0.18) & (V > 0.06)
    sky = (a[..., 2] > a[..., 0] + 0.03) & (V > 0.55) & (S < 0.45)
    sky[int(a.shape[0] * 0.5):] = False
    q = lambda m, lo, hi: m & (L >= np.percentile(L[m], lo)) & (L <= np.percentile(L[m], hi)) if m.sum() > 50 else m
    allm = np.ones_like(L, bool)
    R = dict(shadow=q(allm, 0, 15), mid=q(allm, 40, 60), highlight=q(allm, 90, 99.5),
             fol_shade=q(fol, 0, 30), fol_lit=q(fol, 70, 95), sky=sky)
    return L, {k: (a[m].mean(0) if m.sum() > 50 else None) for k, m in R.items()}


def de(c1, c2):
    if c1 is None or c2 is None:
        return None
    l1 = skc.rgb2lab(c1.reshape(1, 1, 3)); l2 = skc.rgb2lab(c2.reshape(1, 1, 3))
    return float(skc.deltaE_ciede2000(l1, l2)[0, 0])


def panel(ref, shots, out):
    ra = load(ref); rL, rc = regions(ra)
    n = len(shots) + 1
    fig = plt.figure(figsize=(4.2 * n, 9.5), dpi=90)
    items = [('REFERENS', ref)] + shots
    table = {}
    for i, (name, p) in enumerate(items):
        a = load(p); L, c = regions(a)
        ax = fig.add_subplot(3, n, i + 1); ax.imshow(a); ax.set_title(name, fontsize=11); ax.axis('off')
        ax = fig.add_subplot(3, n, n + i + 1)
        ax.hist(rL.ravel() * 255, bins=64, range=(0, 255), color='0.6', alpha=0.6, density=True, label='ref')
        ax.hist(L.ravel() * 255, bins=64, range=(0, 255), color='tab:orange', alpha=0.6, density=True, label=name[:10])
        ax.set_yticks([]); ax.set_title('yorqinlik (kulrang=ref)', fontsize=9)
        ax = fig.add_subplot(3, n, 2 * n + i + 1); ax.axis('off')
        row = {}
        for j, k in enumerate(REGIONS):
            for s, cc in ((0, rc[k]), (1, c[k])):
                if cc is not None:
                    ax.add_patch(plt.Rectangle((s * 0.5, 1 - (j + 1) / len(REGIONS)), 0.48, 0.9 / len(REGIONS), color=np.clip(cc, 0, 1)))
            d = de(rc[k], c[k]); row[k] = None if d is None else round(d, 1)
            ax.text(1.02, 1 - (j + 0.5) / len(REGIONS), f'{k}: ΔE {row[k]}', fontsize=8, va='center', transform=ax.transAxes)
        ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_title('chap=ref  o‘ng=render', fontsize=9)
        table[name] = row
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return table


if __name__ == '__main__':
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    print(json.dumps(panel(cfg['ref'], [tuple(x) for x in cfg['shots']], cfg['out']), indent=1))
