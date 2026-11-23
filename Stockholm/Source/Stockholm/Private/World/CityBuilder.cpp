#include "World/CityBuilder.h"

#include "Core/StockholmSimSubsystem.h"
#include "Stockholm.h"

#include "Materials/MaterialInterface.h"
#include "ProceduralMeshComponent.h"

#include "Sim/City.h"
#include "Sim/Geo.h"

using namespace stockholm::sim;

namespace CityBuilderDetail
{
	enum ESection : int32 { Facade = 0, Landmark, Roof, Road, Path, Water, Land, Park, SectionCount };

	struct FSectionBuffers
	{
		TArray<FVector> Vertices;
		TArray<int32> Triangles;
		TArray<FVector> Normals;
		TArray<FVector2D> UV0;
		TArray<FLinearColor> Colors;
	};

	// Appends a core mesh (local metres, x east / y north) converted to Unreal space.
	void AppendMesh(FSectionBuffers& B, const MeshData& M, double ZOffsetMetres, bool bFlip, const FLinearColor& Color)
	{
		const int32 Base = B.Vertices.Num();
		for (size_t i = 0; i < M.positions.size(); ++i)
		{
			const Vec3& P = M.positions[i];
			const Vec3& N = M.normals[i];
			B.Vertices.Add(FVector(P.x * 100.0, -P.y * 100.0, (P.z + ZOffsetMetres) * 100.0));
			B.Normals.Add(FVector(N.x, -N.y, N.z));
			// UVs in metres / 4 so a facade texture tiles every 4 m (≈ one storey + parapet).
			B.UV0.Add(FVector2D(M.uvs[i].x / 4.0, M.uvs[i].y / 4.0));
			B.Colors.Add(Color);
		}
		for (size_t i = 0; i + 2 < M.indices.size(); i += 3)
		{
			const int32 A = Base + static_cast<int32>(M.indices[i]);
			const int32 Bi = Base + static_cast<int32>(M.indices[i + 1]);
			const int32 C = Base + static_cast<int32>(M.indices[i + 2]);
			if (bFlip) { B.Triangles.Append({A, C, Bi}); }
			else { B.Triangles.Append({A, Bi, C}); }
		}
	}

	MeshData FlatPolygon(const std::vector<Vec2>& Ring, double Z)
	{
		MeshData M;
		const std::vector<Vec2> Clean = CleanRing(Ring);
		const std::vector<uint32_t> Tris = TriangulateEarClip(Clean);
		for (const Vec2& P : Clean)
		{
			M.positions.push_back({P.x, P.y, Z});
			M.normals.push_back({0, 0, 1});
			M.uvs.push_back({P.x, P.y});
		}
		M.indices = Tris;
		return M;
	}

	// Stockholm inner-city palette for untextured blockout: ochre, rust, cream, grey-green.
	FLinearColor FacadeTint(int64_t Id, const std::string& OsmColour)
	{
		static const FLinearColor Palette[] = {
			FLinearColor(0.78f, 0.55f, 0.30f), FLinearColor(0.62f, 0.30f, 0.20f), FLinearColor(0.85f, 0.78f, 0.62f),
			FLinearColor(0.70f, 0.66f, 0.58f), FLinearColor(0.55f, 0.58f, 0.50f), FLinearColor(0.80f, 0.68f, 0.45f)};
		if (!OsmColour.empty())
		{
			const FColor Parsed = FColor::FromHex(StockholmConv::ToF(OsmColour));
			if (Parsed != FColor(0, 0, 0, 255) || OsmColour == "#000000") return FLinearColor(Parsed);
		}
		return Palette[static_cast<uint64_t>(Id) % UE_ARRAY_COUNT(Palette)];
	}
}

ACityBuilder::ACityBuilder()
{
	PrimaryActorTick.bCanEverTick = false;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}

void ACityBuilder::BeginPlay()
{
	Super::BeginPlay();
	Rebuild();
}

