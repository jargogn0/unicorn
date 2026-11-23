#include "Narrative/MissionWorldDirector.h"

#include "Core/StockholmSimSubsystem.h"
#include "Narrative/StoryNpc.h"
#include "Vehicles/StockholmVehicle.h"
#include "Stockholm.h"

#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

using namespace stockholm::sim;
using StockholmConv::ToF;
using StockholmConv::ToStd;

AStoryProp::AStoryProp()
{
	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	RootComponent = Mesh;
	if (UStaticMesh* Cube = LoadObject<UStaticMesh>(nullptr, TEXT("/Engine/BasicShapes/Cube.Cube")))
	{
		Mesh->SetStaticMesh(Cube);
		Mesh->SetWorldScale3D(FVector(0.4f, 0.3f, 0.05f));
	}
}

FText AStoryProp::GetInteractionPrompt_Implementation(APawn* Instigator) const
{
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || Sim->IsDialogueActive()) return FText::GetEmpty();
	for (const ObjectiveView& V : const_cast<UStockholmSimSubsystem*>(Sim)->Sim().ActiveObjectives())
	{
		if (V.type == ObjectiveType::Interact && ToF(V.target) == TargetId) return Prompt;
	}
	return AmbientPrompt;
}

void AStoryProp::Interact_Implementation(APawn* Instigator)
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	const int32 Before = Sim->GetObjectives().Num();
	Sim->NotifyInteracted(TargetId);
	const bool bMissionUse = Sim->GetObjectives().Num() != Before || !GetInteractionPrompt_Implementation(Instigator).EqualTo(AmbientPrompt);
	if (bMissionUse) return;
	if (bIsBed)
	{
		const float Hour = Sim->GetHourOfDay();
		float Hours = 7.5f - Hour;
		if (Hours <= 1.f) Hours += 24.f;
		Sim->Sleep(Hours);
	}
	else if (AmbientHours > 0.f)
	{
		Sim->Sim().AdvanceGameMinutes(AmbientHours * 60.0);
		Sim->Sim().State().Add(Stat::ProductQuality, 1.0);
		Sim->Sim().State().Add(Stat::Energy, -6.0);
	}
}

AMissionWorldDirector::AMissionWorldDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.1f;
}

void AMissionWorldDirector::BeginPlay()
{
	Super::BeginPlay();
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		Sim->OnSimEvent.AddDynamic(this, &AMissionWorldDirector::OnSimEvent);
	}
	SpawnLocations();
	SpawnNpcs();
}

float AMissionWorldDirector::TraceGround(const FVector& At) const
{
	FHitResult Hit;
	const FVector Start(At.X, At.Y, 20000.f), End(At.X, At.Y, -2000.f);
	if (GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_WorldStatic))
	{
		return Hit.ImpactPoint.Z;
	}
	return UStockholmSimSubsystem::DefaultGroundZ;
}

