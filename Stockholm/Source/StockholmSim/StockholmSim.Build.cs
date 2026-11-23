using UnrealBuildTool;

// Engine-independent founder simulation (plain C++17). The same sources are
// compiled and unit-tested outside Unreal by Tests/CMakeLists.txt.
public class StockholmSim : ModuleRules
{
	public StockholmSim(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.NoPCHs;
		CppStandard = CppStandardVersion.Cpp17;
		bUseUnity = true;
		PublicDependencyModuleNames.AddRange(new string[] { "Core" });
		PublicIncludePaths.Add(ModuleDirectory + "/Public");
	}
}
