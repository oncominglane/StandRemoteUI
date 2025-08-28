cmake_minimum_required(VERSION 3.16)
project(GUI_Marathon LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Пути к PCAN
set(PCAN_INCLUDE "${CMAKE_SOURCE_DIR}/Stand_Marathon/Include")
# ВАЖНО: у тебя .lib лежит в подпапке VC_LIB
set(PCAN_LIB_DIR "${CMAKE_SOURCE_DIR}/Stand_Marathon/lib/x64/VC_LIB")

# Зависимости через vcpkg
find_package(Boost REQUIRED COMPONENTS system thread)
find_package(nlohmann_json CONFIG REQUIRED)

# Подключаем CAN_DBC_MODULE (правильный относительный путь)
add_subdirectory(Stand_Marathon/Include/CAN_DBC_MODULE)

# Источники ядра
set(CORE_SOURCES
    Stand_Marathon/src/CANInterface.cpp
    Stand_Marathon/src/CommandSender.cpp
    Stand_Marathon/src/ConfigManager.cpp
    Stand_Marathon/src/MarathonLogic.cpp
    Stand_Marathon/src/StateMachine.cpp
)

# Экзешник с WS
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

# Для Windows добавим системные сокеты (на всякий случай)
if (WIN32)
  target_link_libraries(MarathonWS PRIVATE ws2_32)
endif()


# Выбираем корректную x64 DLL PCANBasic и копируем рядом с exe
# Сначала пробуем DLL из репозитория, если нет — из установленного PCAN-Basic
if(CMAKE_SIZEOF_VOID_P EQUAL 8) # x64 сборка
    if(EXISTS ${CMAKE_SOURCE_DIR}/Stand_Marathon/lib/x64/PCANBasic.dll)
        set(PCANBASIC_DLL ${CMAKE_SOURCE_DIR}/Stand_Marathon/lib/x64/PCANBasic.dll)
    elseif(EXISTS "C:/Program Files/PEAK-System/PCAN-Basic/Win64/PCANBasic.dll")
        set(PCANBASIC_DLL "C:/Program Files/PEAK-System/PCAN-Basic/Win64/PCANBasic.dll")
    else()
        message(FATAL_ERROR "PCANBasic.dll (x64) not найден. Укажи правильный путь.")
    endif()
else() # на всякий случай для x86
    if(EXISTS "C:/Users/n.tulupov/Desktop/StandRemoteUI/server/Stand_Marathon/lib/x86/PCANBasic.dll")
        set(PCANBASIC_DLL "C:/Users/n.tulupov/Desktop/StandRemoteUI/server/Stand_Marathon/lib/x86/PCANBasic.dll")
    elseif(EXISTS "C:/Program Files (x86)/PEAK-System/PCAN-Basic/Win32/PCANBasic.dll")
        set(PCANBASIC_DLL "C:/Program Files (x86)/PEAK-System/PCAN-Basic/Win32/PCANBasic.dll")
    else()
        message(FATAL_ERROR "PCANBasic.dll (x86) not найден. Укажи правильный путь.")
    endif()
endif()

add_custom_command(TARGET MarathonWS POST_BUILD
  COMMAND "${CMAKE_COMMAND}" -E copy_if_different
          "${PCANBASIC_DLL}"
          "$<TARGET_FILE_DIR:MarathonWS>/PCANBasic.dll")    
