"""
ON3RT HF Manager V2
modules/cat/command_queue.py
"""

from __future__ import annotations

from collections import deque
from threading import Lock


class CommandQueue:

    def __init__(self):
        self._queue = deque()
        self._lock = Lock()

    def put(self, command, *args, **kwargs):
        with self._lock:
            self._queue.append((command, args, kwargs))

    def get(self):
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()

    def clear(self):
        with self._lock:
            self._queue.clear()

    def empty(self):
        with self._lock:
            return len(self._queue) == 0

    def size(self):
        with self._lock:
            return len(self._queue)

    def execute_all(self):
        while True:
            item = self.get()
            if item is None:
                break

            command, args, kwargs = item
            if callable(command):
                command(*args, **kwargs)


if __name__ == "__main__":

    print("=" * 50)
    print("ON3RT HF Manager V2")
    print("Test - command_queue.py")
    print("=" * 50)

    q = CommandQueue()

    def test(msg):
        print("Commande :", msg)

    q.put(test, "CAT OK")
    q.put(test, "IC-7300 OK")

    print("Taille :", q.size())
    q.execute_all()
    print("Vide :", q.empty())