void ACityBuilder::ResolveDefaultMaterials()
{
	// Engine fallbacks keep the blockout visible before the art pass. Vertex
	// colour tints only show with a material that reads VertexColor
	// (M_CityBlockout, created by Tools/ue/create_milestone_a_map.py).
	UMaterialInterface* Blockout = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/City/Materials/M_CityBlockout.M_CityBlockout"));
	UMaterialInterface* Fallback = Blockout ? Blockout : LoadObject<UMaterialInterface>(nullptr, TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"));
	UMaterialInterface* Water = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/City/Materials/M_HarbourWater.M_HarbourWater"));
	for (TObjectPtr<UMaterialInterface>* Slot : {&FacadeMaterial, &LandmarkMaterial, &RoofMaterial, &RoadMaterial, &PathMaterial, &LandMaterial, &ParkMaterial})
	{
		if (!*Slot) *Slot = Fallback;
	}
	if (!WaterMaterial) WaterMaterial = Water ? Water : Fallback;
}

UProceduralMeshComponent* ACityBuilder::TileComponent(int32 TileX, int32 TileY)
{
	const FIntPoint Key(TileX, TileY);
	if (const int32* Existing = TileIndex.Find(Key))
	{
		return Tiles[*Existing];
	}
	UProceduralMeshComponent* PMC = NewObject<UProceduralMeshComponent>(this, *FString::Printf(TEXT("CityTile_%d_%d"), TileX, TileY));
	PMC->SetupAttachment(RootComponent);
	PMC->bUseAsyncCooking = true;
	PMC->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	PMC->RegisterComponent();
	TileIndex.Add(Key, Tiles.Add(PMC));
	return PMC;
}

void ACityBuilder::Rebuild()
{
	using namespace CityBuilderDetail;
	for (UProceduralMeshComponent* T : Tiles)
	{
		if (T) T->DestroyComponent();
	}
	Tiles.Reset();
	TileIndex.Reset();
	BuildingCount = 0;
	TriangleCount = 0;

	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || !Sim->HasCity())
	{
		UE_LOG(LogStockholm, Warning, TEXT("CityBuilder: no city data loaded; nothing to build."));
		return;
	}
	ResolveDefaultMaterials();
	const CityModel& City = Sim->City();
	const double Tile = TileSizeMetres;

	TMap<FIntPoint, TArray<FSectionBuffers>> Buffers;
	auto BuffersFor = [&](const Vec2& P) -> TArray<FSectionBuffers>& {
		const FIntPoint Key(FMath::FloorToInt(P.x / Tile), FMath::FloorToInt(P.y / Tile));
		TArray<FSectionBuffers>& B = Buffers.FindOrAdd(Key);
		if (B.Num() == 0) B.SetNum(SectionCount);
		return B;
	};

	// Water: one plane over the bounds at sea level (0 m). Land and parks sit above it.
	{
		const CityBounds& Bd = City.bounds;
		for (double X = Bd.minX; X < Bd.maxX; X += Tile)
		{
			for (double Y = Bd.minY; Y < Bd.maxY; Y += Tile)
			{
				const std::vector<Vec2> Quad = {{X, Y}, {FMath::Min(X + Tile, Bd.maxX), Y}, {FMath::Min(X + Tile, Bd.maxX), FMath::Min(Y + Tile, Bd.maxY)}, {X, FMath::Min(Y + Tile, Bd.maxY)}};
				AppendMesh(BuffersFor(Vec2{X + 1, Y + 1})[Water], FlatPolygon(Quad, -0.3), 0.0, bFlipWinding, FLinearColor(0.05f, 0.12f, 0.16f));
			}
		}
	}
	for (const AreaPolygon& A : City.areas)
	{
		if (A.kind == "water") continue;
		const ESection S = A.kind == "park" ? Park : Land;
		const double Z = A.kind == "park" ? LandHeightMetres + 0.02 : LandHeightMetres;
		AppendMesh(BuffersFor(Centroid(A.outer))[S], FlatPolygon(A.outer, Z), 0.0, bFlipWinding,
			A.kind == "park" ? FLinearColor(0.25f, 0.35f, 0.2f) : FLinearColor(0.42f, 0.42f, 0.4f));
	}

	// Roads: ribbons; bridges raised to deck height with ramps handled by the
	// approach nodes in data (TODO: per-node elevation from OSM layer/ele).
	for (const CityModel::RoadLine& L : City.roadLines)
	{
		if (L.tunnel) continue;
		const bool bDrivable = IsDrivable(L.roadClass);
		const double Z = (L.bridge ? BridgeDeckHeightMetres : LandHeightMetres) + (bDrivable ? 0.05 : 0.08);
		const MeshData Ribbon = BuildRibbon(L.points, L.widthMetres, Z);
		AppendMesh(BuffersFor(L.points[L.points.size() / 2])[bDrivable ? Road : Path], Ribbon, 0.0, bFlipWinding,
			bDrivable ? FLinearColor(0.12f, 0.12f, 0.13f) : FLinearColor(0.55f, 0.52f, 0.48f));
	}

	// Buildings: walls + roof, landmarks separated for hero materials.
	for (const Building& B : City.buildings)
	{
		const double Height = FMath::Max(3.0, B.heightMetres - B.minHeightMetres);
		const MeshData M = ExtrudeFootprint(B.outer, LandHeightMetres + B.minHeightMetres, Height);
		if (M.indices.empty()) continue;
		AppendMesh(BuffersFor(Centroid(B.outer))[B.landmark ? Landmark : Facade], M, 0.0, bFlipWinding, FacadeTint(B.osmId, B.colour));
		++BuildingCount;
	}

	UMaterialInterface* Materials[SectionCount] = {FacadeMaterial, LandmarkMaterial, RoofMaterial, RoadMaterial, PathMaterial, WaterMaterial, LandMaterial, ParkMaterial};
	for (auto& KV : Buffers)
	{
		UProceduralMeshComponent* PMC = TileComponent(KV.Key.X, KV.Key.Y);
		for (int32 S = 0; S < SectionCount; ++S)
		{
			FSectionBuffers& B = KV.Value[S];
			if (B.Triangles.Num() == 0) continue;
			PMC->CreateMeshSection_LinearColor(S, B.Vertices, B.Triangles, B.Normals, B.UV0, B.Colors, TArray<FProcMeshTangent>(), /*bCreateCollision=*/S != Water);
			PMC->SetMaterial(S, Materials[S]);
			TriangleCount += B.Triangles.Num() / 3;
		}
	}
	UE_LOG(LogStockholm, Log, TEXT("CityBuilder: %d buildings, %d triangles in %d tiles"), BuildingCount, TriangleCount, Tiles.Num());
}
