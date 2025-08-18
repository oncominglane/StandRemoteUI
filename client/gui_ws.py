import tkinter as tk
from tkinter import Tk, ttk, Text, StringVar, Entry, Frame
import json

from network import WSClient
WS_URL = "ws://127.0.0.1:9000"  # при необходимости поменять

from utils import make_focusable_scale, on_arrow_key
active_scale = None  # текущий выбранный ползунок

def create_gui():

    root = tk.Tk()
    root.title("Удаленное управление стендом")
    root.geometry("950x700+100+100")
    #try:
    #    root.state('zoomed')
    #except Exception:
    #    pass

    # Коллбеки для WS с безопасным обновлением из главного потока
    log_box = tk.Text(root, height=10, wrap="word")
    def ui_log(msg):
        log_box.insert("end", msg.strip() + "\n")
        log_box.see("end")

    def on_message(msg):
        root.after(0, lambda: ui_log(f"[RX] {msg}"))

    def on_status(msg):
        root.after(0, lambda: ui_log(f"[WS] {msg}"))

    def on_error(msg):
        root.after(0, lambda: ui_log(f"[ERR] {msg}"))

    # Запускаем WS-клиент
    client = WSClient(WS_URL, on_message, on_status, on_error)
    client.start()
    

    root.protocol("WM_DELETE_WINDOW", lambda: (client.stop(), root.destroy()))

    root.bind("<Up>", on_arrow_key)
    root.bind("<Down>", on_arrow_key)

    # Вкладки
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    main_frame = ttk.Frame(notebook)
    notebook.add(main_frame, text="Управление")
    ind_frame = ttk.Frame(notebook)
    notebook.add(ind_frame, text="Индикация")
    log_frame = ttk.Frame(notebook)
    notebook.add(log_frame, text="Журнал")

    # Вкладка 1
    main_inner = ttk.Frame(main_frame)
    main_inner.pack(fill="both", expand=True)

    # Кнопки управления
    control_frame = ttk.Frame(main_inner)
    control_frame.pack(padx=10, pady=10, fill="x")

    ttk.Button(control_frame, text="▶ Старт", width=15,
               command=lambda: client.send_cmd_threadsafe("Init")).pack(side="left", padx=5)
    ttk.Button(control_frame, text="■ Стоп", width=15,
               command=lambda: client.send_cmd_threadsafe("Stop")).pack(side="left", padx=5)
    ttk.Button(control_frame, text="↺ Сброс", width=15,
               command=lambda: client.send_cmd_threadsafe("Read2")).pack(side="left", padx=5)
    ttk.Button(control_frame, text="💾 Сохранить", width=15,
               command=lambda: client.send_cmd_threadsafe("SaveCfg")).pack(side="left", padx=5)

        # ====== Блок "Токи (Id/Iq)" ======
    currents_frame = ttk.LabelFrame(main_inner, text="Токи (Id/Iq)")
    currents_frame.place(x=10, y=120, width=340, height=120)

    En_rem_var = tk.IntVar(value=1)
    Id_var = tk.StringVar(value="-0.5")
    Iq_var = tk.StringVar(value="0.0")

    ttk.Checkbutton(currents_frame, text="Удалённое управление (En_rem)", variable=En_rem_var)\
        .grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=6)

    ttk.Label(currents_frame, text="Id [A]").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(currents_frame, width=10, textvariable=Id_var).grid(row=1, column=1, sticky="w")

    ttk.Label(currents_frame, text="Iq [A]").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(currents_frame, width=10, textvariable=Iq_var).grid(row=1, column=3, sticky="w")

    # ====== Блок "Лимиты" ======
    limits_frame = ttk.LabelFrame(main_inner, text="Лимиты")
    limits_frame.place(x=360, y=120, width=360, height=120)

    M_min_var      = tk.StringVar(value="-50.0")
    M_max_var      = tk.StringVar(value="400.0")
    M_grad_max_var = tk.StringVar(value="50")
    n_max_var      = tk.StringVar(value="1000")

    ttk.Label(limits_frame, text="M_min [Н·м]").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(limits_frame, width=10, textvariable=M_min_var).grid(row=0, column=1, sticky="w")

    ttk.Label(limits_frame, text="M_max [Н·м]").grid(row=0, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(limits_frame, width=10, textvariable=M_max_var).grid(row=0, column=3, sticky="w")

    ttk.Label(limits_frame, text="M_grad_max").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(limits_frame, width=10, textvariable=M_grad_max_var).grid(row=1, column=1, sticky="w")

    ttk.Label(limits_frame, text="n_max [об/мин]").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(limits_frame, width=10, textvariable=n_max_var).grid(row=1, column=3, sticky="w")

    # Доп. команды (если нужны)
    extra_frame = ttk.Frame(main_inner)
    extra_frame.pack(padx=10, pady=(0,10), fill="x")
#    for cmd in ["SendControl", "SendLimits", "SendTorque"]:
#        ttk.Button(extra_frame, text=cmd, width=15,
#                   command=lambda c=cmd: client.send_cmd_threadsafe(c)).pack(side="left", padx=5)
    ttk.Button(
        extra_frame, text="SendControl", width=15,
        command=lambda: client.send_json_threadsafe({
            "cmd": "SendControl",
            "MotorCtrl": 1,           # пример: режим управления
            "GearCtrl": 1,            # пример: передача
            "Kl_15": True,            # «зажигание»
            "Brake_active": False,
            "TCS_active": False
        })
    ).pack(side="left", padx=5)
     # SendLimits: возьмём текущий момент и скорость как M_max и n_max
    ttk.Button(
        extra_frame, text="SendLimits", width=15,
        command=lambda: client.send_json_threadsafe({
            "cmd": "SendLimits",
            "M_max": float(torque_var.get() or 0),   # Н·м
            "n_max": int(float(speed_var.get() or 0))# об/мин
            # при необходимости добавь другие лимиты
        })
    ).pack(side="left", padx=5)

    # SendTorque: берём Id/Iq из формы параметров
    ttk.Button(
        extra_frame, text="SendTorque", width=15,
        command=lambda: client.send_json_threadsafe({
            "cmd": "SendTorque",
            "En_rem": True,                                   # удалённое управление
            "Isd": float(entry_vars["Id"].get() or 0),        # Id
            "Isq": float(entry_vars["Iq"].get() or 0)         # Iq
        })
    ).pack(side="left", padx=5)
    
    # Параметры стенда
    # Параметры стенда (оставим без Id/Iq, чтобы не дублировать)
    params_frame = ttk.LabelFrame(main_inner, text="Параметры стенда")
    params_frame.place(x=10, y=260, width=700, height=200)
    params = ["Скорость вращения", "Температура статора", "Температура ротора"]
    entry_vars = {}
    for i, param in enumerate(params):
        ttk.Label(params_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(params_frame, textvariable=var, width=20)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entry_vars[param] = var

    # CAN
    can_frame = ttk.LabelFrame(main_inner, text="Tx / Rx CAN")
    can_frame.place(x=10, y=390, width=710, height=140)
    can_cells = []
    ttk.Label(can_frame, text="id", anchor="center").grid(row=0, column=1, padx=2, pady=(0, 5))
    for col in range(1, 9):
        ttk.Label(can_frame, text=f"data{col-1}", anchor="center").grid(row=0, column=col + 1, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="len", anchor="center").grid(row=0, column=10, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="flags", anchor="center").grid(row=0, column=11, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="ts", anchor="center").grid(row=0, column=12, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="Tx:").grid(row=1, column=0, sticky="e", padx=3)
    ttk.Label(can_frame, text="Rx:").grid(row=2, column=0, sticky="e", padx=3)
    for row in range(2):
        for col in range(1,13):
            var = StringVar()
            entry = Entry(can_frame, textvariable=var, width=8, justify="center")
            entry.grid(row=row+1, column=col, padx=2, pady=2)
            can_cells.append(var)

    # Режим управления + ползунки
    control_mode_var = tk.StringVar()
    ttk.Label(main_inner, text="Режим управления:").place(x=750, y=10)
    mode_combo = ttk.Combobox(main_inner, textvariable=control_mode_var, values=["-", "Режим 1", "Режим 2"], state="readonly", width=20)
    mode_combo.current(0)
    mode_combo.place(x=750, y=30)

    slider_frame = ttk.Frame(main_inner, width=180, height=450)
    slider_frame.place(x=750, y=60)
    slider_frame.pack_propagate(False)
    speed_var = tk.DoubleVar()
    torque_var = tk.DoubleVar()
    ttk.Label(slider_frame, text="Скорость\nоб/мин").place(x=10, y=0)
    ttk.Label(slider_frame, text="Момент\nН·м").place(x=100, y=0)
    speed_slider = ttk.Scale(slider_frame, from_=20000, to=0, variable=speed_var, orient="vertical", length=300)
    speed_slider.place(x=10, y=40)
    speed_slider.state(["disabled"])
    speed_slider.bind("<Button-1>", lambda e: speed_slider.focus_set())
    make_focusable_scale(speed_slider, speed_var, step=100)
    torque_slider = ttk.Scale(slider_frame, from_=500, to=0, variable=torque_var, orient="vertical", length=300)
    torque_slider.place(x=100, y=40)
    torque_slider.state(["disabled"])
    torque_slider.bind("<Button-1>", lambda e: torque_slider.focus_set())
    make_focusable_scale(torque_slider, torque_var, step=1.0)
    speed_entry = ttk.Entry(slider_frame, textvariable=speed_var, width=6, state="disabled")
    speed_entry.place(x=10, y=350)
    torque_entry = ttk.Entry(slider_frame, textvariable=torque_var, width=6, state="disabled")
    torque_entry.place(x=100, y=350)

    def on_mode_change(event):
        if control_mode_var.get() != "-":
            speed_slider.state(["!disabled"])
            torque_slider.state(["!disabled"])
            speed_entry.config(state="normal")
            torque_entry.config(state="normal")
        else:
            speed_slider.state(["disabled"])
            torque_slider.state(["disabled"])
            speed_entry.config(state="disabled")
            torque_entry.config(state="disabled")
    mode_combo.bind("<<ComboboxSelected>>", on_mode_change)

    # Вкладка 3: лог
    log_box.pack(in_=log_frame, fill="both", padx=10, pady=10, expand=True)

    root.mainloop()


if __name__ == "__main__":
    create_gui()
