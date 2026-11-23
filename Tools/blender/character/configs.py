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
    hooks=[G.reweight('gloves'), G.scarf], scarf=dict(color=(120, 36, 40)),
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
    push=[('sweater', 'pants', 0.006), ('coat', 'sweater', 0.010), ('coat', 'pants', 0.020)],
    cull_rings=dict(sweater=0, pants=1), cull_dist_cloth=0.15,     # trousers hidden by the long coat are removed
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
    hair=SYS + '/hair/short02/short02.mhclo',
    clothes=[('cardigan', 'shirts02_ccby/clothes/mindfront_lusekofta/mindfront_lusekofta.mhclo'),
             ('pants', 'pants02_ccby/clothes/mindfront_female_trousers_1/mindfront_female_trousers_1.mhclo'),
             ('shoes', 'shoes03_ccby/clothes/punkduck_winter_boots/punkduck_winter_boots.mhclo')],
    layers=['cardigan', 'shoes', 'pants'], no_cull=('pants',),
    push=[('cardigan', 'pants', 0.006)], trim_below=[('pants', 'shoes', 0.03)],
    hooks=[G.scarf], scarf=dict(color=(150, 44, 52)),
    mat=dict(hair=dict(post=G.grey_hair(0.95, 1.7)),
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

# ----------------------------------------------------------------------------- story NPCs (npcs.json; all fictional)
COAT = 'shirts02_ccby/clothes/mindfront_cardigan_long_open_front/mindfront_cardigan_long_open_front.mhclo'
HOODED = 'shirts02_ccby/clothes/elvs_hooded_sweat_jacket1/elvs_hooded_sweat_jacket1.mhclo'
FISHERMAN = 'shirts01_cc0/clothes/toigo_fisherman_sweater/toigo_fisherman_sweater.mhclo'
BOOTS_F = 'shoes01_cc0/clothes/toigo_ankle_boots_female/toigo_ankle_boots_female.mhclo'
BLACK_LEATHER = G.tint((12, 11, 11), (70, 64, 60))

# Noor Haddad - cafe owner, 40s: long wool coat (forest green) over a terracotta knit, cream scarf
CONFIGS['npc_noor'] = _ped(
    'npc_noor', height=1.66,
    macro=dict(gender=0.0, age=0.64, muscle=0.45, weight=0.56, height=0.5, proportions=0.5, cupsize=0.5, firmness=0.5,
               race=dict(asian=0.10, caucasian=0.65, african=0.25)),
    skin=SYS + '/skins/middleage_caucasian_female/middleage_caucasian_female.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    hair=SYS + '/hair/long01/long01.mhclo',
    clothes=[('coat', COAT), ('sweater', FISHERMAN),
             ('pants', 'pants01_cc0/clothes/toigo_wool_pants/toigo_wool_pants.mhclo'), ('shoes', BOOTS_F)],
    layers=['coat', 'sweater', 'pants', 'shoes'],
    push=[('sweater', 'pants', 0.006), ('coat', 'sweater', 0.010), ('coat', 'pants', 0.020)],
    cull_rings=dict(sweater=0, pants=1), cull_dist_cloth=0.15,
    hooks=[G.scarf], scarf=dict(color=(226, 212, 186)),
    mat=dict(body=dict(mul=(0.90, 0.80, 0.68)), eyes=dict(post=G.dark_brown_eyes),
             hair=dict(post=G.tint((14, 11, 10), (78, 58, 46))),
             coat=dict(post=G.tint((14, 30, 26), (46, 78, 66)), rough=0.9),
             sweater=dict(post=G.tint((110, 44, 26), (204, 116, 80)), rough=0.9),
             pants=dict(post=G.tint((14, 14, 16), (56, 56, 62)), rough=0.85), shoes=dict(post=BLACK_LEATHER, rough=0.5)),
)

# Sami Okafor - ICU nurse, 30s, tall: navy hooded padded jacket (open zip) over teal scrubs, grey beanie
CONFIGS['npc_sami'] = _ped(
    'npc_sami', height=1.88,
    macro=dict(gender=1.0, age=0.56, muscle=0.62, weight=0.55, height=0.6, proportions=0.6,
               race=dict(asian=0.0, caucasian=0.0, african=1.0)),
    skin=SYS + '/skins/middleage_african_male/middleage_african_male.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    clothes=[('jacket', HOODED),
             ('shirt', 'shirts01_cc0/clothes/elvs_crude_t-shirt_male/elvs_crude_t-shirt_male.mhclo'),
             ('pants', 'pants02_ccby/clothes/mindfront_male_trousers_1/mindfront_male_trousers_1.mhclo'),
             ('shoes', SYS + '/clothes/shoes05/shoes05.mhclo')],
    layers=['hat', 'jacket', 'shirt', 'pants', 'shoes', 'hair'], no_cull=('pants',),      # socks hidden by trouser legs
    push=[('shirt', 'pants', 0.006), ('jacket', 'shirt', 0.008), ('jacket', 'pants', 0.008)],
    hooks=[G.hoodie_pullover, G.hair_cap, G.beanie],
    hoodie=dict(role='jacket', close=False, loosen=0.014, hem_below_hip=0.0),
    hair_cap=dict(top=0.007, side=0.005, edge=0.003, subdiv=1, noise=0.0008),
    beanie=dict(color=(92, 96, 104)),
    mat=dict(eyes=dict(post=G.dark_brown_eyes),
             jacket=dict(post=G.tint((14, 24, 52), (74, 102, 160)), rough=0.75, normal_strength=1.2),
             shirt=dict(post=G.tint((20, 104, 110), (120, 200, 198)), rough=0.85),
             pants=dict(post=G.tint((16, 92, 98), (104, 186, 184)), rough=0.85), shoes=dict(rough=0.6)),
)

