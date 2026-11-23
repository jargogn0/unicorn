#include "UI/StockholmHUD.h"

#include "Core/StockholmSimSubsystem.h"
#include "Player/InteractionComponent.h"
#include "Player/StockholmCharacter.h"
#include "Vehicles/StockholmVehicle.h"

#include "Engine/Canvas.h"
#include "Engine/Engine.h"
#include "Engine/Font.h"
#include "GameFramework/PlayerController.h"

using namespace stockholm::sim;

namespace StockholmHUDDetail
{
	const FLinearColor Ink(0.91f, 0.93f, 0.95f);
	const FLinearColor Mute(0.62f, 0.69f, 0.75f);
	const FLinearColor Warm(1.f, 0.72f, 0.36f);
	const FLinearColor Copper(0.37f, 0.72f, 0.64f);
	const FLinearColor Alert(1.f, 0.42f, 0.35f);
	FString Kr(double V) { return FString::Printf(TEXT("%s kr"), *FText::AsNumber(FMath::RoundToInt64(V)).ToString()); }
	double Now() { return FPlatformTime::Seconds(); }
}
using namespace StockholmHUDDetail;

void AStockholmHUD::BeginPlay()
{
	Super::BeginPlay();
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		Sim->OnSimEvent.AddDynamic(this, &AStockholmHUD::OnSimEvent);
	}
}

void AStockholmHUD::OnSimEvent(const FStockholmSimEvent& E)
{
	const FString T = E.Type.ToString();
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (T == TEXT("phone_message"))
	{
		const NpcDef* N = Sim ? Sim->Sim().Content().FindNpc(StockholmConv::ToStd(E.Id)) : nullptr;
		ShowNotification(N ? StockholmConv::ToF(N->name) : E.Id, E.Text);
	}
	else if (T == TEXT("mission_started")) ShowNotification(TEXT("Mission"), E.Text);
	else if (T == TEXT("mission_completed")) ShowNotification(TEXT("Mission complete"), E.Text);
	else if (T == TEXT("mission_failed")) ShowNotification(TEXT("Mission failed"), E.Text);
	else if (T == TEXT("chapter_changed")) ShowNotification(FString::Printf(TEXT("Chapter %d"), FMath::RoundToInt(E.Value)), E.Text);
	else if (T == TEXT("poi_discovered")) ShowNotification(TEXT("Founder Map"), TEXT("Discovered: ") + E.Text);
	else if (T == TEXT("commitment_made")) ShowNotification(TEXT("Promise"), E.Text);
	else if (T == TEXT("commitment_broken")) ShowNotification(TEXT("Promise broken"), E.Text);
	else if (T == TEXT("notification") && !E.Text.IsEmpty()) ShowNotification(TEXT("Notice"), E.Text);
	else if (T == TEXT("world_event") && !E.Text.IsEmpty() && !E.Id.StartsWith(TEXT("cinematic:opening"))) ShowCaption(E.Text, 4.f);
}

void AStockholmHUD::ShowCaption(const FString& Text, float Seconds) { Caption = Text; CaptionUntil = Now() + Seconds; }
void AStockholmHUD::ShowNotification(const FString& From, const FString& Text)
{
	Toasts.Insert({From, Text, Now() + 6.5}, 0);
	if (Toasts.Num() > 3) Toasts.SetNum(3);
}

void AStockholmHUD::DrawPanel(float X, float Y, float W, float H, const FLinearColor& Color)
{
	FCanvasTileItem Tile(FVector2D(X, Y), FVector2D(W, H), Color);
	Tile.BlendMode = SE_BLEND_Translucent;
	Canvas->DrawItem(Tile);
}

void AStockholmHUD::DrawLabel(const FString& Text, float X, float Y, const FLinearColor& Color, float Scale, UFont* Font)
{
	FCanvasTextItem Item(FVector2D(X, Y), FText::FromString(Text), Font ? Font : GEngine->GetMediumFont(), Color);
	Item.Scale = FVector2D(Scale, Scale);
	Item.EnableShadow(FLinearColor(0, 0, 0, 0.7f));
	Canvas->DrawItem(Item);
}

