// ws_server.cpp
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0A00 // Windows 10 для Boost.Asio/Beast (убирает предупреждение)
#endif

#include <boost/beast/core.hpp>
#include <boost/beast/websocket.hpp>
#include <boost/asio.hpp>
#include <boost/asio/strand.hpp>
#include <nlohmann/json.hpp>
#include <thread>
#include <chrono>
#include <iostream>
#include <type_traits>

// мои заголовки
#include "DataModel.h"
#include "StateMachine.h"
#include "CommandSender.h"
#include "ConfigManager.h"
#include "CANInterface.h"

using tcp = boost::asio::ip::tcp;
namespace websocket = boost::beast::websocket;
using json = nlohmann::json;

DataModel     model;
CANInterface  can;
ConfigManager config(model.configFilePath);
StateMachine  sm(model, can, config);

// утилита: присвоить поле из JSON, если ключ есть
template<class T>
inline void set_if_present(const json& j, const char* key, T& target) {
    if (j.contains(key) && !j.at(key).is_null()) {
        target = j.at(key).get<T>();
    }
}

// применить параметры управления (для "SendControl")
static void apply_control_fields(const json& j) {
    set_if_present(j, "MotorCtrl",    model.MotorCtrl);
    set_if_present(j, "GearCtrl",     model.GearCtrl);
    set_if_present(j, "Kl_15",        model.Kl_15);
    set_if_present(j, "Brake_active", model.Brake_active);
    set_if_present(j, "TCS_active",   model.TCS_active);
}

// применить лимиты (для "SendLimits")
static void apply_limit_fields(const json& j) {
    set_if_present(j, "M_max",       model.M_max);
    set_if_present(j, "M_min",       model.M_min);
    set_if_present(j, "M_grad_max",  model.M_grad_max);
    set_if_present(j, "n_max",       model.n_max);
}

// применить Id/Iq и прочее удалённое управление (для "SendTorque")
static void apply_torque_fields(const json& j) {
    set_if_present(j, "En_rem", model.En_rem);
    set_if_present(j, "Isd",    model.Isd);
    set_if_present(j, "Isq",    model.Isq);
}

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

        // Поток регулярной отправки данных клиенту
        std::thread updater([&ws]() {
            while (true) {
                try {
                    sm.update();
                    std::string data = serializeData();
                    ws.write(boost::asio::buffer(data));
                    std::this_thread::sleep_for(std::chrono::milliseconds(500));
                } catch (...) {
                    break; // клиент отключился — выходим из потока
                }
            }
        });

        // Чтение и обработка команд от клиента
        // цикл приёма команд
        for (;;) {
            boost::beast::flat_buffer buffer;
            ws.read(buffer);
            const std::string msg = boost::beast::buffers_to_string(buffer.data());
            const json j = json::parse(msg);

            const std::string cmd = j.value("cmd", "");
            if (cmd == "Init") {
                sm.setState(State::Init);
            } else if (cmd == "Stop") {
                sm.setState(State::Stop);
            } else if (cmd == "Read2") {
                sm.setState(State::Read2);
            } else if (cmd == "SaveCfg") {
                config.save(model);
            } else if (cmd == "SendControl") {
                apply_control_fields(j);   // обновили модель из JSON
                config.save(model);        // сохранили конфиг
                CommandSender::sendControlCommand(can, model); // отправили кадр
            } else if (cmd == "SendLimits") {
                apply_limit_fields(j);
                config.save(model);
                CommandSender::sendLimitCommand(can, model);
            } else if (cmd == "SendTorque") {
                apply_torque_fields(j);
                config.save(model);
                CommandSender::sendTorqueCommand(can, model);
            }
            // при необходимости можно добавить ответ-ACK через ws.write(...)
            // но тогда нужно синхронизировать записи с updater'ом (strand/мьютекс)
        }

        updater.join();
    } catch (const std::exception& e) {
        std::cerr << "[WS error] " << e.what() << "\n";
    }
}

int main() {
    // Загрузка конфигурации и перевод в исходное состояние
    config.load(model);
    sm.setState(State::Idle);

    try {
        boost::asio::io_context ioc;
        tcp::acceptor acceptor{ioc, {tcp::v4(), 9000}};
        std::cout << "WebSocket server running at ws://0.0.0.0:9000" << std::endl;

        for (;;) {
            tcp::socket socket{ioc};
            acceptor.accept(socket);
            std::thread(&do_session, std::move(socket)).detach();
        }
    } catch (const std::exception& e) {
        std::cerr << "[Fatal] " << e.what() << std::endl;
    }
}






