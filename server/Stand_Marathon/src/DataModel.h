#pragma once
#include <cstdint>
#include <string>

struct DataModel {
    // === CAN настройки ===
    uint16_t canBoard = 0;
    uint16_t canChannel = 0;
    uint32_t canBaud = 0;
    uint32_t canFlags = 0;
    uint32_t amask = 0x00000000;
    uint32_t acode = 0x00000032;

    // === Управление ===
    bool Kl_15 = false;            // Зажигание
    bool En_rem = false;           // Удаленное управление
    bool En_Is = false;            // Управление током
    uint8_t Dampf_U = 0;           // Демпф. U
    bool Brake_active = false;     // Тормоз
    bool TCS_active = false;       // TCS
    uint8_t MotorCtrl = 0;         // Режим управления
    uint8_t GearCtrl = 0;          // Коробка передач
    // === Добавить в секцию "Управление" ===
    float M_desired = 0.0f;           // Желаемый момент (Nm)
    uint8_t SurgeDamperState = 0;     // Состояние демпфера
    uint8_t MCU_RequestedState = 0;   // MCU requested state


    // === Ограничения ===
    float M_max = 10.0f;           // [Нм]
    float M_min = -10.0f;          // [Нм]
    float M_grad_max = 4000.0f;    // [Нм/с]
    float dM_damp_Ctrl = 0.1f;     // Порог демпфирования
    float i_R = 9.78f;             // Передаточное число
    float n_max = 1000.0f;         // Макс. скорость [об/мин]
    float T_Str_max = 85.0f;       // Макс. температура статора

    // === Реальные значения ===
    float Ms = 0.0f;               // Момент
    float ns = 0.0f;               // Скорость
    float Idc = 0.0f;              // Ток DC
    float Isd = 0.0f;              // d-компонента
    float Isq = 0.0f;              // q-компонента
    float Udc = 0.0f;              // Напряжение DC
    float Pe_dc = 0.0f;            // Мощность DC

    // === Температуры ===
    float MCU_IGBTTempU = 0.0f;
    float MCU_IGBTTempV = 0.0f;
    float MCU_IGBTTempW = 0.0f;
    float MCU_IGBTTempMax = 0.0f;
    float MCU_TempCurrStr = 0.0f;
    float MCU_TempCurrStr1 = 0.0f;
    float MCU_TempCurrStr2 = 0.0f;
    float MCU_TempCurrCool = 0.0f;

    float TrqThresholdDampgCtl = 0.0f;

    // === Статусы ===
    uint8_t MCU_Status = 0;        // MCU-Status
    uint8_t M_Status = 0;          // М-статус
    uint8_t n_Status = 0;          // n-статус
    uint8_t MCU_stGateDrv = 0;     // Gate driver status
    uint8_t TempStatus = 0;        // Температурный статус

    // === Версии ПО ===
    std::string MCU_SW_ver;
    std::string MCU_calib_SW_ver;
    std::string MCU_Hv_SW_ver;
    std::string MCU_CPLD_SW_ver;
    std::string MCU_HW_ver;

    // === Прочее ===
    std::string configFilePath = "config/Config.ini";

    float Emf;
    float Welectrical;
    float motorRs;
    float Wmechanical;

    int16_t Ud;
    int16_t Uq;
    int16_t Id;
    int16_t Iq;


};