float AStockholmHUD::DrawWrapped(const FString& Text, float X, float Y, float MaxWidth, const FLinearColor& Color, float Scale)
{
	TArray<FString> Words;
	Text.ParseIntoArray(Words, TEXT(" "));
	FString Line;
	float LineY = Y;
	UFont* Font = GEngine->GetMediumFont();
	for (const FString& W : Words)
	{
		const FString Trial = Line.IsEmpty() ? W : Line + TEXT(" ") + W;
		float TW, TH;
		Canvas->StrLen(Font, Trial, TW, TH);
		if (TW * Scale > MaxWidth && !Line.IsEmpty())
		{
			DrawLabel(Line, X, LineY, Color, Scale);
			LineY += TH * Scale * 1.25f;
			Line = W;
		}
		else
		{
			Line = Trial;
		}
	}
	if (!Line.IsEmpty())
	{
		float TW, TH;
		Canvas->StrLen(Font, Line, TW, TH);
		DrawLabel(Line, X, LineY, Color, Scale);
		LineY += TH * Scale * 1.25f;
	}
	return LineY;
}

void AStockholmHUD::DrawHUD()
{
	Super::DrawHUD();
	if (!Canvas) return;
	DrawStatus();
	DrawObjective();
	DrawMinimap();
	DrawToasts();
	DrawDecision();
	DrawDialogue();
	if (bPhoneOpen) DrawPhone();
	if (bMapOpen) DrawFounderMap();
	if (!Caption.IsEmpty() && Now() < CaptionUntil)
	{
		float TW, TH;
		Canvas->StrLen(GEngine->GetMediumFont(), Caption, TW, TH);
		DrawLabel(Caption, (Canvas->ClipX - TW * 1.3f) * 0.5f, Canvas->ClipY * 0.78f, Ink, 1.3f);
	}
	// Interaction prompt.
	if (const AStockholmCharacter* C = Cast<AStockholmCharacter>(GetOwningPawn()))
	{
		const FText Prompt = C->GetInteraction() ? C->GetInteraction()->GetPrompt() : FText::GetEmpty();
		if (!Prompt.IsEmpty())
		{
			const FString S = TEXT("[E]  ") + Prompt.ToString();
			float TW, TH;
			Canvas->StrLen(GEngine->GetMediumFont(), S, TW, TH);
			const float X = (Canvas->ClipX - TW * 1.2f) * 0.5f, Y = Canvas->ClipY - 150.f;
			DrawPanel(X - 12, Y - 6, TW * 1.2f + 24, TH * 1.2f + 12);
			DrawLabel(S, X, Y, Ink, 1.2f);
		}
	}
}

void AStockholmHUD::DrawStatus()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	DrawLabel(Kr(Sim->GetStat(TEXT("personal_cash"))), 24, 20, Ink, 2.f);
	DrawLabel(FString::Printf(TEXT("Chapter %d · %s"), Sim->GetChapter(), *Sim->GetChapterTitle()), 24, 58, Mute, 1.f);
	const auto& W = Sim->Sim().Clock().Weather();
	DrawLabel(FString::Printf(TEXT("%s   %s   %s %d°"), *Sim->GetTimeLabel(), *Sim->GetDateLabel(), *FString(WeatherToString(W.kind)).Replace(TEXT("_"), TEXT(" ")), FMath::RoundToInt(W.temperatureC)),
		24, Canvas->ClipY - 260, Ink, 1.2f);
	if (const AStockholmVehicle* V = Cast<AStockholmVehicle>(GetOwningPawn()))
	{
		DrawLabel(FString::Printf(TEXT("%d km/h"), FMath::RoundToInt(FMath::Abs(V->GetSpeedKmh()))), 24, Canvas->ClipY - 290, Ink, 1.5f);
	}
}

void AStockholmHUD::DrawObjective()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	const TArray<FStockholmObjective> Objectives = Sim->GetObjectives();
	if (Objectives.Num() == 0) { LastObjectiveKey.Reset(); return; }
	const FStockholmObjective& O = Objectives[0];
	const float W = 420.f, X = Canvas->ClipX - W - 24.f, Y = 20.f;
	DrawPanel(X, Y, W, 96.f);
	DrawLabel(O.MissionTitle.ToUpper(), X + 14, Y + 10, Warm, 0.9f);
	const float EndY = DrawWrapped(O.Text, X + 14, Y + 32, W - 28, Ink, 1.05f);
	if (O.MinutesRemaining >= 0.f)
	{
		const int32 M = FMath::Max(0, FMath::FloorToInt(O.MinutesRemaining));
		DrawLabel(FString::Printf(TEXT("%d h %02d min left"), M / 60, M % 60), X + 14, EndY + 2, M < 45 ? Alert : Mute, 0.9f);
	}
	const FString Key = O.MissionId + TEXT("/") + O.ObjectiveId;
	if (Key != LastObjectiveKey)
	{
		LastObjectiveKey = Key;
		bDecisionOpen = O.Type == FName(TEXT("decision"));
		DecisionStart = Now();
		MinigameSequence.Reset();
		MinigameProgress = 0;
		if (O.Type == FName(TEXT("custom")) && O.Target == TEXT("demo_fix_success"))
		{
			for (int32 i = 0; i < 5; ++i) MinigameSequence.Add(FMath::RandRange(0, 3));
		}
		NextRouteTime = 0.0;
	}
}

