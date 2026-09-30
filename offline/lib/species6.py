"""v6 plant library: every approved tree / shrub model, its role, tone, base scale and footprint.

D, H at scale 1 come from tree_geo.json (D = mean of dense-crown width and bbox width, as in v3).
Roles:  L large shade tree · M medium tree · S small / accent tree · P columnar (rows) · C conifer (own groups)
        K tall shrub (back row, 1.2-2.6 m) · E mounded shrub (middle row) · F low front shrub / edging ball
Tone:   D dark · G mid/fresh green · Y pale yellow-green (rule: D never within 8 m of Y; C never next to G/Y trees).
base = scale giving the intended size; every instance gets base * U(1-j, 1+j), j = 0.08-0.15 (client rule).
"""
import json, os
import env
from env import SP, CFG

# library root on this PC (same folder layout on every PC); data/tree_geo.json was measured under
# tree_library_root_in_data - keys are remapped if the root differs.
R = CFG['tree_library_root'].rstrip('/') + '/'
A = R + 'agalarov/izgirit/'
_R0 = CFG.get('tree_library_root_in_data', R).rstrip('/') + '/'
_geo = {(R + k[len(_R0):]) if k.startswith(_R0) else k: v
        for k, v in json.load(open(env.D('tree_geo.json'))).items()}


def _dim(mesh):
    g = _geo[mesh]
    cw = (g['crown_w_x'] + g['crown_w_y']) / 200.0
    bw = ((g['bbox'][3] - g['bbox'][0]) + (g['bbox'][4] - g['bbox'][1])) / 200.0
    return (cw + bw) / 2.0, g['zmax'] / 100.0


