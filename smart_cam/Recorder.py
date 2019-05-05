import time
import os
import imageio


class Recorder:

    # 感兴趣截图控制，每当有设定事件触发，就会触发一次感兴趣截图，间隔 interest_capture_delay 秒后，才能再次触发
    _last_interest_capture_time = 0
    interest_capture_delay = 15

    def __init__(self, save_dir='record'):
        os.makedirs(save_dir, exist_ok=True)
        self.save_dir = save_dir
        self._log_file = None
        self._video_fps = None
        self._last_frame_time = 0
        self._video_file = None
        self._video_name = None
        self._video_start_time = None
        self._current_frame = None
        self._current_time = None
        self._mark_interest = False
        self._day = -1
        self.new_log()

    def new_log(self, now=None):
        '''
        开始一次新的记录，一般情况下，每天创建一个新的记录文件
        :param now:
        :return:
        '''
        if now is None:
            now = time.localtime()

        if now.tm_mday != self._day:
            self._day = now.tm_mday

            if self._log_file is not None:
                self._log_file.close()

            log_file_name = time.strftime('%Y_%m_%d.log', now)
            log_file_name = '{}/{}'.format(self.save_dir, log_file_name)
            self._log_file = open(log_file_name, 'a')

    def start_video_record(self, fps=20):
        '''
        开始录像，没有停止录像时，重复调用时会被忽略
        :param fps: 帧率
        :return:
        '''
        if self._video_file is None:
            self._video_fps = fps
            ts = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime())
            self._video_name = '{}/{}.mkv'.format(self.save_dir, ts)
            self._video_start_time = time.time()
            self._video_file = imageio.get_writer(self._video_name, fps=fps)
            # 开始录像时，会自动截取一张感兴趣图
            self.do_interest_mark()

    def next_frame(self, frame):
        '''
        录入一帧，在没有开始录像时，调用会被忽略
        :param frame:
        :return:
        '''
        if self._video_file is not None:
            # 限制输入帧速率
            ts = time.time()
            if ts - self._last_frame_time < (1 / self._video_fps):
                return
            self._last_frame_time = ts

            self._video_file.append_data(frame)
            self._current_frame = frame
            self._current_time = ts

            # 如果感兴趣标志被设置，将会生成一次感兴趣截图
            if self._mark_interest:
                self._do_interest_capture()
                self._mark_interest = False

    def stop_video_record(self):
        '''
        停止录像。在没有开始录像时，调用会被忽略
        :return:
        '''
        if self._video_file is not None:
            self._video_file.close()
            self._video_file = None
            self._video_start_time = None
            self._video_name = None

    def do_interest_mark(self):
        '''
        设定兴趣点截图标志
        :return:
        '''
        self._mark_interest = True

    def _do_interest_capture(self):
        '''
        执行一次兴趣点截图
        :return:
        '''
        img = self._current_frame
        ts = self._current_time - self._video_start_time
        interest_img_name = "%s.%.3f.jpg" % (self._video_name, ts)
        imageio.imwrite(interest_img_name, img)

    def notice(self, level: int, msg: str):
        '''
        写入通知函数，执行该命令时，通知将会被写入记录文件
        :param level: 通知类型
        :param msg: 消息
        :return:
        '''
        now = time.localtime()
        self.new_log(now)
        ts = time.strftime('%Y_%m_%d_%H_%M_%S', now)

        data = '{};{};{}\n'.format(ts, level, msg)
        self._log_file.write(data)
        self._log_file.flush()


if __name__ == '__main__':
    import numpy as np

    rd = Recorder('test_record')
    v = imageio.get_reader('<video0>')

    for i in range(10000):
        img = v.get_next_data()

        rd.start_video_record(20)
        rd.next_frame(img)

        if np.random.uniform() < 0.001:
            rd.do_interest_mark()
            rd.notice(-1, 'interest')

        time.sleep(0.01)

    rd.stop_video_record()