void AStockholmHUD::UpdateRoute()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	const APawn* Pawn = GetOwningPawn();
	if (!Sim || !Pawn || Now() < NextRouteTime) return;
	NextRouteTime = Now() + 1.0;
	Route.Reset();
	const TArray<FStockholmObjective> Objectives = Sim->GetObjectives();
	if (Objectives.Num() && Objectives[0].bHasMarker)
	{
		float Length = 0.f;
		Route = Sim->FindRoute(Pawn->GetActorLocation(), Objectives[0].MarkerWorldLocation, Pawn->IsA<AStockholmVehicle>(), Length);
	}
}

void AStockholmHUD::DrawMinimap()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	const APawn* Pawn = GetOwningPawn();
	if (!Sim || !Pawn || !Sim->HasCity()) return;
	UpdateRoute();
	const float Size = 220.f, X0 = 24.f, Y0 = Canvas->ClipY - Size - 24.f;
	const FVector2D Centre(X0 + Size / 2, Y0 + Size / 2);
	DrawPanel(X0, Y0, Size, Size, FLinearColor(0.08f, 0.19f, 0.29f, 0.85f));
	const float Yaw = FMath::DegreesToRadians(GetOwningPlayerController()->GetControlRotation().Yaw);
	const float Scale = Pawn->IsA<AStockholmVehicle>() ? 0.35f : 0.6f; // px per metre
	const FVector P = Pawn->GetActorLocation();
	// Rotate so the camera's forward points up.
	auto ToMap = [&](const FVector& W) {
		const FVector2D D((W.X - P.X) / 100.f, (W.Y - P.Y) / 100.f);
		const float C = FMath::Cos(-Yaw - PI / 2), S = FMath::Sin(-Yaw - PI / 2);
		return Centre + FVector2D(D.X * C - D.Y * S, D.X * S + D.Y * C) * Scale;
	};
	auto Inside = [&](const FVector2D& M) { return FVector2D::Distance(M, Centre) < Size * 0.48f; };
	for (const CityModel::RoadLine& L : Sim->City().roadLines)
	{
		for (size_t i = 0; i + 1 < L.points.size(); ++i)
		{
			const FVector2D A = ToMap(Sim->LocalToWorld(L.points[i])), B = ToMap(Sim->LocalToWorld(L.points[i + 1]));
			if (!Inside(A) && !Inside(B)) continue;
			FCanvasLineItem Line(A, B);
			Line.SetColor(IsDrivable(L.roadClass) ? FLinearColor(0.85f, 0.87f, 0.9f, 0.9f) : FLinearColor(0.6f, 0.65f, 0.6f, 0.7f));
			Line.LineThickness = FMath::Max(1.f, static_cast<float>(L.widthMetres) * Scale * 0.6f);
			Canvas->DrawItem(Line);
		}
	}
	for (int32 i = 0; i + 1 < Route.Num(); ++i)
	{
		const FVector2D A = ToMap(Route[i]), B = ToMap(Route[i + 1]);
		if (!Inside(A) && !Inside(B)) continue;
		FCanvasLineItem Line(A, B);
		Line.SetColor(Warm);
		Line.LineThickness = 4.f;
		Canvas->DrawItem(Line);
	}
	DrawPanel(Centre.X - 4, Centre.Y - 4, 8, 8, Ink);
}

void AStockholmHUD::DrawToasts()
{
	float Y = 130.f;
	const float W = 440.f, X = (Canvas->ClipX - W) * 0.5f;
	for (int32 i = Toasts.Num() - 1; i >= 0; --i)
	{
		if (Now() > Toasts[i].Until) Toasts.RemoveAt(i);
	}
	for (const FToast& T : Toasts)
	{
		DrawPanel(X, Y, W, 62.f);
		DrawLabel(T.From.ToUpper(), X + 12, Y + 8, Copper, 0.85f);
		DrawWrapped(T.Text, X + 12, Y + 28, W - 24, Ink, 0.95f);
		Y += 70.f;
	}
}

