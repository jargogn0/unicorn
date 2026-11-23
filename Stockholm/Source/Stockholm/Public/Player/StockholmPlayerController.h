#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "StockholmPlayerController.generated.h"

class UStockholmInputConfig;
class AStockholmHUD;
struct FInputActionValue;

/**
 * Owns input contexts (on-foot vs vehicle + shared UI), routes phone / Founder
 * Map / dialogue input to the HUD, and blocks gameplay input during
 * conversations, cinematics and full-screen UI.
 */
UCLASS()
class STOCKHOLM_API AStockholmPlayerController : public APlayerController
{
	GENERATED_BODY()

public:
	AStockholmPlayerController();

	virtual void BeginPlay() override;
	virtual void SetupInputComponent() override;
	virtual void OnPossess(APawn* InPawn) override;

	const UStockholmInputConfig* GetInputConfig() const { return InputConfig; }
	bool IsGameplayInputBlocked() const;

	void SetCinematicActive(bool bActive) { bCinematicActive = bActive; }

private:
	void EnsureInputConfig();
	void ApplyContexts(bool bInVehicle);
	AStockholmHUD* StockholmHUD() const;

	void TogglePhone(const FInputActionValue& V);
	void ToggleFounderMap(const FInputActionValue& V);
	void DialogueNext(const FInputActionValue& V);
	void Choose(int32 Slot);
	void Choice1(const FInputActionValue& V) { Choose(0); }
	void Choice2(const FInputActionValue& V) { Choose(1); }
	void Choice3(const FInputActionValue& V) { Choose(2); }
	void Choice4(const FInputActionValue& V) { Choose(3); }
	void QuickSave(const FInputActionValue& V);

	UPROPERTY() TObjectPtr<UStockholmInputConfig> InputConfig;
	bool bCinematicActive = false;
};
