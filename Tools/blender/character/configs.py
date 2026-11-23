"""Character definitions. Asset paths are relative to Assets/ThirdParty/makehuman/ (see fetch_assets.py)."""
from . import garments as G

SYS = 'makehuman_system_assets_cc0'
BROWS = SYS + '/eyebrows/eyebrow001/eyebrow001.mhclo'
LASHES = SYS + '/eyelashes/eyelashes01/eyelashes01.mhclo'

CONFIGS = {}

# ----------------------------------------------------------------------------- Doudou BA (player)
CONFIGS['doudou'] = dict(
    name='doudou', height=1.82,
    macro=dict(gender=1.0, age=0.5, muscle=0.5, weight=0.40, height=0.5, proportions=0.6,
               race=dict(asian=0.0, caucasian=0.0, african=1.0)),
    skin=SYS + '/skins/young_african_male/young_african_male.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    eyebrows=BROWS, eyelashes=LASHES,
    clothes=[
        ('hoodie', 'shirts02_ccby/clothes/elvs_hooded_sweat_jacket1/elvs_hooded_sweat_jacket1.mhclo'),
        ('jeans', 'pants02_ccby/clothes/punkduck_male_classic_jeans/punkduck_male_classic_jeans.mhclo'),
        ('shoes', 'shoes02_ccby/clothes/punkduck_tennis_shoes/punkduck_tennis_shoes.mhclo'),
    ],
    layers=['hoodie', 'jeans', 'shoes'],
    tuck=[('jeans', 'hoodie', 0.035)],
    hooks=[G.hoodie_pullover, G.kangaroo_pocket, G.chest_logo, G.fleece_material, G.hair_cap],
    hoodie=dict(color=(155, 135, 184)),            # #9B87B8
    mat=dict(
        body=dict(rough=0.55),
        eyes=dict(drop_alpha=True, post=G.dark_brown_eyes, rough=0.25, size=512),
        jeans=dict(post=G.washed_denim(), rough=0.85, normal_strength=0.8),
        shoes=dict(rough=0.6, normal_strength=0.8),
        eyebrows=dict(mul=(0.35, 0.3, 0.3), size=256), eyelashes=dict(size=256),
    ),
)

# ----------------------------------------------------------------------------- pedestrians (Stockholm winter)
PED_MAT = dict(body=dict(rough=0.6, size=512), eyes=dict(drop_alpha=True, rough=0.25, size=256),
               eyebrows=dict(size=256), eyelashes=dict(size=256))


def _ped(name, **kw):
    cfg = dict(name=name, eyebrows=BROWS, eyelashes=LASHES, extra_clips=True)
    cfg.update(kw)
    m = {k: dict(v) for k, v in PED_MAT.items()}
    for k, v in kw.get('mat', {}).items():
        m.setdefault(k, {}).update(v)
    for k in m:
        m[k].setdefault('size', 512); m[k].setdefault('normal_size', 512)
    cfg['mat'] = m
    return cfg


# 1: man, mid-50s, quilted jacket + jeans (one CC0 suit mesh), ankle boots, gloves, scarf
CONFIGS['pedestrian_01'] = _ped(
    'pedestrian_01', height=1.80,
    macro=dict(gender=1.0, age=0.72, muscle=0.45, weight=0.62, height=0.5, proportions=0.5,
               race=dict(asian=0.0, caucasian=1.0, african=0.0)),
    skin=SYS + '/skins/middleage_caucasian_male/middleage_caucasian_male.mhmat',
    eye_mat=SYS + '/eyes/materials/blue.mhmat',
    hair=SYS + '/hair/short02/short02.mhclo',
    clothes=[('suit', SYS + '/clothes/male_casualsuit05/male_casualsuit05.mhclo'),
             ('shoes', 'shoes01_cc0/clothes/toigo_ankle_boots_male/toigo_ankle_boots_male.mhclo'),
             ('gloves', 'gloves01_cc0/clothes/toigo_gloves_short/toigo_gloves_short.mhclo')],
    layers=['gloves', 'suit', 'shoes'],
    hooks=[G.scarf], scarf=dict(color=(120, 36, 40)),
    mat=dict(hair=dict(post=G.grey_hair(0.85)), suit=dict(rough=0.8), shoes=dict(rough=0.5), gloves=dict(rough=0.6)),
)

