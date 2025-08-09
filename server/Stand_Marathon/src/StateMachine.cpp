#include "StateMachine.h"
#include <iostream>

StateMachine::StateMachine(DataModel& model, CANInterface& can, ConfigManager& cfg)
    : data(model), canInterface(can), config(cfg) {}

void StateMachine::setState(State newState) {
    currentState = newState;
}

void StateMachine::update() {
    switch (currentState) {
        case State::Idle:     handleIdle(); break;
        case State::Init:     handleInit(); break;
        case State::Read2:    handleRead2(); break;
        case State::Stop:     handleStop(); break;
        case State::Save_Cfg: handleSaveCfg(); break;
        case State::Read_Cfg: handleReadCfg(); break;
    }
}

// --- Реализация состояний ---

void StateMachine::handleIdle() {
    // В LabVIEW: Idle = ничего не делаем, ждём команды
    std::cout << "[STATE] Idle" << std::endl;
}

void StateMachine::handleInit() {
    std::cout << "[STATE] Init" << std::endl;
    if (canInterface.init(data.canChannel, data.canBaud, data.canFlags)) {
        std::cout << "CAN Initialized" << std::endl;
        setState(State::Read2); // после Init сразу Read2
    } else {
        std::cerr << "CAN Init failed!" << std::endl;
        setState(State::Stop);
    }
}

void StateMachine::handleRead2() {
    CANMessage msg;
    while (canInterface.receive(msg)) {
        MarathonLogic::updateFromCAN(msg, data);
    }
}


void StateMachine::handleStop() {
    std::cout << "[STATE] Stop" << std::endl;
    canInterface.stop();
    std::cout << "CAN stopped" << std::endl;
    setState(State::Idle);
}

void StateMachine::handleSaveCfg() {
    std::cout << "[STATE] Save_Cfg" << std::endl;
    config.save(data);
    std::cout << "Config saved" << std::endl;
    setState(State::Idle);
}

void StateMachine::handleReadCfg() {
    std::cout << "[STATE] Read_Cfg" << std::endl;
    config.load(data);
    std::cout << "Config loaded" << std::endl;
    setState(State::Idle);
}