# Aditi Rao - baker / former engineer, late 30s, 1.62 m: plum patterned knit cardigan, dark jeans, braid
CONFIGS['npc_aditi'] = _ped(
    'npc_aditi', height=1.62,
    macro=dict(gender=0.0, age=0.59, muscle=0.45, weight=0.52, height=0.4, proportions=0.5, cupsize=0.5, firmness=0.5,
               race=dict(asian=0.30, caucasian=0.50, african=0.20)),
    skin=SYS + '/skins/young_asian_female/young_asian_female.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    hair=SYS + '/hair/braid01/braid01.mhclo',
    clothes=[('cardigan', 'shirts02_ccby/clothes/mindfront_lusekofta/mindfront_lusekofta.mhclo'),
             ('pants', 'pants02_ccby/clothes/punkduck_female_tight_jeans/punkduck_female_tight_jeans.mhclo'),
             ('shoes', BOOTS_F)],
    layers=['cardigan', 'shoes', 'pants'], no_cull=('pants',),
    push=[('cardigan', 'pants', 0.006)], hooks=[G.trim_fringe],
    mat=dict(body=dict(mul=(0.76, 0.62, 0.50)), eyes=dict(post=G.dark_brown_eyes),
             cardigan=dict(post=G.recolor(('blue', (74, 14, 40), (214, 120, 132))), rough=0.9),
             pants=dict(post=G.tint((14, 15, 20), (72, 74, 86)), rough=0.85, normal_strength=0.8),
             shoes=dict(post=G.tint((34, 22, 16), (120, 84, 60)), rough=0.5)),
)

