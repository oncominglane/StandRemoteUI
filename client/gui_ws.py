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
    
    # Коллбеки для WS с безопасным обновлением из главного потока
    log_box = tk.Text(root, height=10, wrap="word")
    def ui_log(msg):
        log_box.insert("end", msg.strip() + "\n")
        log_box.see("end")

    # Глобальные переменные для CAN данных
    can_rx_data = [StringVar() for _ in range(12)]  # 12 полей для Rx CAN
    can_tx_data = [StringVar() for _ in range(12)]  # 12 полей для Tx CAN

    def on_message(msg):
        root.after(0, lambda: ui_log(f"[RX] {msg}"))
        
        try:
            data = json.loads(msg)

            if data.get("type") == "can_frame":
                handle_can_frame(data)

            # Определим, что это модельные данные — по наличию одного из ключей
            elif any(k in data for k in ["Ms", "ns", "Isd", "Udc"]):
                handle_model_data(data)

            else:
                ui_log("⚠ Неизвестный тип сообщения")
        
        except json.JSONDecodeError:
            ui_log("❌ Не удалось разобрать JSON")
    
    def handle_can_frame(frame_data):
        direction = frame_data.get("direction", "")

        if direction == "rx":
            for i in range(8):
                if f"data{i}" in frame_data:
                    can_rx_data[i+1].set(str(frame_data[f"data{i}"]))
            can_rx_data[0].set(str(frame_data.get("id", "")))
            can_rx_data[9].set(str(frame_data.get("len", "")))
            can_rx_data[10].set(str(frame_data.get("flags", "")))
            can_rx_data[11].set(str(frame_data.get("ts", "")))

        elif direction == "tx":
            for i in range(8):
                if f"data{i}" in frame_data:
                    can_tx_data[i+1].set(str(frame_data[f"data{i}"]))
            can_tx_data[0].set(str(frame_data.get("id", "")))
            can_tx_data[9].set(str(frame_data.get("len", "")))
            can_tx_data[10].set(str(frame_data.get("flags", "")))
            can_tx_data[11].set(str(frame_data.get("ts", "")))

    def handle_model_data(data):
        # Существующий field_map для остальных параметров (кроме MCU_VCU_1)
        field_map = {
            "MCU_IGBTTempU": "Температура статора",
            "MCU_TempCurrStr": "Температура ротора",
            "Ud": "Ud",
            "Uq": "Uq",
            "Id": "Id",
            "Iq": "Iq",
            "Emf": "Emf",
            "Welectrical": "Welectrical",
            "motorRs": "motorRs",
            "Wmechanical": "Wmechanical"
        }

        # Обновляем MCU_VCU_1 поля
        for key in vcu_vars:
            if key in data:
                vcu_vars[key].set(str(data[key]))

        # Обновляем остальные поля
        for key, label in field_map.items():
            if key in data:
                entry_vars[label].set(str(data[key]))

        # Логирование параметров (опционально)
        for key in ["Ms", "Idc", "Isd", "Isq", "Udc"]:
            if key in data:
                ui_log(f"{key}: {data[key]}")

    
    def send_fake_can_from_fields():
        try:
            # Получаем значения
            Id = float(Id_var.get() or 0)
            Iq = float(Iq_var.get() or 0)
            torque = float(torque_var.get() or 0)
            speed = float(speed_var.get() or 0)

            # Формируем CAN-кадр
            can_msg = {
                "cmd": "FakeCAN",
                "direction": "tx",
                "id": 0x555,  # можно выбрать любой ID
                "len": 8,
                "flags": 0,
                "ts": 10,#time.time(),  # или фиксированное значение
                "data0": int(Id * 10) & 0xFF,
                "data1": int(Iq * 10) & 0xFF,
                "data2": int(torque) & 0xFF,
                "data3": int(speed / 10) & 0xFF,
                "data4": 0,
                "data5": 0,
                "data6": 0,
                "data7": 0
            }

            # Отправляем
            client.send_json_threadsafe(can_msg)
            ui_log("[UI] Отправлен FakeCAN из полей: Id/Iq, Момент, Скорость")
        except Exception as e:
            ui_log(f"[Ошибка отправки FakeCAN] {e}")

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

    # Доп. команды
    extra_frame = ttk.Frame(main_inner)
    extra_frame.pack(padx=10, pady=(0,10), fill="x")

    ttk.Button(
        extra_frame, text="SendControl", width=15,
        command=lambda: client.send_json_threadsafe({
            "cmd": "SendControl",
            "MotorCtrl": 1,
            "GearCtrl": 1,
            "Kl_15": True,
            "Brake_active": False,
            "TCS_active": False
        })
    ).pack(side="left", padx=5)

    ttk.Button(
        extra_frame, text="SendLimits", width=15,
        command=lambda: client.send_json_threadsafe({
            "cmd": "SendLimits",
            "M_max": float(torque_var.get() or 0),
            "n_max": int(float(speed_var.get() or 0))
        })
    ).pack(side="left", padx=5)

    ttk.Button(
        extra_frame, text="SendTorque", width=15,
        command=lambda: client.send_json_threadsafe({
            "cmd": "SendTorque",
            "En_rem": True,
            "Isd": float(Id_var.get() or 0),
            "Isq": float(Iq_var.get() or 0)
        })
    ).pack(side="left", padx=5)

    ttk.Button(
        extra_frame, text="FakeCAN из полей", width=18,
        command=lambda: send_fake_can_from_fields()
    ).pack(side="left", padx=5)

    
    # Параметры стенда
    params_frame = ttk.LabelFrame(main_inner, text="Параметры стенда")
    params_frame.place(x=10, y=260, width=700, height=200)
    params = [
        "Скорость вращения",
        "Момент (Ms)",       # новый
        "Ток постоянного (Idc)", # новый
        "Ток статора d (Isd)",   # новый
        "Температура статора",
        "Температура ротора",
        "Ud", "Uq", "Id", "Iq",
        "Emf", "Welectrical", "motorRs", "Wmechanical"
    ]

    # В create_gui(), после создания params_frame и entry_vars

    # Новый блок для MCU_VCU_1 параметров (Ms, ns, Idc, Isd)
    vcu_frame = ttk.LabelFrame(main_inner, text="MCU_VCU_1 параметры")
    vcu_frame.place(x=10, y=470, width=340, height=130)

    vcu_params = {
        "Ms": "Момент (Ms)",
        "ns": "Скорость вращения",
        "Idc": "Ток постоянного (Idc)",
        "Isd": "Ток статора d (Isd)"
    }

    vcu_vars = {}
    for i, (key, label) in enumerate(vcu_params.items()):
        ttk.Label(vcu_frame, text=label + ":").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(vcu_frame, textvariable=var, width=20, state="readonly")
        entry.grid(row=i, column=1, padx=5, pady=5)
        vcu_vars[key] = var

    entry_vars = {}
    for i, param in enumerate(params):
        ttk.Label(params_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(params_frame, textvariable=var, width=20)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entry_vars[param] = var

    # CAN - используем заранее созданные переменные
    can_frame = ttk.LabelFrame(main_inner, text="Tx / Rx CAN")
    can_frame.place(x=10, y=390, width=710, height=140)
    
    # Заголовки
    headers = ["id"] + [f"data{i}" for i in range(8)] + ["len", "flags", "ts"]
    for col, header in enumerate(headers):
        ttk.Label(can_frame, text=header, anchor="center", width=8).grid(row=0, column=col+1, padx=2, pady=(0, 5))
    
    ttk.Label(can_frame, text="Tx:").grid(row=1, column=0, sticky="e", padx=3)
    ttk.Label(can_frame, text="Rx:").grid(row=2, column=0, sticky="e", padx=3)
    
    # Поля Tx
    for col in range(12):
        entry = Entry(can_frame, textvariable=can_tx_data[col], width=8, justify="center", state="readonly")
        entry.grid(row=1, column=col+1, padx=2, pady=2)
    
    # Поля Rx
    for col in range(12):
        entry = Entry(can_frame, textvariable=can_rx_data[col], width=8, justify="center", state="readonly")
        entry.grid(row=2, column=col+1, padx=2, pady=2)
    
    # Блок MCU_CurrentVoltage
    voltage_frame = ttk.LabelFrame(main_inner, text="MCU Current & Voltage")
    voltage_frame.place(x=10, y=470, width=340, height=120)

    voltage_params = ["Ud", "Uq", "Id", "Iq"]
    for i, param in enumerate(voltage_params):
        ttk.Label(voltage_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(voltage_frame, textvariable=var, width=15)
        entry.grid(row=i, column=1, padx=5, pady=3)
        entry_vars[param] = var

    # Блок MCU_FluxParams
    flux_frame = ttk.LabelFrame(main_inner, text="MCU Flux Parameters")
    flux_frame.place(x=360, y=470, width=340, height=120)

    flux_params = ["Emf", "Welectrical", "motorRs", "Wmechanical"]
    for i, param in enumerate(flux_params):
        ttk.Label(flux_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(flux_frame, textvariable=var, width=15)
        entry.grid(row=i, column=1, padx=5, pady=3)
        entry_vars[param] = var

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