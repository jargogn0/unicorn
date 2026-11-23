#include "Player/StockholmPlayerController.h"

#include "Core/StockholmSimSubsystem.h"
#include "Player/StockholmCharacter.h"
#include "Player/StockholmInputConfig.h"
#include "UI/StockholmHUD.h"
#include "Vehicles/StockholmVehicle.h"

#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "Engine/LocalPlayer.h"
#include "InputActionValue.h"

AStockholmPlayerController::AStockholmPlayerController()
{
	bShowMouseCursor = false;
}

void AStockholmPlayerController::EnsureInputConfig()
{
	if (!InputConfig)
	{
		InputConfig = UStockholmInputConfig::Build(this);
	}
}

void AStockholmPlayerController::BeginPlay()
{
	Super::BeginPlay();
	EnsureInputConfig();
	ApplyContexts(GetPawn() && GetPawn()->IsA<AStockholmVehicle>());
	SetInputMode(FInputModeGameOnly());
}

void AStockholmPlayerController::SetupInputComponent()
{
	Super::SetupInputComponent();
	EnsureInputConfig();
	if (UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(InputComponent))
	{
		Input->BindAction(InputConfig->Phone, ETriggerEvent::Started, this, &AStockholmPlayerController::TogglePhone);
		Input->BindAction(InputConfig->FounderMap, ETriggerEvent::Started, this, &AStockholmPlayerController::ToggleFounderMap);
		Input->BindAction(InputConfig->DialogueNext, ETriggerEvent::Started, this, &AStockholmPlayerController::DialogueNext);
		Input->BindAction(InputConfig->Choice1, ETriggerEvent::Started, this, &AStockholmPlayerController::Choice1);
		Input->BindAction(InputConfig->Choice2, ETriggerEvent::Started, this, &AStockholmPlayerController::Choice2);
		Input->BindAction(InputConfig->Choice3, ETriggerEvent::Started, this, &AStockholmPlayerController::Choice3);
		Input->BindAction(InputConfig->Choice4, ETriggerEvent::Started, this, &AStockholmPlayerController::Choice4);
		Input->BindAction(InputConfig->QuickSave, ETriggerEvent::Started, this, &AStockholmPlayerController::QuickSave);
	}
}

void AStockholmPlayerController::OnPossess(APawn* InPawn)
{
	Super::OnPossess(InPawn);
	EnsureInputConfig();
	ApplyContexts(InPawn && InPawn->IsA<AStockholmVehicle>());
}

void AStockholmPlayerController::ApplyContexts(bool bInVehicle)
{
	UEnhancedInputLocalPlayerSubsystem* Subsystem = GetLocalPlayer() ? ULocalPlayer::GetSubsystem<UEnhancedInputLocalPlayerSubsystem>(GetLocalPlayer()) : nullptr;
	if (!Subsystem || !InputConfig)
	{
		return;
	}
	Subsystem->ClearAllMappings();
	Subsystem->AddMappingContext(InputConfig->SharedContext, 10);
	Subsystem->AddMappingContext(bInVehicle ? InputConfig->VehicleContext : InputConfig->OnFootContext, 0);
}

AStockholmHUD* AStockholmPlayerController::StockholmHUD() const
{
	return Cast<AStockholmHUD>(GetHUD());
}

bool AStockholmPlayerController::IsGameplayInputBlocked() const
{
	if (bCinematicActive)
	{
		return true;
	}
	if (const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		if (Sim->IsDialogueActive())
		{
			return true;
		}
	}
	const AStockholmHUD* HUD = StockholmHUD();
	return HUD && HUD->IsFullscreenUIOpen();
}

void AStockholmPlayerController::TogglePhone(const FInputActionValue&)
{
	if (AStockholmHUD* HUD = StockholmHUD())
	{
		HUD->TogglePhone();
	}
}

void AStockholmPlayerController::ToggleFounderMap(const FInputActionValue&)
{
	if (AStockholmHUD* HUD = StockholmHUD())
	{
		HUD->ToggleFounderMap();
	}
}

void AStockholmPlayerController::DialogueNext(const FInputActionValue&)
{
	if (AStockholmHUD* HUD = StockholmHUD())
	{
		HUD->DialogueAdvancePressed();
	}
}

void AStockholmPlayerController::Choose(int32 Slot)
{
	if (AStockholmHUD* HUD = StockholmHUD())
	{
		HUD->ChoicePressed(Slot);
	}
}

void AStockholmPlayerController::QuickSave(const FInputActionValue&)
{
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		Sim->SaveGame();
	}
}
