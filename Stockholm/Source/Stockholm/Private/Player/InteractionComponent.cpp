#include "Player/InteractionComponent.h"

#include "Player/StockholmInteractable.h"

#include "Components/PrimitiveComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/Controller.h"

UInteractionComponent::UInteractionComponent()
{
	PrimaryComponentTick.bCanEverTick = true;
	PrimaryComponentTick.TickInterval = 0.1f;
}

void UInteractionComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
	Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
	APawn* Owner = Cast<APawn>(GetOwner());
	if (!Owner || !Owner->IsLocallyControlled())
	{
		return;
	}
	const FVector Origin = Owner->GetActorLocation();
	const FVector Facing = Owner->GetControlRotation().Vector().GetSafeNormal2D();

	TArray<FOverlapResult> Overlaps;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(StockholmInteract), false, Owner);
	GetWorld()->OverlapMultiByObjectType(Overlaps, Origin, FQuat::Identity,
		FCollisionObjectQueryParams(FCollisionObjectQueryParams::AllObjects), FCollisionShape::MakeSphere(Radius), Params);

	AActor* Best = nullptr;
	float BestScore = -FLT_MAX;
	for (const FOverlapResult& O : Overlaps)
	{
		AActor* A = O.GetActor();
		if (!A || A == Owner || !A->Implements<UStockholmInteractable>())
		{
			continue;
		}
		if (IStockholmInteractable::Execute_GetInteractionPrompt(A, Owner).IsEmpty())
		{
			continue;
		}
		const FVector To = (A->GetActorLocation() - Origin);
		const float Dot = FVector::DotProduct(Facing, To.GetSafeNormal2D());
		if (Dot < MinFacingDot)
		{
			continue;
		}
		const float Score = Dot * 2.f - To.Size() / Radius;
		if (Score > BestScore)
		{
			BestScore = Score;
			Best = A;
		}
	}
	SetFocus(Best);
}

void UInteractionComponent::SetFocus(AActor* NewFocus)
{
	if (Focused.Get() != NewFocus)
	{
		// Custom-depth outline highlight (post-process material reads stencil 1).
		if (AActor* Old = Focused.Get())
		{
			TArray<UPrimitiveComponent*> Prims;
			Old->GetComponents(Prims);
			for (UPrimitiveComponent* P : Prims) P->SetRenderCustomDepth(false);
		}
		if (NewFocus)
		{
			TArray<UPrimitiveComponent*> Prims;
			NewFocus->GetComponents(Prims);
			for (UPrimitiveComponent* P : Prims)
			{
				P->SetRenderCustomDepth(true);
				P->SetCustomDepthStencilValue(1);
			}
		}
		Focused = NewFocus;
	}
	Prompt = NewFocus ? IStockholmInteractable::Execute_GetInteractionPrompt(NewFocus, Cast<APawn>(GetOwner())) : FText::GetEmpty();
}

bool UInteractionComponent::TryInteract()
{
	AActor* Target = Focused.Get();
	if (!Target)
	{
		return false;
	}
	IStockholmInteractable::Execute_Interact(Target, Cast<APawn>(GetOwner()));
	return true;
}
