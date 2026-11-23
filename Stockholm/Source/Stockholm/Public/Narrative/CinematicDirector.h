#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Core/StockholmTypes.h"
#include "CinematicDirector.generated.h"

class ACineCameraActor;

/**
 * Plays data-driven camera shots (Content/Data/Cinematics/<id>.json) when the
 * simulation emits "cinematic:<id>": eased camera moves relative to a gameplay
 * location, with captions and phone notifications on the HUD. This lets the
 * opening play before Level Sequences are authored; Sequencer assets can later
 * replace a shot list 1:1 (same ids).
 */
UCLASS()
class STOCKHOLM_API ACinematicDirector : public AActor
{
	GENERATED_BODY()

public:
	ACinematicDirector();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UFUNCTION(BlueprintCallable, Category = "Cinematics") bool Play(const FString& CinematicId);
	UFUNCTION(BlueprintCallable, Category = "Cinematics") void Skip();
	UFUNCTION(BlueprintPure, Category = "Cinematics") bool IsPlaying() const { return Shots.Num() > 0; }

private:
	UFUNCTION() void OnSimEvent(const FStockholmSimEvent& Event);
	void Finish();
	struct FShot { FVector FromPos, ToPos, FromLook, ToLook; float Duration = 3.f; FString Caption, NotifFrom, NotifText; };
	TArray<FShot> Shots;
	int32 ShotIndex = 0;
	float ShotTime = 0.f;
	UPROPERTY() TObjectPtr<ACineCameraActor> Camera;
};