# Elin Bergqvist - head of operations, 40s, blonde: tailored double-breasted dark coat-suit, pale scarf
CONFIGS['npc_elin'] = _ped(
    'npc_elin', height=1.72,
    macro=dict(gender=0.0, age=0.63, muscle=0.45, weight=0.42, height=0.6, proportions=0.6, cupsize=0.45, firmness=0.5,
               race=dict(asian=0.0, caucasian=1.0, african=0.0)),
    skin=SYS + '/skins/young_caucasian_female/young_caucasian_female.mhmat',
    eye_mat=SYS + '/eyes/materials/blue.mhmat',
    hair=SYS + '/hair/ponytail01/ponytail01.mhclo',
    clothes=[('suit', 'suits01_cc0/clothes/toigo_female_double-breasted_suit/toigo_female_double-breasted_suit.mhclo'),
             ('shoes', BOOTS_F)],
    layers=['suit', 'shoes'],
    hooks=[G.scarf], scarf=dict(color=(204, 206, 212)),
    mat=dict(hair=dict(post=G.tint((112, 84, 40), (240, 216, 150))),
             suit=dict(post=G.recolor(('dark', (10, 12, 22), (58, 62, 82))), rough=0.8), shoes=dict(post=BLACK_LEATHER, rough=0.45)),
)

# Mateo Ruiz - backend developer, late 20s: rust hoodie (hood out) under a charcoal quilted jacket, black jeans
CONFIGS['npc_mateo'] = _ped(
    'npc_mateo', height=1.77,
    macro=dict(gender=1.0, age=0.51, muscle=0.5, weight=0.5, height=0.5, proportions=0.5,
               race=dict(asian=0.15, caucasian=0.70, african=0.15)),
    skin=SYS + '/skins/young_caucasian_male/young_caucasian_male.mhmat',
    eye_mat=SYS + '/eyes/materials/brown.mhmat',
    hair='hair01_cc0/hair/cortu_short_messy_hair/cortu_short_messy_hair.mhclo',
    clothes=[('suit', SYS + '/clothes/male_casualsuit05/male_casualsuit05.mhclo'), ('hoodie', HOODED),
             ('shoes', SYS + '/clothes/shoes06/shoes06.mhclo')],
    layers=['suit', 'hoodie', 'jeans', 'shoes'], no_cull=('hoodie',),      # jacket_over_hoodie trims the hoodie itself
    tuck=[('jeans', 'hoodie', 0.035)],
    hooks=[G.split_by_color('suit', dict(jeans=('blue', 0.5), shirt=('red', 0.2)), delete=('shirt',)),
           G.hoodie_pullover, G.fleece_material, G.jacket_over_hoodie('suit', 'hoodie')],
    hoodie=dict(color=(188, 88, 46)),
    mat=dict(body=dict(mul=(0.92, 0.80, 0.68)), eyes=dict(post=G.dark_brown_eyes),
             hair=dict(post=G.tint((16, 12, 10), (92, 66, 48))),
             suit=dict(post=G.recolor(('green_grey', (20, 20, 24), (82, 82, 90)), ('denim', (16, 17, 22), (58, 60, 70))), rough=0.8),
             shoes=dict(rough=0.6)),
)

# Helena Sjoberg - angel investor, 50s, silver bob: charcoal trouser suit with white sneakers
CONFIGS['npc_helena'] = _ped(
    'npc_helena', height=1.70,
    macro=dict(gender=0.0, age=0.72, muscle=0.45, weight=0.46, height=0.5, proportions=0.55, cupsize=0.45, firmness=0.45,
               race=dict(asian=0.0, caucasian=1.0, african=0.0)),
    skin=SYS + '/skins/middleage_caucasian_female/middleage_caucasian_female.mhmat',
    eye_mat=SYS + '/eyes/materials/grey.mhmat',
    hair='hair01_cc0/hair/toigo_blunt_bob/toigo_blunt_bob.mhclo',
    clothes=[('suit', 'suits01_cc0/clothes/toigo_female_suit_2/toigo_female_suit_2.mhclo'),
             ('shoes', 'shoes02_ccby/clothes/punkduck_tennis_shoes/punkduck_tennis_shoes.mhclo')],
    layers=['suit', 'shoes'],
    mat=dict(hair=dict(post=G.grey_hair(0.95, 1.15)),
             suit=dict(post=G.recolor(('magenta', (18, 21, 30), (66, 72, 92))), rough=0.8), shoes=dict(rough=0.6)),
)
