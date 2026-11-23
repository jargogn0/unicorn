#include "Vehicles/StockholmVehicle.h"

#include "Core/StockholmSimSubsystem.h"
#include "Player/StockholmCharacter.h"
#include "Player/StockholmInputConfig.h"
#include "Player/StockholmPlayerController.h"
#include "Stockholm.h"

#include "Camera/CameraComponent.h"
#include "ChaosWheeledVehicleMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EnhancedInputComponent.h"
#include "Engine/World.h"
#include "GameFramework/SpringArmComponent.h"
#include "InputActionValue.h"

UStockholmFrontWheel::UStockholmFrontWheel()
{
	AxleType = EAxleType::Front;
	WheelRadius = 33.f;
	WheelWidth = 21.f;
	bAffectedBySteering = true;
	MaxSteerAngle = 36.f;
	bAffectedByEngine = true;
	bAffectedByHandbrake = false;
	bAffectedByBrake = true;
	MaxBrakeTorque = 2200.f;
	FrictionForceMultiplier = 3.0f;
	CorneringStiffness = 900.f;
	SuspensionMaxRaise = 9.f;
	SuspensionMaxDrop = 11.f;
	SpringRate = 220.f;
}

UStockholmRearWheel::UStockholmRearWheel()
{
	AxleType = EAxleType::Rear;
	WheelRadius = 33.f;
	WheelWidth = 21.f;
	bAffectedBySteering = false;
	bAffectedByEngine = false;
	bAffectedByHandbrake = true;
	bAffectedByBrake = true;
	MaxBrakeTorque = 1600.f;
	MaxHandBrakeTorque = 3200.f;
	FrictionForceMultiplier = 3.0f;
	CorneringStiffness = 900.f;
	SuspensionMaxRaise = 9.f;
	SuspensionMaxDrop = 11.f;
	SpringRate = 200.f;
}

AStockholmVehicle::AStockholmVehicle()
{
	PrimaryActorTick.bCanEverTick = true;

	UChaosWheeledVehicleMovementComponent* Move = CastChecked<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
	Move->ChassisHeight = 140.f;
	Move->DragCoefficient = 0.32f;
	Move->Mass = 1550.f;
	Move->WheelSetups.SetNum(4);
	for (int32 i = 0; i < 4; ++i)
	{
		Move->WheelSetups[i].WheelClass = i < 2 ? UStockholmFrontWheel::StaticClass() : UStockholmRearWheel::StaticClass();
		Move->WheelSetups[i].BoneName = WheelBoneNames.IsValidIndex(i) ? WheelBoneNames[i] : NAME_None;
	}
	// 2.4 L five-cylinder-ish torque curve (normalised), automatic gearbox.
	Move->EngineSetup.MaxTorque = 320.f;
	Move->EngineSetup.MaxRPM = 6200.f;
	Move->EngineSetup.EngineIdleRPM = 850.f;
	Move->EngineSetup.EngineBrakeEffect = 0.12f;
	Move->EngineSetup.TorqueCurve.GetRichCurve()->Reset();
	Move->EngineSetup.TorqueCurve.GetRichCurve()->AddKey(0.f, 0.55f);
	Move->EngineSetup.TorqueCurve.GetRichCurve()->AddKey(2200.f, 0.95f);
	Move->EngineSetup.TorqueCurve.GetRichCurve()->AddKey(4500.f, 1.0f);
	Move->EngineSetup.TorqueCurve.GetRichCurve()->AddKey(6200.f, 0.75f);
	Move->TransmissionSetup.bUseAutomaticGears = true;
	Move->TransmissionSetup.bUseAutoReverse = true;
	Move->TransmissionSetup.ChangeUpRPM = 4800.f;
	Move->TransmissionSetup.ChangeDownRPM = 1800.f;
	Move->DifferentialSetup.DifferentialType = EVehicleDifferential::FrontWheelDrive;
	Move->SteeringSetup.SteeringType = ESteeringType::AngleRatio;

	CameraBoom = CreateDefaultSubobject<USpringArmComponent>(TEXT("CameraBoom"));
	CameraBoom->SetupAttachment(GetMesh());
	CameraBoom->TargetArmLength = 620.f;
	CameraBoom->SocketOffset = FVector(0.f, 0.f, 150.f);
	CameraBoom->bUsePawnControlRotation = true;
	CameraBoom->bEnableCameraLag = true;
	CameraBoom->bEnableCameraRotationLag = true;
	CameraBoom->CameraLagSpeed = 8.f;
	CameraBoom->CameraRotationLagSpeed = 6.f;
	CameraBoom->bInheritRoll = false;

	ChaseCamera = CreateDefaultSubobject<UCameraComponent>(TEXT("ChaseCamera"));
	ChaseCamera->SetupAttachment(CameraBoom, USpringArmComponent::SocketName);
	ChaseCamera->SetFieldOfView(86.f);

	// UE5 Vehicle template sedan (add the Vehicle content pack) until licensed cars are integrated.
	DefaultMesh = TSoftObjectPtr<USkeletalMesh>(FSoftObjectPath(TEXT("/Game/VehicleTemplate/Blueprints/SportsCar/SKM_SportsCar.SKM_SportsCar")));
	DefaultAnimClass = TSoftClassPtr<UAnimInstance>(FSoftObjectPath(TEXT("/Game/VehicleTemplate/Blueprints/SportsCar/ABP_SportsCar.ABP_SportsCar_C")));
	AutoPossessPlayer = EAutoReceiveInput::Disabled;
}

