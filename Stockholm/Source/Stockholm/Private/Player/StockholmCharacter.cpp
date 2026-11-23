#include "Player/StockholmCharacter.h"

#include "Core/StockholmSimSubsystem.h"
#include "Player/InteractionComponent.h"
#include "Player/StockholmInputConfig.h"
#include "Player/StockholmPlayerController.h"
#include "Stockholm.h"

#include "Camera/CameraComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"

AStockholmCharacter::AStockholmCharacter()
{
	PrimaryActorTick.bCanEverTick = true;
	GetCapsuleComponent()->InitCapsuleSize(38.f, 92.f);

	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	UCharacterMovementComponent* Move = GetCharacterMovement();
	Move->bOrientRotationToMovement = true;
	Move->RotationRate = FRotator(0.f, 540.f, 0.f);
	Move->MaxWalkSpeed = JogSpeed;
	Move->MinAnalogWalkSpeed = 40.f;
	Move->BrakingDecelerationWalking = 1600.f;
	Move->JumpZVelocity = 420.f;
	Move->AirControl = 0.25f;
	Move->bCanWalkOffLedgesWhenCrouching = true;
	Move->NavAgentProps.bCanCrouch = true;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(RootComponent);
	CameraBoom->TargetArmLength = 340.f;
	CameraBoom->SocketOffset = FVector(0.f, 55.f, 65.f); // over-the-shoulder framing
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->CameraLagSpeed = 12.f;
	CameraBoom->ProbeSize = 14.f;

	FollowCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("FollowCamera"));
	FollowCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	FollowCamera->bUsePawnControlRotation = false;
	FollowCamera->SetFieldOfView(78.f);

	Interaction = CreateDefaultSubobject<UInteractionComponent>(TEXT("Interaction"));

	GetMesh()->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -92.f), FRotator(0.f, -90.f, 0.f));
	// UE5 Third Person template mannequin (add via "Add Feature or Content Pack").
	DefaultMesh = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple")));
	DefaultAnimClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C")));
}

void AStockholmCharacter::BeginPlay()
{
	Super::BeginPlay();
	if (!GetMesh()->GetSkeletalMeshAsset())
	{
		if (USkeletalMesh* Mesh = DefaultMesh.LoadSynchronous())
		{
			GetMesh()->SetSkeletalMeshAsset(Mesh);
		}
		else
		{
			UE_LOG(LogStockholm, Warning, TEXT("Founder mesh missing (%s). Add the Third Person content pack or assign a MetaHuman."), *DefaultMesh.ToString());
		}
		if (UClass* Anim = DefaultAnimClass.LoadSynchronous())
		{
			GetMesh()->SetAnimInstanceClass(Anim);
		}
	}
}

void AStockholmCharacter::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	// Snow underfoot slows you down a little; drives footstep FX via snow cover elsewhere.
	if (const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this))
	{
		const float Snow = static_cast<float>(Sim->Sim().Clock().Weather().snowCover);
		const float Base = bSprinting ? SprintSpeed : JogSpeed;
		GetCharacterMovement()->MaxWalkSpeed = Base * FMath::Lerp(1.f, SnowSpeedFactor, FMath::Clamp(Snow, 0.f, 1.f));
	}
}

void AStockholmCharacter::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	const AStockholmPlayerController* PC = Cast<AStockholmPlayerController>(GetController());
	const UStockholmInputConfig* Cfg = PC ? PC->GetInputConfig() : nullptr;
	if (!Input || !Cfg)
	{
		UE_LOG(LogStockholm, Error, TEXT("Enhanced Input not configured (check DefaultInput.ini)."));
		return;
	}
	Input->BindAction(Cfg->Move, ETriggerEvent::Triggered, this, &AStockholmCharacter::Move);
	Input->BindAction(Cfg->Look, ETriggerEvent::Triggered, this, &AStockholmCharacter::Look);
	Input->BindAction(Cfg->Jump, ETriggerEvent::Started, this, &ACharacter::Jump);
	Input->BindAction(Cfg->Jump, ETriggerEvent::Completed, this, &ACharacter::StopJumping);
	Input->BindAction(Cfg->Sprint, ETriggerEvent::Started, this, &AStockholmCharacter::SprintStarted);
	Input->BindAction(Cfg->Sprint, ETriggerEvent::Completed, this, &AStockholmCharacter::SprintEnded);
	Input->BindAction(Cfg->Interact, ETriggerEvent::Started, this, &AStockholmCharacter::InteractPressed);
}

bool AStockholmCharacter::InputBlocked() const
{
	const AStockholmPlayerController* PC = Cast<AStockholmPlayerController>(GetController());
	return PC && PC->IsGameplayInputBlocked();
}

void AStockholmCharacter::Move(const FInputActionValue& Value)
{
	if (InputBlocked() || !Controller)
	{
		return;
	}
	const FVector2D Axis = Value.Get<FVector2D>();
	const FRotator Yaw(0.f, Controller->GetControlRotation().Yaw, 0.f);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::X), Axis.Y);
	AddMovementInput(FRotationMatrix(Yaw).GetUnitAxis(EAxis::Y), Axis.X);
}

void AStockholmCharacter::Look(const FInputActionValue& Value)
{
	if (InputBlocked())
	{
		return;
	}
	const FVector2D Axis = Value.Get<FVector2D>();
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

void AStockholmCharacter::SprintStarted(const FInputActionValue&) { bSprinting = true; }
void AStockholmCharacter::SprintEnded(const FInputActionValue&) { bSprinting = false; }

void AStockholmCharacter::InteractPressed(const FInputActionValue&)
{
	if (!InputBlocked())
	{
		Interaction->TryInteract();
	}
}

void AStockholmCharacter::EnterVehicleState(AActor* Vehicle)
{
	SetActorHiddenInGame(true);
	SetActorEnableCollision(false);
	GetCharacterMovement()->DisableMovement();
	AttachToActor(Vehicle, FAttachmentTransformRules::SnapToTargetNotIncludingScale);
}

void AStockholmCharacter::ExitVehicleState(const FVector& ExitLocation, const FRotator& ExitRotation)
{
	DetachFromActor(FDetachmentTransformRules::KeepWorldTransform);
	SetActorLocationAndRotation(ExitLocation, FRotator(0.f, ExitRotation.Yaw, 0.f), false, nullptr, ETeleportType::TeleportPhysics);
	SetActorHiddenInGame(false);
	SetActorEnableCollision(true);
	GetCharacterMovement()->SetMovementMode(MOVE_Walking);
}
