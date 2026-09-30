"""Numeric image audit: luminance percentiles, clipping / crushing, contrast, shadow & highlight colour,
foliage share and colour bands, sky colour, saturation. Run it on the reference AND the render.

Usage:  python imgaudit.py image1.png [image2.jpg ...]     (prints JSON)
Origin: imgaudit.py."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib'))
import env  # noqa: E402
import json  # noqa: E402
import numpy as np
from PIL import Image
import colorsys


def load(p, w=960):
    im = Image.open(p).convert('RGB')
    im = im.resize((w, int(im.height * w / im.width)))
    return np.asarray(im).astype(np.float32)


def lin(a):
    a = a / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def stats(p):
    a = load(p)
    L = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    hsv = np.asarray(Image.fromarray(a.astype(np.uint8)).convert('HSV')).astype(np.float32)
    H, S, V = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    foliage = (H > 35) & (H < 150) & (S > 0.18) & (V > 0.06)
    sky = (a[..., 2] > a[..., 0] + 8) & (V > 0.55) & (S < 0.45)
    sky[int(a.shape[0] * 0.5):] = False
    out = {}
    out['lum_p'] = {k: round(float(np.percentile(L, k)), 1) for k in (1, 5, 25, 50, 75, 95, 99)}
    out['clip%'] = round(float((L >= 250).mean() * 100), 2)
    out['crush%'] = round(float((L <= 8).mean() * 100), 2)
    out['contrast_p95/p5_lin'] = round(float(np.percentile(lin(L), 95) / max(np.percentile(lin(L), 5), 1e-4)), 1)
    sh = L < np.percentile(L, 15)
    hi = L > np.percentile(L, 90)
    for name, m in (('shadow', sh), ('highlight', hi)):
        c = a[m].mean(0)
        out[name + '_rgb'] = [int(x) for x in c]
        out[name + '_B/G'] = round(float(c[2] / max(c[1], 1)), 2)
        out[name + '_R/G'] = round(float(c[0] / max(c[1], 1)), 2)
    out['foliage%'] = round(float(foliage.mean() * 100), 1)
    if foliage.sum() > 200:
        fl = L[foliage]; fa = a[foliage]
        bands = {}
        for nm, lo, hi_ in (('shade', 0, 30), ('mid', 30, 70), ('lit', 70, 95), ('top', 95, 100)):
            q0, q1 = np.percentile(fl, lo), np.percentile(fl, hi_)
            m = (fl >= q0) & (fl <= q1)
            bands[nm] = [int(x) for x in fa[m].mean(0)]
        out['foliage_bands_rgb'] = bands
        out['foliage_hue_med'] = round(float(np.median(H[foliage])), 1)
        out['foliage_sat_med'] = round(float(np.median(S[foliage])), 2)
    if sky.sum() > 200:
        out['sky_rgb'] = [int(x) for x in a[sky].mean(0)]
        out['sky_sat'] = round(float(S[sky].mean()), 2)
    out['global_sat_med'] = round(float(np.median(S)), 2)
    return out


if __name__ == '__main__':
    res = {os.path.basename(p): stats(p) for p in sys.argv[1:]}
    print(json.dumps(res, indent=1))