# 2: woman, ~30, long cardigan-coat over a fisherman sweater, wool trousers, ankle boots, scarf
CONFIGS['pedestrian_02'] = _ped(
    'pedestrian_02', height=1.69,
    macro=dict(gender=0.0, age=0.54, muscle=0.45, weight=0.45, height=0.5, proportions=0.6, cupsize=0.45, firmness=0.5,
               race=dict(asian=0.0, caucasian=0.0, african=1.0)),
    skin=SYS + '/skins/young_african_female/young_african_female.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    hair=SYS + '/hair/afro01/afro01.mhclo',
    clothes=[('coat', 'shirts02_ccby/clothes/mindfront_cardigan_long_open_front/mindfront_cardigan_long_open_front.mhclo'),
             ('sweater', 'shirts01_cc0/clothes/toigo_fisherman_sweater/toigo_fisherman_sweater.mhclo'),
             ('pants', 'pants01_cc0/clothes/toigo_wool_pants/toigo_wool_pants.mhclo'),
             ('shoes', 'shoes01_cc0/clothes/toigo_ankle_boots_female/toigo_ankle_boots_female.mhclo')],
    layers=['coat', 'sweater', 'pants', 'shoes'],
    push=[('coat', 'sweater', 0.010), ('coat', 'pants', 0.008), ('sweater', 'pants', 0.006)],
    cull_rings=dict(sweater=0), no_cull=('pants',),
    hooks=[G.scarf], scarf=dict(color=(196, 150, 48)),
    mat=dict(eyes=dict(post=G.dark_brown_eyes),
             coat=dict(post=G.tint((70, 52, 40), (176, 140, 104)), rough=0.9),
             sweater=dict(post=G.tint((150, 144, 132), (236, 230, 216)), rough=0.9),
             pants=dict(post=G.tint((22, 22, 26), (70, 70, 78)), rough=0.85), shoes=dict(post=G.tint((20, 16, 14), (90, 70, 56)), rough=0.5)),
)

# 3: woman, mid-60s, Norwegian-style knitted cardigan, jeans tucked into winter boots, scarf
CONFIGS['pedestrian_03'] = _ped(
    'pedestrian_03', height=1.63,
    macro=dict(gender=0.0, age=0.80, muscle=0.4, weight=0.62, height=0.5, proportions=0.45, cupsize=0.5, firmness=0.4,
               race=dict(asian=0.0, caucasian=1.0, african=0.0)),
    skin=SYS + '/skins/old_caucasian_female/old_caucasian_female.mhmat',
    eye_mat=SYS + '/eyes/materials/grey.mhmat',
    hair=SYS + '/hair/short03/short03.mhclo',
    clothes=[('cardigan', 'shirts02_ccby/clothes/mindfront_lusekofta/mindfront_lusekofta.mhclo'),
             ('pants', 'pants02_ccby/clothes/mindfront_female_trousers_1/mindfront_female_trousers_1.mhclo'),
             ('shoes', 'shoes03_ccby/clothes/punkduck_winter_boots/punkduck_winter_boots.mhclo')],
    layers=['cardigan', 'shoes', 'pants'], no_cull=('pants',),
    push=[('cardigan', 'pants', 0.006)], trim_below=[('pants', 'shoes', 0.03)],
    hooks=[G.scarf], scarf=dict(color=(150, 44, 52)),
    mat=dict(hair=dict(post=G.grey_hair(0.9, 1.3)),
             cardigan=dict(rough=0.9), pants=dict(rough=0.85), shoes=dict(rough=0.7)),
)

# 4: man, mid-20s, heavy knit sweater, cargo trousers, boots, scarf, beanie
CONFIGS['pedestrian_04'] = _ped(
    'pedestrian_04', height=1.76,
    macro=dict(gender=1.0, age=0.48, muscle=0.5, weight=0.5, height=0.5, proportions=0.5,
               race=dict(asian=1.0, caucasian=0.0, african=0.0)),
    skin=SYS + '/skins/young_asian_male/young_asian_male.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    hair=SYS + '/hair/short04/short04.mhclo',
    clothes=[('sweater', 'shirts01_cc0/clothes/toigo_fisherman_sweater/toigo_fisherman_sweater.mhclo'),
             ('pants', 'pants01_cc0/clothes/cortu_cargo_pants/cortu_cargo_pants.mhclo'),
             ('shoes', SYS + '/clothes/shoes03/shoes03.mhclo')],
    layers=['hat', 'sweater', 'shoes', 'pants', 'hair'], no_cull=('pants',),
    push=[('sweater', 'pants', 0.010)],
    hooks=[G.scarf, G.beanie], scarf=dict(color=(92, 96, 100)), beanie=dict(color=(188, 146, 52)),
    mat=dict(eyes=dict(post=G.dark_brown_eyes), sweater=dict(post=G.tint((18, 30, 52), (70, 96, 140)), rough=0.9),
             pants=dict(post=G.tint((50, 52, 40), (128, 126, 100)), rough=0.85), shoes=dict(rough=0.5)),
)
