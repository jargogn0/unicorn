#include "Core/StockholmGameMode.h"

#include "Core/StockholmSimSubsystem.h"
#include "Narrative/MissionWorldDirector.h"
#include "Narrative/CinematicDirector.h"
#include "Player/StockholmCharacter.h"
#include "Player/StockholmPlayerController.h"
#include "UI/StockholmHUD.h"
#include "World/AmbientPopulation.h"
#include "World/CityBuilder.h"
#include "World/TrafficManager.h"
#include "World/WorldAtmosphere.h"
#include "Stockholm.h"

#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"

AStockholmGameMode::AStockholmGameMode()
{
	DefaultPawnClass = AStockholmCharacter::StaticClass();
	PlayerControllerClass = AStockholmPlayerController::StaticClass();
	HUDClass = AStockholmHUD::StaticClass();
}

template <typename T>
T* AStockholmGameMode::EnsureActor()
{
	for (TActorIterator<T> It(GetWorld()); It; ++It)
	{
		return *It;
	}
	FActorSpawnParameters Params;
	Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
	return GetWorld()->SpawnActor<T>(T::StaticClass(), FTransform::Identity, Params);
}

void AStockholmGameMode::StartPlay()
{
	// World systems first so the city geometry exists before the pawn lands on it.
	EnsureActor<ACityBuilder>();
	EnsureActor<AWorldAtmosphere>();
	EnsureActor<ATrafficManager>();
	EnsureActor<AAmbientPopulation>();
	EnsureActor<AMissionWorldDirector>();
	EnsureActor<ACinematicDirector>();

	Super::StartPlay();

	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		if (!(bResumeFromSave && Sim->HasSaveGame() && Sim->LoadGame()))
		{
			Sim->NewGame();
		}
	}
}

AActor* AStockholmGameMode::ChoosePlayerStart_Implementation(AController* Player)
{
	// Prefer a PlayerStart tagged "Apartment" (placed by the map script in the player's room).
	for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
	{
		if (It->PlayerStartTag == FName(TEXT("Apartment")))
		{
			return *It;
		}
	}
	return Super::ChoosePlayerStart_Implementation(Player);
}
