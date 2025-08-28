#pragma once
#include "DataModel.h"
#include "CANInterface.h"
#include "ConfigManager.h"
#include "MarathonLogic.h"
#include <functional>

enum class State {
    Idle,
    Init,
    Read2,
    Stop,
    Save_Cfg,
    Read_Cfg
};

class StateMachine {
public:
    StateMachine(DataModel& model, CANInterface& can, ConfigManager& cfg);
    void setState(State newState);
    void update(); // вызывает действия для текущего состояния

private:
    State currentState = State::Idle;
    DataModel& data;
    CANInterface& canInterface;
    ConfigManager& config;

    void handleIdle();
    void handleInit();
    CANMessage handleRead2();
    void handleStop();
    void handleSaveCfg();
    void handleReadCfg();
};
