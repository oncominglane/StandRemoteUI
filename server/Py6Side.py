import matplotlib.pyplot as plt
import numpy as np
import time
import random

# Настройки графика
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

ax.set_xlabel('Id')
ax.set_ylabel('Iq')
ax.set_zlabel('Ld')

ax.set_xlim(-10, 10)
ax.set_ylim(-10, 10)
ax.set_zlim(-5, 5)

# Начальные данные
Id_data = []
Iq_data = []
Ld_data = []

# Создаём scatter с пустыми данными
scatter = ax.scatter([], [], [], c='b', marker='o')

plt.ion()
plt.show()

try:
    while True:
        # Генерация новых данных
        Id = random.uniform(-10, 10)
        Iq = random.uniform(-10, 10)
        Ld = np.sin(Id/3) + np.cos(Iq/3)

        # Добавляем точку
        Id_data.append(Id)
        Iq_data.append(Iq)
        Ld_data.append(Ld)

        # Ограничиваем размер массива (например, последние 200 точек)
        if len(Id_data) > 200:
            Id_data.pop(0)
            Iq_data.pop(0)
            Ld_data.pop(0)

        # Обновляем данные scatter
        scatter._offsets3d = (Id_data, Iq_data, Ld_data)

        plt.draw()
        plt.pause(1)

        time.sleep(0.5)

except KeyboardInterrupt:
    print("Остановка визуализации")
