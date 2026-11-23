using UnrealBuildTool;
using System.Collections.Generic;

public class StockholmTarget : TargetRules
{
	public StockholmTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.AddRange(new string[] { "StockholmSim", "Stockholm" });
	}
}
