import tkinter as tk
from tkinter import Tk, ttk, Text, StringVar, Entry, Frame

active_scale = None  # будет указывать на текущий выбранный ползунок
def make_focusable_scale(scale, var, step=1.0):
    def on_click(event):
        global active_scale
        active_scale = (scale, var, step)
        scale.focus_set()

    scale.bind("<Button-1>", on_click)

 # Привязка к ttk.Scale и переменной
def on_arrow_key(event):
    global active_scale
    if active_scale is None:
        return
    scale, var, step = active_scale
    value = var.get()
    if event.keysym == "Up":
        var.set(value + step)
    elif event.keysym == "Down":
        var.set(value - step)

def create_gui():
    root = tk.Tk()
    root.title("Удаленное управление стендом")
    root.geometry("950x700+100+100")
    root.state('zoomed')

    root.bind("<Up>", on_arrow_key)
    root.bind("<Down>", on_arrow_key)

    # --- Вкладки ---
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    # Вкладка 1: управление и параметры
    main_frame = ttk.Frame(notebook)
    notebook.add(main_frame, text="Управление")
    # Вкладка 2: индикация
    ind_frame = ttk.Frame(notebook)
    notebook.add(ind_frame, text="Индикация")
    # Вкладка 3: лог
    log_frame = ttk.Frame(notebook)
    notebook.add(log_frame, text="Журнал")

    # Вкладка 1 
    main_inner = ttk.Frame(main_frame)
    main_inner.pack(fill="both", expand=True)

    # --- Контейнер с основными кнопками ---
    control_frame = ttk.Frame(main_inner)
    control_frame.pack(padx=10, pady=10, fill="x")
    ttk.Button(control_frame, text="▶ Старт", width=15).pack(side="left", padx=5)
    ttk.Button(control_frame, text="■ Стоп", width=15).pack(side="left", padx=5)
    ttk.Button(control_frame, text="↺ Сброс", width=15).pack(side="left", padx=5)
    ttk.Button(control_frame, text="💾 Сохранить", width=15).pack(side="left", padx=5)

   # --- Контейнер с параметрами ---
    params_frame = ttk.LabelFrame(main_inner, text="Параметры стенда")
    params_frame.place(x=10, y=50, width=700, height=300)
    params = ["Скорость вращения", "Iq", "Id", "Температура статора", "Температура ротора"] # Пример строк параметров
    entry_vars = {}
    for i, param in enumerate(params):
        ttk.Label(params_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(params_frame, textvariable=var, width=20)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entry_vars[param] = var

    # --- Контейнер с CAN сообщениями ---
    can_frame = ttk.LabelFrame(main_inner, text="Tx / Rx CAN")
    can_frame.place(x=10, y=350, width=710, height=120)
    can_cells = []
    ttk.Label(can_frame, text="id", anchor="center").grid(row=0, column=1, padx=2, pady=(0, 5))
    for col in range(1, 9):
        ttk.Label(can_frame, text=f"data{col-1}", anchor="center").grid(row=0, column=col + 1, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="len", anchor="center").grid(row=0, column=10, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="flags", anchor="center").grid(row=0, column=11, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="ts", anchor="center").grid(row=0, column=12, padx=2, pady=(0, 5))
    ttk.Label(can_frame, text="Tx:").grid(row=1, column=0, sticky="e", padx=3)
    ttk.Label(can_frame, text="Rx:").grid(row=2, column=0, sticky="e", padx=3)
    for row in range(2):  # 2 строки: 0 - Tx, 1 - Rx
        for col in range(1,13):  # 12 ячеек в строке
            var = StringVar()
            entry = Entry(can_frame, textvariable=var, width=8, justify="center")
            entry.grid(row=row+1, column=col, padx=2, pady=2)
            can_cells.append(var)  # можно потом обращаться по индексу


    # --- Режим управления ---
    control_mode_var = tk.StringVar()
    ttk.Label(main_inner, text="Режим управления:").place(x=750, y=10)
    mode_combo = ttk.Combobox(main_inner, textvariable=control_mode_var, values=["-", "Режим 1", "Режим 2"], state="readonly", width=20)
    mode_combo.current(0)
    mode_combo.place(x=750, y=30)
    # --- Контейнер для ползунков ---
    slider_frame = ttk.Frame(main_inner, width=180, height=450)
    slider_frame.place(x=750, y=60)
    slider_frame.pack_propagate(False)
    speed_var = tk.DoubleVar()
    torque_var = tk.DoubleVar()
    # --- Подписи ---
    ttk.Label(slider_frame, text="Скорость\nоб/мин").place(x=10, y=0)
    ttk.Label(slider_frame, text="Момент\nН·м").place(x=100, y=0)

   
    # --- Ползунки ---
    speed_slider = ttk.Scale(slider_frame, from_=20000, to=0, variable=speed_var, orient="vertical", length=300)
    speed_slider.place(x=10, y=40)
    speed_slider.state(["disabled"])
    speed_slider.bind("<Button-1>", lambda e: speed_slider.focus_set()) 
    make_focusable_scale(speed_slider, speed_var, step=100)
    
    torque_slider = ttk.Scale(slider_frame, from_=500, to=0, variable=torque_var, orient="vertical", length=300)
    torque_slider.place(x=100, y=40)
    torque_slider.state(["disabled"])
    torque_slider.bind("<Button-1>", lambda e: speed_slider.focus_set())
    make_focusable_scale(torque_slider, torque_var, step=0.0)
    # --- Entry-поля ---
    speed_entry = ttk.Entry(slider_frame, textvariable=speed_var, width=6, state="disabled")
    speed_entry.place(x=10, y=350)
    torque_entry = ttk.Entry(slider_frame, textvariable=torque_var, width=6, state="disabled")
    torque_entry.place(x=100, y=350)
    # --- Показывать ползунки при выборе режима ---
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
   















    # Вкладка 3
    log_box = tk.Text(log_frame, height=20, wrap="word")
    log_box.pack(fill="both", padx=10, pady=10, anchor="n")




    root.mainloop()

if __name__ == "__main__":
    create_gui()