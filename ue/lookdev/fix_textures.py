"""LOOKDEV (in editor): give the foliage textures mip-maps (distant trees sparkled / looked broken without them).

!! SHARED LIBRARY EDIT !!  the textures live in /Game/SHABLON/MODEL (tree library) - every project on the PC sees it.

List: data/lookdev/tex_roles.json ([texture path, [roles]] for the 177 textures used by foliage materials).
A texture is touched only if it still needs it (NoMipmaps, TC_EDITOR_ICON compression or never_stream):
  mip_gen_settings NoMipmaps -> FromTextureGroup; compression EDITOR_ICON -> DEFAULT; never_stream -> False;
  non power-of-two -> stretch to power of two; opacity/mask maps: scale mips for alpha coverage (threshold 0.3333)
  and 4k masks capped to 2048. sRGB / sampler type stay as they are.
Backup .uasset.bak_YYYYMMDD first, then save. Rebuilding textures is slow: ARGS batch (10) per call, call again
until left == 0. On Zaliniy 103 textures were fixed (data/lookdev/logs/applied_tex.json).
ARGS: batch (10), dry_run (False)
Origin: fix_tex.py + calls #574-#577.
"""
import datetime
import json
import os
import sys

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
sys.path.insert(0, os.path.join(_d, 'ue'))
import ue_common as U  # noqa: E402
import unreal  # noqa: E402

A = U.args(dict(batch=10, dry_run=False))
OPAC = ('Opacity', 'Mask', 'opacity')


def is_pot(n):
    return n > 0 and (n & (n - 1)) == 0


def load_tex(p):
    return unreal.find_object(None, p + '.' + p.split('/')[-1]) or unreal.load_asset(p)


def needs(t):
    return (t.get_editor_property('mip_gen_settings') == unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS
            or t.compression_settings == unreal.TextureCompressionSettings.TC_EDITOR_ICON or t.never_stream)


def todo():
    out = []
    for p, r in json.load(open(U.D('lookdev', 'tex_roles.json'))):
        if p.split('/')[-1].startswith('Default'):
            continue
        t = load_tex(p)
        if t is None:
            continue
        if needs(t):
            out.append((p, r))
    return out


def fix(p, r):
    t = load_tex(p)
    U.backup_asset(p)
    w, h = t.blueprint_get_size_x(), t.blueprint_get_size_y()
    ch = {}
    if t.get_editor_property('mip_gen_settings') == unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS:
        t.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP); ch['mips'] = 1
    if t.compression_settings == unreal.TextureCompressionSettings.TC_EDITOR_ICON:
        t.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_DEFAULT); ch['comp'] = 'DEFAULT'
    if t.never_stream:
        t.set_editor_property('never_stream', False); ch['stream'] = 1
    if not (is_pot(w) and is_pot(h)):
        t.set_editor_property('power_of_two_mode', unreal.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO); ch['pot'] = 1
    if any(x in r for x in OPAC):
        t.set_editor_property('do_scale_mips_for_alpha_coverage', True)
        t.set_editor_property('alpha_coverage_thresholds', unreal.Vector4(0.3333, 0, 0, 0)); ch['cov'] = 1
        if max(w, h) >= 4096:
            t.set_editor_property('max_texture_size', 2048); ch['max'] = 2048
    t.modify()
    unreal.EditorAssetLibrary.save_loaded_asset(t)
    return (p.split('/')[-1], r, w, h, ch)


def main():
    U.editor_world()
    L = todo()
    if A['dry_run']:
        return dict(need_fix=len(L), first=[p for p, r in L[:20]])
    log = [fix(p, r) for p, r in L[:int(A['batch'])]]
    out = U.W('lookdev', 'textures_%s.json' % datetime.date.today().strftime('%Y%m%d'))
    prev = json.load(open(out)) if os.path.exists(out) else []
    json.dump(prev + log, open(out, 'w'), indent=0)
    return dict(fixed=len(log), left=len(L) - len(log), log=out)


if __name__ == '__main__':
    RESULT = main()
    print(RESULT)
