#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "CityBuilder.generated.h"

class UProceduralMeshComponent;
class UMaterialInterface;

/**
 * Builds the playable city from processed OpenStreetMap data at runtime:
 * extruded building footprints, road ribbons (bridges raised), water plane,
 * land slab, parks. Geometry is chunked into tiles so each tile is one
 * ProceduralMeshComponent with collision (and can later map 1:1 onto World
 * Partition cells when baked to static meshes by Tools/ue/bake_city.py).
 *
 * This is BLOCKOUT geometry: the authoritative layout for the city. It is
 * replaced tile-by-tile by modular facade kits / Nanite meshes (see
 * WORLD_DESIGN.md §6). Landmarks are flagged for bespoke hero assets.
 */
UCLASS()
class STOCKHOLM_API ACityBuilder : public AActor
{
	GENERATED_BODY()

public:
	ACityBuilder();
	virtual void BeginPlay() override;

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "City") void Rebuild();

	UPROPERTY(EditAnywhere, Category = "City") float TileSizeMetres = 250.f;
	/** Land surface height above water (metres). Real terrain comes from a DEM later. */
	UPROPERTY(EditAnywhere, Category = "City") float LandHeightMetres = 2.5f;
	UPROPERTY(EditAnywhere, Category = "City") float BridgeDeckHeightMetres = 6.0f;
	UPROPERTY(EditAnywhere, Category = "City") bool bFlipWinding = false;

	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> FacadeMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> LandmarkMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> RoofMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> RoadMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> PathMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> WaterMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> LandMaterial;
	UPROPERTY(EditAnywhere, Category = "City|Materials") TObjectPtr<UMaterialInterface> ParkMaterial;

	UPROPERTY(VisibleAnywhere, Category = "City|Stats") int32 BuildingCount = 0;
	UPROPERTY(VisibleAnywhere, Category = "City|Stats") int32 TriangleCount = 0;

private:
	void ResolveDefaultMaterials();
	UProceduralMeshComponent* TileComponent(int32 TileX, int32 TileY);

	UPROPERTY() TArray<TObjectPtr<UProceduralMeshComponent>> Tiles;
	TMap<FIntPoint, int32> TileIndex;
};
