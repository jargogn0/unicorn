// STOCKHOLM — game module.
#pragma once

#include "CoreMinimal.h"

#include <string>

DECLARE_LOG_CATEGORY_EXTERN(LogStockholm, Log, All);

namespace StockholmConv
{
	inline FString ToF(const std::string& S) { return FString(UTF8_TO_TCHAR(S.c_str())); }
	inline std::string ToStd(const FString& S) { return std::string(TCHAR_TO_UTF8(*S)); }
	inline FName ToName(const std::string& S) { return FName(UTF8_TO_TCHAR(S.c_str())); }
}
