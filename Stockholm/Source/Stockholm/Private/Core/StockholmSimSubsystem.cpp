#include "Core/StockholmSimSubsystem.h"

#include "Core/StockholmSaveGame.h"
#include "Core/StockholmSettings.h"
#include "Stockholm.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Paths.h"

using namespace stockholm::sim;
using StockholmConv::ToF;
using StockholmConv::ToStd;

void UStockholmSimSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	SimPtr = MakeUnique<FounderSim>(static_cast<uint64_t>(FDateTime::UtcNow().GetTicks()));
	LoadContent();
	LoadCity();
}

void UStockholmSimSubsystem::Deinitialize()
{
	SimPtr.Reset();
	Super::Deinitialize();
}

UStockholmSimSubsystem* UStockholmSimSubsystem::Get(const UObject* WorldContext)
{
	const UWorld* World = WorldContext ? WorldContext->GetWorld() : nullptr;
	const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
	return GI ? GI->GetSubsystem<UStockholmSimSubsystem>() : nullptr;
}

TStatId UStockholmSimSubsystem::GetStatId() const
{
	RETURN_QUICK_DECLARE_CYCLE_STAT(UStockholmSimSubsystem, STATGROUP_Tickables);
}

UWorld* UStockholmSimSubsystem::GetTickableGameObjectWorld() const
{
	const UGameInstance* GI = GetGameInstance();
	return GI ? GI->GetWorld() : nullptr;
}

void UStockholmSimSubsystem::LoadContent()
{
	const UStockholmSettings* Settings = GetDefault<UStockholmSettings>();
	const FString Dir = UStockholmSettings::ContentPath(Settings->ContentManifestDir);
	std::string Error;
	bContentLoaded = SimPtr->Content().LoadFromManifest(ToStd(Dir), &Error);
	if (!bContentLoaded)
	{
		UE_LOG(LogStockholm, Error, TEXT("Narrative content failed to load from %s: %s"), *Dir, *ToF(Error));
		return;
	}
	for (const std::string& Problem : SimPtr->Content().Validate())
	{
		UE_LOG(LogStockholm, Warning, TEXT("Content: %s"), *ToF(Problem));
	}
	UE_LOG(LogStockholm, Log, TEXT("Loaded %d missions, %d dialogues, %d NPCs, %d ecosystem entries"),
		static_cast<int32>(SimPtr->Content().missions.size()), static_cast<int32>(SimPtr->Content().dialogues.size()),
		static_cast<int32>(SimPtr->Content().npcs.size()), static_cast<int32>(SimPtr->Content().ecosystem.size()));
}

void UStockholmSimSubsystem::LoadCity()
{
	const UStockholmSettings* Settings = GetDefault<UStockholmSettings>();
	const FString Path = UStockholmSettings::ContentPath(Settings->CityDataFile);
	std::string Error;
	bCityLoaded = CityModel.LoadFromFile(ToStd(Path), &Error);
	if (!bCityLoaded)
	{
		UE_LOG(LogStockholm, Warning, TEXT("City data not loaded (%s): %s. Run Tools/geodata/build_city.sh."), *Path, *ToF(Error));
		return;
	}
	GeoProj = GeoProjection(CityModel.originLat, CityModel.originLon);
	UE_LOG(LogStockholm, Log, TEXT("City: %d buildings (%d with sourced height), %d road edges, %d areas"),
		static_cast<int32>(CityModel.buildings.size()), static_cast<int32>(CityModel.BuildingsWithSourcedHeight()),
		static_cast<int32>(CityModel.roads.EdgeCount()), static_cast<int32>(CityModel.areas.size()));
}

void UStockholmSimSubsystem::Tick(float DeltaTime)
{
	if (!bSimPaused)
	{
		SimPtr->Tick(DeltaTime);
	}
	PumpEvents();

	const float Interval = GetDefault<UStockholmSettings>()->AutoSaveIntervalSeconds;
	AutoSaveAccumulator += DeltaTime;
	if (Interval > 0.f && AutoSaveAccumulator >= Interval && !SimPtr->IsDialogueActive())
	{
		AutoSaveAccumulator = 0.f;
		SaveGame();
	}
}

void UStockholmSimSubsystem::PumpEvents()
{
	SimEvent Event;
	while (SimPtr->PollEvent(Event))
	{
		FStockholmSimEvent Out;
		Out.Type = FName(SimEventTypeToString(Event.type));
		Out.Id = ToF(Event.id);
		Out.Text = ToF(Event.text);
		Out.Value = static_cast<float>(Event.value);
		OnSimEvent.Broadcast(Out);
	}
}

// ---------------------------------------------------------------- lifecycle

void UStockholmSimSubsystem::NewGame()
{
	SimPtr->BeginNewGame();
	AutoSaveAccumulator = 0.f;
	PumpEvents();
}