void AStockholmVehicle::BeginPlay()
{
	Super::BeginPlay();
	if (!GetMesh()->GetSkeletalMeshAsset())
	{
		if (USkeletalMesh* Mesh = DefaultMesh.LoadSynchronous())
		{
			GetMesh()->SetSkeletalMeshAsset(Mesh);
			if (UClass* Anim = DefaultAnimClass.LoadSynchronous())
			{
				GetMesh()->SetAnimInstanceClass(Anim);
			}
		}
		else
		{
			UE_LOG(LogStockholm, Warning, TEXT("Vehicle %s has no mesh (%s missing). It will not be drivable."), *GetName(), *DefaultMesh.ToString());
		}
	}
	GetMesh()->SetSimulatePhysics(true);
}

void AStockholmVehicle::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	GripTimer -= DeltaSeconds;
	if (GripTimer <= 0.f)
	{
		GripTimer = 1.f;
		UpdateGrip();
	}
}

void AStockholmVehicle::UpdateGrip()
{
	const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
	UChaosWheeledVehicleMovementComponent* Move = Cast<UChaosWheeledVehicleMovementComponent>(GetVehicleMovement());
	if (!Sim || !Move)
	{
		return;
	}
	const auto& W = Sim->Sim().Clock().Weather();
	const float Snow = FMath::Clamp(static_cast<float>(W.snowCover), 0.f, 1.f);
	const float Wet = FMath::Clamp(static_cast<float>(W.wetness), 0.f, 1.f);
	const float Friction = DryFriction * FMath::Lerp(1.f, SnowFrictionScale, Snow) * FMath::Lerp(1.f, WetFrictionScale, Wet * (1.f - Snow));
	for (int32 i = 0; i < Move->WheelSetups.Num(); ++i)
	{
		Move->SetWheelFrictionMultiplier(i, Friction);
	}
}

float AStockholmVehicle::GetSpeedKmh() const
{
	return GetVehicleMovement() ? GetVehicleMovement()->GetForwardSpeed() * 0.036f : 0.f;
}

void AStockholmVehicle::SetupPlayerInputComponent(UInputComponent* PlayerInputComponent)
{
	Super::SetupPlayerInputComponent(PlayerInputComponent);
	UEnhancedInputComponent* Input = Cast<UEnhancedInputComponent>(PlayerInputComponent);
	const AStockholmPlayerController* PC = Cast<AStockholmPlayerController>(GetController());
	const UStockholmInputConfig* Cfg = PC ? PC->GetInputConfig() : nullptr;
	if (!Input || !Cfg)
	{
		return;
	}
	Input->BindAction(Cfg->Throttle, ETriggerEvent::Triggered, this, &AStockholmVehicle::Throttle);
	Input->BindAction(Cfg->Throttle, ETriggerEvent::Completed, this, &AStockholmVehicle::ZeroThrottle);
	Input->BindAction(Cfg->Brake, ETriggerEvent::Triggered, this, &AStockholmVehicle::Brake);
	Input->BindAction(Cfg->Brake, ETriggerEvent::Completed, this, &AStockholmVehicle::ZeroBrake);
	Input->BindAction(Cfg->Steer, ETriggerEvent::Triggered, this, &AStockholmVehicle::Steer);
	Input->BindAction(Cfg->Steer, ETriggerEvent::Completed, this, &AStockholmVehicle::ZeroSteer);
	Input->BindAction(Cfg->Handbrake, ETriggerEvent::Started, this, &AStockholmVehicle::HandbrakeOn);
	Input->BindAction(Cfg->Handbrake, ETriggerEvent::Completed, this, &AStockholmVehicle::HandbrakeOff);
	Input->BindAction(Cfg->Look, ETriggerEvent::Triggered, this, &AStockholmVehicle::Look);
	Input->BindAction(Cfg->ExitVehicle, ETriggerEvent::Started, this, &AStockholmVehicle::ExitPressed);
}

