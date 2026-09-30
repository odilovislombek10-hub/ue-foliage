"""Shared config loader for ue/ (inside Unreal) and offline/ (UE-bundled python) scripts.

Reads <repo>/config.json (copy config.example.json and edit it). Nothing machine-specific is hard-coded
in the scripts: every path comes from here.
"""
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, 'data')


def _deep_update(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_update(a[k], v)
        else:
            a[k] = v
    return a


def load(path=None):
    """config.example.json supplies defaults, config.json overrides them."""
    ex = os.path.join(REPO, 'config.example.json')
    cfg = json.load(open(ex, encoding='utf-8'))
    p = path or os.environ.get('UEFOL_CONFIG') or os.path.join(REPO, 'config.json')
    if os.path.exists(p):
        _deep_update(cfg, json.load(open(p, encoding='utf-8')))
    else:
        print('[uefol] WARNING: %s not found, using config.example.json values' % p)
    cfg['_repo'] = REPO
    cfg['_data'] = DATA
    cfg['work_dir'] = os.path.abspath(os.path.expandvars(os.path.expanduser(cfg['work_dir'])))
    os.makedirs(cfg['work_dir'], exist_ok=True)
    pl = cfg.get('pylib') or os.path.join(REPO, 'pylib')
    pl = os.path.abspath(os.path.expandvars(os.path.expanduser(pl)))
    cfg['pylib'] = pl
    if os.path.isdir(pl) and pl not in sys.path:
        sys.path.insert(0, pl)
    return cfg


CFG = load()
WORK = CFG['work_dir']


def W(*parts):
    """path inside the work dir (created on demand)"""
    p = os.path.join(WORK, *parts)
    d = os.path.dirname(p)
    if d:
        os.makedirs(d, exist_ok=True)
    return p


def D(*parts):
    """path inside <repo>/data"""
    return os.path.join(DATA, *parts)


def lot_level_name(name):
    """lot / merged-lot name -> streaming sublevel name ('LOT_4' -> 'FOL_4', '34-1+34-2' -> 'FOL_34x1_34x2')"""
    n = name[4:] if name.startswith('LOT_') else name
    return CFG['foliage_level_prefix'] + n.replace('+', '_').replace('-', 'x')


def ft_path(mesh_path):
    """FoliageType asset path for a mesh: FT_<mesh name[:60]> in the FoliageType folder"""
    return CFG['foliage_type_folder'].rstrip('/') + '/FT_' + mesh_path.split('/')[-1].split('.')[0][:60]


def lib(rel):
    """tree-library relative path -> /Game path (rel like 'archa/pine_650cm')"""
    return CFG['tree_library_root'].rstrip('/') + '/' + rel