bool UStockholmSimSubsystem::SaveGame()
{
	if (SimPtr->IsDialogueActive())
	{
		return false; // conversations are atomic; save before/after
	}
	UStockholmSaveGame* Save = Cast<UStockholmSaveGame>(UGameplayStatics::CreateSaveGameObject(UStockholmSaveGame::StaticClass()));
	Save->SimJson = ToF(SimPtr->Save().Dump());
	Save->SavedAtUtc = FDateTime::UtcNow();
	const ChapterDef* Chapter = SimPtr->CurrentChapterDef();
	Save->DisplayLabel = FString::Printf(TEXT("%s · Chapter %d%s"), *ToF(SimPtr->Clock().FormatDate()), SimPtr->CurrentChapter(),
		Chapter ? *FString(TEXT(" · ") + ToF(Chapter->title)) : TEXT(""));

	if (const UWorld* World = GetTickableGameObjectWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			if (const APawn* Pawn = PC->GetPawn())
			{
				Save->bPlayerInVehicle = !Pawn->IsA<ACharacter>();
				Save->PlayerTransform = Pawn->GetActorTransform();
				if (Save->bPlayerInVehicle)
				{
					Save->VehicleTransform = Pawn->GetActorTransform();
					Save->VehicleId = Pawn->GetFName();
				}
			}
		}
	}
	const bool bOk = UGameplayStatics::SaveGameToSlot(Save, GetDefault<UStockholmSettings>()->SaveSlotName, 0);
	UE_LOG(LogStockholm, Log, TEXT("Save %s: %s"), bOk ? TEXT("ok") : TEXT("FAILED"), *Save->DisplayLabel);
	return bOk;
}

bool UStockholmSimSubsystem::LoadGame()
{
	const FString Slot = GetDefault<UStockholmSettings>()->SaveSlotName;
	const UStockholmSaveGame* Save = Cast<UStockholmSaveGame>(UGameplayStatics::LoadGameFromSlot(Slot, 0));
	if (!Save)
	{
		return false;
	}
	std::string Error;
	const JsonValue Doc = JsonValue::Parse(ToStd(Save->SimJson), &Error);
	if (!SimPtr->Load(Doc, &Error))
	{
		UE_LOG(LogStockholm, Error, TEXT("Load failed: %s"), *ToF(Error));
		return false;
	}
	if (const UWorld* World = GetTickableGameObjectWorld())
	{
		if (const APlayerController* PC = World->GetFirstPlayerController())
		{
			if (APawn* Pawn = PC->GetPawn())
			{
				Pawn->SetActorTransform(Save->PlayerTransform, false, nullptr, ETeleportType::TeleportPhysics);
			}
		}
	}
	return true;
}

bool UStockholmSimSubsystem::HasSaveGame() const
{
	return UGameplayStatics::DoesSaveGameExist(GetDefault<UStockholmSettings>()->SaveSlotName, 0);
}

// ---------------------------------------------------------------- state

float UStockholmSimSubsystem::GetStat(FName StatName) const
{
	Stat S;
	if (!StatFromString(ToStd(StatName.ToString()), S))
	{
		return 0.f;
	}
	return static_cast<float>(SimPtr->State().Get(S));
}

float UStockholmSimSubsystem::GetRunwayMonths() const { return static_cast<float>(SimPtr->State().RunwayMonths()); }
float UStockholmSimSubsystem::GetFounderOwnership() const { return static_cast<float>(SimPtr->State().capTable.FounderOwnership()); }
int32 UStockholmSimSubsystem::GetChapter() const { return SimPtr->CurrentChapter(); }

FString UStockholmSimSubsystem::GetChapterTitle() const
{
	const ChapterDef* C = SimPtr->CurrentChapterDef();
	return C ? ToF(C->title) : FString();
}

FString UStockholmSimSubsystem::GetTimeLabel() const { return ToF(SimPtr->Clock().FormatTime()); }
FString UStockholmSimSubsystem::GetDateLabel() const { return ToF(SimPtr->Clock().FormatDate()); }
float UStockholmSimSubsystem::GetHourOfDay() const { return static_cast<float>(SimPtr->Clock().HourOfDay()); }

void UStockholmSimSubsystem::Sleep(float Hours)
{
	SimPtr->Sleep(Hours);
	PumpEvents();
}

// ---------------------------------------------------------------- missions

FStockholmChoice UStockholmSimSubsystem::ToChoice(const ChoiceView& View)
{
	FStockholmChoice C;
	C.Index = View.index;
	C.Text = ToF(View.text);
	C.bAvailable = View.available;
	C.LockedHint = ToF(View.lockedHint);
	return C;
}

