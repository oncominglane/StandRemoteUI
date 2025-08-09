#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio.hpp>
#include <boost/asio/strand.hpp>
#include <nlohmann/json.hpp>
#include <thread>
#include <chrono>
#include <iostream>

// Твои заголовки
#include "DataModel.h"
#include "StateMachine.h"
#include "CommandSender.h"
#include "ConfigManager.h"
#include "CANInterface.h"

using tcp = boost::asio::ip::tcp;
namespace websocket = boost::beast::websocket;
using json = nlohmann::json;

DataModel model;
CANInterface can;
ConfigManager config(model.configFilePath);
StateMachine sm(model, can, config);

// Сериализация DataModel в JSON
std::string serializeData() {
    json j;
    j["Ms"] = model.Ms;
    j["ns"] = model.ns;
    j["Idc"] = model.Idc;
    j["Isd"] = model.Isd;
    j["Isq"] = model.Isq;
    j["Udc"] = model.Udc;
    j["Kl_15"] = model.Kl_15;
    j["Brake_active"] = model.Brake_active;
    j["TCS_active"] = model.TCS_active;
    j["MCU_IGBTTempU"] = model.MCU_IGBTTempU;
    j["MCU_TempCurrStr"] = model.MCU_TempCurrStr;
    return j.dump();
}

void do_session(tcp::socket socket) {
    try {
        websocket::stream<tcp::socket> ws{std::move(socket)};
        ws.accept();
        std::cout << "[WS] Client connected" << std::endl;

        // Поток обновлений данных
        std::thread updater([&ws]() {
            while (true) {
                try {
                    sm.update();
                    std::string data = serializeData();
                    ws.write(boost::asio::buffer(data));
                    std::this_thread::sleep_for(std::chrono::milliseconds(500));
                } catch (...) {
                    break; // если клиент отключился
                }
            }
        });

        // Чтение команд
        for (;;) {
            boost::beast::flat_buffer buffer;
            ws.read(buffer);
            std::string msg = boost::beast::buffers_to_string(buffer.data());
            auto j = json::parse(msg);

            std::string cmd = j.value("cmd", "");
            if (cmd == "Init") sm.setState(State::Init);
            else if (cmd == "Stop") sm.setState(State::Stop);
            else if (cmd == "Read2") sm.setState(State::Read2);
            else if (cmd == "SaveCfg") sm.setState(State::Save_Cfg);
            else if (cmd == "SendControl") CommandSender::sendControlCommand(can, model);
            else if (cmd == "SendLimits") CommandSender::sendLimitCommand(can, model);
            else if (cmd == "SendTorque") CommandSender::sendTorqueCommand(can, model);
        }

        updater.join();

    } catch (std::exception const& e) {
        std::cerr << "[Error] " << e.what() << std::endl;
    }
}

int main() {
    config.load(model);
    sm.setState(State::Idle);

    try {
        boost::asio::io_context ioc;
        tcp::acceptor acceptor{ioc, {tcp::v4(), 9000}};
        std::cout << "✅ WebSocket server running at ws://0.0.0.0:9000" << std::endl;
        for (;;) {
            tcp::socket socket{ioc};
            acceptor.accept(socket);
            std::thread(&do_session, std::move(socket)).detach();
        }
    } catch (std::exception const& e) {
        std::cerr << "[Fatal] " << e.what() << std::endl;
    }
}
