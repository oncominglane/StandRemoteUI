import os
import sys
import subprocess

def build_exe(script_name, icon_path=None, no_console=False):
    # Проверяем наличие pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("[INFO] Устанавливаю PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Формируем команду
    command = [
        "pyinstaller",
        "--onefile",       # один exe файл
        "--clean",         # чистка временных файлов
    ]

    if no_console:
        command.append("--noconsole")  # убираем консоль для GUI-приложений

    if icon_path:
        command.append(f"--icon={icon_path}")  # добавляем иконку

    command.append(script_name)  # основной файл

    # Запускаем команду
    print(f"[INFO] Запуск сборки: {' '.join(command)}")
    subprocess.run(command)

    print("\n✅ Сборка завершена!")
    print("📂 Файл находится в папке: dist")

if __name__ == "__main__":
    # Задай имя своего файла ниже
    script_file = "ui_modern.py"  # <-- замени на свой .py файл
    icon = None                  # или путь к иконке .ico (например: "icon.ico")
    gui_mode = True             # True, если хочешь убрать консоль (для GUI)

    build_exe(script_file, icon_path=icon, no_console=gui_mode)
