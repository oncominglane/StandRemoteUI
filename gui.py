import tkinter as tk
from tkinter import Tk, ttk, Text, StringVar, Entry, Frame

def create_gui():
    root = tk.Tk()
    root.title("Удаленное управление стендом")
    root.geometry("950x700")
    root.state('zoomed')

     # --- Вкладки ---
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    # Вкладка 1: управление и параметры
    main_frame = ttk.Frame(notebook)
    notebook.add(main_frame, text="Управление")
    main_inner = ttk.Frame(main_frame)
    main_inner.pack(anchor="n", fill="x")  # прижать вверх
    # Вкладка 2: индикация
    ind_frame = ttk.Frame(notebook)
    notebook.add(ind_frame, text="Индикация")
    # Вкладка 3: лог
    log_frame = ttk.Frame(notebook)
    notebook.add(log_frame, text="Журнал")

    # Вкладка 1
    # --- Верхний блок: кнопки управления -
    control_frame = ttk.Frame(main_inner)
    control_frame.pack(padx=10, pady=10, fill="x")
    ttk.Button(control_frame, text="▶ Старт", width=15).pack(side="left", padx=5)
    ttk.Button(control_frame, text="■ Стоп", width=15).pack(side="left", padx=5)
    ttk.Button(control_frame, text="↺ Сброс", width=15).pack(side="left", padx=5)
    ttk.Button(control_frame, text="💾 Сохранить", width=15).pack(side="left", padx=5)
    
    # --- Средний блок: параметры (ввод + текущие значения) ---
    params_frame = ttk.LabelFrame(main_inner, text="Параметры стенда")
    params_frame.pack(padx=10, pady=10, fill="both", expand=True)
    # Пример строк параметров
    params = [
        "Скорость вращения", "Iq", "Id", "Температура статора", "Температура ротора"
    ]
    entry_vars = {}
    for i, param in enumerate(params):
        ttk.Label(params_frame, text=param + ":").grid(row=i, column=0, sticky="e", padx=5, pady=5)
        var = tk.StringVar()
        entry = ttk.Entry(params_frame, textvariable=var, width=20)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entry_vars[param] = var

    # Вкладка 3
    log_box = tk.Text(log_frame, height=20, wrap="word")
    log_box.pack(fill="both", padx=10, pady=10, anchor="n")

    root.mainloop()

if __name__ == "__main__":
    create_gui()