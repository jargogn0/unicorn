"""Unreal Editor Python: create the Milestone A World Partition map and the
blockout materials the C++ city builder and atmosphere expect.

Run (headless):
  UnrealEditor-Cmd Stockholm.uproject -run=pythonscript -script=Tools/ue/create_milestone_a_map.py

Idempotent: existing assets are left alone. NOT YET EXECUTED. It was written
without access to an Unreal Editor, so verify on first run (see BUILD_STATUS.md).
"""
import unreal

MAP_PATH = "/Game/Maps/Stockholm_MilestoneA"
MAT_DIR = "/Game/City/Materials"

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
mel = unreal.MaterialEditingLibrary


def ensure_material(name, build):
    path = f"{MAT_DIR}/{name}"
    if eal.does_asset_exist(path):
        return eal.load_asset(path)
    mat = asset_tools.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    build(mat)
    mel.recompile_material(mat)
    eal.save_asset(path)
    return mat


def build_blockout(mat):
    # Vertex colour (facade palette baked by ACityBuilder) × texture-free base, rough plaster.
    vc = mel.create_material_expression(mat, unreal.MaterialExpressionVertexColor, -400, 0)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.85)
    mel.connect_material_property(vc, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)


def build_water(mat):
    col = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -400, 0)
    col.set_editor_property("constant", unreal.LinearColor(0.02, 0.06, 0.09, 1.0))
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 200)
    rough.set_editor_property("r", 0.05)
    spec = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 300)
    spec.set_editor_property("r", 0.8)
    mel.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.connect_material_property(spec, "", unreal.MaterialProperty.MP_SPECULAR)


def ensure_weather_mpc():
    path = f"{MAT_DIR}/MPC_Weather"
    if eal.does_asset_exist(path):
        return
    mpc = asset_tools.create_asset("MPC_Weather", MAT_DIR, unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    params = []
    for n in ("Wetness", "SnowCover", "Precipitation"):
        p = unreal.CollectionScalarParameter()
        p.set_editor_property("parameter_name", n)
        p.set_editor_property("default_value", 0.0)
        params.append(p)
    mpc.set_editor_property("scalar_parameters", params)
    eal.save_asset(path)


def ensure_map():
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if eal.does_asset_exist(MAP_PATH):
        les.load_level(MAP_PATH)
    else:
        # The Open World template enables World Partition with a runtime grid.
        les.new_level_from_template(MAP_PATH, "/Engine/Maps/Templates/OpenWorld")
    eas = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    # Remove template lighting: AWorldAtmosphere owns sun/sky/fog/clouds at runtime.
    for actor in eas.get_all_level_actors():
        if isinstance(actor, (unreal.DirectionalLight, unreal.SkyAtmosphere, unreal.SkyLight, unreal.ExponentialHeightFog, unreal.VolumetricCloud)):
            eas.destroy_actor(actor)
    # Player start in front of the apartment door on Brännkyrkagatan
    # (59.3182 N, 18.0601 E → local x≈-450 m, y≈-1036 m → UE cm).
    start = eas.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-45000.0, 103600.0, 400.0))
    start.set_editor_property("player_start_tag", "Apartment")
    world_settings = unreal.EditorLevelLibrary.get_editor_world().get_world_settings()
    world_settings.set_editor_property("default_game_mode", unreal.load_class(None, "/Script/Stockholm.StockholmGameMode"))
    les.save_current_level()


def import_starter_pack():
    """Import the owner's starter-pack blockouts (axis-fixed FBX from Tools/blender/glb_to_ue_fbx.py)."""
    import os
    src_dir = os.path.join(unreal.Paths.project_content_dir(), "Import", "StarterPack", "UE_Ready")
    tasks = []
    for name in ("INT_Founder_Studio_Blockout", "VEH_Scandinavian_Sedan_Blockout"):
        fbx = os.path.join(src_dir, name + ".fbx")
        if not os.path.exists(fbx) or eal.does_asset_exist(f"/Game/Stockholm/Blockout/{name}"):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", fbx)
        t.set_editor_property("destination_path", "/Game/Stockholm/Blockout")
        t.set_editor_property("automated", True)
        t.set_editor_property("save", True)
        opts = unreal.FbxImportUI()
        opts.set_editor_property("import_mesh", True)
        opts.set_editor_property("import_as_skeletal", False)
        opts.static_mesh_import_data.set_editor_property("combine_meshes", True)
        opts.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
        opts.static_mesh_import_data.set_editor_property("auto_generate_collision", True)
        t.set_editor_property("options", opts)
        tasks.append(t)
    if tasks:
        asset_tools.import_asset_tasks(tasks)
    # The studio becomes the apartment interior level instance used by the opening cinematic.


ensure_material("M_CityBlockout", build_blockout)
ensure_material("M_HarbourWater", build_water)
ensure_weather_mpc()
import_starter_pack()
ensure_map()
unreal.log("STOCKHOLM: Milestone A map and blockout materials ready.")
