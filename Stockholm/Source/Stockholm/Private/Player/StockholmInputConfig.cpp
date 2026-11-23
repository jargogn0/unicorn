#include "Player/StockholmInputConfig.h"

#include "InputAction.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "InputTriggers.h"

namespace StockholmInputDetail
{
	UInputAction* MakeAction(UObject* Outer, const TCHAR* Name, EInputActionValueType Type)
	{
		UInputAction* A = NewObject<UInputAction>(Outer, FName(Name));
		A->ValueType = Type;
		return A;
	}

	// Maps a 1D key onto one axis of a 2D action: Swizzle moves X→Y, Negate flips.
	void Map2D(UInputMappingContext* Ctx, UInputAction* Action, const FKey& Key, bool bToY, bool bNegate)
	{
		FEnhancedActionKeyMapping& M = Ctx->MapKey(Action, Key);
		if (bToY)
		{
			UInputModifierSwizzleAxis* Swizzle = NewObject<UInputModifierSwizzleAxis>(Ctx);
			Swizzle->Order = EInputAxisSwizzle::YXZ;
			M.Modifiers.Add(Swizzle);
		}
		if (bNegate)
		{
			M.Modifiers.Add(NewObject<UInputModifierNegate>(Ctx));
		}
	}

	void MapWithDeadZone(UInputMappingContext* Ctx, UInputAction* Action, const FKey& Key)
	{
		FEnhancedActionKeyMapping& M = Ctx->MapKey(Action, Key);
		M.Modifiers.Add(NewObject<UInputModifierDeadZone>(Ctx));
	}
}

