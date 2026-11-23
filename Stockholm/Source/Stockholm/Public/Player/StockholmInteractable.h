#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "StockholmInteractable.generated.h"

UINTERFACE(MinimalAPI, BlueprintType)
class UStockholmInteractable : public UInterface
{
	GENERATED_BODY()
};

/** Anything the founder can use: NPCs, doors, laptops, vehicles, beds, phones. */
class STOCKHOLM_API IStockholmInteractable
{
	GENERATED_BODY()

public:
	/** Short verb phrase for the prompt, e.g. "Talk to Noor", "Open laptop". Empty = not usable now. */
	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Interaction")
	FText GetInteractionPrompt(APawn* Instigator) const;

	UFUNCTION(BlueprintNativeEvent, BlueprintCallable, Category = "Interaction")
	void Interact(APawn* Instigator);
};