void AStockholmVehicle::Throttle(const FInputActionValue& V) { GetVehicleMovementComponent()->SetThrottleInput(V.Get<float>()); }
void AStockholmVehicle::Brake(const FInputActionValue& V) { GetVehicleMovementComponent()->SetBrakeInput(V.Get<float>()); }
void AStockholmVehicle::Steer(const FInputActionValue& V) { GetVehicleMovementComponent()->SetSteeringInput(V.Get<float>()); }
void AStockholmVehicle::ZeroThrottle(const FInputActionValue&) { GetVehicleMovementComponent()->SetThrottleInput(0.f); }
void AStockholmVehicle::ZeroBrake(const FInputActionValue&) { GetVehicleMovementComponent()->SetBrakeInput(0.f); }
void AStockholmVehicle::ZeroSteer(const FInputActionValue&) { GetVehicleMovementComponent()->SetSteeringInput(0.f); }
void AStockholmVehicle::HandbrakeOn(const FInputActionValue&) { GetVehicleMovementComponent()->SetHandbrakeInput(true); }
void AStockholmVehicle::HandbrakeOff(const FInputActionValue&) { GetVehicleMovementComponent()->SetHandbrakeInput(false); }

void AStockholmVehicle::Look(const FInputActionValue& V)
{
	const FVector2D Axis = V.Get<FVector2D>();
	AddControllerYawInput(Axis.X);
	AddControllerPitchInput(Axis.Y);
}

void AStockholmVehicle::ExitPressed(const FInputActionValue&)
{
	if (GetSpeedKmh() < 8.f)
	{
		ExitVehicle();
	}
}

FText AStockholmVehicle::GetInteractionPrompt_Implementation(APawn* Instigator) const
{
	if (Driver.IsValid() || !Instigator || !Instigator->IsA<AStockholmCharacter>() || !GetMesh()->GetSkeletalMeshAsset())
	{
		return FText::GetEmpty();
	}
	if (!RequiredFact.IsEmpty())
	{
		const UStockholmSimSubsystem* Sim = UStockholmSimSubsystem::Get(this);
		if (!Sim || Sim->Sim().Fact(StockholmConv::ToStd(RequiredFact)) == 0.0)
		{
			return FText::GetEmpty();
		}
	}
	return FText::Format(NSLOCTEXT("Stockholm", "DriveVehicle", "Drive {0}"), DisplayName);
}

void AStockholmVehicle::Interact_Implementation(APawn* Instigator)
{
	EnterVehicle(Cast<AStockholmCharacter>(Instigator));
}

void AStockholmVehicle::EnterVehicle(AStockholmCharacter* InDriver)
{
	if (!InDriver || Driver.IsValid())
	{
		return;
	}
	AController* C = InDriver->GetController();
	if (!C)
	{
		return;
	}
	Driver = InDriver;
	InDriver->EnterVehicleState(this);
	C->Possess(this);
	SetControlRotationOnPossess(C);
}

void AStockholmVehicle::SetControlRotationOnPossess(AController* C)
{
	if (C)
	{
		C->SetControlRotation(GetActorRotation());
	}
}

bool AStockholmVehicle::FindExitLocation(FVector& Out) const
{
	// Try driver side, passenger side, then behind the car.
	const FVector Candidates[] = {-GetActorRightVector() * 160.f, GetActorRightVector() * 160.f, -GetActorForwardVector() * 320.f};
	for (const FVector& Offset : Candidates)
	{
		const FVector Test = GetActorLocation() + Offset + FVector(0.f, 0.f, 60.f);
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(VehicleExit), false, this);
		const bool bBlocked = GetWorld()->SweepSingleByChannel(Hit, Test, Test + FVector(0, 0, 1), FQuat::Identity, ECC_Pawn,
			FCollisionShape::MakeCapsule(38.f, 90.f), Params);
		if (!bBlocked)
		{
			Out = Test;
			return true;
		}
	}
	return false;
}

void AStockholmVehicle::ExitVehicle()
{
	AStockholmCharacter* D = Driver.Get();
	AController* C = GetController();
	if (!D || !C)
	{
		return;
	}
	FVector ExitLocation;
	if (!FindExitLocation(ExitLocation))
	{
		return; // boxed in: stay seated
	}
	GetVehicleMovementComponent()->SetThrottleInput(0.f);
	GetVehicleMovementComponent()->SetHandbrakeInput(true);
	C->UnPossess();
	D->ExitVehicleState(ExitLocation, GetActorRotation());
	C->Possess(D);
	Driver.Reset();
}
