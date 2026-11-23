using UnrealBuildTool;

public class Stockholm : ModuleRules
{
	public Stockholm(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "InputCore",
			"EnhancedInput",
			"ChaosVehicles", "PhysicsCore",
			"ProceduralMeshComponent",
			"UMG", "Slate", "SlateCore",
			"AIModule", "NavigationSystem",
			"Niagara",
			"CinematicCamera",
			"DeveloperSettings",
			"StockholmSim"
		});

		PublicIncludePaths.AddRange(new string[]
		{
			ModuleDirectory + "/Public",
			ModuleDirectory + "/Public/Core",
			ModuleDirectory + "/Public/Player",
			ModuleDirectory + "/Public/Vehicles",
			ModuleDirectory + "/Public/World",
			ModuleDirectory + "/Public/Narrative",
			ModuleDirectory + "/Public/UI"
		});
	}
}
