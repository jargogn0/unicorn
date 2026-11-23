// Blueprint-facing mirrors of simulation views. The simulation itself lives in
// the engine-independent StockholmSim module (namespace stockholm::sim).
#pragma once

#include "CoreMinimal.h"
#include "StockholmTypes.generated.h"

USTRUCT(BlueprintType)
struct FStockholmSimEvent
{
	GENERATED_BODY()
	/** e.g. phone_message, mission_started, objective_changed, world_event (see SimEventTypeToString). */
	UPROPERTY(BlueprintReadOnly) FName Type;
	UPROPERTY(BlueprintReadOnly) FString Id;
	UPROPERTY(BlueprintReadOnly) FString Text;
	UPROPERTY(BlueprintReadOnly) float Value = 0.f;
};

USTRUCT(BlueprintType)
struct FStockholmChoice
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) int32 Index = 0;
	UPROPERTY(BlueprintReadOnly) FString Text;
	UPROPERTY(BlueprintReadOnly) bool bAvailable = true;
	UPROPERTY(BlueprintReadOnly) FString LockedHint;
};

USTRUCT(BlueprintType)
struct FStockholmObjective
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FString MissionId;
	UPROPERTY(BlueprintReadOnly) FString MissionTitle;
	UPROPERTY(BlueprintReadOnly) FString ObjectiveId;
	UPROPERTY(BlueprintReadOnly) FString Text;
	UPROPERTY(BlueprintReadOnly) FName Type;
	UPROPERTY(BlueprintReadOnly) FString Target;
	UPROPERTY(BlueprintReadOnly) FString MarkerLocationId;
	UPROPERTY(BlueprintReadOnly) bool bHasMarker = false;
	UPROPERTY(BlueprintReadOnly) FVector MarkerWorldLocation = FVector::ZeroVector;
	UPROPERTY(BlueprintReadOnly) float MinutesRemaining = -1.f;
	UPROPERTY(BlueprintReadOnly) float DecisionSeconds = 0.f;
	UPROPERTY(BlueprintReadOnly) int32 DecisionDefault = -1;
	UPROPERTY(BlueprintReadOnly) TArray<FStockholmChoice> Options;
};

USTRUCT(BlueprintType)
struct FStockholmDialogueLine
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) bool bActive = false;
	UPROPERTY(BlueprintReadOnly) FString DialogueId;
	UPROPERTY(BlueprintReadOnly) FString NodeId;
	UPROPERTY(BlueprintReadOnly) FString SpeakerId;
	UPROPERTY(BlueprintReadOnly) FString SpeakerName;
	UPROPERTY(BlueprintReadOnly) FString Text;
	UPROPERTY(BlueprintReadOnly) FName Animation;
	UPROPERTY(BlueprintReadOnly) FName Camera;
	UPROPERTY(BlueprintReadOnly) float TimeoutSeconds = 0.f;
	UPROPERTY(BlueprintReadOnly) int32 TimeoutChoice = -1;
	UPROPERTY(BlueprintReadOnly) bool bHasChoices = false;
	UPROPERTY(BlueprintReadOnly) bool bIsEnd = false;
	UPROPERTY(BlueprintReadOnly) TArray<FStockholmChoice> Choices;
};

USTRUCT(BlueprintType)
struct FStockholmPhoneMessage
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FString Thread;
	UPROPERTY(BlueprintReadOnly) FString SenderName;
	UPROPERTY(BlueprintReadOnly) FString Text;
	UPROPERTY(BlueprintReadOnly) FString TimeLabel;
	UPROPERTY(BlueprintReadOnly) bool bRead = false;
};

USTRUCT(BlueprintType)
struct FFounderMapEntry
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly) FString Id;
	UPROPERTY(BlueprintReadOnly) FString Name;
	UPROPERTY(BlueprintReadOnly) TArray<FName> Categories;
	UPROPERTY(BlueprintReadOnly) FString Summary;
	UPROPERTY(BlueprintReadOnly) FString Status;
	UPROPERTY(BlueprintReadOnly) FString Verification;
	UPROPERTY(BlueprintReadOnly) TArray<FString> StorylineHooks;
	UPROPERTY(BlueprintReadOnly) TArray<FString> Sources;
	UPROPERTY(BlueprintReadOnly) bool bDiscovered = false;
	/** False for entries without a sourced address or known district: listed, never pinned. */
	UPROPERTY(BlueprintReadOnly) bool bHasWorldPin = false;
	/** True when the pin is a district-level approximation, not a sourced address. */
	UPROPERTY(BlueprintReadOnly) bool bApproximate = true;
	UPROPERTY(BlueprintReadOnly) FVector WorldLocation = FVector::ZeroVector;
	UPROPERTY(BlueprintReadOnly) int32 FoundedYear = 0;
};
