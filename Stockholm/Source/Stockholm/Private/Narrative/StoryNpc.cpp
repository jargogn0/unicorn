#include "Narrative/StoryNpc.h"

#include "Core/StockholmSimSubsystem.h"
#include "Stockholm.h"

#include "AIController.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"

using namespace stockholm::sim;
using StockholmConv::ToF;
using StockholmConv::ToStd;

AStoryNpc::AStoryNpc()
{
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.TickInterval = 0.25f;
	AutoPossessAI = EAutoPossessAI::PlacedInWorldOrSpawned;
	AIControllerClass = AAIController::StaticClass();
	GetCharacterMovement()->MaxWalkSpeed = 150.f;
	GetCharacterMovement()->bOrientRotationToMovement = true;
	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -90.f), FRotator(0.f, -90.f, 0.f));
	if (USkeletalMesh* Mesh = LoadObject<USkeletalMesh>(nullptr, TEXT("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple.SKM_Manny_Simple")))
	{
		GetMesh()->SetSkeletalMeshAsset(Mesh);
	}
}

void AStoryNpc::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	PlacementTimer -= DeltaSeconds;
	if (PlacementTimer <= 0.f)
	{
		PlacementTimer = 2.f;
		UpdatePlacement();
	}
}

void AStoryNpc::UpdatePlacement()
{
	UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim) return;
	FounderSim& S = Sim->Sim();
	std::string Loc;
	for (const ObjectiveView& V : S.ActiveObjectives())
	{
		if (V.type == ObjectiveType::Talk && V.target == ToStd(NpcId))
		{
			Loc = V.marker;
			if (Loc.empty())
			{
				if (const RoutineEntry* R = S.CurrentRoutine(V.target)) Loc = R->location;
				if (Loc.empty())
				{
					if (const NpcDef* D = S.Content().FindNpc(V.target))
					{
						for (const RoutineEntry& R : D->routine) { if (!R.location.empty()) { Loc = R.location; break; } }
					}
				}
			}
		}
	}
	if (Loc.empty())
	{
		if (const RoutineEntry* R = S.CurrentRoutine(ToStd(NpcId))) Loc = R->location;
	}
	const bool bPresent = !Loc.empty();
	SetActorHiddenInGame(!bPresent);
	SetActorEnableCollision(bPresent);
	if (!bPresent || ToF(Loc) == CurrentLocationId) return;
	CurrentLocationId = ToF(Loc);
	FVector Target;
	if (Sim->GetLocationWorldPosition(CurrentLocationId, Target))
	{
		// Characters out of sight teleport; visible ones walk via navmesh.
		const APawn* Player = UGameplayStatics::GetPlayerPawn(this, 0);
		const bool bVisible = Player && FVector::Dist(Player->GetActorLocation(), GetActorLocation()) < 4000.f && WasRecentlyRendered(0.5f);
		if (AAIController* AI = Cast<AAIController>(GetController()); AI && bVisible)
		{
			AI->MoveToLocation(Target, 80.f);
		}
		else
		{
			SetActorLocation(Target + FVector(0, 0, GetCapsuleComponent()->GetScaledCapsuleHalfHeight()), false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
}

FText AStoryNpc::GetInteractionPrompt_Implementation(APawn* Instigator) const
{
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	if (!Sim || IsHidden() || Sim->IsDialogueActive() || Sim->Sim().DialogueForNpc(ToStd(NpcId)).empty()) return FText::GetEmpty();
	const NpcDef* D = Sim->Sim().Content().FindNpc(ToStd(NpcId));
	FString First = D ? ToF(D->name) : NpcId;
	First.Split(TEXT(" "), &First, nullptr);
	return FText::Format(NSLOCTEXT("Stockholm", "TalkTo", "Talk to {0}"), FText::FromString(First));
}

void AStoryNpc::Interact_Implementation(APawn* Instigator)
{
	if (UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		if (Instigator)
		{
			SetActorRotation(FRotator(0.f, (Instigator->GetActorLocation() - GetActorLocation()).Rotation().Yaw, 0.f));
		}
		Sim->StartDialogueWithNpc(NpcId);
	}
}
