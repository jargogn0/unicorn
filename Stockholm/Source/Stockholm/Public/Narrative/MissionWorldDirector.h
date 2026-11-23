#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Core/StockholmTypes.h"
#include "Player/StockholmInteractable.h"
#include "MissionWorldDirector.generated.h"

class AStoryNpc;
class AStockholmVehicle;

/** A world object the simulation knows by id (laptop_home, laptop_demo, bed, doors). */
UCLASS()
class STOCKHOLM_API AStoryProp : public AActor, public IStockholmInteractable
{
	GENERATED_BODY()
public:
	AStoryProp();
	virtual FText GetInteractionPrompt_Implementation(APawn* Instigator) const override;
	virtual void Interact_Implementation(APawn* Instigator) override;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FString TargetId;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FText Prompt;
	/** Ambient use when no mission needs it, e.g. "Work on the product (2 h)". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") FText AmbientPrompt;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") float AmbientHours = 0.f;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Story") bool bIsBed = false;
	UPROPERTY(VisibleAnywhere, Category = "Story") TObjectPtr<UStaticMeshComponent> Mesh;
};

/**
 * Connects simulation and world: spawns location triggers for every gameplay
 * location (locations.json) at projected coordinates with traced ground
 * height, spawns story NPCs and props, and executes scripted world events
 * from mission data (vehicle spawn/despawn, taxi travel, forced weather).
 */
UCLASS()
class STOCKHOLM_API AMissionWorldDirector : public AActor
{
	GENERATED_BODY()

public:
	AMissionWorldDirector();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

private:
	UFUNCTION() void OnSimEvent(const FStockholmSimEvent& Event);
	void SpawnLocations();
	void SpawnNpcs();
	float TraceGround(const FVector& At) const;

	struct FTrigger { FString Id; FVector Location; float RadiusCm = 1000.f; bool bInside = false; };
	TArray<FTrigger> Triggers;
	UPROPERTY() TArray<TObjectPtr<AStoryNpc>> Npcs;
	UPROPERTY() TMap<FName, TObjectPtr<AStockholmVehicle>> Vehicles;
};
