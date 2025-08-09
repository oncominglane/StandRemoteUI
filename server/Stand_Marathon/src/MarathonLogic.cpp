#include "MarathonLogic.h"
#include <iostream>
#include <cstring>

static int16_t toInt16(const uint8_t* d) {
    return static_cast<int16_t>((d[1] << 8) | d[0]);
}

void MarathonLogic::updateFromCAN(const CANMessage& msg, DataModel& data) {
    switch (msg.id) {
        case 0x300: { // Основные рабочие параметры
            data.Ms  = toInt16(&msg.data[0]) / 10.0f;   // момент Нм
            data.ns  = toInt16(&msg.data[2]);           // скорость об/мин
            data.Idc = toInt16(&msg.data[4]) / 10.0f;   // ток DC
            data.Isd = toInt16(&msg.data[6]) / 10.0f;   // ток d
            std::cout << "[RX] Ms=" << data.Ms << " Ns=" << data.ns
                      << " Idc=" << data.Idc << " Isd=" << data.Isd << std::endl;
            break;
        }
        case 0x046: { // Управление
            data.MotorCtrl = msg.data[0];
            data.GearCtrl  = msg.data[1];
            data.Brake_active = msg.data[2] & 0x01;
            data.TCS_active   = msg.data[2] & 0x02;
            data.Kl_15 = msg.data[3] & 0x01;
            std::cout << "[RX] MotorCtrl=" << (int)data.MotorCtrl
                      << " GearCtrl=" << (int)data.GearCtrl
                      << " Brake=" << data.Brake_active
                      << " TCS=" << data.TCS_active << std::endl;
            break;
        }
        case 0x475: { // Ограничения
            data.M_max = toInt16(&msg.data[0]) / 10.0f;
            data.M_min = toInt16(&msg.data[2]) / 10.0f;
            data.M_grad_max = toInt16(&msg.data[4]);
            std::cout << "[RX] Limits: M_max=" << data.M_max
                      << " M_min=" << data.M_min
                      << " Grad=" << data.M_grad_max << std::endl;
            break;
        }
        case 0x2C5: { // MCU статус
            data.MCU_Status = msg.data[0];
            std::cout << "[RX] MCU_Status=" << (int)data.MCU_Status << std::endl;
            break;
        }
        case 0x2C6: { // Ошибки
            std::cout << "[RX] Error Level: " << (int)msg.data[0] << std::endl;
            break;
        }
        case 0x47A: { // Температуры IGBT
            data.MCU_IGBTTempU = msg.data[0];
            data.MCU_IGBTTempV = msg.data[1];
            data.MCU_IGBTTempW = msg.data[2];
            data.MCU_IGBTTempMax = msg.data[3];
            std::cout << "[RX] IGBT Temps: U=" << data.MCU_IGBTTempU
                      << " V=" << data.MCU_IGBTTempV
                      << " W=" << data.MCU_IGBTTempW << std::endl;
            break;
        }
        case 0x47B: { // Температура статора
            data.MCU_TempCurrStr = msg.data[0];
            data.MCU_TempCurrCool = msg.data[1];
            std::cout << "[RX] Stator Temp=" << data.MCU_TempCurrStr
                      << " Coolant=" << data.MCU_TempCurrCool << std::endl;
            break;
        }
        case 0x49A: { // Версия ПО MCU
            char buff[5] = {};
            memcpy(buff, msg.data, 4);
            data.MCU_SW_ver = std::string(buff);
            std::cout << "[RX] MCU_SW_ver=" << data.MCU_SW_ver << std::endl;
            break;
        }
        default:
            std::cout << "[RX] Unknown ID: 0x" << std::hex << msg.id << std::dec << std::endl;
            break;
    }
}
