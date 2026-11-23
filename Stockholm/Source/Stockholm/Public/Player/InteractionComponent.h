#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "InteractionComponent.generated.h"

/** Finds the best interactable in front of the player (sphere overlap + view-cone scoring). */
UCLASS(ClassGroup = (Stockholm), meta = (BlueprintSpawnableComponent))
class STOCKHOLM_API UInteractionComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UInteractionComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	UFUNCTION(BlueprintCallable, Category = "Interaction") bool TryInteract();
	UFUNCTION(BlueprintPure, Category = "Interaction") AActor* GetFocusedActor() const { return Focused.Get(); }
	UFUNCTION(BlueprintPure, Category = "Interaction") FText GetPrompt() const { return Prompt; }

	UPROPERTY(EditAnywhere, Category = "Interaction") float Radius = 220.f;
	UPROPERTY(EditAnywhere, Category = "Interaction") float MinFacingDot = 0.3f;

private:
	void SetFocus(AActor* NewFocus);
	TWeakObjectPtr<AActor> Focused;
	FText Prompt;
};
