#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "Core/StockholmTypes.h"
#include "StockholmHUD.generated.h"

/**
 * Canvas-drawn HUD so the game is fully playable before UMG/CommonUI assets
 * exist: money, clock, weather, objective + timer, interaction prompt,
 * minimap with GPS route, dialogue with timed choices, mission decisions, the
 * demo-repair minigame, phone (messages / bank / promises) and the Founder Map.
 * The art pass replaces each panel with a UMG widget bound to the same
 * UStockholmSimSubsystem API (see TECHNICAL_ARCHITECTURE.md §6).
 */
UCLASS()
class STOCKHOLM_API AStockholmHUD : public AHUD
{
	GENERATED_BODY()

public:
	virtual void BeginPlay() override;
	virtual void DrawHUD() override;

	void TogglePhone() { bPhoneOpen = !bPhoneOpen; bMapOpen = false; }
	void ToggleFounderMap() { bMapOpen = !bMapOpen; bPhoneOpen = false; }
	bool IsFullscreenUIOpen() const { return bMapOpen || bDecisionOpen; }
	void DialogueAdvancePressed();
	void ChoicePressed(int32 Slot);

	void ShowCaption(const FString& Text, float Seconds);
	void ShowNotification(const FString& From, const FString& Text);

private:
	UFUNCTION() void OnSimEvent(const FStockholmSimEvent& Event);
	void DrawPanel(float X, float Y, float W, float H, const FLinearColor& Color = FLinearColor(0.03f, 0.07f, 0.11f, 0.8f));
	void DrawLabel(const FString& Text, float X, float Y, const FLinearColor& Color, float Scale = 1.f, UFont* Font = nullptr);
	float DrawWrapped(const FString& Text, float X, float Y, float MaxWidth, const FLinearColor& Color, float Scale = 1.f);
	void DrawStatus();
	void DrawObjective();
	void DrawMinimap();
	void DrawDialogue();
	void DrawDecision();
	void DrawPhone();
	void DrawFounderMap();
	void DrawToasts();
	void UpdateRoute();

	bool bPhoneOpen = false;
	bool bMapOpen = false;
	bool bDecisionOpen = false;
	FString LastObjectiveKey;
	FString LastDialogueNode;
	double DialogueNodeStart = 0.0;
	double DecisionStart = 0.0;
	TArray<int32> MinigameSequence;
	int32 MinigameProgress = 0;
	FString Caption;
	double CaptionUntil = 0.0;
	struct FToast { FString From; FString Text; double Until; };
	TArray<FToast> Toasts;
	TArray<FVector> Route;
	double NextRouteTime = 0.0;
	int32 MapCategory = -1; // -1 = all
	int32 MapSelection = 0;
};
