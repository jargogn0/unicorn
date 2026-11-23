#include "Narrative/CinematicDirector.h"

#include "Core/StockholmSettings.h"
#include "Core/StockholmSimSubsystem.h"
#include "Player/StockholmPlayerController.h"
#include "UI/StockholmHUD.h"
#include "Stockholm.h"

#include "CineCameraActor.h"
#include "CineCameraComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"

#include "Sim/Json.h"

using namespace stockholm::sim;

ACinematicDirector::ACinematicDirector()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bTickEvenWhenPaused = true;
}

void ACinematicDirector::BeginPlay()
{
	Super::BeginPlay();
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		Sim->OnSimEvent.AddDynamic(this, &ACinematicDirector::OnSimEvent);
	}
}

void ACinematicDirector::OnSimEvent(const FStockholmSimEvent& Event)
{
	if (Event.Type == FName(TEXT("world_event")) && Event.Id.StartsWith(TEXT("cinematic:")))
	{
		Play(Event.Id.RightChop(10));
	}
}

bool ACinematicDirector::Play(const FString& CinematicId)
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	const FString Path = UStockholmSettings::ContentPath(FString::Printf(TEXT("Data/Cinematics/%s.json"), *CinematicId));
	bool bOk = false;
	const JsonValue Doc = JsonValue::Parse(ReadTextFile(StockholmConv::ToStd(Path), &bOk));
	if (!Sim || !bOk || !Doc.IsObject()) return false;

	FVector Anchor = FVector::ZeroVector;
	Sim->GetLocationWorldPosition(StockholmConv::ToF(Doc["anchor"].AsString("apt_player")), Anchor);
	auto Vec = [&](const JsonValue& V) { return Anchor + FVector(V[static_cast<size_t>(0)].AsNumber(), V[static_cast<size_t>(1)].AsNumber(), V[static_cast<size_t>(2)].AsNumber()) * 100.0; };
	Shots.Reset();
	for (const JsonValue& S : Doc["shots"].Elements())
	{
		FShot Shot;
		Shot.FromPos = Vec(S["from"]["pos"]); Shot.FromLook = Vec(S["from"]["look"]);
		Shot.ToPos = Vec(S["to"]["pos"]); Shot.ToLook = Vec(S["to"]["look"]);
		Shot.Duration = static_cast<float>(S["seconds"].AsNumber(3.0));
		Shot.Caption = StockholmConv::ToF(S["caption"].AsString(""));
		Shot.NotifFrom = StockholmConv::ToF(S["notification"]["from"].AsString(""));
		Shot.NotifText = StockholmConv::ToF(S["notification"]["text"].AsString(""));
		Shots.Add(Shot);
	}
	if (Shots.Num() == 0) return false;
	if (!Camera)
	{
		Camera = GetWorld()->SpawnActor<ACineCameraActor>(ACineCameraActor::StaticClass(), FTransform::Identity);
		Camera->GetCineCameraComponent()->CurrentFocalLength = 28.f;
		Camera->GetCineCameraComponent()->CurrentAperture = 2.0f;
	}
	ShotIndex = 0;
	ShotTime = 0.f;
	Sim->SetSimPaused(true);
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		PC->SetViewTargetWithBlend(Camera, 0.f);
		if (AStockholmPlayerController* SPC = Cast<AStockholmPlayerController>(PC)) SPC->SetCinematicActive(true);
	}
	return true;
}

void ACinematicDirector::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	if (Shots.Num() == 0 || !Camera) return;
	const FShot& S = Shots[ShotIndex];
	if (ShotTime == 0.f)
	{
		if (AStockholmHUD* HUD = Cast<AStockholmHUD>(UGameplayStatics::GetPlayerController(this, 0)->GetHUD()))
		{
			if (!S.Caption.IsEmpty()) HUD->ShowCaption(S.Caption, S.Duration - 0.2f);
			if (!S.NotifText.IsEmpty()) HUD->ShowNotification(S.NotifFrom, S.NotifText);
		}
	}
	ShotTime += DeltaSeconds;
	const float A = FMath::InterpEaseInOut(0.f, 1.f, FMath::Clamp(ShotTime / S.Duration, 0.f, 1.f), 2.f);
	const FVector Pos = FMath::Lerp(S.FromPos, S.ToPos, A);
	const FVector Look = FMath::Lerp(S.FromLook, S.ToLook, A);
	Camera->SetActorLocationAndRotation(Pos, (Look - Pos).Rotation());
	if (ShotTime >= S.Duration)
	{
		ShotTime = 0.f;
		if (++ShotIndex >= Shots.Num()) Finish();
	}
}

void ACinematicDirector::Skip() { if (Shots.Num()) Finish(); }

void ACinematicDirector::Finish()
{
	Shots.Reset();
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this)) Sim->SetSimPaused(false);
	if (APlayerController* PC = UGameplayStatics::GetPlayerController(this, 0))
	{
		PC->SetViewTargetWithBlend(PC->GetPawn(), 0.6f);
		if (AStockholmPlayerController* SPC = Cast<AStockholmPlayerController>(PC)) SPC->SetCinematicActive(false);
	}
}