void AStockholmHUD::DrawDialogue()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || !Sim->IsDialogueActive()) return;
	const FStockholmDialogueLine L = Sim->GetDialogueLine();
	if (!L.bActive) return;
	if (L.NodeId != LastDialogueNode) { LastDialogueNode = L.NodeId; DialogueNodeStart = Now(); }
	const float W = FMath::Min(780.f, Canvas->ClipX - 48.f), X = (Canvas->ClipX - W) * 0.5f;
	const float H = 120.f + L.Choices.Num() * 30.f, Y = Canvas->ClipY - H - 24.f;
	DrawPanel(X, Y, W, H);
	DrawLabel(L.SpeakerName.ToUpper(), X + 16, Y + 12, Warm, 1.f);
	float CY = DrawWrapped(L.Text, X + 16, Y + 38, W - 32, Ink, 1.15f) + 6.f;
	for (int32 i = 0; i < L.Choices.Num(); ++i)
	{
		const FStockholmChoice& C = L.Choices[i];
		DrawLabel(FString::Printf(TEXT("%d  %s%s"), i + 1, *C.Text, C.bAvailable ? TEXT("") : *(TEXT("  (") + C.LockedHint + TEXT(")"))), X + 24, CY, C.bAvailable ? Ink : Mute, 1.f);
		CY += 30.f;
	}
	if (L.TimeoutSeconds > 0.f)
	{
		const float Left = 1.f - static_cast<float>((Now() - DialogueNodeStart) / L.TimeoutSeconds);
		DrawPanel(X, Y + H - 4, W * FMath::Clamp(Left, 0.f, 1.f), 4, Alert);
		if (Left <= 0.f && L.TimeoutChoice >= 0) Sim->ChooseDialogueOption(L.TimeoutChoice);
	}
	if (!L.bHasChoices) DrawLabel(TEXT("Enter / click to continue"), X + W - 210, Y + H - 26, Mute, 0.85f);
}

void AStockholmHUD::DrawDecision()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	const TArray<FStockholmObjective> Objectives = Sim->GetObjectives();
	if (Objectives.Num() == 0) return;
	const FStockholmObjective& O = Objectives[0];
	const float W = 540.f, X = (Canvas->ClipX - W) * 0.5f, Y = Canvas->ClipY * 0.3f;
	if (MinigameSequence.Num() > 0)
	{
		static const TCHAR* Glyph[] = {TEXT("1 ←"), TEXT("2 ↑"), TEXT("3 ↓"), TEXT("4 →")};
		DrawPanel(X, Y, W, 150.f, FLinearColor(0.02f, 0.05f, 0.08f, 0.92f));
		DrawLabel(TEXT("RESTART THE SYNC — PRESS IN ORDER"), X + 16, Y + 14, Warm, 1.f);
		for (int32 i = 0; i < MinigameSequence.Num(); ++i)
		{
			DrawPanel(X + 16 + i * 100, Y + 50, 88, 60, i < MinigameProgress ? Copper : FLinearColor(1, 1, 1, 0.08f));
			DrawLabel(Glyph[MinigameSequence[i]], X + 34 + i * 100, Y + 66, Ink, 1.3f);
		}
		return;
	}
	if (!bDecisionOpen || O.Type != FName(TEXT("decision"))) return;
	const float H = 90.f + O.Options.Num() * 34.f;
	DrawPanel(X, Y, W, H, FLinearColor(0.02f, 0.05f, 0.08f, 0.92f));
	DrawLabel(O.MissionTitle.ToUpper(), X + 16, Y + 12, Mute, 0.9f);
	DrawWrapped(O.Text, X + 16, Y + 34, W - 32, Ink, 1.25f);
	for (int32 i = 0; i < O.Options.Num(); ++i)
	{
		DrawLabel(FString::Printf(TEXT("%d  %s"), i + 1, *O.Options[i].Text), X + 24, Y + 76 + i * 34.f, O.Options[i].bAvailable ? Ink : Mute, 1.05f);
	}
	if (O.DecisionSeconds > 0.f)
	{
		const float Left = 1.f - static_cast<float>((Now() - DecisionStart) / O.DecisionSeconds);
		DrawPanel(X, Y + H - 4, W * FMath::Clamp(Left, 0.f, 1.f), 4, Alert);
		if (Left <= 0.f) { Sim->ChooseDecision(O.MissionId, FMath::Max(0, O.DecisionDefault)); bDecisionOpen = false; }
	}
}

