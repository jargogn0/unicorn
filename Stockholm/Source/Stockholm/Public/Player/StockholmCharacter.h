#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "StockholmCharacter.generated.h"

class UCameraComponent;
class USpringArmComponent;
class UInteractionComponent;
class UStockholmInputConfig;
struct FInputActionValue;

/**
 * The founder on foot: third-person camera, jog/sprint locomotion, interaction.
 * Mesh/animation come from SkeletalMesh/AnimClass (defaults point at the UE5
 * Third Person template mannequin until MetaHuman founders are authored).
 */
UCLASS()
class STOCKHOLM_API AStockholmCharacter : public ACharacter
{
	GENERATED_BODY()

public:
	AStockholmCharacter();

	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;
	virtual void SetupPlayerInputComponent(UInputComponent* PlayerInputComponent) override;

	UFUNCTION(BlueprintPure, Category = "Stockholm") UInteractionComponent* GetInteraction() const { return Interaction; }

	/** Hidden while driving: vehicles possess the controller and attach the character. */
	void EnterVehicleState(AActor* Vehicle);
	void ExitVehicleState(const FVector& ExitLocation, const FRotator& ExitRotation);

	UPROPERTY(EditAnywhere, Category = "Locomotion") float WalkSpeed = 170.f;
	UPROPERTY(EditAnywhere, Category = "Locomotion") float JogSpeed = 420.f;
	UPROPERTY(EditAnywhere, Category = "Locomotion") float SprintSpeed = 640.f;
	/** Reduced grip and speed on packed snow (from weather snow cover). */
	UPROPERTY(EditAnywhere, Category = "Locomotion") float SnowSpeedFactor = 0.88f;

	UPROPERTY(EditDefaultsOnly, Category = "Appearance") TSoftObjectPtr<USkeletalMesh> DefaultMesh;
	UPROPERTY(EditDefaultsOnly, Category = "Appearance") TSoftClassPtr<UAnimInstance> DefaultAnimClass;

protected:
	void Move(const FInputActionValue& Value);
	void Look(const FInputActionValue& Value);
	void SprintStarted(const FInputActionValue& Value);
	void SprintEnded(const FInputActionValue& Value);
	void InteractPressed(const FInputActionValue& Value);

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera") TObjectPtr<USpringArmComponent> CameraBoom;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Camera") TObjectPtr<UCameraComponent> FollowCamera;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Interaction") TObjectPtr<UInteractionComponent> Interaction;

private:
	bool bSprinting = false;
	bool InputBlocked() const;
};
