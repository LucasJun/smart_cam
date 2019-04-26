import time
import os
import imageio


class Recorder:
    def __init__(self, save_dir='record'):
        os.makedirs(save_dir, exist_ok=True)
        self.save_dir = save_dir
        self.log_file = None
        self.video_file = None
        self.day = -1
        self.new_log()

    def new_log(self, now=None):
        if now is None:
            now = time.localtime()

        if now.tm_mday != self.day:
            self.day = now.tm_mday

            if self.log_file is not None:
                self.log_file.close()

            log_file_name = time.strftime('%Y_%m_%d.log', now)
            log_file_name = '{}/{}'.format(self.save_dir, log_file_name)
            self.log_file = open(log_file_name, 'a')

    def start_video_record(self, fps=20):
        '''
        开始录像
        :param fps: 帧率
        :return:
        '''
        if self.video_file is None:
            ts = time.strftime('%Y_%m_%d_%H_%M_%S', time.localtime())
            name = '{}/{}.mkv'.format(self.save_dir, ts)
            self.video_file = imageio.get_writer(name, fps=fps)

    def next_frame(self, frame):
        '''
        输入帧
        :param frame:
        :return:
        '''
        if self.video_file is not None:
            self.video_file.append_data(frame)

    def stop_video_record(self):
        '''
        停止录像
        :return:
        '''
        if self.video_file is not None:
            self.video_file.close()
            self.video_file = None

    def notice(self, level: int, msg: str):

        now = time.localtime()
        self.new_log(now)
        ts = time.strftime('%Y_%m_%d_%H_%M_%S', now)

        data = '{};{};{}\n'.format(ts, level, msg)
        self.log_file.write(data)
        self.log_file.flush()
