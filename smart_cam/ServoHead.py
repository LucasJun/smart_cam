import numpy as np
try:
    import RPi.GPIO as io
    _no_gpio = False
except ModuleNotFoundError as e:
    print('load RPi.GPIO failure')
    _no_gpio = True


class ServoHead:

    _motor1_pin = 12

    _motor1_dafaule_angle = 13
    _current_angle = 0

    _motor1_min_angle = 1
    _motor1_max_angle = 26

    def __init__(self):
        if _no_gpio:
            print('ServoHead module will do nothing beacause gpio lib is not activate')
        else:
            io.setmode(io.BOARD)
            io.setup(self._motor1_pin, io.OUT)
            self.motor1 = io.PWM(self._motor1_pin, 100)
            self.motor1.start(self._motor1_dafaule_angle)
            self._current_angle = self._motor1_dafaule_angle

    def watch_left(self, diff=0.5):
        angle = self._current_angle - diff
        self.watch_angle(angle)

    def watch_right(self, diff=0.5):
        angle = self._current_angle + diff
        self.watch_angle(angle)

    def watch_angle(self, angle1):
        if angle1 is not None:
            angle1 = np.clip(angle1, self._motor1_min_angle, self._motor1_max_angle)
            self._current_angle = angle1
            if not _no_gpio:
                self.motor1.ChangeDutyCycle(angle1)

    def get_current_angle(self):
        return self._current_angle

    def cleanup(self):
        if not _no_gpio:
            self.motor1.stop()
            del self.motor1
