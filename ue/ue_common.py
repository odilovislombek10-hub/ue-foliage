"""Helpers shared by every in-editor script (import only inside Unreal).

How to run any ue/ script from the Unreal MCP tool (mcp__unreal__run_python):

    import runpy
    result = runpy.run_path(r'<REPO>/ue/01_export_grass.py', init_globals={'ARGS': {}}, run_name='__main__').get('RESULT')

or from the editor console:  py "<REPO>/ue/01_export_grass.py"

Safety rules baked in here (learned the hard way on Zaliniy):
 * never keep UObjects (actors, components, worlds, assets) in builtins - they block GC and UE crashes
   ("Old World not cleaned up") on the next load_level. Only plain data (numbers, lists, numpy) is kept.
 * never delete builtins that are not ours - the MCP listener keeps its own state there.
 * always check that the editor world exists (it is None while a map is loading).
"""
import builtins
import ctypes
import datetime
import gc
import json
import os
import shutil
import sys
import time

import unreal

_d = os.path.dirname(os.path.abspath(__file__))
while not os.path.exists(os.path.join(_d, 'config.example.json')):
    _d = os.path.dirname(_d)
if os.path.join(_d, 'common') not in sys.path:
    sys.path.insert(0, os.path.join(_d, 'common'))
import uefol_config as C  # noqa: E402

CFG, W, D = C.CFG, C.W, C.D

# names this pipeline (and the original Zaliniy session) ever put into builtins
OWN_BUILTINS = ('_uefol', '_uefol_trace', '_uefol_shots', '_uefol_cine', '_uefol_settle', '_uefol_chain',
                '_grass', '_zones', '_studio', '_staged', '_vp', '_fts', '_shotq', '_st', '_vpg', '_tg', '_tm',
                '_tmeta', '_tgeo', '_tgeo_file', '_go', '_gg', '_gtris', '_gov', '_gw', '_zg', '_zg2', '_z3',
                '_pl', '_d2_20', '_geo', '_geo2', '_align', '_cem', '_cx', '_ln', '_spl', '_shot_done', '_shot_todo')


def editor_world(required=True):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if w is None and required:
        raise RuntimeError('editor world is None (map still loading?) - wait and retry')
    return w


def world_name():
    w = editor_world(False)
    return None if w is None else w.get_name()


def clear_refs(keep=()):
    """drop our own builtins entries that may hold UObjects (never touches foreign names)"""
    for k in OWN_BUILTINS:
        if k in keep:
            continue
        v = builtins.__dict__.get(k)
        if isinstance(v, dict) and v.get('state') not in (None, 'finished') and 'cb' in v:
            continue  # a running tick queue; stop it with its own stop() first
        builtins.__dict__.pop(k, None)
    gc.collect()


def mem():
    class _MS(ctypes.Structure):
        _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong), ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong), ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong), ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong), ('x', ctypes.c_ulonglong)]
    m = _MS(); m.dwLength = ctypes.sizeof(_MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return dict(phys_free_gb=round(m.ullAvailPhys / 2 ** 30, 1), commit_free_gb=round(m.ullAvailPageFile / 2 ** 30, 1))


def today_suffix():
    s = CFG.get('lookdev', {}).get('backup_suffix') or ''
    return s or ('.bak_' + datetime.date.today().strftime('%Y%m%d'))


def content_dir():
    return unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())


def asset_file(obj_or_path):
    """/Game/... package (or asset object) -> .uasset file on disk"""
    p = obj_or_path if isinstance(obj_or_path, str) else obj_or_path.get_path_name()
    pkg = p.split('.')[0]
    if not pkg.startswith('/Game/'):
        return None
    return content_dir() + pkg[len('/Game/'):] + '.uasset'


def backup_asset(obj_or_path):
    """copy <asset>.uasset to <asset>.uasset.bak_YYYYMMDD once (never overwrites an existing backup)"""
    f = asset_file(obj_or_path)
    if not f or not os.path.exists(f):
        return False
    b = f + today_suffix()
    if not os.path.exists(b):
        shutil.copy2(f, b)
    return True


def save_dirty():
    ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    left = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
            + unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    return dict(saved=ok, still_dirty=left)


def load_level(path):
    """switch the editor map; clears our builtins first (UObject refs crash the old-world GC)"""
    clear_refs()
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(path)
    gc.collect()
    return ok


def short(path):
    return path.split('/')[-1].split('.')[0]


def refresh():
    """re-read config.json (modules stay cached inside the editor between MCP calls)"""
    global C, CFG, W, D
    import importlib
    C = importlib.reload(C)
    CFG, W, D = C.CFG, C.W, C.D


def args(defaults):
    """merge ARGS (runpy init_globals) / sys.argv key=value pairs over defaults (also re-reads config.json)"""
    refresh()
    out = dict(defaults)
    g = sys._getframe(1).f_globals
    a = g.get('ARGS') or {}
    out.update(a)
    for s in sys.argv[1:]:
        if '=' in s:
            k, v = s.split('=', 1)
            try:
                v = json.loads(v)
            except Exception:
                pass
            out[k] = v
    return out


class Timer:
    def __init__(self, budget):
        self.t0 = time.time(); self.budget = budget

    def left(self):
        return self.budget - (time.time() - self.t0)

    def over(self):
        return self.left() <= 0
