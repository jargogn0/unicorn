#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "StockholmSettings.generated.h"

/** Project settings (Config/DefaultGame.ini, section [/Script/Stockholm.StockholmSettings]). */
UCLASS(Config = Game, DefaultConfig, meta = (DisplayName = "STOCKHOLM"))
class STOCKHOLM_API UStockholmSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	/** Processed OpenStreetMap city file, relative to the project Content directory. */
	UPROPERTY(Config, EditAnywhere, Category = "World")
	FString CityDataFile = TEXT("Data/Geo/milestone_a_city.json");

	/** Directory (relative to Content) holding manifest.json for narrative/world/ecosystem data. */
	UPROPERTY(Config, EditAnywhere, Category = "Narrative")
	FString ContentManifestDir = TEXT("Data");

	UPROPERTY(Config, EditAnywhere, Category = "Saving")
	FString SaveSlotName = TEXT("Stockholm_Save");

	UPROPERTY(Config, EditAnywhere, Category = "Saving", meta = (ClampMin = "0"))
	float AutoSaveIntervalSeconds = 120.f;

	static FString ContentPath(const FString& Relative);
};
