#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "StockholmGameMode.generated.h"

/**
 * Spawns the founder at the apartment start, starts a new game or resumes the
 * save, and creates the world directors (city builder, atmosphere, traffic,
 * pedestrians, mission world bridge) if the map didn't place them.
 */
UCLASS()
class STOCKHOLM_API AStockholmGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	AStockholmGameMode();

	virtual void StartPlay() override;
	virtual AActor* ChoosePlayerStart_Implementation(AController* Player) override;

	/** Resume from save when one exists (otherwise new game). Toggle off for test maps. */
	UPROPERTY(EditAnywhere, Category = "Stockholm")
	bool bResumeFromSave = true;

private:
	template <typename T>
	T* EnsureActor();
};
