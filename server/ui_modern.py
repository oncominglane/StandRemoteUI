import sys
import asyncio
import json
import websockets
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from qasync import QEventLoop  # <--- Новый импорт

WS_URL = "ws://127.0.0.1:9000"

class MarathonUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Marathon Stand Control")
        self.setMinimumSize(1000, 600)
        self.ws = None
        self.data_labels = {}

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_main_tab(), "Главная")
        layout.addWidget(self.tabs)

    def create_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.current_group = self.group_current_data()
        layout.addWidget(self.current_group)

        hbox = QHBoxLayout()
        for cmd in ["Init", "Stop", "Read2", "SaveCfg", "SendControl", "SendLimits", "SendTorque"]:
            btn = QPushButton(cmd)
            btn.clicked.connect(lambda _, c=cmd: asyncio.ensure_future(self.send_cmd(c)))
            hbox.addWidget(btn)
        layout.addLayout(hbox)

        return tab

    def group_current_data(self):
        group = QGroupBox("Текущие параметры")
        layout = QGridLayout()
        params = ["Ms", "ns", "Idc", "Isd", "Isq", "Udc", "MCU_IGBTTempU", "MCU_TempCurrStr"]
        for i, p in enumerate(params):
            lbl_name = QLabel(p)
            lbl_value = QLabel("0")
            self.data_labels[p] = lbl_value
            layout.addWidget(lbl_name, i, 0)
            layout.addWidget(lbl_value, i, 1)
        group.setLayout(layout)
        return group

    async def connect_ws(self):
        async with websockets.connect(WS_URL) as ws:
            self.ws = ws
            print("[WS] Connected to server")
            while True:
                data = await ws.recv()
                obj = json.loads(data)
                for k, v in obj.items():
                    if k in self.data_labels:
                        self.data_labels[k].setText(str(v))

    async def send_cmd(self, cmd):
        if self.ws:
            print(f"[WS] Sending: {cmd}")
            await self.ws.send(json.dumps({"cmd": cmd}))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MarathonUI()
    window.show()

    asyncio.ensure_future(window.connect_ws())

    with loop:
        loop.run_forever()
