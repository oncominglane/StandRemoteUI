#include "CommandSender.h"
#include <iostream>

void CommandSender::sendControlCommand(CANInterface& can, const DataModel& data) {
    uint8_t payload[8] = {0};
    payload[0] = data.MotorCtrl;
    payload[1] = data.GearCtrl;
    payload[2] = (data.Brake_active ? 0x01 : 0x00) | (data.TCS_active ? 0x02 : 0x00);
    payload[3] = (data.Kl_15 ? 0x01 : 0x00);
    can.send(0x046, payload, 8);
    std::cout << "[TX] Control Sent" << std::endl;
}

void CommandSender::sendLimitCommand(CANInterface& can, const DataModel& data) {
    uint8_t payload[8] = {0};
    int16_t m_max = (int16_t)(data.M_max * 10);
    int16_t m_min = (int16_t)(data.M_min * 10);
    int16_t grad = (int16_t)data.M_grad_max;
    payload[0] = m_max & 0xFF;
    payload[1] = (m_max >> 8) & 0xFF;
    payload[2] = m_min & 0xFF;
    payload[3] = (m_min >> 8) & 0xFF;
    payload[4] = grad & 0xFF;
    payload[5] = (grad >> 8) & 0xFF;
    can.send(0x475, payload, 8);
    std::cout << "[TX] Limits Sent" << std::endl;
}

void CommandSender::sendTorqueCommand(CANInterface& can, const DataModel& data) {
    uint8_t payload[8] = {0};
    payload[0] = (data.En_rem ? 0x01 : 0x00);
    int16_t isd = (int16_t)(data.Isd * 10);
    int16_t isq = (int16_t)(data.Isq * 10);
    payload[2] = isd & 0xFF;
    payload[3] = (isd >> 8) & 0xFF;
    payload[4] = isq & 0xFF;
    payload[5] = (isq >> 8) & 0xFF;
    can.send(0x300, payload, 8);
    std::cout << "[TX] Torque Sent" << std::endl;
}
