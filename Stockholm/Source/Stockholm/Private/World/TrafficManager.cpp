#include "World/TrafficManager.h"

#include "Core/StockholmSimSubsystem.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

using namespace stockholm::sim;

ATrafficManager::ATrafficManager()
{
	PrimaryActorTick.bCanEverTick = true;
	Instances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Cars"));
	RootComponent = Instances;
	Instances->SetCollisionProfileName(TEXT("Vehicle"));
	Instances->SetCastShadow(true);
	// Engine cube as a scale-matched stand-in until licensed traffic cars are imported.
	CarMeshes.Add(TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(TEXT("/Engine/BasicShapes/Cube.Cube"))));
}

void ATrafficManager::BeginPlay()
{
	Super::BeginPlay();
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || !Sim->HasCity())
	{
		return;
	}
	if (UStaticMesh* Mesh = CarMeshes.Num() ? CarMeshes[0].LoadSynchronous() : nullptr)
	{
		Instances->SetStaticMesh(Mesh);
	}
	Cars.SetNum(CarCount);
	for (FCar& Car : Cars)
	{
		Car.Instance = Instances->AddInstance(FTransform(FRotator::ZeroRotator, FVector::ZeroVector, FVector(4.6f, 1.85f, 1.5f)));
		Respawn(Car, FVector2D::ZeroVector);
	}
}

bool ATrafficManager::PickNextEdge(FCar& Car, uint32 AtNode, uint32 AvoidNode) const
{
	const RoadGraph& G = UStockholmSimSubsystem::Get(this)->City().roads;
	TArray<uint32, TInlineAllocator<8>> Options;
	for (const uint32 E : G.Node(AtNode).outEdges)
	{
		const RoadEdge& Edge = G.Edge(E);
		if (IsDrivable(Edge.roadClass) && !Edge.againstOneway && Edge.to != AvoidNode) Options.Add(E);
	}
	if (Options.Num() == 0)
	{
		for (const uint32 E : G.Node(AtNode).outEdges)
		{
			if (IsDrivable(G.Edge(E).roadClass) && !G.Edge(E).againstOneway) Options.Add(E);
		}
	}
	if (Options.Num() == 0) return false;
	Car.Edge = Options[FMath::RandRange(0, Options.Num() - 1)];
	Car.From = AtNode;
	Car.To = G.Edge(Car.Edge).to;
	Car.T = 0.f;
	Car.Cruise = static_cast<float>(G.Edge(Car.Edge).speedKmh / 3.6) * FMath::FRandRange(0.8f, 1.05f);
	return true;
}

void ATrafficManager::Respawn(FCar& Car, const FVector2D& Around)
{
	const RoadGraph& G = UStockholmSimSubsystem::Get(this)->City().roads;
	for (int32 Attempt = 0; Attempt < 32; ++Attempt)
	{
		const uint32 N = static_cast<uint32>(FMath::RandRange(0, static_cast<int32>(G.NodeCount()) - 1));
		const Vec2 P = G.Node(N).pos;
		const float D = FVector2D::Distance(FVector2D(P.x, P.y), Around);
		if ((Around.IsZero() || (D > 120.f && D < 380.f)) && PickNextEdge(Car, N, UINT32_MAX))
		{
			return;
		}
	}
}

void ATrafficManager::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || !Sim->HasCity() || Cars.Num() == 0)
	{
		return;
	}
	const RoadGraph& G = Sim->City().roads;
	FVector2D PlayerPos = FVector2D::ZeroVector;
	if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		if (const APawn* Pawn = PC->GetPawn())
		{
			const Vec2 L = Sim->WorldToLocal(Pawn->GetActorLocation());
			PlayerPos = FVector2D(L.x, L.y);
		}
	}
	for (FCar& Car : Cars)
	{
		const RoadEdge& E = G.Edge(Car.Edge);
		const FVector2D A(E.shape.front().x, E.shape.front().y), B(E.shape.back().x, E.shape.back().y);
		const FVector2D Dir = (B - A).GetSafeNormal();
		const FVector2D Ahead = Car.Pos + Dir * 9.f;
		bool bStop = FVector2D::Distance(Ahead, PlayerPos) < 5.f || Car.Wait > 0.f;
		for (const FCar& Other : Cars)
		{
			if (&Other != &Car && FVector2D::Distance(Ahead, Other.Pos) < 5.f) { bStop = true; break; }
		}
		Car.Wait = FMath::Max(0.f, Car.Wait - DeltaSeconds);
		Car.Speed = FMath::FInterpTo(Car.Speed, bStop ? 0.f : Car.Cruise, DeltaSeconds, bStop ? 5.f : 1.5f);
		Car.T += Car.Speed * DeltaSeconds / FMath::Max(1.f, static_cast<float>(E.lengthMetres));
		if (Car.T >= 1.f && !PickNextEdge(Car, Car.To, Car.From))
		{
			Respawn(Car, PlayerPos);
		}
		const RoadEdge& E2 = G.Edge(Car.Edge);
		const FVector2D A2(E2.shape.front().x, E2.shape.front().y), B2(E2.shape.back().x, E2.shape.back().y);
		const FVector2D Dir2 = (B2 - A2).GetSafeNormal();
		const FVector2D Right(Dir2.Y, -Dir2.X);
		Car.Pos = FMath::Lerp(A2, B2, Car.T) + Right * LaneOffsetMetres;
		if (FVector2D::Distance(Car.Pos, PlayerPos) > RecycleRadiusMetres && !PlayerPos.IsZero())
		{
			Respawn(Car, PlayerPos);
		}
		const FVector World = Sim->LocalToWorld(Vec2{Car.Pos.X, Car.Pos.Y}, UStockholmSimSubsystem::DefaultGroundZ / 100.0 + 0.75);
		// Local +y is north; Unreal yaw is measured from +X (east) towards +Y (south).
		const float Yaw = FMath::RadiansToDegrees(FMath::Atan2(-Dir2.Y, Dir2.X));
		Instances->UpdateInstanceTransform(Car.Instance, FTransform(FRotator(0.f, Yaw, 0.f), World, FVector(4.6f, 1.85f, 1.5f)), true, false, true);
	}
	Instances->MarkRenderStateDirty();
}
