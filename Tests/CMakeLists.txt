# Standalone build of the engine-independent STOCKHOLM simulation core.
# Mirrors Unreal's compile constraints: no exceptions, no RTTI, warnings as errors.
cmake_minimum_required(VERSION 3.16)
project(StockholmSimTests CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(SIM_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/../Stockholm/Source/StockholmSim)

file(GLOB SIM_SOURCES ${SIM_ROOT}/Private/Sim/*.cpp)
add_library(stockholm_sim STATIC ${SIM_SOURCES})
target_include_directories(stockholm_sim PUBLIC ${SIM_ROOT}/Public)

set(STRICT_FLAGS -Wall -Wextra -Wshadow -Wconversion -Wno-sign-conversion -Werror -fno-exceptions -fno-rtti)
target_compile_options(stockholm_sim PRIVATE ${STRICT_FLAGS})

add_executable(sim_tests sim_tests.cpp)
target_link_libraries(sim_tests PRIVATE stockholm_sim)
target_compile_options(sim_tests PRIVATE -Wall -Wextra -Werror -fno-exceptions -fno-rtti)
target_compile_definitions(sim_tests PRIVATE STOCKHOLM_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../Stockholm/Content/Data" STOCKHOLM_FIXTURE_DIR="${CMAKE_CURRENT_SOURCE_DIR}/fixtures")

add_executable(sim_playthrough playthrough.cpp)
target_link_libraries(sim_playthrough PRIVATE stockholm_sim)
target_compile_definitions(sim_playthrough PRIVATE STOCKHOLM_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/../Stockholm/Content/Data")

enable_testing()
add_test(NAME sim_tests COMMAND sim_tests)
