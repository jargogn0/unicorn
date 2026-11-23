using UnrealBuildTool;
using System.Collections.Generic;

public class StockholmEditorTarget : TargetRules
{
	public StockholmEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.AddRange(new string[] { "StockholmSim", "Stockholm" });
	}
}