# key: (mesh, role, tone, base_scale, jitter)
LIB = {
    # ---- large shade trees
    'hornbeam': (R + 'yangi/Autumn_hornbeam_02_02', 'L', 'G', 1.10, 0.12),
    'ash0202':  (R + 'Ash-tree_0202_15_5m_', 'L', 'G', 1.10, 0.12),
    'ash0521':  (R + 'Ash-tree_05_21_2m_', 'L', 'G', 0.86, 0.10),
    'sbf3':     (R + 'Sample_Broadleaf_Forest3', 'L', 'G', 1.30, 0.12),
    'sbf2':     (R + 'Sample_Broadleaf_Forest2', 'L', 'G', 1.20, 0.12),
    'leaf':     (R + 'leaf', 'L', 'D', 1.38, 0.12),
    'birch':    (R + 'Silver_Birch_02', 'L', 'D', 0.80, 0.10),
    'ashY':     (R + 'Ash_tree', 'L', 'Y', 1.55, 0.10),      # Ash_tree x1.6 as a large tree
    # ---- medium
    'ash1':     (R + 'Ash_tree_1', 'M', 'D', 1.45, 0.12),
    'leafsg':   (R + 'leaf_MatSG', 'M', 'D', 1.20, 0.12),
    'pear':     (R + 'Autumn_pear_tree_02_02', 'M', 'G', 1.40, 0.10),
    'ashYm':    (R + 'Ash_tree', 'M', 'Y', 1.15, 0.10),
    'proxy137': (A + 'Corona_Proxy137', 'M', 'D', 1.30, 0.12),
    'birch6':   (R + 'Silver_Birch_Medium_6m_01', 'M', 'G', 1.30, 0.12),
    'birch6b':  (R + 'Silver_Birch_Medium_6m_02', 'M', 'G', 1.30, 0.12),
    # ---- small / accent trees
    'crataegus': (R + 'Crataegus_Prunifolia', 'S', 'G', 1.15, 0.12),
    'crat_m1':  (R + 'Crataegus_Prunifolia_min_01', 'S', 'G', 1.20, 0.12),
    'crat_m2':  (R + 'Crataegus_Prunifolia_min_02', 'S', 'G', 1.25, 0.12),
    'irga':     (R + '3m_Irga_02', 'S', 'D', 1.05, 0.12),
    'sakura':   (R + 'sakura/Cherry_flowering_0302_Cerasus_', 'S', 'G', 1.05, 0.10),
    'lager':    (R + 'Lagerstroemia_speciosa', 'S', 'D', 1.20, 0.10),
    'pot65':    (A + 'Collection_outdoor_indoor_62_pot_plant___tree___bush___fern_the_garden_pot65', 'S', 'D', 1.30, 0.10),
    'dub':      (R + 'dub_4m_02', 'S', 'G', 1.30, 0.10),
    # ---- columnar
    'terak1':   (R + '18m_Terak_01', 'P', 'G', 0.87, 0.08),
    'terak2':   (R + '18m_Terak_02', 'P', 'G', 0.82, 0.08),
    'pearP':    (R + 'Autumn_pear_tree_02_02', 'P', 'G', 1.35, 0.08),
    # ---- conifers
    'pine650':  (R + 'archa/pine_650cm', 'C', 'D', 1.00, 0.10),
    'pine550':  (R + 'archa/pine_550cm', 'C', 'D', 1.10, 0.10),
    'pine450':  (R + 'archa/pine_450cm', 'C', 'D', 1.20, 0.10),
    'hach':     (A + 'Hach-Pine-tall002', 'C', 'D', 1.40, 0.10),
    'junip':    (R + 'Juniperus_Scopulorum', 'C', 'D', 1.90, 0.10),
    # ---- tall shrubs (back row)
    'oleander': (A + 'crp_MT_PM_Nerium_Oleander_01_020', 'K', 'D', 1.05, 0.10),
    'tsh2':     (A + 'TSH-Tree002', 'K', 'G', 1.10, 0.10),
    'tsh1':     (A + 'TSH-Tree001', 'K', 'G', 1.10, 0.10),
    'montra2':  (A + 'Montra_Olive_Tree_Version7_2', 'K', 'D', 1.35, 0.10),
    'plant':    (A + 'plant', 'K', 'D', 1.25, 0.10),
    'bidi':     (R + 'Biger-Bidi001', 'K', 'Y', 1.00, 0.10),
    # ---- mounded shrubs (middle row)
    'box22788': (A + 'Corona_Proxy22788', 'E', 'D', 1.30, 0.10),
    'box26394': (A + 'Corona_Proxy26394', 'E', 'D', 1.30, 0.10),
    'block26313': (A + 'Corona_Proxy26313', 'E', 'D', 1.00, 0.08),
    'ros':      (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary', 'E', 'D', 1.45, 0.10),
    'ros04':    (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary04', 'E', 'D', 1.35, 0.10),
    'ros04b':   (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary04_02', 'E', 'D', 1.30, 0.10),
    'ros05':    (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary05', 'E', 'D', 1.40, 0.10),
    'ros05b':   (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary05_02', 'E', 'D', 1.35, 0.10),
    'spirea':   (A + 'Spirea_japonica_1', 'E', 'G', 1.30, 0.10),
    'lav02':    (A + 'Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata02', 'E', 'G', 1.15, 0.10),
    'lav03':    (A + 'Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata03', 'E', 'G', 1.15, 0.10),
    'lav04':    (A + 'Lavandula_Pedunculata_Atlantica_Stoechas_Subpedunculata04', 'E', 'G', 1.15, 0.10),
    # ---- low front shrubs / balls
    'box071':   (A + 'Corona_Proxy071', 'F', 'D', 1.80, 0.10),
    'box072':   (A + 'Corona_Proxy072', 'F', 'D', 1.60, 0.10),
    'montra1':  (A + 'Montra_Olive_Tree_Version7_1', 'F', 'D', 1.35, 0.10),
    'rosf04':   (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower04', 'F', 'D', 1.40, 0.10),
    'rosf05':   (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower05', 'F', 'D', 1.60, 0.10),
    'rosv2':    (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower_Version02_2', 'F', 'D', 1.70, 0.10),
    'rosv4':    (A + 'Grey_Box_Westringia_Fruticosa_Coastal_Rosemary_Flower_Version02_4', 'F', 'D', 1.70, 0.10),
    'lavanda':  (A + 'LAVANDA', 'F', 'G', 1.40, 0.10),
}
TREE_ROLES = set('LMSPC')
SHRUB_ROLES = set('KEF')

DIM = {}
for k, v in LIB.items():
    DIM[k] = _dim(v[0])


def mesh(k): return LIB[k][0]
def role(k): return LIB[k][1]
def tone(k): return LIB[k][2]
def base(k): return LIB[k][3]
def jit(k): return LIB[k][4]
def D(k, s): return DIM[k][0] * s
def H(k, s): return DIM[k][1] * s
def is_tree(k): return LIB[k][1] in TREE_ROLES


MESH_D = {}   # mesh path -> D at s=1 (for metrics on any xf file)
for k, v in LIB.items():
    MESH_D[v[0]] = DIM[k][0]
for m in _geo:
    if m not in MESH_D and 'bbox' in _geo[m]:
        g = _geo[m]
        MESH_D[m] = ((g['crown_w_x'] + g['crown_w_y']) / 200.0 + ((g['bbox'][3] - g['bbox'][0]) + (g['bbox'][4] - g['bbox'][1])) / 200.0) / 2

# ---------------------------------------------------------------------------------------------
# Harmony groups (one per courtyard / lot).  Weights ~ 60/30/10 dominance inside each list.
GROUPS = {
    'fresh':   dict(L=[('hornbeam', .45), ('ash0202', .30), ('ashY', .25)],
                    M=[('pear', .5), ('ashYm', .3), ('birch6', .1), ('birch6b', .1)],
                    S=[('crataegus', .4), ('crat_m1', .35), ('sakura', .25)], C=None),
    'sage':    dict(L=[('ash0202', .40), ('sbf3', .35), ('sbf2', .25)],
                    M=[('pear', .6), ('ashYm', .4)],
                    S=[('crataegus', .4), ('dub', .3), ('crat_m2', .3)], C=None),
    'deep':    dict(L=[('leaf', .40), ('birch', .35), ('sbf3', .25)],
                    M=[('ash1', .45), ('leafsg', .35), ('proxy137', .20)],
                    S=[('irga', .45), ('pot65', .30), ('lager', .25)], C=['pine650', 'pine550', 'pine450', 'hach', 'junip']),
    'blossom': dict(L=[('sbf3', .40), ('hornbeam', .30), ('ash0202', .30)],
                    M=[('ash1', .5), ('pear', .5)],
                    S=[('sakura', .40), ('lager', .30), ('crat_m1', .30)], C=None),
}
# street rows (masterplan-wide so a street reads the same across lots)
STREET_WIDE = [('ash0521', .30), ('ash0202', .25), ('sbf3', .20), ('hornbeam', .15), ('ashY', .10)]
STREET_NARROW = [('terak1', .42), ('terak2', .42), ('pearP', .16)]

# shrub combinations: (back K, middle E, front F).  Each skirt / drift uses one combo -> 2-4 species.
COMBOS = {
    'c1': ('oleander', ['ros05', 'ros'], 'box071'),
    'c2': ('tsh2', ['ros05b'], 'rosf04'),
    'c3': ('montra2', ['box22788', 'box26394'], 'montra1'),
    'c4': ('plant', ['ros'], 'box072'),
    'c5': ('montra2', ['box26394', 'lav03'], 'rosf05'),
    'c6': ('tsh2', ['spirea', 'ros05'], 'box071'),
    'c7': ('oleander', ['box26394', 'ros04'], 'rosv2'),
    'c8': ('plant', ['ros04b', 'lav04'], 'rosv4'),
    'c9': ('tsh1', ['lav02', 'ros05b'], 'lavanda'),
    'c10': ('bidi', ['lav02', 'spirea'], 'rosf05'),
}
# light-tone combos go with fresh/blossom lots, dark with deep/sage; each lot gets 3-4 of them
LOT_COMBOS = {
    'fresh': ['c2', 'c6', 'c9', 'c10', 'c4'],
    'sage': ['c1', 'c3', 'c5', 'c8', 'c2'],
    'deep': ['c1', 'c3', 'c7', 'c4', 'c8'],
    'blossom': ['c5', 'c6', 'c9', 'c2', 'c3'],
}
NO_PLAY = {'oleander'}   # toxic: never within 10 m of a playground

# placement offsets (m)
EDGE_OFF = dict(L=2.5, M=1.8, S=1.2, P=1.3, C=2.0)          # lawn edge -> trunk
FACADE_OFF = dict(L=6.0, M=4.5, S=3.0, P=4.0, C=5.0)         # facade -> trunk
ROAD_OFF = dict(L=2.0, M=2.0, S=1.8, P=1.5, C=3.0)

# lot -> harmony group and public-park lots come from <work>/lots_resolved.json (offline/04_lots.py apply).
# Zaliniy values: data/examples/lots.zaliniy.json.  Lots missing there fall back to 'fresh' (engine default).
_lr = os.path.join(SP, 'lots_resolved.json')
_lots = json.load(open(_lr, encoding='utf-8')) if os.path.exists(_lr) else {}
LOT_GROUP = dict(_lots.get('palettes', {}))
PARK_LOTS = set(_lots.get('parks', []))   # public parks: deliberate glades allowed