TArray<FStockholmObjective> UStockholmSimSubsystem::GetObjectives()
{
	TArray<FStockholmObjective> Out;
	for (const ObjectiveView& V : SimPtr->ActiveObjectives())
	{
		FStockholmObjective O;
		O.MissionId = ToF(V.missionId);
		O.MissionTitle = ToF(V.missionTitle);
		O.ObjectiveId = ToF(V.objectiveId);
		O.Text = ToF(V.text);
		O.Type = FName(ObjectiveTypeToString(V.type));
		O.Target = ToF(V.target);
		O.MarkerLocationId = ToF(V.marker);
		O.bHasMarker = !V.marker.empty() && GetLocationWorldPosition(O.MarkerLocationId, O.MarkerWorldLocation);
		O.MinutesRemaining = static_cast<float>(V.minutesRemaining);
		O.DecisionSeconds = static_cast<float>(V.decisionSeconds);
		O.DecisionDefault = V.decisionDefault;
		for (const ChoiceView& C : V.options)
		{
			O.Options.Add(ToChoice(C));
		}
		Out.Add(MoveTemp(O));
	}
	return Out;
}

bool UStockholmSimSubsystem::ChooseDecision(const FString& MissionId, int32 OptionIndex)
{
	const bool bOk = SimPtr->ChooseDecision(ToStd(MissionId), OptionIndex);
	PumpEvents();
	return bOk;
}

void UStockholmSimSubsystem::NotifyReached(const FString& LocationId, bool bInVehicle)
{
	SimPtr->NotifyReached(ToStd(LocationId), bInVehicle);
	PumpEvents();
}

void UStockholmSimSubsystem::NotifyInteracted(const FString& TargetId)
{
	SimPtr->NotifyInteracted(ToStd(TargetId));
	PumpEvents();
}

void UStockholmSimSubsystem::NotifyCustomEvent(const FString& EventId)
{
	SimPtr->NotifyCustomEvent(ToStd(EventId));
	PumpEvents();
}

// ---------------------------------------------------------------- dialogue

bool UStockholmSimSubsystem::StartDialogueWithNpc(const FString& NpcId)
{
	const std::string Dialogue = SimPtr->DialogueForNpc(ToStd(NpcId));
	return !Dialogue.empty() && StartDialogue(ToF(Dialogue));
}

bool UStockholmSimSubsystem::StartDialogue(const FString& DialogueId)
{
	const bool bOk = SimPtr->StartDialogue(ToStd(DialogueId));
	PumpEvents();
	return bOk;
}

FStockholmDialogueLine UStockholmSimSubsystem::GetDialogueLine()
{
	FStockholmDialogueLine L;
	const DialogueLineView V = SimPtr->CurrentLine();
	L.bActive = V.active;
	if (!V.active)
	{
		return L;
	}
	L.DialogueId = ToF(V.dialogueId);
	L.NodeId = ToF(V.nodeId);
	L.SpeakerId = ToF(V.speaker);
	L.SpeakerName = ToF(V.speakerName);
	L.Text = ToF(V.text);
	L.Animation = FName(ToF(V.animation));
	L.Camera = FName(ToF(V.camera));
	L.TimeoutSeconds = static_cast<float>(V.timeoutSeconds);
	L.TimeoutChoice = V.timeoutChoice;
	L.bHasChoices = V.hasChoices;
	L.bIsEnd = V.isEnd;
	if (V.hasChoices)
	{
		for (const ChoiceView& C : SimPtr->CurrentChoices())
		{
			L.Choices.Add(ToChoice(C));
		}
	}
	return L;
}

bool UStockholmSimSubsystem::ChooseDialogueOption(int32 ChoiceIndex)
{
	const bool bOk = SimPtr->ChooseDialogueOption(ChoiceIndex);
	PumpEvents();
	return bOk;
}

bool UStockholmSimSubsystem::AdvanceDialogue()
{
	const bool bOk = SimPtr->AdvanceDialogue();
	PumpEvents();
	return bOk;
}

bool UStockholmSimSubsystem::IsDialogueActive() const { return SimPtr->IsDialogueActive(); }

// ---------------------------------------------------------------- phone

TArray<FStockholmPhoneMessage> UStockholmSimSubsystem::GetMessages() const
{
	TArray<FStockholmPhoneMessage> Out;
	for (const PhoneMessage& M : SimPtr->Messages())
	{
		FStockholmPhoneMessage P;
		P.Thread = ToF(M.thread);
		const NpcDef* Npc = SimPtr->Content().FindNpc(M.sender);
		P.SenderName = Npc ? ToF(Npc->name) : (M.sender == "bank" ? TEXT("Bank") : ToF(M.sender));
		P.Text = ToF(M.text);
		const int32 Minute = static_cast<int32>(M.minute) % 1440;
		P.TimeLabel = FString::Printf(TEXT("%02d:%02d"), Minute / 60, Minute % 60);
		P.bRead = M.read;
		Out.Add(MoveTemp(P));
	}
	return Out;
}

