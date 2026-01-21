# app.py
import tkinter as tk

from network import WSClient
from state import AppState
from ui_style import init_style
from view import build_ui
from controllers import Controllers
from telemetry import Telemetry

# Тот же адрес, что и в исходном gui_ws.py
#WS_URL = "ws://192.168.1.161:9000"
WS_URL = "ws://192.168.8.100:9000"

def main():
    # --- TK root ---
    root = tk.Tk()
    root.title("StandRemoteGUI")
    root.geometry("1080x740+100+100")
    try:
        root.state("zoomed")
    except Exception:
        pass

    # --- Состояние приложения (все tk.Variable, буферы и пр.) ---
    state = AppState(root)

    # --- Стиль/тема (точно как было в gui_ws.py) ---
    init_style(root, dark=False)\
    
    
    # --- Контроллеры (логика кнопок/команд), пока без видов и без сети ---
    controllers = Controllers(root, state)

    # --- View (построение всего GUI), прокидываем обработчики от контроллеров ---
    views = build_ui(root, state, handlers=controllers.handlers())
    controllers.attach_views(views)

    # --- Телеметрия (разбор входящих сообщений, обновление state и UI) ---
    telemetry = Telemetry(root, state, views, ui_log=controllers.ui_log)

    # --- Сеть (WebSocket клиент остаётся из network.py как есть) ---
    client = WSClient(
        WS_URL,
        on_message=telemetry.on_message,
        on_status=telemetry.on_status,
        on_error=telemetry.on_error,
    )
    controllers.bind_network(client)
    client.start()

    # --- Таймеры телеметрии/рендера графиков ---
    telemetry.start_timers()

    # --- Корректное закрытие ---
    def _on_close():
        try:
            client.stop()
        finally:
            try:
                root.destroy()
            except Exception:
                pass

    root.protocol("WM_DELETE_WINDOW", _on_close)

    # --- Главный цикл ---
    root.mainloop()


if __name__ == "__main__":
    main()
