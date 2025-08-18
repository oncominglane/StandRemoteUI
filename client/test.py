import json
import tkinter as tk
from tkinter import ttk

# твой клиент (как и было)
from network import WSClient
WS_URL = "ws://127.0.0.1:9000"  # поменяй при необходимости


def create_gui():
    root = tk.Tk()
    root.title("Удаленное управление стендом")
    root.geometry("980x720+100+100")

    # ——— лог и статус в UI ———
    status_var = tk.StringVar(value="disconnected")
    ttk.Label(root, textvariable=status_var).pack(anchor="w", padx=8, pady=4)
    log = tk.Text(root, height=12)
    log.pack(fill="both", expand=True, padx=8, pady=8)

    def ui_append(text):
        # потокобезопасно добавляем строки в Text
        log.after(0, lambda: (log.insert("end", text + "\n"), log.see("end")))

    # ——— требуемые WSClient колбэки ———
    def on_message(msg: str):
        ui_append(f"< {msg}")

    def on_status(connected: bool):
        status = "connected" if connected else "disconnected"
        root.after(0, status_var.set, status)
        ui_append(f"[status] {status}")

    def on_error(err: Exception):
        ui_append(f"[error] {err}")
        
    # --- сеть ---
    client = WSClient(WS_URL, on_message, on_status, on_error)
    client.start()  # внутри должен подняться поток чтения

    # универсальная отправка JSON
    def send_json(payload: dict):
        # Пытаемся вызвать метод JSON-отправки; если его нет — шлём строку
        text = json.dumps(payload, ensure_ascii=False)
        if hasattr(client, "send_json_threadsafe"):
            client.send_json_threadsafe(payload)
        elif hasattr(client, "send_text_threadsafe"):
            client.send_text_threadsafe(text)
        elif hasattr(client, "send_cmd_threadsafe"):
            # у некоторых твоих версий send_cmd_threadsafe умеет dict
            client.send_cmd_threadsafe(payload)
        else:
            # крайний случай
            client.send(text)

    # --- хелперы ввода ---
    def get_int(var, default=0):
        try:
            return int(var.get())
        except Exception:
            return default

    def get_float(var, default=0.0):
        try:
            return float(str(var.get()).replace(',', '.'))
        except Exception:
            return default

    # --- вкладки ---
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    tab_main = ttk.Frame(nb)
    tab_limits = ttk.Frame(nb)
    tab_currents = ttk.Frame(nb)
    tab_log = ttk.Frame(nb)

    nb.add(tab_main, text="Управление")
    nb.add(tab_limits, text="Лимиты")
    nb.add(tab_currents, text="Токи (Id/Iq)")
    nb.add(tab_log, text="Журнал")

    # ========================= Управление =========================
    # Поля управления
    MotorCtrl = tk.IntVar(value=0)     # включение привода (0/1)
    GearCtrl = tk.StringVar(value="P") # P/R/N/D — подставь свой набор
    Kl_15 = tk.IntVar(value=1)         # зажигание
    Brake_active = tk.IntVar(value=0)
    TCS_active = tk.IntVar(value=0)

    frm_ctl = ttk.LabelFrame(tab_main, text="Панель управления")
    frm_ctl.pack(fill="x", padx=12, pady=12)

    row = 0
    ttk.Checkbutton(frm_ctl, text="Зажигание (Kl_15)", variable=Kl_15).grid(row=row, column=0, sticky="w", padx=6, pady=6)
    ttk.Checkbutton(frm_ctl, text="Тормоз активен", variable=Brake_active).grid(row=row, column=1, sticky="w", padx=6, pady=6)
    ttk.Checkbutton(frm_ctl, text="TCS активна", variable=TCS_active).grid(row=row, column=2, sticky="w", padx=6, pady=6)

    row += 1
    ttk.Label(frm_ctl, text="Привод (MotorCtrl)").grid(row=row, column=0, sticky="w", padx=6)
    ttk.Spinbox(frm_ctl, from_=0, to=1, width=6, textvariable=MotorCtrl).grid(row=row, column=1, sticky="w", padx=6)

    ttk.Label(frm_ctl, text="Коробка (GearCtrl)").grid(row=row, column=2, sticky="e", padx=6)
    gear_cb = ttk.Combobox(frm_ctl, width=8, textvariable=GearCtrl, values=["P", "R", "N", "D"])
    gear_cb.grid(row=row, column=3, sticky="w", padx=6)

    # Кнопки запуск/останов
    row += 1
    frm_buttons = ttk.Frame(tab_main)
    frm_buttons.pack(fill="x", padx=12, pady=(0,12))

    ttk.Button(frm_buttons, text="▶ Init", width=14,
               command=lambda: send_json({"cmd": "Init"})).pack(side="left", padx=6)
    ttk.Button(frm_buttons, text="■ Stop", width=14,
               command=lambda: send_json({"cmd": "Stop"})).pack(side="left", padx=6)
    ttk.Button(frm_buttons, text="⟳ Read2", width=14,
               command=lambda: send_json({"cmd": "Read2"})).pack(side="left", padx=6)
    ttk.Button(frm_buttons, text="💾 SaveCfg", width=14,
               command=lambda: send_json({"cmd": "SaveCfg"})).pack(side="left", padx=6)

    # Кнопка SendControl
    def on_send_control():
        payload = {
            "cmd": "SendControl",
            "MotorCtrl": get_int(MotorCtrl),
            "GearCtrl": GearCtrl.get(),
            "Kl_15": int(Kl_15.get()),
            "Brake_active": int(Brake_active.get()),
            "TCS_active": int(TCS_active.get()),
            # опционально: persist для автосохранения
            "persist": False
        }
        send_json(payload)

    ttk.Button(tab_main, text="➤ SendControl", command=on_send_control).pack(anchor="w", padx=18, pady=6)

    # ========================= Лимиты =========================
    M_min = tk.StringVar(value="-50.0")
    M_max = tk.StringVar(value="400.0")
    M_grad_max = tk.StringVar(value="50")   # шаг/градиент
    n_max = tk.StringVar(value="1000")

    frm_lim = ttk.LabelFrame(tab_limits, text="Лимиты")
    frm_lim.pack(fill="x", padx=12, pady=12)

    ttk.Label(frm_lim, text="M_min [Nm]").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(frm_lim, width=10, textvariable=M_min).grid(row=0, column=1, sticky="w")

    ttk.Label(frm_lim, text="M_max [Nm]").grid(row=0, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(frm_lim, width=10, textvariable=M_max).grid(row=0, column=3, sticky="w")

    ttk.Label(frm_lim, text="M_grad_max").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(frm_lim, width=10, textvariable=M_grad_max).grid(row=1, column=1, sticky="w")

    ttk.Label(frm_lim, text="n_max [rpm]").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(frm_lim, width=10, textvariable=n_max).grid(row=1, column=3, sticky="w")

    def on_send_limits():
        payload = {
            "cmd": "SendLimits",
            "M_min":      get_float(M_min),
            "M_max":      get_float(M_max),
            "M_grad_max": get_float(M_grad_max),
            "n_max":      get_float(n_max),
            "persist": False
        }
        send_json(payload)

    ttk.Button(tab_limits, text="➤ SendLimits", command=on_send_limits).pack(anchor="w", padx=18, pady=10)

    # ========================= Токи (Id/Iq) =========================
    En_rem = tk.IntVar(value=1)
    Isd = tk.StringVar(value="-0.5")
    Isq = tk.StringVar(value="0.0")

    frm_cur = ttk.LabelFrame(tab_currents, text="Токи (FOC)")
    frm_cur.pack(fill="x", padx=12, pady=12)

    ttk.Checkbutton(frm_cur, text="Удалённое управление (En_rem)", variable=En_rem).grid(row=0, column=0, sticky="w", padx=6, pady=6)

    ttk.Label(frm_cur, text="Id [A]").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(frm_cur, width=10, textvariable=Isd).grid(row=1, column=1, sticky="w")

    ttk.Label(frm_cur, text="Iq [A]").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(frm_cur, width=10, textvariable=Isq).grid(row=1, column=3, sticky="w")

    def on_send_torque():  # историческое имя; фактически — токи
        payload = {
            "cmd": "SendTorque",
            "En_rem": int(En_rem.get()),
            "Isd":    get_float(Isd),
            "Isq":    get_float(Isq),
            "persist": False
        }
        send_json(payload)

    ttk.Button(tab_currents, text="➤ SendTorque (Id/Iq)", command=on_send_torque).pack(anchor="w", padx=18, pady=10)

    # ========================= Лог =========================
    # простой вывод сетевых сообщений, если у WSClient есть колбэк
    log = tk.Text(tab_log, height=24)
    log.pack(fill="both", expand=True, padx=12, pady=12)

    # опционально: подписка на входящие сообщения
    def on_msg(txt: str):
        log.insert("end", txt + "\n")
        log.see("end")

    if hasattr(client, "on_message_append"):
        client.on_message_append = on_msg

    root.mainloop()


if __name__ == "__main__":
    create_gui()
