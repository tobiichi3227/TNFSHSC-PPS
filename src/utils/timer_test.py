import time
import unittest
from timer import Timer


class TimerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.timer = Timer().set_duration(10).set_timer_type("test")
        self.completed = False
        self.run_cnt = 0

    def test_timer_start(self):
        def func():
            self.completed = True

        def func2():
            self.run_cnt += 1

        self.timer.set_each_callback(func2)
        self.timer.set_completed_callback(func)

        self.timer.start()

        time.sleep(11)

        self.assertEqual(True, self.timer.is_done)
        self.assertEqual(10, self.run_cnt)
        self.assertEqual(10, self.timer.get_run_times())
        self.assertEqual(True, self.completed)

    def test_timer_pause(self):
        def func():
            self.run_cnt += 1

        self.timer.set_each_callback(func)
        self.timer.start()

        time.sleep(3)
        self.timer.pause()
        self.assertEqual(True, self.timer.is_paused)
        self.assertEqual(3, self.run_cnt)

        self.timer.keep()
        self.assertEqual(False, self.timer.is_paused)
        time.sleep(7)

        self.assertEqual(10, self.run_cnt)

    def test_timer_stop(self):
        def func():
            self.run_cnt += 1

        self.timer.set_each_callback(func)
        self.timer.start()

        time.sleep(5)
        self.timer.stop()
        self.assertEqual(True, self.timer.is_done)
        self.assertEqual(5, self.run_cnt)


if __name__ == '__main__':
    unittest.main()