int32 UStockholmSimSubsystem::GetUnreadCount() const { return SimPtr->UnreadCount(); }
void UStockholmSimSubsystem::MarkThreadRead(const FString& Thread) { SimPtr->MarkThreadRead(ToStd(Thread)); }
bool UStockholmSimSubsystem::HasPendingCall() const { return !SimPtr->PendingPhoneCall().empty(); }

bool UStockholmSimSubsystem::AnswerPendingCall()
{
	const std::string D = SimPtr->PendingPhoneCall();
	return !D.empty() && StartDialogue(ToF(D));
}

bool UStockholmSimSubsystem::PayRent()
{
	const bool bOk = SimPtr->PayRent();
	PumpEvents();
	return bOk;
}

// ---------------------------------------------------------------- Founder Map

TArray<FFounderMapEntry> UStockholmSimSubsystem::GetFounderMapEntries() const
{
	TArray<FFounderMapEntry> Out;
	for (const auto& KV : SimPtr->Content().ecosystem)
	{
		const EcosystemEntry& E = KV.second;
		FFounderMapEntry M;
		M.Id = ToF(E.id);
		M.Name = ToF(E.name);
		for (const std::string& C : E.categories) M.Categories.Add(FName(ToF(C)));
		M.Summary = ToF(E.summary);
		M.Status = ToF(E.statusDetail.empty() ? E.statusLabel : E.statusDetail);
		M.Verification = ToF(E.verification);
		for (const std::string& H : E.storylineHooks) M.StorylineHooks.Add(ToF(H));
		for (const std::string& S : E.sourceUrls) M.Sources.Add(ToF(S));
		M.bDiscovered = SimPtr->IsDiscovered(E.id);
		M.FoundedYear = E.foundedYear;
		Vec2 Pos;
		bool bApprox = true;
		M.bHasWorldPin = ResolveEcosystemPosition(E, SimPtr->Content(), GeoProj, Pos, bApprox);
		M.bApproximate = bApprox;
		if (M.bHasWorldPin)
		{
			M.WorldLocation = LocalToWorld(Pos, DefaultGroundZ / 100.0);
		}
		Out.Add(MoveTemp(M));
	}
	return Out;
}

TArray<FName> UStockholmSimSubsystem::GetFounderMapCategories() const
{
	TArray<FName> Out;
	for (const std::string& C : SimPtr->Content().EcosystemCategories()) Out.Add(FName(ToF(C)));
	return Out;
}

bool UStockholmSimSubsystem::DiscoverEntry(const FString& EntryId)
{
	const bool bOk = SimPtr->Discover(ToStd(EntryId));
	PumpEvents();
	return bOk;
}

// ---------------------------------------------------------------- geography

FVector UStockholmSimSubsystem::LocalToWorld(const Vec2& Local, double HeightMetres) const
{
	const Vec3 UE = GeoProjection::LocalToUnreal(Local, HeightMetres);
	return FVector(UE.x, UE.y, UE.z);
}

Vec2 UStockholmSimSubsystem::WorldToLocal(const FVector& World) const
{
	return GeoProjection::UnrealToLocal(Vec3{World.X, World.Y, World.Z});
}

bool UStockholmSimSubsystem::GetLocationWorldPosition(const FString& LocationId, FVector& OutLocation) const
{
	const LocationDef* L = SimPtr->Content().FindLocation(ToStd(LocationId));
	if (!L || !L->hasCoordinates)
	{
		return false;
	}
	OutLocation = LocalToWorld(GeoProj.ToLocal(L->lat, L->lon));
	const float* Z = LocationGroundZ.Find(LocationId);
	OutLocation.Z = Z ? *Z : DefaultGroundZ;
	return true;
}

void UStockholmSimSubsystem::RegisterLocationGround(const FString& LocationId, float GroundZ)
{
	LocationGroundZ.Add(LocationId, GroundZ);
}

TArray<FVector> UStockholmSimSubsystem::FindRoute(FVector From, FVector To, bool bDriving, float& OutLengthMetres) const
{
	TArray<FVector> Out;
	OutLengthMetres = 0.f;
	if (!bCityLoaded)
	{
		return Out;
	}
	const Route R = CityModel.roads.FindRoute(WorldToLocal(From), WorldToLocal(To), bDriving ? TravelMode::Drive : TravelMode::Walk);
	if (!R.found)
	{
		return Out;
	}
	OutLengthMetres = static_cast<float>(R.lengthMetres);
	for (const Vec2& P : R.Polyline(CityModel.roads))
	{
		Out.Add(LocalToWorld(P, DefaultGroundZ / 100.0));
	}
	return Out;
}

FString UStockholmSimSubsystem::GetMapAttribution() const
{
	return bCityLoaded ? ToF(CityModel.attribution) : FString(TEXT("© OpenStreetMap contributors"));
}
