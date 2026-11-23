#include "World/AmbientPopulation.h"

#include "Core/StockholmSimSubsystem.h"

#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

using namespace stockholm::sim;

AAmbientPopulation::AAmbientPopulation()
{
	PrimaryActorTick.bCanEverTick = true;
	Instances = CreateDefaultSubobject<UInstancedStaticMeshComponent>(TEXT("Pedestrians"));
	RootComponent = Instances;
	Instances->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (UStaticMesh* Capsule = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cylinder.Cylinder")))
	{
		Instances->SetStaticMesh(Capsule);
	}
}

void AAmbientPopulation::BeginPlay()
{
	Super::BeginPlay();
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || !Sim->HasCity() || Sim->City().roads.EdgeCount() == 0) return;
	Walkers.SetNum(MaxPedestrians);
	for (FWalker& W : Walkers)
	{
		W.Instance = Instances->AddInstance(FTransform::Identity);
		W.Speed = FMath::FRandRange(1.1f, 1.6f);
		W.Side = FMath::RandBool() ? 1.f : -1.f;
		Respawn(W, FVector2D::ZeroVector);
	}
}

void AAmbientPopulation::Respawn(FWalker& W, const FVector2D& Around)
{
	const RoadGraph& G = UStockholmSimSubsystem::Get(this)->City().roads;
	for (int32 Attempt = 0; Attempt < 32; ++Attempt)
	{
		const uint32 E = static_cast<uint32>(FMath::RandRange(0, static_cast<int32>(G.EdgeCount()) - 1));
		if (!IsWalkable(G.Edge(E).roadClass)) continue;
		const Vec2 P = G.Edge(E).shape.front();
		const float D = FVector2D::Distance(FVector2D(P.x, P.y), Around);
		if (Around.IsZero() || (D > 60.f && D < 220.f))
		{
			W.Edge = E;
			W.T = FMath::FRand();
			return;
		}
	}
}

void AAmbientPopulation::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || Walkers.Num() == 0) return;
	const RoadGraph& G = Sim->City().roads;
	// Fewer people out late at night and in heavy snow.
	const double Hour = Sim->Sim().Clock().HourOfDay();
	const double Night = (Hour < 6.0 || Hour > 22.0) ? 0.25 : 1.0;
	const int32 Active = FMath::RoundToInt(Walkers.Num() * Night * (1.0 - 0.4 * Sim->Sim().Clock().Weather().precipitation));
	FVector2D PlayerPos = FVector2D::ZeroVector;
	if (const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
	{
		const Vec2 L = Sim->WorldToLocal(Pawn->GetActorLocation());
		PlayerPos = FVector2D(L.x, L.y);
	}
	for (int32 i = 0; i < Walkers.Num(); ++i)
	{
		FWalker& W = Walkers[i];
		if (i >= Active)
		{
			Instances->UpdateInstanceTransform(W.Instance, FTransform(FRotator::ZeroRotator, FVector(0, 0, -100000), FVector(0.01f)), true, false, true);
			continue;
		}
		const RoadEdge& E = G.Edge(W.Edge);
		W.T += W.Speed * DeltaSeconds / FMath::Max(1.f, static_cast<float>(E.lengthMetres));
		if (W.T >= 1.f)
		{
			// Continue onto a walkable edge from the end node (avoid immediate U-turn).
			const RoadNode& N = G.Node(E.to);
			TArray<uint32, TInlineAllocator<8>> Next;
			for (const uint32 Out : N.outEdges) if (IsWalkable(G.Edge(Out).roadClass) && G.Edge(Out).to != E.from) Next.Add(Out);
			if (Next.Num()) { W.Edge = Next[FMath::RandRange(0, Next.Num() - 1)]; W.T = 0.f; }
			else { Respawn(W, PlayerPos); }
		}
		const RoadEdge& E2 = G.Edge(W.Edge);
		const FVector2D A(E2.shape.front().x, E2.shape.front().y), B(E2.shape.back().x, E2.shape.back().y);
		const FVector2D Dir = (B - A).GetSafeNormal();
		const float Offset = IsDrivable(E2.roadClass) ? static_cast<float>(DefaultWidthMetres(E2.roadClass, E2.lanes)) * 0.5f + 1.6f : 1.2f;
		const FVector2D Pos = FMath::Lerp(A, B, W.T) + FVector2D(-Dir.Y, Dir.X) * Offset * W.Side;
		if (FVector2D::Distance(Pos, PlayerPos) > RecycleRadiusMetres && !PlayerPos.IsZero()) Respawn(W, PlayerPos);
		const FVector World = Sim->LocalToWorld(Vec2{Pos.X, Pos.Y}, UStockholmSimSubsystem::DefaultGroundZ / 100.0 + 0.85);
		Instances->UpdateInstanceTransform(W.Instance, FTransform(FRotator::ZeroRotator, World, FVector(0.45f, 0.45f, 1.7f)), true, false, true);
	}
	Instances->MarkRenderStateDirty();
}
