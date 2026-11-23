#include "World/WorldAtmosphere.h"

#include "Core/StockholmSimSubsystem.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/KismetMaterialLibrary.h"
#include "Materials/MaterialParameterCollection.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

#include "Sim/WorldClock.h"

using namespace stockholm::sim;

AWorldAtmosphere::AWorldAtmosphere()
{
	PrimaryActorTick.bCanEverTick = true;
	RootComponent = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));

	Sun = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Sun"));
	Sun->SetupAttachment(RootComponent);
	Sun->SetAtmosphereSunLight(true);
	Sun->SetAtmosphereSunLightIndex(0);
	Sun->SetIntensity(10.f);
	Sun->SetDynamicShadowCascades(4);
	Sun->bUseTemperature = true;
	Sun->Temperature = 5600.f;
	Sun->SetCastShadows(true);

	Moon = CreateDefaultSubobject<UDirectionalLightComponent>(TEXT("Moon"));
	Moon->SetupAttachment(RootComponent);
	Moon->SetAtmosphereSunLight(true);
	Moon->SetAtmosphereSunLightIndex(1);
	Moon->SetIntensity(0.08f);
	Moon->bUseTemperature = true;
	Moon->Temperature = 8500.f;
	Moon->SetCastShadows(false);

	Sky = CreateDefaultSubobject<USkyAtmosphereComponent>(TEXT("SkyAtmosphere"));
	Sky->SetupAttachment(RootComponent);

	SkyLight = CreateDefaultSubobject<USkyLightComponent>(TEXT("SkyLight"));
	SkyLight->SetupAttachment(RootComponent);
	SkyLight->bRealTimeCapture = true;
	SkyLight->SetMobility(EComponentMobility::Movable);

	Fog = CreateDefaultSubobject<UExponentialHeightFogComponent>(TEXT("HeightFog"));
	Fog->SetupAttachment(RootComponent);
	Fog->SetVolumetricFog(true);
	Fog->SetFogDensity(0.02f);
	Fog->SetFogHeightFalloff(0.2f);

	Clouds = CreateDefaultSubobject<UVolumetricCloudComponent>(TEXT("VolumetricClouds"));
	Clouds->SetupAttachment(RootComponent);

	Precipitation = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Precipitation"));
	Precipitation->SetupAttachment(RootComponent);
	Precipitation->SetAutoActivate(false);

	SnowSystem = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/City/FX/NS_Snowfall.NS_Snowfall")));
	RainSystem = TSoftObjectPtr<UNiagaraSystem>(FSoftObjectPath(TEXT("/Game/City/FX/NS_Rain.NS_Rain")));
	WeatherParameters = TSoftObjectPtr<UMaterialParameterCollection>(FSoftObjectPath(TEXT("/Game/City/Materials/MPC_Weather.MPC_Weather")));
}

void AWorldAtmosphere::BeginPlay()
{
	Super::BeginPlay();
	for (int32 i = 0; i < StreetLightPoolSize; ++i)
	{
		UPointLightComponent* L = NewObject<UPointLightComponent>(this);
		L->SetupAttachment(RootComponent);
		L->SetMobility(EComponentMobility::Movable);
		L->bUseTemperature = true;
		L->Temperature = 2700.f; // sodium-replacement warm white used along Stockholm streets
		L->SetIntensityUnits(ELightUnits::Candelas);
		L->SetIntensity(900.f);
		L->SetAttenuationRadius(2400.f);
		L->SetSourceRadius(20.f);
		L->SetCastShadows(false);
		L->SetVisibility(false);
		L->RegisterComponent();
		StreetLights.Add(L);
	}
	UpdateSky();
}

void AWorldAtmosphere::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);
	UpdateSky();
	UpdateWeather(DeltaSeconds);
	StreetLightTimer -= DeltaSeconds;
	if (StreetLightTimer <= 0.f)
	{
		StreetLightTimer = 1.5f;
		UpdateStreetLights();
	}
}

void AWorldAtmosphere::UpdateSky()
{
	const UStockholmSimSubsystem* SimSys = UStockholmSimSubsystem::Get(this);
	if (!SimSys)
	{
		return;
	}
	const SunPosition S = SimSys->Sim().Clock().Sun();
	// Directional light points FROM the sun: pitch = -elevation, yaw from azimuth.
	// World +X = east, -Y = north (GeoProjection), so azimuth 0 (north) → yaw -90.
	const float Yaw = static_cast<float>(S.azimuthDeg) - 90.f + 180.f;
	Sun->SetWorldRotation(FRotator(-static_cast<float>(S.elevationDeg), Yaw, 0.f));
	// Moon: simple opposite-ish placement until a lunar ephemeris is added.
	Moon->SetWorldRotation(FRotator(-FMath::Max(10.f, -static_cast<float>(S.elevationDeg) * 0.6f), Yaw + 180.f, 0.f));
	const float Day = FMath::Clamp(static_cast<float>(S.elevationDeg + 6.0) / 12.f, 0.f, 1.f);
	Moon->SetIntensity(FMath::Lerp(0.12f, 0.f, Day));
	// Low winter sun is warm; overcast dulls it.
	const auto& W = SimSys->Sim().Clock().Weather();
	Sun->SetIntensity(FMath::Lerp(10.f, 2.5f, static_cast<float>(W.cloudCover)) * FMath::Clamp(static_cast<float>(S.elevationDeg + 2.0) / 8.f, 0.f, 1.f));
	Sun->SetTemperature(FMath::Lerp(3600.f, 5800.f, FMath::Clamp(static_cast<float>(S.elevationDeg) / 30.f, 0.f, 1.f)));
}

