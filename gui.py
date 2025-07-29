import tkinter as tk

def create_gui():
    root = tk.Tk()
    root.title("Запуск Motor-CAD")
    root.geometry("950x700")
    #root.state('zoomed')
    root.mainloop()

if __name__ == "__main__":
    create_gui()