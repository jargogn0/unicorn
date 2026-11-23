#pragma once

#include "CoreMinimal.h"
#include "WheeledVehiclePawn.h"
#include "ChaosVehicleWheel.h"
#include "Player/StockholmInteractable.h"
#include "StockholmVehicle.generated.h"

class UCameraComponent;
class USpringArmComponent;
class AStockholmCharacter;
struct FInputActionValue;

UCLASS()
class STOCKHOLM_API UStockholmFrontWheel : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UStockholmFrontWheel();
};

UCLASS()
class STOCKHOLM_API UStockholmRearWheel : public UChaosVehicleWheel
{
	GENERATED_BODY()
public:
	UStockholmRearWheel();
};

/**
 * Drivable car (Chaos Vehicles). Tuned as a 2000s Swedish estate on winter
 * tyres: front-wheel drive, soft suspension, grip scaled by road snow/wetness.
 * The skeletal mesh + physics asset must come from a licensed vehicle asset
 * whose wheel bones match WheelBoneNames (default: UE vehicle template names).
 */
UCLASS()
class STOCKHOLM_API AStockholmVehicle : public AWheeledVehiclePawn, public IStockholmInteractable
{
	GENERATED_BODY()

public:
	AStockholmVehicle();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	// IStockholmInteractable
	virtual FText GetInteractionPrompt_Implementation(APawn* Instigator) const override;
	virtual void Interact_Implementation(APawn* Instigator) override;

	UFUNCTION(BlueprintCallable, Category = "Vehicle") void EnterVehicle(AStockholmCharacter* Driver);
	UFUNCTION(BlueprintCallable, Category = "Vehicle") void ExitVehicle();

	/** Stable id for missions/saves, e.g. "sami_volvo". */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vehicle") FName VehicleId;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vehicle") FText DisplayName = NSLOCTEXT("Stockholm", "Car", "car");
	/** Mission-locked vehicles can only be entered when the player has permission (e.g. after Sami hands over keys). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Vehicle") FString RequiredFact;

	UPROPERTY(EditAnywhere, Category = "Vehicle") TArray<FName> WheelBoneNames = {TEXT("Phys_Wheel_FL"), TEXT("Phys_Wheel_FR"), TEXT("Phys_Wheel_BL"), TEXT("Phys_Wheel_BR")};
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle") TSoftObjectPtr<USkeletalMesh> DefaultMesh;
	UPROPERTY(EditDefaultsOnly, Category = "Vehicle") TSoftClassPtr<UAnimInstance> DefaultAnimClass;
	/** Dry-asphalt friction multiplier; snow/wet scale it down. */
	UPROPERTY(EditAnywhere, Category = "Vehicle|Grip") float DryFriction = 3.0f;
	UPROPERTY(EditAnywhere, Category = "Vehicle|Grip") float SnowFrictionScale = 0.55f;
	UPROPERTY(EditAnywhere, Category = "Vehicle|Grip") float WetFrictionScale = 0.85f;

	UFUNCTION(BlueprintPure, Category = "Vehicle") float GetSpeedKmh() const;
	AStockholmCharacter* GetDriver() const { return Driver.Get(); }

protected:
	void Throttle(const FInputActionValue& V);
	void Brake(const FInputActionValue& V);
	void Steer(const FInputActionValue& V);
	void HandbrakeOn(const FInputActionValue& V);
	void HandbrakeOff(const FInputActionValue& V);
	void Look(const FInputActionValue& V);
	void ExitPressed(const FInputActionValue& V);
	void ZeroThrottle(const FInputActionValue& V);
	void ZeroBrake(const FInputActionValue& V);
	void ZeroSteer(const FInputActionValue& V);

	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, Category = "Camera") TObjectPtr<UCameraComponent> ChaseCamera;

private:
	void UpdateGrip();
	bool FindExitLocation(FVector& Out) const;
	void SetControlRotationOnPossess(AController* C);
	TWeakObjectPtr<AStockholmCharacter> Driver;
	float GripTimer = 0.f;
};