void AWorldAtmosphere::UpdateWeather(float DeltaSeconds)
{
	UStockholmSimSubsystem* SimSys = UStockholmSimSubsystem::Get(this);
	if (!SimSys)
	{
		return;
	}
	const WeatherState& W = SimSys->Sim().Clock().Weather();
	const float Blend = FMath::Clamp(DeltaSeconds * 0.5f, 0.f, 1.f);
	const float TargetFog = 0.01f + static_cast<float>(W.fogDensity) * 0.12f + static_cast<float>(W.precipitation) * 0.03f;
	Fog->SetFogDensity(FMath::Lerp(Fog->FogDensity, TargetFog, Blend));

	// Keep the precipitation emitter on the camera.
	if (const APlayerController* PC = GetWorld()->GetFirstPlayerController())
	{
		if (PC->PlayerCameraManager)
		{
			Precipitation->SetWorldLocation(PC->PlayerCameraManager->GetCameraLocation() + FVector(0, 0, 800.f));
		}
	}
	const int32 Want = W.precipitation < 0.05 ? -1 : (W.precipIsSnow ? 0 : 1);
	if (Want != ActivePrecipitation)
	{
		ActivePrecipitation = Want;
		UNiagaraSystem* System = Want == 0 ? SnowSystem.LoadSynchronous() : (Want == 1 ? RainSystem.LoadSynchronous() : nullptr);
		if (System)
		{
			Precipitation->SetAsset(System);
			Precipitation->Activate(true);
		}
		else
		{
			Precipitation->Deactivate();
		}
	}
	if (ActivePrecipitation >= 0)
	{
		Precipitation->SetFloatParameter(TEXT("Intensity"), static_cast<float>(W.precipitation));
		Precipitation->SetFloatParameter(TEXT("Wind"), static_cast<float>(W.windMps));
	}
	if (UMaterialParameterCollection* MPC = WeatherParameters.LoadSynchronous())
	{
		UKismetMaterialLibrary::SetScalarParameterValue(this, MPC, TEXT("Wetness"), static_cast<float>(W.wetness));
		UKismetMaterialLibrary::SetScalarParameterValue(this, MPC, TEXT("SnowCover"), static_cast<float>(W.snowCover));
		UKismetMaterialLibrary::SetScalarParameterValue(this, MPC, TEXT("Precipitation"), static_cast<float>(W.precipitation));
	}
}

void AWorldAtmosphere::UpdateStreetLights()
{
	UStockholmSimSubsystem* SimSys = UStockholmSimSubsystem::Get(this);
	const APlayerController* PC = GetWorld()->GetFirstPlayerController();
	const APawn* Pawn = PC ? PC->GetPawn() : nullptr;
	if (!SimSys || !Pawn || !SimSys->HasCity())
	{
		return;
	}
	const bool bLit = SimSys->Sim().Clock().Sun().elevationDeg < 2.0 || SimSys->Sim().Clock().Weather().fogDensity > 0.5;
	int32 Used = 0;
	if (bLit)
	{
		// Place pooled lights on nearby road nodes, spaced out — a dense, warm
		// pool around the player rather than thousands of lights city-wide.
		const Vec2 P = SimSys->WorldToLocal(Pawn->GetActorLocation());
		const RoadGraph& Roads = SimSys->City().roads;
		TArray<Vec2> Placed;
		const float R2 = StreetLightRadiusMetres * StreetLightRadiusMetres;
		const float S2 = StreetLightSpacingMetres * StreetLightSpacingMetres;
		for (size_t i = 0; i < Roads.NodeCount() && Used < StreetLights.Num(); ++i)
		{
			const Vec2& N = Roads.Node(static_cast<uint32_t>(i)).pos;
			const double DX = N.x - P.x, DY = N.y - P.y;
			if (DX * DX + DY * DY > R2) continue;
			bool bTooClose = false;
			for (const Vec2& Q : Placed)
			{
				if ((N.x - Q.x) * (N.x - Q.x) + (N.y - Q.y) * (N.y - Q.y) < S2) { bTooClose = true; break; }
			}
			if (bTooClose) continue;
			Placed.Add(N);
			UPointLightComponent* L = StreetLights[Used++];
			L->SetWorldLocation(SimSys->LocalToWorld(N, 2.5 + 7.0));
			L->SetVisibility(true);
		}
	}
	for (int32 i = Used; i < StreetLights.Num(); ++i)
	{
		StreetLights[i]->SetVisibility(false);
	}
}
