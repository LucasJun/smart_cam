import numpy as np
import json
import cv2
import time
import threading
import imageio
import sys


sys.path.append('smart_cam')

import notify_type
from FireDetector import ColorFireDetector as FireDetector
from MoveDetector import FrameDiffMoveDetector as DiffMoveDetector
from Yolov3HumanDetector import Yolov3HumanDetector as HumanDetector
from SmokeDetector import SmokeDetector
from Recorder import Recorder
from Notifier import Notifier
from smart_cam_receiver import smart_cam_receiver

'''
设计思路，每个检测器都有独立的检测线程，主线程负责图像获取，消息分发，与检测器现成通讯
'''


class SmartCam:
    # 帧大小
    frame_hw = [480, 640]
    # 帧速率
    fps = 30
    # 图像质量
    jpeg_quality = 80

    need_quit = False

    has_move = False
    has_smoke = False
    has_fire = False
    has_human = False

    _is_start = False
    _recording_frame_hw = None

    def __init__(self, cam_id=0, *, debug_show=False):
        self.debug_show = debug_show
        print('initing cam')
        self.cam_id = cam_id
        if cam_id == -1:
            self.smart_cam = smart_cam_receiver()
        else:
            # 打开摄像头失败时，抛出异常
            self.cam = imageio.get_reader('<video%d>' % cam_id, fps=self.fps)
        print('open cam complete')

        print('load detector')
        self.fire_detector = FireDetector(debug_show=debug_show)
        self.smoke_detector = SmokeDetector()
        self.diff_move_detector = DiffMoveDetector(debug_show=debug_show)
        self.human_detector = HumanDetector(debug_show=debug_show)
        self.recoder = Recorder()
        self.notifier = Notifier(self.recoder)
        print('load detector complete')

        self.frame = np.zeros([*self.frame_hw, 3], np.uint8)

        self.fire_detect_thread = threading.Thread(target=self.fire_detect_run)
        self.smoke_detect_thread = threading.Thread(target=self.smoke_detect_run)
        self.human_detect_thread = threading.Thread(target=self.human_detect_run)
        self.move_detect_thread = threading.Thread(target=self.move_detect_run)

        if self.cam_id == -1:
            self.smart_cam.ctrl_framehw(self.frame_hw)
            self.smart_cam.ctrl_fps(self.fps)

    def load(self, path='smart_cam/config.json'):
        print('loading config')
        # 载入配置时，应当暂停部分操作
        cfg = json.load(open(path, 'r'))
        self.frame_hw = cfg['frame_hw']
        self.fps = cfg['fps']
        self.jpeg_quality = cfg['jpeg_quality']
        self.fire_detector.load(cfg['FireDetector'])
        self.smoke_detector.load(cfg['SmokeDetector'])
        self.diff_move_detector.load(cfg['DiffMoveDetector'])
        self.human_detector.load(cfg['HumanDetector'])
        self.notifier.load(cfg['Notifier'])
        if self.cam_id == -1:
            self.smart_cam.load(cfg['cam'])
            self.smart_cam.ctrl_framehw(self.frame_hw)
            self.smart_cam.ctrl_fps(self.fps)
            self.smart_cam.ctrl_jpeg_quality(self.jpeg_quality)
        print('load config success')

    def save(self, path='config.json'):
        print('saving config')
        cfg = {
            'frame_hw': self.frame_hw,
            'fps': self.fps,
            'jpeg_quality': self.jpeg_quality,
            'FireDetector': self.fire_detector.save(),
            'SmokeDetector': self.smoke_detector.save(),
            'DiffMoveDetector': self.diff_move_detector.save(),
            'HumanDetector': self.human_detector.save(),
            'Notifier': self.notifier.save()
        }
        if self.cam_id == -1:
            cfg.update({'cam': self.smart_cam.save()})
        json.dump(cfg, open(path, 'w'))
        print('save config success')
        return cfg

    def fire_detect_run(self):
        '''
        火焰监测
        :return:
        '''
        while not self.need_quit:
            self.fire_detector.push_frame(self.frame)
            bboxes = self.fire_detector.detect()
            if len(bboxes) > 0:
                self.notifier.notice(notify_type.type_fire, 'found fire')
                self.has_fire = True
            else:
                self.has_fire = False
            time.sleep(1/self.fps)

    def smoke_detect_run(self):
        '''
        烟雾检测
        :return:
        '''
        if self.cam_id == -1:
            while not self.need_quit:
                b = self.smart_cam.found_smoke
                if b:
                    self.notifier.notice(notify_type.type_smoke, 'found smoke')
                    self.has_smoke = True
                else:
                    self.has_smoke = False
                time.sleep(1 / self.fps)
        else:
            self.smoke_detector.start()
            while not self.need_quit:
                b = self.smoke_detector.detect()
                if b:
                    self.notifier.notice(notify_type.type_smoke, 'found smoke')
                    self.has_smoke = True
                else:
                    self.has_smoke = False
                time.sleep(1 / self.fps)
            self.smoke_detector.stop()
            self.smoke_detector.cleanup()

    def move_detect_run(self):
        '''
        画面变动检测
        :return:
        '''
        while not self.need_quit:
            self.diff_move_detector.push_frame(self.frame)
            bboxes = self.diff_move_detector.detect()
            if len(bboxes) > 0:
                self.notifier.notice(notify_type.type_move, 'found move')
                self.has_move = True
            else:
                self.has_move = False
            time.sleep(1 / self.fps)

    def human_detect_run(self):
        '''
        人类检测
        :return:
        '''
        while not self.need_quit:
            self.human_detector.push_frame(self.frame)
            bboxes = self.human_detector.detect()
            if len(bboxes) > 0:
                self.notifier.notice(notify_type.type_human, 'found human')
                self.has_human = True
            else:
                self.has_human = False
            time.sleep(1 / self.fps)

    # def noise_detect_run(self):
    #     while not self.need_quit:
    #         # 尚未完成异常噪音检测
    #         time.sleep(1 / self.fps)

    def cleanup(self):
        self.need_quit = True
        self.fire_detect_thread.join()
        self.smoke_detect_thread.join()
        self.human_detect_thread.join()
        self.move_detect_thread.join()
        self.smart_cam.cleanup()
        self.notifier.cleanup()

    def run(self):
        '''
        消息循环
        :return:
        '''
        print('start watch')
        while not self.need_quit:
            # 检查摄像机id，如果是-1代表使用远程摄像头
            if self.cam_id == -1:
                if self.smart_cam.offline:
                    print('camera offline')
                img = self.smart_cam.get_cam_img()
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    self.frame = img
            else:
                img = self.cam.get_next_data()
                self.frame = img

            if not self._is_start:
                self._is_start = True
                self.fire_detect_thread.start()
                self.smoke_detect_thread.start()
                self.human_detect_thread.start()
                self.move_detect_thread.start()

            if self.notifier.can_record:
                # 如果录像中途切换了分辨率，关闭上一个录像后，再次启动
                if self._recording_frame_hw != self.frame_hw:
                    self.recoder.stop_video_record()
                    self._recording_frame_hw = self.frame_hw
                self.recoder.start_video_record(self.fps)
                self.recoder.next_frame(self.frame)
            else:
                self.recoder.stop_video_record()

            if not self.debug_show:
                time.sleep(1 / self.fps)
            else:
                cv2.imshow('main', sc.frame)
                cv2.waitKey(1000 // self.fps)

    def get_current_img(self):
        '''
        返回当前图像，如果没有初始化成功，返回None
        :return:
        '''
        return self.frame

    def get_current_jpg(self):
        '''
        返回当前图像，如果没有初始化成功，返回None
        :return:
        '''
        data = None
        if self.frame is not None:
            _, data = cv2.imencode('.jpg', self.frame, (cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality))
        return data


if __name__ == '__main__':
    sc = SmartCam(-1, debug_show=False)
    sc.load()
    # exit(0)
    sc.run()
