cmake_minimum_required(VERSION 3.16)
project(GUI_Marathon LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Пути
set(PCAN_INCLUDE "${CMAKE_SOURCE_DIR}/Stand_Marathon/Include")
set(PCAN_LIB_DIR "${CMAKE_SOURCE_DIR}/Stand_Marathon/lib/x64")

# Boost + JSON
find_package(Boost REQUIRED COMPONENTS system thread)
find_package(nlohmann_json CONFIG REQUIRED)

# Подключаем CAN_DBC_MODULE
add_subdirectory(CAN_DBC_MODULE)
add_subdirectory(Stand_Marathon)

# Stand_Marathon
file(GLOB_RECURSE CORE_SOURCES "${CMAKE_SOURCE_DIR}/Stand_Marathon/src/*.cpp")

add_executable(Stand_Marathon ${CORE_SOURCES})

target_include_directories(Stand_Marathon PRIVATE
    ${PCAN_INCLUDE}
    ${CMAKE_SOURCE_DIR}/Stand_Marathon/src
)

target_link_directories(Stand_Marathon PRIVATE ${PCAN_LIB_DIR})
target_link_libraries(Stand_Marathon PRIVATE CAN_DBC_MODULE PCANBasic)

# MarathonWS
add_executable(MarathonWS ws_server.cpp ${CORE_SOURCES})

target_include_directories(MarathonWS PRIVATE
    ${PCAN_INCLUDE}
    ${CMAKE_SOURCE_DIR}/Stand_Marathon/src
)

target_link_directories(MarathonWS PRIVATE ${PCAN_LIB_DIR})
target_link_libraries(MarathonWS PRIVATE
    CAN_DBC_MODULE
    Boost::system Boost::thread
    nlohmann_json::nlohmann_json
    PCANBasic
)
