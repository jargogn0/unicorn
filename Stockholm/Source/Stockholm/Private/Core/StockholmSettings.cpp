#include "Core/StockholmSettings.h"
#include "Misc/Paths.h"

FString UStockholmSettings::ContentPath(const FString& Relative)
{
	return FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectContentDir(), Relative));
}
