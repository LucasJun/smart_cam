import time
import threading
try:
    import RPi.GPIO as io
    _has_gpio = True
except ImportError as e:
    _has_gpio = False
    print(e)


class SmokeDetector:
    # 警告次数，减少突然间的误检，连续warning_count次警告时，真正发出警告
    warning_thresh = 5
    # 每1秒检测1次
    detect_freq = 1
    # 警告标志持续时间，一旦设置警告标志，将持续至少30s
    keep_found_duration = 30

    _is_start = 0
    _need_quit = False

    _smoke_warning_count = 0

    # 发现标志
    found = False
    _found_last_time = 0

    def __init__(self, pin=7):
        self.pin = pin
        # init gpio
        if _has_gpio:
            io.setmode(io.BOARD)
            io.setup(self.pin, io.IN)
        self.detect_thread = threading.Thread(target=self._detect_run)
        self.detect_thread.start()

    def load(self, cfg):
        self.detect_freq = int(cfg['smoke_detect_freq'])
        self.warning_thresh = int(cfg['smoke_warning_thresh'])
        self.keep_found_duration = int(cfg['smoke_keep_found_duration'])

    def save(self):
        cfg = dict()
        cfg['smoke_detect_freq'] = self.detect_freq
        cfg['smoke_warning_thresh'] = self.warning_thresh
        cfg['smoke_keep_found_duration'] = self.keep_found_duration
        return cfg

    def _check_pin(self):
        # 无烟雾时输出1
        # 有烟雾时输出0
        if _has_gpio:
            return not io.input(self.pin)
        else:
            return 0

    def _detect_run(self):
        while not self._need_quit:
            time.sleep(1 / self.detect_freq)
            if not self._is_start:
                self.found = False
                continue

            if self._check_pin():
                self._smoke_warning_count += 1
                if self._smoke_warning_count >= self.warning_thresh:
                    self.found = True
                    self._found_last_time = time.time()
            else:
                self._smoke_warning_count = 0
                if self.found and time.time() - self._found_last_time >= self.keep_found_duration:
                    self.found = False

    def start(self):
        self._is_start = True

    def stop(self):
        self._is_start = False

    def detect(self):
        return self.found

    def cleanup(self):
        self._need_quit = True
        self.detect_thread.join()


if __name__ == '__main__':
    sd = SmokeDetector(7)
    sd.start()
    while True:
        print(sd.detect())
        time.sleep(0.5)
    sd.cleanup()
