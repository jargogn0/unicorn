#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "AmbientPopulation.generated.h"

class UInstancedStaticMeshComponent;

/**
 * Ambient pedestrians on the walkable road graph (sidewalk offset on roads,
 * centre line on pedestrian streets). Density scales with time of day and
 * weather; agents are recycled around the player. Rendered as instanced
 * stand-in meshes until animated crowd characters (Mass + AnimToTexture) land
 * — tracked in BUILD_STATUS.md as a known placeholder.
 */
UCLASS()
class STOCKHOLM_API AAmbientPopulation : public AActor
{
	GENERATED_BODY()

public:
	AAmbientPopulation();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(EditAnywhere, Category = "Population") int32 MaxPedestrians = 120;
	UPROPERTY(EditAnywhere, Category = "Population") float RecycleRadiusMetres = 300.f;

private:
	struct FWalker { uint32 Edge = 0; float T = 0.f; float Speed = 1.3f; float Side = 1.f; int32 Instance = -1; };
	void Respawn(FWalker& W, const FVector2D& Around);
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Instances;
	TArray<FWalker> Walkers;
};