void AMissionWorldDirector::SpawnLocations()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	for (const auto& KV : Sim->Sim().Content().locations)
	{
		const LocationDef& L = KV.second;
		if (!L.hasCoordinates) continue;
		FTrigger T;
		T.Id = ToF(L.id);
		T.Location = Sim->LocalToWorld(Sim->Projection().ToLocal(L.lat, L.lon));
		T.Location.Z = TraceGround(T.Location);
		T.RadiusCm = static_cast<float>(L.radiusMetres) * 100.f;
		Sim->RegisterLocationGround(T.Id, T.Location.Z);
		Triggers.Add(T);

		// Props the missions reference by id.
		auto SpawnProp = [&](const TCHAR* Target, const FText& Prompt, const FText& Ambient, float Hours, bool bBed, const FVector& Offset)
		{
			AStoryProp* P = GetWorld()->SpawnActor<AStoryProp>(AStoryProp::StaticClass(), FTransform(T.Location + Offset));
			if (!P) return;
			P->TargetId = Target; P->Prompt = Prompt; P->AmbientPrompt = Ambient; P->AmbientHours = Hours; P->bIsBed = bBed;
		};
		if (L.id == "laptop_home")
		{
			SpawnProp(TEXT("laptop_home"), NSLOCTEXT("Stockholm", "UseLaptop", "Use your laptop"), NSLOCTEXT("Stockholm", "WorkProduct", "Work on the product (2 h)"), 2.f, false, FVector(0, 0, 80));
			SpawnProp(TEXT("bed"), FText::GetEmpty(), NSLOCTEXT("Stockholm", "Sleep", "Sleep until morning"), 0.f, true, FVector(-250, 120, 40));
		}
		if (L.id == "office_malarbrod")
		{
			SpawnProp(TEXT("laptop_demo"), NSLOCTEXT("Stockholm", "StartDemo", "Start the live demo"), FText::GetEmpty(), 0.f, false, FVector(150, 0, 80));
		}
		if (L.id == "sami_car_spot")
		{
			AStockholmVehicle* Car = GetWorld()->SpawnActor<AStockholmVehicle>(AStockholmVehicle::StaticClass(), FTransform(T.Location + FVector(0, 0, 60)));
			if (Car)
			{
				Car->VehicleId = TEXT("sami_volvo");
				Car->DisplayName = NSLOCTEXT("Stockholm", "SamiVolvo", "Sami's Volvo");
				Car->RequiredFact = TEXT("has_sami_car");
				Vehicles.Add(Car->VehicleId, Car);
			}
		}
	}
}

void AMissionWorldDirector::SpawnNpcs()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	for (const auto& KV : Sim->Sim().Content().npcs)
	{
		if (KV.first == "landlord") continue; // phone-only character
		FActorSpawnParameters Params;
		Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AdjustIfPossibleButAlwaysSpawn;
		AStoryNpc* Npc = GetWorld()->SpawnActor<AStoryNpc>(AStoryNpc::StaticClass(), FTransform::Identity, Params);
		if (Npc)
		{
			Npc->NpcId = ToF(KV.first);
			Npcs.Add(Npc);
		}
	}
}

void AMissionWorldDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	const APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
	if (!Sim || !Pawn) return;
	const bool bInVehicle = Pawn->IsA<AStockholmVehicle>();
	const FVector P = Pawn->GetActorLocation();
	for (FTrigger& T : Triggers)
	{
		const float R = T.RadiusCm + (bInVehicle ? 600.f : 0.f);
		const float D = FVector::Dist2D(P, T.Location);
		if (!T.bInside && D < R)
		{
			T.bInside = true;
			Sim->NotifyReached(T.Id, bInVehicle);
		}
		else if (T.bInside && D > R + 1500.f)
		{
			T.bInside = false;
		}
	}
}

void AMissionWorldDirector::OnSimEvent(const FStockholmSimEvent& Event)
{
	if (Event.Type == FName(TEXT("objective_changed")))
	{
		for (FTrigger& T : Triggers) T.bInside = false; // re-evaluate presence for the new objective
		return;
	}
	if (Event.Type != FName(TEXT("world_event"))) return;
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	TArray<FString> Parts;
	Event.Id.ParseIntoArray(Parts, TEXT(":"));
	if (Parts.Num() == 0 || !Sim) return;

	if (Parts[0] == TEXT("weather") && Parts.Num() > 1)
	{
		Sim->Sim().Clock().ForceWeather(WeatherFromString(ToStd(Parts[1])));
	}
	else if (Parts[0] == TEXT("travel") && Parts.Num() > 2)
	{
		FVector Dest;
		APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0);
		if (Pawn && Sim->GetLocationWorldPosition(Parts[2], Dest))
		{
			Pawn->SetActorLocation(Dest + FVector(200, 200, 120), false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
	else if (Parts[0] == TEXT("despawn_vehicle") && Parts.Num() > 1)
	{
		if (TObjectPtr<AStockholmVehicle>* Car = Vehicles.Find(FName(*Parts[1])))
		{
			if (*Car && (*Car)->GetDriver()) (*Car)->ExitVehicle();
		}
	}
	// spawn_vehicle: Sami's car is persistent at its spot (gated by RequiredFact), nothing to do.
	// cinematic:* and demo_failure are handled by ACinematicDirector / HUD.
}
