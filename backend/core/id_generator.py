import threading
import time


class IdGenerator:
    def __init__(self, machine_id: int) -> None:
        self._machine_id = machine_id & 0x3FF
        self._lock = threading.Lock()
        self._last_ms = -1
        self._sequence = 0

    def next_id(self) -> int:
        with self._lock:
            current_ms = int(time.time() * 1000)

            if current_ms == self._last_ms:
                self._sequence = (self._sequence + 1) & 0xFFF
            else:
                self._sequence = 0
                self._last_ms = current_ms

            return ((current_ms - 1_700_000_000_000) << 22) | (self._machine_id << 12) | self._sequence
