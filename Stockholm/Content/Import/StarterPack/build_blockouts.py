import trimesh, numpy as np, os, json, math
from pathlib import Path
out=Path('/mnt/data/stockholm_work/UE5_STARTER_3D');out.mkdir(exist_ok=True)

def cube(scene,name,at,ext,color):
 m=trimesh.creation.box(extents=ext);m.apply_translation(at);m.visual.vertex_colors=color;scene.add_geometry(m,geom_name=name)
def cylinder(scene,name,at,r,h,color,sections=24,axis='z'):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=sections)
 if axis=='y': m.apply_transform(trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]))
 m.apply_translation(at);m.visual.vertex_colors=color;scene.add_geometry(m,geom_name=name)
def save(scene,name):
 fp=out/name; scene.export(fp); print(name,fp.stat().st_size)
# A compact stylized *fictional blockout* motivated by the material refs, NOT georeferenced Stockholm.
city=trimesh.Scene()
cube(city,'ground',(0,0,-.16),(180,140,.3),[142,151,146,255])
cube(city,'north_south_road',(0,0,.035),(17,140,.08),[48,52,60,255]);cube(city,'east_west_road',(0,0,.055),(180,14,.09),[48,52,60,255])
# 3m crossing and lanes
for i in range(-60,61,8):
 cube(city,f'lane_NS_{i}',(0,i,.11),(.19,3.0,.015),[242,237,210,255])
for i in range(-80,81,8):
 cube(city,f'lane_EW_{i}',(i,0,.12),(3.0,.19,.015),[242,237,210,255])
for idx,(x,y,w,d,h,clr) in enumerate([(-48,-35,28,26,21,[209,185,142,255]),(-48,33,30,28,18,[217,201,174,255]),(43,-34,37,30,24,[204,189,170,255]),(43,35,38,30,27,[191,199,202,255]),(-79,34,15,26,14,[213,197,173,255]),(75,-36,18,28,17,[211,188,149,255])]):
 cube(city,f'bld_{idx}_main',(x,y,h/2),(w,d,h),clr)
 cube(city,f'bld_{idx}_roof',(x,y,h+.35),(w+.5,d+.5,.7),[77,84,88,255])
 for floor in range(2,int(h/3.5)):
  for k in range(max(1,int(w/4))):
   wx=x-w/2+2+k*4
   cube(city,f'bld_{idx}_window_front_{floor}_{k}',(wx,y-d/2-.018,floor*3.4),(1.6,.04,1.5),[57,79,95,255])
# streets
for i,(x,y) in enumerate([(-12,-25),(-12,25),(12,-25),(12,25),(-25,-12),(25,12)]):
 cylinder(city,f'lamp_{i}',(x,y,2.3),.095,4.6,[67,73,80,255]);cube(city,f'lamp_head_{i}',(x,y,4.65),(.8,.35,.2),[228,215,166,255])
save(city,'STK_District_Prototype.glb')
# Sedan: static body mesh. Four separate wheel components, *not* a vehicle rig.
car=trimesh.Scene()
cube(car,'chassis',(0,0,.48),(4.76,1.85,.45),[102,112,122,255]);cube(car,'cabin',(-.20,0,1.05),(2.65,1.64,.63),[74,99,119,255]);cube(car,'bonnet',(1.45,0,.83),(1.72,1.78,.25),[119,129,138,255]);cube(car,'boot',(-1.8,0,.78),(.92,1.8,.21),[119,129,138,255])
for xa in (-1.55,1.5):
 for ya in (-.96,.96):
  cylinder(car,f'wheel_{xa}_{ya}',(xa,ya,.39),.37,.19,[28,29,31,255],sections=32,axis='y')
for ya in (-.61,.61):
 cube(car,'headlight_'+str(ya),(2.39,ya,.61),(.035,.38,.14),[255,245,185,255]);cube(car,'taillight_'+str(ya),(-2.39,ya,.61),(.035,.38,.14),[187,33,42,255])
save(car,'VEH_Scandinavian_Sedan_Blockout.glb')
# Apartment interior 6.4m x 5m, door gap, furnishings, no collision logic.
apt=trimesh.Scene()
cube(apt,'floor',(0,0,-.06),(6.4,5,.12),[195,166,125,255])
cube(apt,'north_wall',(0,2.46,1.35),(6.4,.09,2.7),[228,225,216,255])
cube(apt,'east_wall',(3.16,0,1.35),(.09,5,2.7),[224,224,220,255])
cube(apt,'west_wall',(-3.16,0,1.35),(.09,5,2.7),[224,224,220,255])
cube(apt,'south_wall_left',(-2.2,-2.46,1.35),(2.0,.09,2.7),[224,224,220,255])
cube(apt,'south_wall_right',(1.0,-2.46,1.35),(4.4,.09,2.7),[224,224,220,255])
cube(apt,'bed',(-1.65,1.35,.30),(2.0,1.15,.6),[222,221,217,255])
cube(apt,'bed_pillow',(-2.25,1.35,.65),(.42,.90,.13),[240,240,238,255])
cube(apt,'desk',(1.5,1.66,.75),(1.45,.65,.08),[143,103,65,255])
for x in (1,2):cylinder(apt,f'desk_leg_{x}',(x,1.66,.37),.035,.73,[64,68,68,255])
cube(apt,'monitor',(1.5,1.81,1.17),(.65,.07,.46),[33,39,45,255]);cube(apt,'chair',(1.5,.91,.47),(.51,.50,.1),[63,67,72,255]);cube(apt,'chair_back',(1.5,.68,.86),(.51,.09,.7),[63,67,72,255]);cube(apt,'kitchenette',(2.7,-.85,.45),(.82,2.5,.9),[225,225,218,255]);cube(apt,'window',(0.4,2.43,1.65),(1.5,.04,1.1),[101,153,173,180])
save(apt,'INT_Founder_Studio_Blockout.glb')
# Material and metadata
metadata={'source_zip':'STOCKHOLM_GTA_ASSETS_PACK.zip','coordinate_system':'Y-up glTF (trimesh exports coordinate positions as authored; dimensions in meters). Confirm UE5 import axis orientation and scale.','status':'procedural blockout (not real-world-accurate, not photorealistic, not animated)','geometry':[{'file':'STK_District_Prototype.glb','purpose':'fictional urban blockout only','georeferenced':False},{'file':'VEH_Scandinavian_Sedan_Blockout.glb','purpose':'static sedan body + component meshes; requires Chaos vehicle blueprint / wheel rig'},{'file':'INT_Founder_Studio_Blockout.glb','purpose':'6.4m x 5m interior staging'}]}
(out/'ASSET_METADATA.json').write_text(json.dumps(metadata,indent=2))
for f in out.glob('*.glb'):
 s=trimesh.load(f,force='scene');print('validated',f.name,'meshes',len(s.geometry),'bounds',s.bounds)
