// Bridges the engine-independent founder simulation into Unreal: owns the
// FounderSim instance and the processed city model, ticks game time, forwards
// world notifications and broadcasts SimEvents to UI/world listeners.
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Tickable.h"
#include "StockholmTypes.h"

#include "Sim/City.h"
#include "Sim/FounderSim.h"
#include "Sim/Geo.h"

#include "StockholmSimSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnStockholmSimEvent, const FStockholmSimEvent&, Event);

UCLASS()
class STOCKHOLM_API UStockholmSimSubsystem : public UGameInstanceSubsystem, public FTickableGameObject
{
	GENERATED_BODY()

public:
	// UGameInstanceSubsystem
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// FTickableGameObject
	virtual void Tick(float DeltaTime) override;
	virtual TStatId GetStatId() const override;
	virtual bool IsTickable() const override { return bContentLoaded && !IsTemplate(); }
	virtual bool IsTickableWhenPaused() const override { return false; }
	virtual UWorld* GetTickableGameObjectWorld() const override;

	static UStockholmSimSubsystem* Get(const UObject* WorldContext);

	stockholm::sim::FounderSim& Sim() { return *SimPtr; }
	const stockholm::sim::FounderSim& Sim() const { return *SimPtr; }
	const stockholm::sim::CityModel& City() const { return CityModel; }
	const stockholm::sim::GeoProjection& Projection() const { return GeoProj; }
	bool HasCity() const { return bCityLoaded; }

	// ---- lifecycle ---------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Game") void NewGame();
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Game") bool SaveGame();
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Game") bool LoadGame();
	UFUNCTION(BlueprintPure, Category = "Stockholm|Game") bool HasSaveGame() const;
	/** Pauses game-time (menus, cinematics, phone). Real-time dialogue timers keep running in UI. */
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Game") void SetSimPaused(bool bPaused) { bSimPaused = bPaused; }
	UFUNCTION(BlueprintPure, Category = "Stockholm|Game") bool IsSimPaused() const { return bSimPaused; }

	// ---- state -------------------------------------------------------------
	UFUNCTION(BlueprintPure, Category = "Stockholm|State") float GetStat(FName StatName) const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|State") float GetRunwayMonths() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|State") float GetFounderOwnership() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|State") int32 GetChapter() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|State") FString GetChapterTitle() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|Time") FString GetTimeLabel() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|Time") FString GetDateLabel() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|Time") float GetHourOfDay() const;
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Time") void Sleep(float Hours);

	// ---- missions -----------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Missions") TArray<FStockholmObjective> GetObjectives();
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Missions") bool ChooseDecision(const FString& MissionId, int32 OptionIndex);
	UFUNCTION(BlueprintCallable, Category = "Stockholm|World") void NotifyReached(const FString& LocationId, bool bInVehicle);
	UFUNCTION(BlueprintCallable, Category = "Stockholm|World") void NotifyInteracted(const FString& TargetId);
	UFUNCTION(BlueprintCallable, Category = "Stockholm|World") void NotifyCustomEvent(const FString& EventId);

	// ---- dialogue -----------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Dialogue") bool StartDialogueWithNpc(const FString& NpcId);
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Dialogue") bool StartDialogue(const FString& DialogueId);
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Dialogue") FStockholmDialogueLine GetDialogueLine();
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Dialogue") bool ChooseDialogueOption(int32 ChoiceIndex);
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Dialogue") bool AdvanceDialogue();
	UFUNCTION(BlueprintPure, Category = "Stockholm|Dialogue") bool IsDialogueActive() const;

	// ---- phone --------------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Phone") TArray<FStockholmPhoneMessage> GetMessages() const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|Phone") int32 GetUnreadCount() const;
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Phone") void MarkThreadRead(const FString& Thread);
	UFUNCTION(BlueprintPure, Category = "Stockholm|Phone") bool HasPendingCall() const;
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Phone") bool AnswerPendingCall();
	UFUNCTION(BlueprintCallable, Category = "Stockholm|Phone") bool PayRent();

	// ---- Founder Map ---------------------------------------------------------
	UFUNCTION(BlueprintCallable, Category = "Stockholm|FounderMap") TArray<FFounderMapEntry> GetFounderMapEntries() const;
	UFUNCTION(BlueprintCallable, Category = "Stockholm|FounderMap") TArray<FName> GetFounderMapCategories() const;
	UFUNCTION(BlueprintCallable, Category = "Stockholm|FounderMap") bool DiscoverEntry(const FString& EntryId);

	// ---- geography ------------------------------------------------------------
	/** World location of a gameplay location id (locations.json). Z = registered ground height. */
	UFUNCTION(BlueprintCallable, Category = "Stockholm|World") bool GetLocationWorldPosition(const FString& LocationId, FVector& OutLocation) const;
	/** World actors report their traced ground height so markers sit on real surfaces. */
	UFUNCTION(BlueprintCallable, Category = "Stockholm|World") void RegisterLocationGround(const FString& LocationId, float GroundZ);
	/** GPS: road-graph route between two world points, as world-space polyline. */
	UFUNCTION(BlueprintCallable, Category = "Stockholm|World") TArray<FVector> FindRoute(FVector From, FVector To, bool bDriving, float& OutLengthMetres) const;
	UFUNCTION(BlueprintPure, Category = "Stockholm|World") FString GetMapAttribution() const;

	FVector LocalToWorld(const stockholm::sim::Vec2& Local, double HeightMetres = 0.0) const;
	stockholm::sim::Vec2 WorldToLocal(const FVector& World) const;

	UPROPERTY(BlueprintAssignable, Category = "Stockholm|Events")
	FOnStockholmSimEvent OnSimEvent;

	/** Default land height in cm used before the world builder registers traced ground. */
	static constexpr float DefaultGroundZ = 250.f;

private:
	void LoadContent();
	void LoadCity();
	void PumpEvents();
	static FStockholmChoice ToChoice(const stockholm::sim::ChoiceView& View);

	TUniquePtr<stockholm::sim::FounderSim> SimPtr;
	stockholm::sim::CityModel CityModel;
	stockholm::sim::GeoProjection GeoProj;
	TMap<FString, float> LocationGroundZ;
	bool bContentLoaded = false;
	bool bCityLoaded = false;
	bool bSimPaused = false;
	float AutoSaveAccumulator = 0.f;
};
