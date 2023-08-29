import asyncio
import time
from threading import Thread, Event


class Timer(object):
    def __init__(self):
        self._pause_event = Event()
        self._stop_event = Event()

        self.timer_type = ''
        self.duration = 0
        self.run_times = 0

        self._timer_thread = None
        self._completed_callback = None
        self._each_callback = None
        self.is_paused = False
        self.is_done = False
        self.is_started = False

    def run_func(self, loop):
        asyncio.set_event_loop(loop)
        self.is_started = True
        self.run_times = 0
        duration = self.duration

        while self.run_times <= duration:
            if not self._pause_event.is_set():
                self._pause_event.wait()

            if self._stop_event.is_set():
                break

            if self._each_callback is not None:
                self._each_callback()

            time.sleep(1)

            self.run_times += 1

        if self._completed_callback is not None:
            self._completed_callback()

        self.is_done = True

    def start(self):
        self._timer_thread = Thread(target=self.run_func, args=(asyncio.get_event_loop(),))
        self._pause_event.set()
        self._timer_thread.start()

    def pause(self):
        self._pause_event.clear()
        self.is_paused = True

    def keep(self):
        self._pause_event.set()
        self.is_paused = False

    def stop(self):
        self._stop_event.set()
        self.is_done = True

    def set_completed_callback(self, callback):
        self._completed_callback = callback

        return self

    def set_each_callback(self, callback):
        self._each_callback = callback

        return self

    def set_duration(self, duration: int):
        duration = int(duration)
        if duration <= 0:
            raise ValueError()

        self.duration = duration

        return self

    def set_timer_type(self, timer_type: str):
        self.timer_type = timer_type

        return self

    def get_duration(self):
        return self.duration

    def get_run_times(self):
        return self.run_times
