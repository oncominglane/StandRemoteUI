import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, QCheckBox,
    QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox, QScrollArea
)
from PyQt5.QtChart import QChart, QChartView, QLineSeries
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt


class MarathonGUI(QWidget):
    def __init__(self):
        super().__init__()

        # === Основные параметры окна ===
        self.setWindowTitle("CAN Marathon - Каркас интерфейса")
        self.setFixedSize(1600, 900)
        self.setStyleSheet("background-color: #F0F0F0;")  # Светло-серый фон

        # === Основной контейнер ===
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_widget = QWidget()
        scroll_area.setWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # ==========================
        # ЛЕВАЯ КОЛОНКА (CAN + Rx/Tx)
        # ==========================
        left_layout = QVBoxLayout()

        # === CAN Настройки ===
        can_group = self.create_group("CAN Настройки")
        can_layout = QGridLayout()
        can_labels = ["Can-Board", "Can-Ch", "Can-Baud", "AMask", "ACode", "Flags"]
        for i, label in enumerate(can_labels):
            can_layout.addWidget(QLabel(label), i, 0)
            can_layout.addWidget(QLineEdit(), i, 1)
        can_group.setLayout(can_layout)
        left_layout.addWidget(can_group)

        # === Ошибки CAN ===
        errs_group = self.create_group("Ошибки CAN")
        errs_layout = QGridLayout()
        errs_labels = ["ewl", "boff", "hwovr", "swovr", "wtout", "Rx-err out", "Tx-err out"]
        for i, label in enumerate(errs_labels):
            errs_layout.addWidget(QLabel(label), i, 0)
            errs_layout.addWidget(QLineEdit(), i, 1)
        errs_group.setLayout(errs_layout)
        left_layout.addWidget(errs_group)

        # === Rx-Can ===
        rx_group = self.create_group("Rx-Can")
        rx_layout = QGridLayout()
        rx_fields = ["id", "len", "flags"] + [f"data[{i}]" for i in range(8)]
        for i, label in enumerate(rx_fields):
            rx_layout.addWidget(QLabel(label), i, 0)
            rx_layout.addWidget(QLineEdit(), i, 1)
        rx_group.setLayout(rx_layout)
        left_layout.addWidget(rx_group)

        # === Tx-Can ===
        tx_group = self.create_group("Tx-Can")
        tx_layout = QGridLayout()
        tx_fields = ["id", "len", "flags"] + [f"data[{i}]" for i in range(8)]
        for i, label in enumerate(tx_fields):
            tx_layout.addWidget(QLabel(label), i, 0)
            tx_layout.addWidget(QLineEdit(), i, 1)
        tx_group.setLayout(tx_layout)
        left_layout.addWidget(tx_group)

        main_layout.addLayout(left_layout)

        # ==========================
        # ПРАВАЯ КОЛОНКА (управление, параметры)
        # ==========================
        right_layout = QVBoxLayout()

        # === Управление ===
        ctrl_group = self.create_group("Управление")
        ctrl_layout = QHBoxLayout()
        for name in ["Init", "Stop", "Read2", "Save_Cfg", "Read_Cfg"]:
            btn = QPushButton(name)
            btn.setFixedWidth(100)
            ctrl_layout.addWidget(btn)
        ctrl_group.setLayout(ctrl_layout)
        right_layout.addWidget(ctrl_group)

        # === Опции ===
        opts_group = self.create_group("Опции")
        opts_layout = QHBoxLayout()
        for text in ["Kl_15", "Brake Active", "TCS Active", "En_rem", "En_Is"]:
            opts_layout.addWidget(QCheckBox(text))
        opts_group.setLayout(opts_layout)
        right_layout.addWidget(opts_group)

        # === Ограничения ===
        limits_group = self.create_group("Ограничения")
        limits_layout = QGridLayout()
        for label in ["M_max", "M_min", "M_grad_max", "dM_damp_Ctrl", "i_R", "n_max", "T_Str_max"]:
            row = limits_layout.rowCount()
            limits_layout.addWidget(QLabel(label), row, 0)
            limits_layout.addWidget(QLineEdit(), row, 1)
        limits_group.setLayout(limits_layout)
        right_layout.addWidget(limits_group)

        # === Онлайн-индикация ===
        values_group = self.create_group("Онлайн-индикация")
        values_layout = QGridLayout()
        for label in ["Ms [Нм]", "ns [об/мин]", "Idc [A]", "Isd [A]", "Isq [A]", "Udc [V]", "Pe_dc [W]"]:
            row = values_layout.rowCount()
            values_layout.addWidget(QLabel(label), row, 0)
            values_layout.addWidget(QLineEdit(), row, 1)
        values_group.setLayout(values_layout)
        right_layout.addWidget(values_group)

        # === Температуры ===
        temp_group = self.create_group("Температуры")
        temp_layout = QGridLayout()
        for label in ["IGBT-U", "IGBT-V", "IGBT-W", "IGBT Max", "Статор", "NTC1", "NTC2", "Охлажд."]:
            row = temp_layout.rowCount()
            temp_layout.addWidget(QLabel(label), row, 0)
            temp_layout.addWidget(QLineEdit(), row, 1)
        temp_group.setLayout(temp_layout)
        right_layout.addWidget(temp_group)

        # === Статусы ===
        status_group = self.create_group("Статусы")
        status_layout = QGridLayout()
        for label in ["MCU-Status", "М-статус", "n-статус", "GateDrv"]:
            row = status_layout.rowCount()
            status_layout.addWidget(QLabel(label), row, 0)
            status_layout.addWidget(QLineEdit(), row, 1)
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)

        # === Версии ПО ===
        ver_group = self.create_group("Версии ПО")
        ver_layout = QGridLayout()
        for label in ["MCU SW-ver", "MCU HW-ver", "CPLD SW-ver", "Hv SW-ver", "Calib SW-ver"]:
            row = ver_layout.rowCount()
            ver_layout.addWidget(QLabel(label), row, 0)
            ver_layout.addWidget(QLineEdit(), row, 1)
        ver_group.setLayout(ver_layout)
        right_layout.addWidget(ver_group)

        main_layout.addLayout(right_layout)

        # === График ===
        chart_group = self.create_group("График Moment vs Speed")
        chart = QChart()
        series = QLineSeries()
        series.append(0, 0)
        series.append(500, 5)
        series.append(1000, 10)
        chart.addSeries(series)
        chart.createDefaultAxes()
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_layout = QVBoxLayout()
        chart_layout.addWidget(chart_view)
        chart_group.setLayout(chart_layout)

        root_layout = QVBoxLayout()
        root_layout.addWidget(scroll_area)
        root_layout.addWidget(chart_group)
        self.setLayout(root_layout)

    def create_group(self, title):
        group = QGroupBox(title)
        return group


if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = MarathonGUI()
    gui.show()
    sys.exit(app.exec_())
