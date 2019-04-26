import time
import notify_type
import threading


class Notifier:
    # 发现人时，是否发送通知
    is_warning_when_human = False
    # 发现画面异动时，是否发送通知
    is_warning_when_move = False
    # 发现火时，是否发送通知
    is_warning_when_fire = False
    # 发现烟雾时，是否发送通知
    is_warning_when_smoke = False
    # 发现人时，是否开始录像
    is_record_when_human = False
    # 发现画面异动时，是否开始录像
    is_record_when_move = False
    # 发现火时，是否开始录像
    is_record_when_fire = False
    # 发现烟雾时，是否开始录像
    is_record_when_smoke = False
    # 记录延迟，每隔1s重复写入一次同类警告记录日志
    record_delay = 1
    # 远程通知延迟，发送通知后隔多长时间后再次发送通知，默认10分钟
    remote_warning_delay = 10 * 60
    # 开始录像后，在没有事件多长时间后停止，默认60s
    stop_record_after_no_event_delay = 60

    _last_notice_human_time = 0
    _last_notice_smoke_time = 0
    _last_notice_fire_time = 0
    _last_notice_move_time = 0

    _last_remote_warning_human_time = 0
    _last_remote_warning_smoke_time = 0
    _last_remote_warning_fire_time = 0
    _last_remote_warning_move_time = 0

    _last_record_time = 0

    _lock_notice = threading.Lock()
    _need_quit = False

    can_record = False

    def __init__(self, recorder=None, web_notifier=None, wx_notifier=None):
        self.recorder = recorder
        self.web_notifier = web_notifier
        self.wx_notifier = wx_notifier
        self._delay_stop_record_thread = threading.Thread(target=self.delay_stop_record_run)
        self._delay_stop_record_thread.start()

    def load(self, cfg: dict):
        self.is_warning_when_human = cfg['is_warning_when_human']
        self.is_warning_when_move = cfg['is_warning_when_move']
        self.is_warning_when_fire = cfg['is_warning_when_fire']
        self.is_warning_when_smoke = cfg['is_warning_when_smoke']
        self.is_record_when_human = cfg['is_record_when_human']
        self.is_record_when_move = cfg['is_record_when_move']
        self.is_record_when_fire = cfg['is_record_when_fire']
        self.is_record_when_smoke = cfg['is_record_when_smoke']
        self.record_delay = cfg['record_delay']
        self.remote_warning_delay = cfg['remote_warning_delay']
        self.stop_record_after_no_event_delay = cfg['stop_record_after_no_event_delay']

    def save(self):
        cfg = {
            'is_warning_when_human': self.is_warning_when_human,
            'is_warning_when_move': self.is_warning_when_move,
            'is_warning_when_fire': self.is_warning_when_fire,
            'is_warning_when_smoke': self.is_warning_when_smoke,
            'is_record_when_human': self.is_record_when_human,
            'is_record_when_move': self.is_record_when_move,
            'is_record_when_fire': self.is_record_when_fire,
            'is_record_when_smoke': self.is_record_when_smoke,
            'record_delay': self.record_delay,
            'remote_warning_delay': self.remote_warning_delay,
            'stop_record_after_no_event_delay': self.stop_record_after_no_event_delay,
        }
        return cfg

    def remote_notice(self, now, level, msg):
        can_notice = False
        if level == notify_type.type_human and now - self._last_remote_warning_human_time > self.remote_warning_delay:
            self._last_remote_warning_human_time = time.time()
            can_notice = True
        elif level == notify_type.type_fire and now - self._last_remote_warning_fire_time > self.remote_warning_delay:
            self._last_remote_warning_fire_time = time.time()
            can_notice = True
        elif level == notify_type.type_smoke and now - self._last_remote_warning_smoke_time > self.remote_warning_delay:
            self._last_remote_warning_smoke_time = time.time()
            can_notice = True
        elif level == notify_type.type_move and now - self._last_remote_warning_move_time > self.remote_warning_delay:
            self._last_remote_warning_move_time = time.time()
            can_notice = True

        if can_notice:
            if self.web_notifier is not None:
                self.web_notifier.notice(level, msg)
            if self.wx_notifier is not None:
                self.wx_notifier.notice(level, msg)

    def delay_stop_record_run(self):
        # 如果一段时间内没有事件发生，关闭录像标志位
        while not self._need_quit:
            if self.can_record and time.time() - self._last_record_time > self.stop_record_after_no_event_delay:
                self.can_record = False
            time.sleep(1)

    def cleanup(self):
        self._need_quit = True
        self._delay_stop_record_thread.join()

    def notice(self, level: int = 0, msg: str = ''):
        '''
        :param level: 通知级别
        :param msg: 通知内容
        :return:
        '''
        now = time.time()

        can_notice = False

        if level == notify_type.type_human and now - self._last_notice_human_time > self.record_delay:
            self._last_notice_human_time = time.time()
            can_notice = True
        elif level == notify_type.type_fire and now - self._last_notice_fire_time > self.record_delay:
            self._last_notice_fire_time = time.time()
            can_notice = True
        elif level == notify_type.type_smoke and now - self._last_notice_smoke_time > self.record_delay:
            self._last_notice_smoke_time = time.time()
            can_notice = True
        elif level == notify_type.type_move and now - self._last_notice_move_time > self.record_delay:
            self._last_notice_move_time = time.time()
            can_notice = True

        # 延迟写入日志，用于减少写入次数
        if can_notice and self.recorder is not None:
            with self._lock_notice:
                print(level, msg)
                self.recorder.notice(level, msg)

        if level == notify_type.type_human and self.is_record_when_human:
            self._last_record_time = time.time()
            self.can_record = True
        elif level == notify_type.type_fire and self.is_record_when_fire:
            self._last_record_time = time.time()
            self.can_record = True
        elif level == notify_type.type_smoke and self.is_record_when_smoke:
            self._last_record_time = time.time()
            self.can_record = True
        elif level == notify_type.type_move and self.is_record_when_move:
            self._last_record_time = time.time()
            self.can_record = True
