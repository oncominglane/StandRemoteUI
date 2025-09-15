import tkinter as tk
from tkinter import Tk, ttk, Text, StringVar, Entry, Frame
import json
import time

# ---------- Глобальные настройки UI ----------
APP_FONT = ("Segoe UI", 10)
MONO_FONT = ("Cascadia Mono", 9)  # или "Consolas"
PAD = 8

def init_style(dark=False):
    style = ttk.Style()
    # cross-platform базовая тема
    base_theme = "clam" if "clam" in style.theme_names() else style.theme_use()
    style.theme_use(base_theme)

    if dark:
        bg = "#1f2227"; fg = "#e6e6e6"; acc = "#3a7afe"; sub = "#9aa0a6"; frame = "#2a2f36"
    else:
        bg = "#f6f7fb"; fg = "#202124"; acc = "#215df0"; sub = "#5f6368"; frame = "#ffffff"

    # Общий фон окна
    style.configure(".", font=APP_FONT)
    style.configure("TFrame", background=bg)
    style.configure("TLabelframe", background=bg)
    style.configure("TLabelframe.Label", background=bg, foreground=fg, font=("Segoe UI Semibold", 10))
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", padding=(10, 6))
    style.configure("Accent.TButton", foreground="white", background=acc)
    style.map("Accent.TButton", background=[("active", acc)])

    style.configure("Toolbar.TFrame", background=frame)
    style.configure("Card.TFrame", background=frame, relief="groove", borderwidth=1)

    # Treeview (CAN-таблица)
    style.configure("Treeview", font=MONO_FONT, background=frame, fieldbackground=frame, foreground=fg, rowheight=22)
    style.configure("Treeview.Heading", font=("Segoe UI Semibold", 9))
    return style


from network import WSClient
WS_URL = "ws://127.0.0.1:9000"  # при необходимости поменять

from utils import make_focusable_scale, on_arrow_key
active_scale = None  # текущий выбранный ползунок

