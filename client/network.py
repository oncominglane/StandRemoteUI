import asyncio
import json
import threading
import traceback
try:
    import websockets
except ImportError:
    websockets = None  


class WSClient:
    def __init__(self, url, on_message, on_status, on_error):
        self.url = url
        self.on_message = on_message # функция, вызываемая при получении сообщения
        self.on_status = on_status # функция, вызываемая при смене состояния (подключён, отключён и т. п.)
        self.on_error = on_error # функция, вызываемая при ошибке

        self.loop = None # ссылка на asyncio-цикл, который будет обрабатывать сетевые события.
        self.thread = None # поток, в котором будет запущен asyncio-цикл
        self.ws = None  # активное соединение websockets.connect(...) (или None, если нет подключения).
        self._running = threading.Event()  # потокобезопасный флаг («работать/остановиться»).
        self._running.clear()

    def start(self):
        if self.thread and self.thread.is_alive():
            return # если поток уже создан и работает — выходим, повторный запуск не нужен
        self._running.set()
        self.thread = threading.Thread(target=self._run_loop, daemon=True) # Создаём отдельный поток, который будет запускать метод _run_loop().
        self.thread.start() # 

    def stop(self):
        self._running.clear()
        if self.loop and self.loop.is_running():
            def _stop():
                for task in asyncio.all_tasks(loop=self.loop):
                    task.cancel() # отменяем все активные задачи в loop
                self.loop.stop() # останавливаем цикл loop
            self.loop.call_soon_threadsafe(_stop) #

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._connect_forever())
        except Exception as e:
            self.on_error(f"Fatal WS loop error: {e}\n{traceback.format_exc()}")
        finally:
            try:
                if self.loop.is_running():
                    self.loop.stop()
            except Exception:
                pass
            self.loop.close()

    async def _connect_forever(self):
        backoff = 1.0
        while self._running.is_set():
            try:
                self.on_status(f"Подключение к {self.url}...")
                async with websockets.connect(self.url) as ws:
                    self.ws = ws
                    self.on_status("WS подключен")
                    backoff = 1.0
                    while self._running.is_set():
                        msg = await ws.recv()
                        self.on_message(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.on_error(f"WS ошибка: {e}")
                self.on_status("WS отключен")
                self.ws = None
                # экспоненциальный бэкофф
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

    def send_cmd_threadsafe(self, cmd: str):
        """Без await. Можно вызывать из любого потока (в т.ч. из Tk)."""
        if not self.loop:
            self.on_error("WS: нет event loop")
            return
        async def _send():
            if self.ws is None:
                raise RuntimeError("WS не подключен")
            await self.ws.send(json.dumps({"cmd": cmd}))
        fut = asyncio.run_coroutine_threadsafe(_send(), self.loop)
        def _cb(f):
            try:
                f.result()
                self.on_status(f"Отправлено: {cmd}")
            except Exception as e:
                self.on_error(f"Ошибка отправки '{cmd}': {e}")
        fut.add_done_callback(_cb)