void AStockholmHUD::DialogueAdvancePressed()
{
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		if (Sim->IsDialogueActive()) { Sim->AdvanceDialogue(); return; }
		if (Sim->HasPendingCall() && bPhoneOpen) { bPhoneOpen = false; Sim->AnswerPendingCall(); }
	}
}

void AStockholmHUD::ChoicePressed(int32 Slot)
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	if (Sim->IsDialogueActive())
	{
		const FStockholmDialogueLine L = Sim->GetDialogueLine();
		if (L.Choices.IsValidIndex(Slot) && L.Choices[Slot].bAvailable) Sim->ChooseDialogueOption(L.Choices[Slot].Index);
		return;
	}
	const TArray<FStockholmObjective> Objectives = Sim->GetObjectives();
	if (Objectives.Num() == 0) return;
	if (MinigameSequence.Num() > 0)
	{
		if (MinigameSequence[MinigameProgress] == Slot)
		{
			if (++MinigameProgress >= MinigameSequence.Num())
			{
				MinigameSequence.Reset();
				Sim->NotifyCustomEvent(TEXT("demo_fix_success"));
			}
		}
		else
		{
			MinigameProgress = 0;
		}
		return;
	}
	if (Objectives[0].Type == FName(TEXT("decision")))
	{
		bDecisionOpen = true;
		if (Sim->ChooseDecision(Objectives[0].MissionId, Slot)) bDecisionOpen = false;
		return;
	}
	if (bPhoneOpen && Slot == 0) Sim->PayRent();
	if (bMapOpen)
	{
		static const int32 Count = 9;
		if (Slot == 0) MapCategory = MapCategory + 1 >= Count ? -1 : MapCategory + 1;
		if (Slot == 2) ++MapSelection;
		if (Slot == 1) MapSelection = FMath::Max(0, MapSelection - 1);
	}
}

void AStockholmHUD::DrawPhone()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	const float W = 360.f, H = 600.f, X = Canvas->ClipX - W - 24.f, Y = Canvas->ClipY - H - 24.f;
	DrawPanel(X, Y, W, H, FLinearColor(0.02f, 0.04f, 0.07f, 0.96f));
	DrawLabel(Sim->GetTimeLabel(), X + 18, Y + 12, Mute, 0.9f);
	float CY = Y + 40.f;
	if (Sim->HasPendingCall())
	{
		DrawLabel(TEXT("Unanswered message · Enter to reply"), X + 18, CY, Warm, 1.f);
		CY += 30.f;
	}
	DrawLabel(FString::Printf(TEXT("Bank: %s   Rent %s   (1 = pay rent)"), *Kr(Sim->GetStat(TEXT("personal_cash"))),
		Sim->Sim().State().rentPaidThisMonth ? TEXT("paid") : *Kr(Sim->GetStat(TEXT("rent_monthly")))), X + 18, CY, Ink, 0.9f);
	CY += 34.f;
	TArray<FStockholmPhoneMessage> Messages = Sim->GetMessages();
	for (int32 i = Messages.Num() - 1; i >= 0 && CY < Y + H - 60; --i)
	{
		DrawLabel(Messages[i].SenderName.ToUpper() + TEXT("  ") + Messages[i].TimeLabel, X + 18, CY, Copper, 0.85f);
		CY = DrawWrapped(Messages[i].Text, X + 18, CY + 20, W - 36, Ink, 0.95f) + 10.f;
	}
	for (const Commitment& C : Sim->Sim().Commitments())
	{
		if (C.status != Commitment::Status::Pending || CY > Y + H - 30) continue;
		DrawLabel(TEXT("Promise: ") + StockholmConv::ToF(C.text), X + 18, CY, Warm, 0.85f);
		CY += 22.f;
	}
}

