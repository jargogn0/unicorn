#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "TrafficManager.generated.h"

class UInstancedStaticMeshComponent;
class UStaticMesh;

/**
 * Lightweight AI traffic: kinematic cars that follow drivable road-graph edges
 * (right-hand traffic), keep distance to the car ahead and to the player, and
 * are recycled around the player so nearby streets stay busy. Rendered as
 * instanced static meshes (one draw call per car model). Full Chaos physics is
 * reserved for player-driven vehicles; see TECHNICAL_ARCHITECTURE.md §5.
 */
UCLASS()
class STOCKHOLM_API ATrafficManager : public AActor
{
	GENERATED_BODY()

public:
	ATrafficManager();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(EditAnywhere, Category = "Traffic") int32 CarCount = 40;
	UPROPERTY(EditAnywhere, Category = "Traffic") float LaneOffsetMetres = 2.6f;
	UPROPERTY(EditAnywhere, Category = "Traffic") float RecycleRadiusMetres = 520.f;
	UPROPERTY(EditAnywhere, Category = "Traffic") TArray<TSoftObjectPtr<UStaticMesh>> CarMeshes;

private:
	struct FCar { uint32 From = 0; uint32 To = 0; uint32 Edge = 0; float T = 0.f; float Speed = 0.f; float Cruise = 10.f; int32 Instance = -1; FVector2D Pos = FVector2D::ZeroVector; float Wait = 0.f; };
	bool PickNextEdge(FCar& Car, uint32 AtNode, uint32 AvoidNode) const;
	void Respawn(FCar& Car, const FVector2D& Around);
	UPROPERTY() TObjectPtr<UInstancedStaticMeshComponent> Instances;
	TArray<FCar> Cars;
};
