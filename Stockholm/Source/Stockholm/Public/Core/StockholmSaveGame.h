#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "StockholmSaveGame.generated.h"

/**
 * Save container. The founder simulation serialises itself to versioned JSON
 * (FounderSim::Save, kSaveVersion), so story/economy changes never break the
 * binary layout; the world layer adds only what the simulation can't know.
 */
UCLASS()
class STOCKHOLM_API UStockholmSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	UPROPERTY() int32 SaveFormat = 1;
	UPROPERTY() FString SimJson;
	UPROPERTY() FTransform PlayerTransform;
	UPROPERTY() bool bPlayerInVehicle = false;
	UPROPERTY() FName VehicleId;
	UPROPERTY() FTransform VehicleTransform;
	UPROPERTY() FDateTime SavedAtUtc;
	UPROPERTY() FString DisplayLabel; // e.g. "Tue 13 Jan 2026 · Chapter 1 · The First Pitch"
};
