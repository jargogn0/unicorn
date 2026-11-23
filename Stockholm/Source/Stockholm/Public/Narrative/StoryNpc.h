#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Player/StockholmInteractable.h"
#include "StoryNpc.generated.h"

/**
 * A persistent story character (npcs.json). Where they stand follows their
 * daily routine from the simulation; an active Talk objective overrides the
 * routine so missions can never soft-lock on an absent character. Talking opens
 * whatever conversation the simulation says is current (mission or ambient),
 * so lines reflect relationship memory.
 */
UCLASS()
class STOCKHOLM_API AStoryNpc : public ACharacter, public IStockholmInteractable
{
	GENERATED_BODY()

public:
	AStoryNpc();
	virtual void Tick(float DeltaSeconds) override;

	virtual FText GetInteractionPrompt_Implementation(APawn* Instigator) const override;
	virtual void Interact_Implementation(APawn* Instigator) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString NpcId;

private:
	void UpdatePlacement();
	FString CurrentLocationId;
	float PlacementTimer = 0.f;
};
