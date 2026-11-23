// Enhanced Input actions and mapping contexts created in C++ so the game is
// controllable (keyboard/mouse + gamepad) before any input assets exist.
// Designers can later replace these with assets without touching gameplay code.
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "StockholmInputConfig.generated.h"

class UInputAction;
class UInputMappingContext;

UCLASS()
class STOCKHOLM_API UStockholmInputConfig : public UObject
{
	GENERATED_BODY()

public:
	static UStockholmInputConfig* Build(UObject* Outer);

	// On foot
	UPROPERTY() TObjectPtr<UInputAction> Move;
	UPROPERTY() TObjectPtr<UInputAction> Look;
	UPROPERTY() TObjectPtr<UInputAction> Jump;
	UPROPERTY() TObjectPtr<UInputAction> Sprint;
	UPROPERTY() TObjectPtr<UInputAction> Interact;
	// Vehicle
	UPROPERTY() TObjectPtr<UInputAction> Throttle;
	UPROPERTY() TObjectPtr<UInputAction> Brake;
	UPROPERTY() TObjectPtr<UInputAction> Steer;
	UPROPERTY() TObjectPtr<UInputAction> Handbrake;
	UPROPERTY() TObjectPtr<UInputAction> ExitVehicle;
	// Shared UI
	UPROPERTY() TObjectPtr<UInputAction> Phone;
	UPROPERTY() TObjectPtr<UInputAction> FounderMap;
	UPROPERTY() TObjectPtr<UInputAction> DialogueNext;
	UPROPERTY() TObjectPtr<UInputAction> Choice1;
	UPROPERTY() TObjectPtr<UInputAction> Choice2;
	UPROPERTY() TObjectPtr<UInputAction> Choice3;
	UPROPERTY() TObjectPtr<UInputAction> Choice4;
	UPROPERTY() TObjectPtr<UInputAction> QuickSave;

	UPROPERTY() TObjectPtr<UInputMappingContext> OnFootContext;
	UPROPERTY() TObjectPtr<UInputMappingContext> VehicleContext;
	UPROPERTY() TObjectPtr<UInputMappingContext> SharedContext;
};
