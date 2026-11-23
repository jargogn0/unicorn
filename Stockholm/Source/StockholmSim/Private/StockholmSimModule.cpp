// Unreal module shell for the engine-independent simulation core.
// Excluded from the standalone CMake build (Tests/CMakeLists.txt globs Private/Sim only).
#include "Modules/ModuleManager.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, StockholmSim);
