#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "WorldAtmosphere.generated.h"

class UDirectionalLightComponent;
class USkyAtmosphereComponent;
class USkyLightComponent;
class UExponentialHeightFogComponent;
class UVolumetricCloudComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class UMaterialParameterCollection;

/**
 * Drives sun, moon, sky, fog, clouds, precipitation and street lighting from
 * the simulation clock: real solar position for Stockholm (59.33°N) so
 * January days are short and blue-hour long, plus the seasonal weather model.
 * Surface wetness / snow cover are pushed to MPC_Weather for materials.
 */
UCLASS()
class STOCKHOLM_API AWorldAtmosphere : public AActor
{
	GENERATED_BODY()

public:
	AWorldAtmosphere();
	virtual void BeginPlay() override;
	virtual void Tick(float DeltaSeconds) override;

	UPROPERTY(EditAnywhere, Category = "Atmosphere|Precipitation") TSoftObjectPtr<UNiagaraSystem> SnowSystem;
	UPROPERTY(EditAnywhere, Category = "Atmosphere|Precipitation") TSoftObjectPtr<UNiagaraSystem> RainSystem;
	UPROPERTY(EditAnywhere, Category = "Atmosphere|Surfaces") TSoftObjectPtr<UMaterialParameterCollection> WeatherParameters;

	UPROPERTY(EditAnywhere, Category = "Atmosphere|Street lights") int32 StreetLightPoolSize = 40;
	UPROPERTY(EditAnywhere, Category = "Atmosphere|Street lights") float StreetLightRadiusMetres = 160.f;
	UPROPERTY(EditAnywhere, Category = "Atmosphere|Street lights") float StreetLightSpacingMetres = 28.f;

	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<UDirectionalLightComponent> Sun;
	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<UDirectionalLightComponent> Moon;
	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<USkyAtmosphereComponent> Sky;
	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<USkyLightComponent> SkyLight;
	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<UExponentialHeightFogComponent> Fog;
	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<UVolumetricCloudComponent> Clouds;
	UPROPERTY(VisibleAnywhere, Category = "Atmosphere") TObjectPtr<UNiagaraComponent> Precipitation;

private:
	void UpdateSky();
	void UpdateWeather(float DeltaSeconds);
	void UpdateStreetLights();
	UPROPERTY() TArray<TObjectPtr<UPointLightComponent>> StreetLights;
	float StreetLightTimer = 0.f;
	int32 ActivePrecipitation = -1; // 0 snow, 1 rain
};