def create_gui():
    root = tk.Tk()
    root.title("Удалённое управление стендом")
    root.geometry("1080x740+100+100")
    style = init_style(dark=False)  # dark=True для тёмной темы

    # Индикатор статуса (цветная «пилюля»)
    conn_var = tk.StringVar(value="Отключено")
    conn_color = tk.StringVar(value="#d93025")  # красный

    toolbar = ttk.Frame(root, style="Toolbar.TFrame")
    toolbar.pack(fill="x")

    def pill(parent, textvar, colorvar):
        wrap = tk.Frame(parent, bg=style.lookup("Toolbar.TFrame", "background"))
        dot = tk.Canvas(wrap, width=10, height=10, highlightthickness=0, bg=style.lookup("Toolbar.TFrame", "background"))
        oval = dot.create_oval(2,2,8,8, fill=colorvar.get(), outline="")
        lbl = ttk.Label(wrap, textvariable=textvar)
        dot.grid(row=0, column=0, padx=(0,4))
        lbl.grid(row=0, column=1)
        # обновление цвета
        def upd(*_):
            dot.itemconfig(oval, fill=colorvar.get())
        colorvar.trace_add("write", upd)
        return wrap

    # Крупные кнопки
    ttk.Button(toolbar, text="▶ Старт", width=14, style="Accent.TButton",
               command=lambda: client.send_cmd_threadsafe("Init")).pack(side="left", padx=(PAD, 4), pady=PAD)
    ttk.Button(toolbar, text="■ Стоп", width=14,
               command=lambda: client.send_cmd_threadsafe("Stop")).pack(side="left", padx=4, pady=PAD)
    ttk.Button(toolbar, text="↺ Сброс", width=14,
               command=lambda: client.send_cmd_threadsafe("Read2")).pack(side="left", padx=4, pady=PAD)
    ttk.Button(toolbar, text="💾 Сохранить", width=14,
               command=lambda: client.send_cmd_threadsafe("SaveCfg")).pack(side="left", padx=4, pady=PAD)

    # Индикатор соединения справа
    pill(toolbar, conn_var, conn_color).pack(side="right", padx=PAD, pady=PAD)

    
    # Коллбеки для WS с безопасным обновлением из главного потока
    log_box = tk.Text(root, height=10, wrap="word")
    def ui_log(msg):
        log_box.insert("end", msg.strip() + "\n")
        log_box.see("end")

    # Глобальные переменные для CAN данных
    can_rx_data = [StringVar() for _ in range(12)]  # 12 полей для Rx CAN
    can_tx_data = [StringVar() for _ in range(12)]  # 12 полей для Tx CAN

    # ==== КНОПОЧНЫЕ ХЭНДЛЕРЫ ====

    def send_control_now():
        """Применить режим и ключевые флаги (и, если режим 'Частота', то ns)."""
        if mode_var.get() == "speed":
            try:
                ns = float(speed_var.get() or 0.0)
            except Exception:
                ui_log("[UI] ns: некорректное значение", "ERR"); return
            client.send_json_threadsafe({
                "cmd": "SendControl",
                "En_Is": False,
                "Kl_15": True,
                "ns": ns
            })
            ui_log(f"[UI] SendControl: Частота (ns={ns:.0f})", "UI")
        else:
            client.send_json_threadsafe({
                "cmd": "SendControl",
                "En_Is": True,
                "Kl_15": False
            })
            ui_log("[UI] SendControl: Токи (En_Is=1, Kl_15=0)", "UI")


    def send_limits_now():
        """Отправить лимиты (M_min/M_max/M_grad_max/n_max)."""
        def _pf(v, name, as_int=False):
            try:
                return (int(float(v.get())) if as_int else float(v.get()))
            except Exception:
                ui_log(f"[UI] {name}: некорректное значение", "ERR")
                raise

        try:
            payload = {
                "cmd": "SendLimits",
                "M_min": _pf(M_min_var, "M_min"),
                "M_max": _pf(M_max_var, "M_max"),
                "M_grad_max": _pf(M_grad_max_var, "M_grad_max", as_int=True),
                "n_max": _pf(n_max_var, "n_max", as_int=True),
            }
        except Exception:
            return

        client.send_json_threadsafe(payload)
        ui_log("[UI] SendLimits отправлен", "UI")


    def send_torque_now():
        """Отправить Id/Iq (всегда с En_Is=True, чтобы зафиксировать токовый режим)."""
        try:
            Id = float(Id_var.get() or 0.0)
            Iq = float(Iq_var.get() or 0.0)
        except Exception:
            ui_log("[UI] Id/Iq: некорректные значения", "ERR"); return

        client.send_json_threadsafe({
            "cmd": "SendTorque",
            "En_Is": True,
            "Isd": Id,
            "Isq": Iq
        })
        ui_log(f"[UI] SendTorque: Id={Id:.2f}, Iq={Iq:.2f}", "UI")


    def set_mode_from_ui():
        """Кнопка 'Применить режим' — вызывает ту же логику, что и радиокнопки."""
        # просто переиспользуем текущий режим
        if mode_var.get() == "speed":
            # включаем частоту
            send_control_now()
        else:
            # включаем токи + сразу текущие Id/Iq (как мы делали при переключении)
            send_control_now()
            send_torque_now()


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

        # --- Новый переключатель режима ---
    mode_frame = ttk.LabelFrame(main_inner, text="Режим управления")
    mode_frame.place(x=10, y=10, width=710, height=90)

    # текущее значение режима: "currents" (токи) или "speed" (частота)
    mode_var = tk.StringVar(value="currents")

    def update_mode_controls():
        # включаем/выключаем ползунки в зависимости от режима
        if mode_var.get() == "speed":
            speed_slider.state(["!disabled"])
            speed_entry.config(state="normal")
            torque_slider.state(["disabled"])
            torque_entry.config(state="disabled")
        else:
            speed_slider.state(["disabled"])
            speed_entry.config(state="disabled")
            torque_slider.state(["!disabled"])
            torque_entry.config(state="normal")

    def set_mode(val: str):
        mode_var.set(val)
        if val == "currents":
            # переходим в режим токов — включаем удалёнку, выключаем Kl_15
            client.send_json_threadsafe({"cmd": "SendControl", "En_Is": True, "Kl_15": False})
            # сразу пробрасываем текущие Id/Iq (обязательно с En_Is=True)
            client.send_json_threadsafe({
                "cmd": "SendTorque",
                "En_Is": True,
                "Isd": float(Id_var.get() or 0.0),
                "Isq": float(Iq_var.get() or 0.0)
            })
            ui_log("[UI] Режим: Токи (Id/Iq) — En_Is=1, Kl_15=0, отправлены текущие Id/Iq", "UI")
        else:
            # переходим в режим частоты — выключаем удалёнку, включаем Kl_15 и передаём ns
            client.send_json_threadsafe({
                "cmd": "SendControl",
                "En_Is": False,
                "Kl_15": True,
                "ns": float(speed_var.get() or 0.0)
            })
            ui_log("[UI] Режим: Частота (ns) — En_Is=0, Kl_15=1, передан ns", "UI")

        update_mode_controls()

    # сами «сегменты» — две радиокнопки
    rb1 = ttk.Radiobutton(mode_frame, text="Токи (Id/Iq)",
                        value="currents", variable=mode_var,
                        command=lambda: set_mode("currents"))
    rb2 = ttk.Radiobutton(mode_frame, text="Частота (ns)",
                        value="speed", variable=mode_var,
                        command=lambda: set_mode("speed"))

    rb1.grid(row=0, column=0, padx=8, pady=8, sticky="w")
    rb2.grid(row=0, column=1, padx=8, pady=8, sticky="w")


    # Кнопки управления
    control_frame = ttk.Frame(main_inner)
    control_frame.pack(padx=10, pady=10, fill="x")

    # ====== Блок "Токи (Id/Iq)" ======
    currents_frame = ttk.LabelFrame(main_inner, text="Токи (Id/Iq)")
    currents_frame.place(x=10, y=120, width=340, height=120)

    En_Is_var = tk.IntVar(value=1)
    Id_var = tk.StringVar(value="-0.5")
    Iq_var = tk.StringVar(value="0.0")

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
    # ==== КНОПКИ ДЕЙСТВИЙ ====
    extra_frame = ttk.Frame(main_inner)
    extra_frame.pack(padx=10, pady=(0,10), fill="x")

    # Применить режим (замена старой SendControl-кнопки)
    ttk.Button(
        extra_frame, text="Применить режим", width=18,
        command=set_mode_from_ui
    ).pack(side="left", padx=5)

    # Лимиты
    ttk.Button(
        extra_frame, text="SendLimits", width=15,
        command=send_limits_now
    ).pack(side="left", padx=5)

    # Токи Id/Iq
    ttk.Button(
        extra_frame, text="SendTorque (Id/Iq)", width=20,
        command=send_torque_now
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

    # --- Переключатель режима (новый) ---
    mode_frame = ttk.LabelFrame(main_inner, text="Режим управления")
    mode_frame.place(x=10, y=10, width=710, height=90)

    mode_var = tk.StringVar(value="currents")

    def update_mode_controls():
        if mode_var.get() == "speed":
            speed_slider.state(["!disabled"])
            speed_entry.config(state="normal")
            torque_slider.state(["disabled"])
            torque_entry.config(state="disabled")
        else:
            speed_slider.state(["disabled"])
            speed_entry.config(state="disabled")
            torque_slider.state(["!disabled"])
            torque_entry.config(state="normal")

    def _on_speed_released(_=None):
        if mode_var.get() == "speed":
            client.send_json_threadsafe({
                "cmd": "SendControl",
                "En_Is": False,
                "Kl_15": True,
                "ns": float(speed_var.get() or 0.0),
            })
            ui_log(f"[UI] Обновлено ns={speed_var.get():.0f} (режим Частота)")

    def _on_torque_released(_=None):
        if mode_var.get() == "currents":
            client.send_json_threadsafe({
                "cmd": "SendTorque",
                "En_Is": True,
                "Isd": float(Id_var.get() or 0.0),
                "Isq": float(Iq_var.get() or 0.0),
            })
            ui_log("[UI] Обновлены Id/Iq (по отпусканию ползунка момента)")

    speed_slider.bind("<ButtonRelease-1>", _on_speed_released)
    torque_slider.bind("<ButtonRelease-1>", _on_torque_released)


    def set_mode(val: str):
        mode_var.set(val)
        if val == "currents":
            # включаем удалёнку, выключаем Kl_15, сразу прокидываем Id/Iq
            client.send_json_threadsafe({"cmd": "SendControl", "En_Is": True, "Kl_15": False})
            client.send_json_threadsafe({
                "cmd": "SendTorque",
                "En_Is": True,
                "Isd": float(Id_var.get() or 0.0),
                "Isq": float(Iq_var.get() or 0.0)
            })
            ui_log("[UI] Режим: Токи (Id/Iq) — En_Is=1, Kl_15=0, отправлены текущие Id/Iq")
        else:
            # выключаем удалёнку, включаем Kl_15, передаём ns
            client.send_json_threadsafe({
                "cmd": "SendControl",
                "En_Is": False,
                "Kl_15": True,
                "ns": float(speed_var.get() or 0.0)
            })
            ui_log("[UI] Режим: Частота (ns) — En_Is=0, Kl_15=1, передан ns")

        update_mode_controls()

    ttk.Radiobutton(mode_frame, text="Токи (Id/Iq)", value="currents",
                    variable=mode_var, command=lambda: set_mode("currents"))\
    .grid(row=0, column=0, padx=8, pady=8, sticky="w")

    ttk.Radiobutton(mode_frame, text="Частота (ns)", value="speed",
                    variable=mode_var, command=lambda: set_mode("speed"))\
    .grid(row=0, column=1, padx=8, pady=8, sticky="w")


    # Вкладка 3: лог
    log_box.pack(in_=log_frame, fill="both", padx=10, pady=10, expand=True)

    def _init_mode():
        set_mode("currents")   # или "speed"
    root.after(0, _init_mode)

    root.mainloop()

if __name__ == "__main__":
    create_gui()