void AStockholmHUD::DrawFounderMap()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	static const TCHAR* Cats[] = {TEXT("unicorn_landmark"), TEXT("startup"), TEXT("vc_firm"), TEXT("angel_investor"), TEXT("accelerator"), TEXT("coworking"), TEXT("university_research"), TEXT("founder_event"), TEXT("potential_customer")};
	static const FLinearColor CatColor[] = {Warm, FLinearColor(1, 0.54f, 0.42f), FLinearColor(0.71f, 0.57f, 1), FLinearColor(0.9f, 0.63f, 0.82f), Copper, FLinearColor(0.44f, 0.72f, 1), FLinearColor(0.78f, 0.88f, 0.42f), FLinearColor(1, 0.85f, 0.29f), FLinearColor(1, 0.42f, 0.54f)};
	DrawPanel(0, 0, Canvas->ClipX, Canvas->ClipY, FLinearColor(0.02f, 0.05f, 0.07f, 0.94f));
	DrawLabel(TEXT("FOUNDER MAP"), 32, 24, Ink, 2.f);
	DrawLabel(FString::Printf(TEXT("Filter: %s   (1 = next category, 2/3 = select, M = close)"), MapCategory < 0 ? TEXT("all") : Cats[MapCategory]), 32, 68, Mute, 0.95f);
	const float MapW = Canvas->ClipX * 0.62f, MapH = Canvas->ClipY - 140.f, MX = 32.f, MY = 100.f;
	DrawPanel(MX, MY, MapW, MapH, FLinearColor(0.06f, 0.14f, 0.23f, 1.f));
	const float Scale = MapH / 7000.f; // ~7 km tall view centred on the old town
	auto ToMap = [&](const Vec2& L) { return FVector2D(MX + MapW / 2 + static_cast<float>(L.x) * Scale, MY + MapH / 2 - static_cast<float>(L.y) * Scale); };
	for (const CityModel::RoadLine& L : Sim->City().roadLines)
	{
		for (size_t i = 0; i + 1 < L.points.size(); ++i)
		{
			FCanvasLineItem Line(ToMap(L.points[i]), ToMap(L.points[i + 1]));
			Line.SetColor(FLinearColor(0.9f, 0.93f, 0.95f, 0.25f));
			Canvas->DrawItem(Line);
		}
	}
	TArray<FFounderMapEntry> Entries = Sim->GetFounderMapEntries();
	Entries.RemoveAll([&](const FFounderMapEntry& E) { return MapCategory >= 0 && !E.Categories.Contains(FName(Cats[MapCategory])); });
	MapSelection = Entries.Num() ? MapSelection % Entries.Num() : 0;
	for (int32 i = 0; i < Entries.Num(); ++i)
	{
		const FFounderMapEntry& E = Entries[i];
		if (!E.bHasWorldPin) continue;
		const Vec2 L = Sim->WorldToLocal(E.WorldLocation);
		const FVector2D P = ToMap(L);
		int32 CatIndex = 0;
		for (int32 c = 0; c < 9; ++c) { if (E.Categories.Contains(FName(Cats[c]))) { CatIndex = c; break; } }
		FLinearColor Col = CatColor[CatIndex];
		Col.A = E.bDiscovered ? 1.f : 0.35f;
		const float R = i == MapSelection ? 7.f : 4.f;
		DrawPanel(P.X - R, P.Y - R, R * 2, R * 2, Col);
	}
	// Detail card for the selection.
	const float DX = MX + MapW + 24.f, DW = Canvas->ClipX - DX - 32.f;
	if (Entries.IsValidIndex(MapSelection))
	{
		const FFounderMapEntry& E = Entries[MapSelection];
		float CY = MY;
		DrawLabel(E.bDiscovered ? E.Name : TEXT("Undiscovered"), DX, CY, Ink, 1.6f);
		CY += 40.f;
		if (E.bDiscovered)
		{
			DrawLabel(FString::Printf(TEXT("%s · founded %d · %s"), *E.Verification, E.FoundedYear, E.bHasWorldPin ? (E.bApproximate ? TEXT("approximate area") : TEXT("sourced address")) : TEXT("directory only")), DX, CY, Mute, 0.9f);
			CY = DrawWrapped(E.Summary, DX, CY + 26, DW, Ink, 0.95f);
			CY = DrawWrapped(E.Status, DX, CY + 10, DW, Mute, 0.9f);
			for (const FString& Hook : E.StorylineHooks) { CY = DrawWrapped(TEXT("· ") + Hook, DX, CY + 6, DW, Warm, 0.9f); }
		}
		else
		{
			DrawWrapped(TEXT("Someone in the city knows about this place. Talk to founders, visit coworking spaces and attend events."), DX, CY, DW, Mute, 0.95f);
		}
	}
	DrawLabel(Sim->GetMapAttribution() + TEXT(" · pins without a sourced address are district approximations"), MX, MY + MapH + 8, Mute, 0.8f);
}