UStockholmInputConfig* UStockholmInputConfig::Build(UObject* Outer)
{
	using namespace StockholmInputDetail;
	UStockholmInputConfig* C = NewObject<UStockholmInputConfig>(Outer);

	C->Move = MakeAction(C, TEXT("IA_Move"), EInputActionValueType::Axis2D);
	C->Look = MakeAction(C, TEXT("IA_Look"), EInputActionValueType::Axis2D);
	C->Jump = MakeAction(C, TEXT("IA_Jump"), EInputActionValueType::Boolean);
	C->Sprint = MakeAction(C, TEXT("IA_Sprint"), EInputActionValueType::Boolean);
	C->Interact = MakeAction(C, TEXT("IA_Interact"), EInputActionValueType::Boolean);
	C->Throttle = MakeAction(C, TEXT("IA_Throttle"), EInputActionValueType::Axis1D);
	C->Brake = MakeAction(C, TEXT("IA_Brake"), EInputActionValueType::Axis1D);
	C->Steer = MakeAction(C, TEXT("IA_Steer"), EInputActionValueType::Axis1D);
	C->Handbrake = MakeAction(C, TEXT("IA_Handbrake"), EInputActionValueType::Boolean);
	C->ExitVehicle = MakeAction(C, TEXT("IA_ExitVehicle"), EInputActionValueType::Boolean);
	C->Phone = MakeAction(C, TEXT("IA_Phone"), EInputActionValueType::Boolean);
	C->FounderMap = MakeAction(C, TEXT("IA_FounderMap"), EInputActionValueType::Boolean);
	C->DialogueNext = MakeAction(C, TEXT("IA_DialogueNext"), EInputActionValueType::Boolean);
	C->Choice1 = MakeAction(C, TEXT("IA_Choice1"), EInputActionValueType::Boolean);
	C->Choice2 = MakeAction(C, TEXT("IA_Choice2"), EInputActionValueType::Boolean);
	C->Choice3 = MakeAction(C, TEXT("IA_Choice3"), EInputActionValueType::Boolean);
	C->Choice4 = MakeAction(C, TEXT("IA_Choice4"), EInputActionValueType::Boolean);
	C->QuickSave = MakeAction(C, TEXT("IA_QuickSave"), EInputActionValueType::Boolean);

	// ---- On foot: WASD / left stick, mouse / right stick ----------------------
	UInputMappingContext* Foot = NewObject<UInputMappingContext>(C, TEXT("IMC_OnFoot"));
	Map2D(Foot, C->Move, EKeys::W, true, false);
	Map2D(Foot, C->Move, EKeys::S, true, true);
	Map2D(Foot, C->Move, EKeys::D, false, false);
	Map2D(Foot, C->Move, EKeys::A, false, true);
	MapWithDeadZone(Foot, C->Move, EKeys::Gamepad_Left2D);
	{
		FEnhancedActionKeyMapping& M = Foot->MapKey(C->Look, EKeys::Mouse2D);
		UInputModifierNegate* NegY = NewObject<UInputModifierNegate>(Foot);
		NegY->bX = false; NegY->bY = true; NegY->bZ = false;
		M.Modifiers.Add(NegY);
	}
	MapWithDeadZone(Foot, C->Look, EKeys::Gamepad_Right2D);
	Foot->MapKey(C->Jump, EKeys::SpaceBar);
	Foot->MapKey(C->Jump, EKeys::Gamepad_FaceButton_Bottom);
	Foot->MapKey(C->Sprint, EKeys::LeftShift);
	Foot->MapKey(C->Sprint, EKeys::Gamepad_LeftThumbstick);
	Foot->MapKey(C->Interact, EKeys::E);
	Foot->MapKey(C->Interact, EKeys::Gamepad_FaceButton_Left);
	C->OnFootContext = Foot;

	// ---- Vehicle: W/S throttle-brake, A/D steer, triggers on gamepad ----------
	UInputMappingContext* Car = NewObject<UInputMappingContext>(C, TEXT("IMC_Vehicle"));
	Car->MapKey(C->Throttle, EKeys::W);
	Car->MapKey(C->Throttle, EKeys::Gamepad_RightTriggerAxis);
	Car->MapKey(C->Brake, EKeys::S);
	Car->MapKey(C->Brake, EKeys::Gamepad_LeftTriggerAxis);
	Car->MapKey(C->Steer, EKeys::D);
	{
		FEnhancedActionKeyMapping& M = Car->MapKey(C->Steer, EKeys::A);
		M.Modifiers.Add(NewObject<UInputModifierNegate>(Car));
	}
	MapWithDeadZone(Car, C->Steer, EKeys::Gamepad_LeftX);
	Car->MapKey(C->Handbrake, EKeys::SpaceBar);
	Car->MapKey(C->Handbrake, EKeys::Gamepad_FaceButton_Right);
	Car->MapKey(C->ExitVehicle, EKeys::F);
	Car->MapKey(C->ExitVehicle, EKeys::Gamepad_FaceButton_Top);
	{
		FEnhancedActionKeyMapping& M = Car->MapKey(C->Look, EKeys::Mouse2D);
		UInputModifierNegate* NegY = NewObject<UInputModifierNegate>(Car);
		NegY->bX = false; NegY->bY = true; NegY->bZ = false;
		M.Modifiers.Add(NegY);
	}
	MapWithDeadZone(Car, C->Look, EKeys::Gamepad_Right2D);
	C->VehicleContext = Car;

	// ---- Shared: phone, Founder Map, dialogue --------------------------------
	UInputMappingContext* Shared = NewObject<UInputMappingContext>(C, TEXT("IMC_Shared"));
	Shared->MapKey(C->Phone, EKeys::Tab);
	Shared->MapKey(C->Phone, EKeys::Gamepad_DPad_Up);
	Shared->MapKey(C->FounderMap, EKeys::M);
	Shared->MapKey(C->FounderMap, EKeys::Gamepad_Special_Right);
	Shared->MapKey(C->DialogueNext, EKeys::Enter);
	Shared->MapKey(C->DialogueNext, EKeys::LeftMouseButton);
	Shared->MapKey(C->DialogueNext, EKeys::Gamepad_FaceButton_Bottom);
	Shared->MapKey(C->Choice1, EKeys::One);
	Shared->MapKey(C->Choice1, EKeys::Gamepad_DPad_Left);
	Shared->MapKey(C->Choice2, EKeys::Two);
	Shared->MapKey(C->Choice2, EKeys::Gamepad_DPad_Down);
	Shared->MapKey(C->Choice3, EKeys::Three);
	Shared->MapKey(C->Choice3, EKeys::Gamepad_DPad_Right);
	Shared->MapKey(C->Choice4, EKeys::Four);
	Shared->MapKey(C->QuickSave, EKeys::F5);
	C->SharedContext = Shared;
	return C;
}
