import tkinter as tk
from tkinter import Tk, ttk, Text, StringVar, Entry, Frame
import json
import time
from datetime import datetime
import csv
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque

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
    root.title("StandRemoteGUI")
    root.geometry("1080x740+100+100")
    try:
        root.state("zoomed")
    except Exception:
        pass
    style = init_style(dark=False)  # dark=True для тёмной темы

    # Индикатор статуса (цветная «пилюля»)
    conn_var = tk.StringVar(value="disabled")
    conn_color = tk.StringVar(value="#d72c20")  # красный

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
    ttk.Button(toolbar, text="▶ Start", width=14, style="Accent.TButton",
               command=lambda: client.send_cmd_threadsafe("Init")).pack(side="left", padx=(PAD, 4), pady=PAD)
    ttk.Button(toolbar, text="■ Stop", width=14,
               command=lambda: client.send_cmd_threadsafe("Stop")).pack(side="left", padx=4, pady=PAD)
    ttk.Button(toolbar, text="↺ Reset", width=14,
               command=lambda: client.send_cmd_threadsafe("Read2")).pack(side="left", padx=4, pady=PAD)
    ttk.Button(toolbar, text="💾 Save", width=14,
               command=lambda: client.send_cmd_threadsafe("SaveCfg")).pack(side="left", padx=4, pady=PAD)

    # Индикатор соединения справа
    pill(toolbar, conn_var, conn_color).pack(side="right", padx=PAD, pady=PAD)

    
    # Коллбеки для WS с безопасным обновлением из главного потока
    log_box = tk.Text(root, height=10, wrap="word")
    def ui_log(*parts):
        msg = " ".join(str(p) for p in parts).strip()
        log_box.insert("end", msg + "\n")
        log_box.see("end")

    # Глобальные переменные для CAN данных
    can_rx_data = [StringVar() for _ in range(12)]  # 12 полей для Rx CAN
    can_tx_data = [StringVar() for _ in range(12)]  # 12 полей для Tx CAN

    # Журнал телеметрии
    log_enabled = tk.BooleanVar(value=True)
    log_rows = []  # список словарей
    max_rows = 5000  # ограничение на длину буфера/таблицы

    # Колонки журнала (порядок)
    TELEM_COLUMNS = [
        "ts",
        "ns", "Ms",
        "Idc", "Isd",
        "Ud", "Uq", "Id", "Iq",
        "Emf", "Welectrical", "motorRs", "Wmechanical",
    ]

    # Буферы для трендов (последние N точек)
    TREND_CAP = 3000  # сколько точек держим на графиках
    trend_ts   = deque(maxlen=TREND_CAP)  # datetime для оси X
    trend_ns   = deque(maxlen=TREND_CAP)
    trend_Ms   = deque(maxlen=TREND_CAP)
    trend_Idc  = deque(maxlen=TREND_CAP)
    trend_Isd  = deque(maxlen=TREND_CAP)
    trend_Ud   = deque(maxlen=TREND_CAP)
    trend_Uq   = deque(maxlen=TREND_CAP)
    trend_Id   = deque(maxlen=TREND_CAP)
    trend_Iq   = deque(maxlen=TREND_CAP)


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
            ui_log("[UI] Id/Iq: incorrect values", "ERR"); return

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
        try:
            data = json.loads(msg)
        except json.JSONDecodeError:
            root.after(0, lambda: ui_log("❌ Couldn't parse JSON"))
            return

        def _ui_work():
            ui_log(f"[RX] {msg}")
            if data.get("type") == "can_frame":
                handle_can_frame(data)
            elif any(k in data for k in ["Ms", "ns", "Isd", "Udc", "Ud", "Uq", "Id", "Iq"]):
                handle_model_data(data)   # теперь точно в UI-потоке
            else:
                ui_log("⚠ Unknown message type")

        root.after(0, _ui_work)
    
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

    # ===== журнал телеметрии =====
    def log_telemetry_row(data):
        """Собрать строку журнала, добавить в буфер и в таблицу."""
        if not log_enabled.get():
            return

        row = {}
        row["ts"] = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        for k in TELEM_COLUMNS:
            if k == "ts":
                continue
            if k in data:
                row[k] = data[k]
        # если ничего нового нет — не шумим
        if len(row) <= 1:
            return

        log_rows.append(row)
        if len(log_rows) > max_rows:
            del log_rows[0]
            kids = telem_tree.get_children()
            if kids:
                telem_tree.delete(kids[0])

        telem_tree.insert("", "end", values=[row.get(k, "") for k in TELEM_COLUMNS])

         # === подпитаем тренды ===
        now = datetime.now()
        trend_ts.append(now)
        if "ns" in data:  trend_ns.append(float(data["ns"]))
        if "Ms" in data:  trend_Ms.append(float(data["Ms"]))
        if "Idc" in data: trend_Idc.append(float(data["Idc"]))
        if "Isd" in data: trend_Isd.append(float(data["Isd"]))
        if "Ud" in data:  trend_Ud.append(float(data["Ud"]))
        if "Uq" in data:  trend_Uq.append(float(data["Uq"]))
        if "Id" in data:  trend_Id.append(float(data["Id"]))
        if "Iq" in data:  trend_Iq.append(float(data["Iq"]))

    def _update_trends():
        # ось X — секунды относительно последней точки
        if not trend_ts:
            root.after(500, _update_trends)
            return
        t0 = trend_ts[-1]
        xs = [(t - t0).total_seconds() for t in trend_ts]  # идут отрицательные числа (в прошлое)

        # обновляем данные линий
        if trend_ns:
            l_ns.set_data(xs[-len(trend_ns):], list(trend_ns))
            ax1.relim(); ax1.autoscale_view()

        if trend_Ms:
            l_ms.set_data(xs[-len(trend_Ms):], list(trend_Ms))
            ax2.relim(); ax2.autoscale_view()

        if trend_Idc:
            l_idc.set_data(xs[-len(trend_Idc):], list(trend_Idc))
        if trend_Isd:
            l_isd.set_data(xs[-len(trend_Isd):], list(trend_Isd))
        ax3.relim(); ax3.autoscale_view()

        # внизу рисуем Id/Iq и Ud/Uq одним графиком: если нет одних — будут другие
        if trend_Id:
            l_id.set_data(xs[-len(trend_Id):], list(trend_Id))
        if trend_Iq:
            l_iq.set_data(xs[-len(trend_Iq):], list(trend_Iq))
        if trend_Ud:
            l_ud.set_data(xs[-len(trend_Ud):], list(trend_Ud))
        if trend_Uq:
            l_uq.set_data(xs[-len(trend_Uq):], list(trend_Uq))
        ax4.relim(); ax4.autoscale_view()

        # едва заметные подписи оси X
        for ax in (ax1, ax2, ax3, ax4):
            ax.set_xlabel("seconds from now")

        canvas.draw_idle()
        root.after(500, _update_trends)  # ~2 FPS; можно 200мс для плавнее    

    def handle_model_data(data):
        field_map = {
            # Параметры стенда
            "ns": "Скорость вращения",
            "Ms": "Момент (Ms)",
            "Idc": "Ток постоянного (Idc)",
            "Isd": "Ток статора d (Isd)",
            "MCU_IGBTTempU": "Температура статора",
            "MCU_TempCurrStr": "Температура ротора",

            # MCU Current & Voltage
            "Ud": "Ud",
            "Uq": "Uq",
            "Id": "Id",
            "Iq": "Iq",

            # MCU Flux Parameters
            "Emf": "Emf",
            "Welectrical": "Welectrical",
            "motorRs": "motorRs",
            "Wmechanical": "Wmechanical",
        }

        for key, label in field_map.items():
            if key in data and label in entry_vars:
                entry_vars[label].set(str(data[key]))

        # Доп. лог (опционально)
        for key in ("Ms", "Idc", "Isd", "ns", "Udc"):
            if key in data:
                ui_log(f"{key}: {data[key]}")
        
        # строка в журнал
        log_telemetry_row(data)

    
    
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
            ui_log("[UI] Sent a FakeCAN from the fields: Id/Iq, Torque, Speed")
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
    notebook.add(main_frame, text="Control")
    ind_frame = ttk.Frame(notebook)
    notebook.add(ind_frame, text="Indication")
    log_frame = ttk.Frame(notebook)
    notebook.add(log_frame, text="Logbook")
    trends_frame = ttk.Frame(notebook)
    notebook.add(trends_frame, text="Trends")

    # === Trends UI ===
    trends_container = ttk.Frame(trends_frame)
    trends_container.pack(fill="both", expand=True, padx=10, pady=10)

    fig = Figure(figsize=(8, 5), dpi=100)
    ax1 = fig.add_subplot(221)  # Speed (ns)
    ax2 = fig.add_subplot(222)  # Torque (Ms)
    ax3 = fig.add_subplot(223)  # Currents (Idc/Isd)
    ax4 = fig.add_subplot(224)  # dq currents/voltages (Id/Iq or Ud/Uq)

    ax1.set_title("Speed (ns)")
    ax2.set_title("Torque (Ms)")
    ax3.set_title("Currents (Idc / Isd)")
    ax4.set_title("dq (Id/Iq) and Voltages (Ud/Uq)")

    # линии (пустые на старте)
    l_ns, = ax1.plot([], [])
    l_ms, = ax2.plot([], [])
    l_idc, = ax3.plot([], [])
    l_isd, = ax3.plot([], [])
    l_id, = ax4.plot([], [])
    l_iq, = ax4.plot([], [])
    l_ud, = ax4.plot([], [])
    l_uq, = ax4.plot([], [])

    for ax in (ax1, ax2, ax3, ax4):
        ax.grid(True)

    canvas = FigureCanvasTkAgg(fig, master=trends_container)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill="both", expand=True)

    notebook.enable_traversal()

    # Вкладка 1
    main_inner = ttk.Frame(main_frame)
    main_inner.pack(fill="both", expand=True)

    for i in range(3):
        main_inner.grid_columnconfigure(i, weight=1)   # 2 левые колонки растягиваются
    main_inner.grid_columnconfigure(2, weight=0)       # правая колонка под слайдеры
    for r in range(10):
        main_inner.grid_rowconfigure(r, weight=0)

    controls_container = ttk.Frame(main_inner)
    controls_container.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

    # Сетка: 3 колонки (левая/средняя/правая-«слайдеры»)
    for col in (0, 1):
        main_inner.columnconfigure(col, weight=1)   # растягиваем контент
    main_inner.columnconfigure(2, weight=0)         # колонка со слайдерами фикс ширины
    # строки, где большие панели, пусть растягиваются
    for r in (2, 3):
        main_inner.rowconfigure(r, weight=1)


        # ---  переключатель режима ---
    mode_frame = ttk.LabelFrame(main_inner, text="Control mode")
    mode_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

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
    rb1 = ttk.Radiobutton(mode_frame, text="Currents (Id/Iq)",
                        value="currents", variable=mode_var,
                        command=lambda: set_mode("currents"))
    rb2 = ttk.Radiobutton(mode_frame, text="Frequency (ns)",
                        value="speed", variable=mode_var,
                        command=lambda: set_mode("speed"))

    rb1.grid(row=0, column=0, padx=8, pady=8, sticky="w")
    rb2.grid(row=0, column=1, padx=8, pady=8, sticky="w")


    # Кнопки управления
    control_frame = ttk.Frame(controls_container)
    control_frame.pack(padx=10, pady=10, fill="x")

    # ====== Блок "Токи (Id/Iq)" ======
    currents_frame = ttk.LabelFrame(main_inner, text="Currents")
    currents_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

    En_Is_var = tk.IntVar(value=1)
    Id_var = tk.StringVar(value="-0.5")
    Iq_var = tk.StringVar(value="0.0")

    ttk.Label(currents_frame, text="Id [A]").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    ttk.Entry(currents_frame, width=10, textvariable=Id_var).grid(row=1, column=1, sticky="w")

    ttk.Label(currents_frame, text="Iq [A]").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(currents_frame, width=10, textvariable=Iq_var).grid(row=1, column=3, sticky="w")

    # ====== Блок "Лимиты" ======
    limits_frame = ttk.LabelFrame(main_inner, text="Limits")
    limits_frame.grid(  row=1, column=1, padx=10, pady=10, sticky="nsew")

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

    ttk.Label(limits_frame, text="n_max [rpm]").grid(row=1, column=2, sticky="e", padx=6, pady=6)
    ttk.Entry(limits_frame, width=10, textvariable=n_max_var).grid(row=1, column=3, sticky="w")

    # Доп. команды
    extra_frame = ttk.Frame(controls_container)
    extra_frame.pack(padx=0, pady=(6, 0), fill="x")

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
    params_frame = ttk.LabelFrame(main_inner, text="MCU_VCU_parameters")
    params_frame.grid(  row=2, column=0, columnspan=2, padx=10, pady=0, sticky="nsew")
    params = [
        "Speed вращения",
        "Torque (Ms)",       # новый
        "Constant current (Idc)", # новый
        "Stator currentd (Isd)",   # новый
        "stator temperature",
        "Rotor temperature",
    ]
    

    


    entry_vars = {}
    for i, param in enumerate(params):
        ttk.Label(params_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(params_frame, textvariable=var, width=20)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entry_vars[param] = var

    # CAN - используем заранее созданные переменные
    can_frame = ttk.LabelFrame(main_inner, text="Tx / Rx CAN")
    can_frame.grid(     row=3, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
    
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
    voltage_frame.grid( row=4, column=0, padx=10, pady=10, sticky="nsew")

    voltage_params = ["Ud", "Uq", "Id", "Iq"]
    for i, param in enumerate(voltage_params):
        ttk.Label(voltage_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(voltage_frame, textvariable=var, width=15)
        entry.grid(row=i, column=1, padx=5, pady=3)
        entry_vars[param] = var

    # Блок MCU_FluxParams
    flux_frame = ttk.LabelFrame(main_inner, text="MCU Flux Parameters")
    flux_frame.grid(    row=4, column=1, padx=10, pady=10, sticky="nsew")

    flux_params = ["Emf", "Welectrical", "motorRs", "Wmechanical"]
    for i, param in enumerate(flux_params):
        ttk.Label(flux_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=3)
        var = tk.StringVar()
        entry = ttk.Entry(flux_frame, textvariable=var, width=15)
        entry.grid(row=i, column=1, padx=5, pady=3)
        entry_vars[param] = var
    
    # Правая колонка: слайдеры
    slider_frame = ttk.Frame(main_inner, width=180, height=450)
    slider_frame.grid(  row=0, column=2, rowspan=6, padx=10, pady=10, sticky="ns")
    slider_frame.pack_propagate(False)

    speed_var = tk.DoubleVar()
    torque_var = tk.DoubleVar()

    # layout на grid (без .place)
    slider_frame.grid_columnconfigure(0, weight=1, minsize=80)
    slider_frame.grid_columnconfigure(1, weight=1, minsize=80)
    
    ttk.Label(slider_frame, text="Speed\nrpm").grid(row=0, column=0, pady=(0,4))
    ttk.Label(slider_frame,  text="Torque\nN*m").grid(    row=0, column=1, pady=(0,4))

    speed_slider = ttk.Scale(slider_frame, from_=20000, to=0, variable=speed_var, orient="vertical", length=300)
    speed_slider.grid(row=1, column=0, sticky="ns", padx=6, pady=6)
    speed_slider.state(["disabled"])
    speed_slider.bind("<Button-1>", lambda e: speed_slider.focus_set())
    make_focusable_scale(speed_slider, speed_var, step=100)

    torque_slider = ttk.Scale(slider_frame, from_=500, to=0, variable=torque_var, orient="vertical", length=300)
    torque_slider.grid(row=1, column=1, sticky="ns", padx=6, pady=6)
    torque_slider.state(["disabled"])
    torque_slider.bind("<Button-1>", lambda e: torque_slider.focus_set())
    make_focusable_scale(torque_slider, torque_var, step=1.0)

    speed_entry = ttk.Entry(slider_frame, textvariable=speed_var, width=6, state="disabled")
    speed_entry.grid(row=2, column=0, pady=(4,0))
    torque_entry = ttk.Entry(slider_frame, textvariable=torque_var, width=6, state="disabled")
    torque_entry.grid(row=2, column=1, pady=(4,0))


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
    
    # режим уже создан выше
    update_mode_controls()

    ttk.Radiobutton(mode_frame, text="Currents (Id/Iq)", value="currents",
                    variable=mode_var, command=lambda: set_mode("currents"))\
    .grid(row=0, column=0, padx=8, pady=8, sticky="w")

    ttk.Radiobutton(mode_frame, text="Frequency (ns)", value="speed",
                    variable=mode_var, command=lambda: set_mode("speed"))\
    .grid(row=0, column=1, padx=8, pady=8, sticky="w")


     # === Logbook UI ===
    logbook_top = ttk.Frame(log_frame)
    logbook_top.pack(fill="both", expand=True, padx=10, pady=(10,5))

    # toolbar
    lb_toolbar = ttk.Frame(logbook_top)
    lb_toolbar.pack(fill="x", pady=(0,6))

    def toggle_logging():
        ui_log("📒 logging:", "ON" if log_enabled.get() else "OFF")

    ttk.Checkbutton(lb_toolbar, text="Log telemetry", variable=log_enabled,
                    command=toggle_logging).pack(side="left")

    def clear_log():
        log_rows.clear()
        for i in telem_tree.get_children():
            telem_tree.delete(i)
        ui_log("🧹 journal cleared")

    def export_csv():
        # простой экспорт в файл рядом с клиентом
        fname = f"logbook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(fname, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(TELEM_COLUMNS)
            for row in log_rows:
                w.writerow([row.get(k, "") for k in TELEM_COLUMNS])
        ui_log(f"💾 exported: {fname}")

    ttk.Button(lb_toolbar, text="Clear", command=clear_log).pack(side="right", padx=4)
    ttk.Button(lb_toolbar, text="Export CSV", command=export_csv).pack(side="right", padx=4)

    # таблица
    columns = TELEM_COLUMNS
    telem_tree = ttk.Treeview(logbook_top, columns=columns, show="headings", height=12)
    for col in columns:
        telem_tree.heading(col, text=col)
        telem_tree.column(col, width=100, anchor="center")

    ys = ttk.Scrollbar(logbook_top, orient="vertical", command=telem_tree.yview)
    telem_tree.configure(yscroll=ys.set)

    telem_tree.pack(side="left", fill="both", expand=True)
    ys.pack(side="right", fill="y")

    # нижняя панель с текстовым логом событий
    log_events = ttk.LabelFrame(log_frame, text="Events")
    log_events.pack(fill="both", expand=True, padx=10, pady=(0,10))
    log_box.pack(in_=log_events, fill="both", padx=6, pady=6, expand=True)

    # Горячие клавиши для журнала
    root.bind_all("<Control-l>", lambda e: log_enabled.set(not log_enabled.get()))
    root.bind_all("<Control-e>", lambda e: export_csv())
    root.bind_all("<Control-Shift-C>", lambda e: clear_log())

    def _init_mode():
        set_mode("currents")   # или "speed"
    root.after(0, _init_mode)

    root.after(500, _update_trends)

    root.mainloop()

if __name__ == "__main__":
    create_gui()