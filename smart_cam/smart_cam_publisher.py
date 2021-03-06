import numpy as np
import cv2
import imageio
import zmq
import time
import threading
from collections import deque
import control_code
from SmokeDetector import SmokeDetector
from ServoHead import ServoHead

_allow_no_cam = False


class smart_cam_publisher:
    is_quit = False
    found_smoke = False

    cam1_id = 0

    frame_hw = [480, 640]

    wait_to_send = deque(maxlen=100)
    recv_msg_quene = deque(maxlen=5000)

    jpeg_quality = 80
    fps = 30

    real_fps = 0

    def __init__(self):

        # 初始化烟雾探测器和舵机云台控制器
        self.smoke_detector = SmokeDetector()
        self.smoke_detector.start()
        self.servo_head = ServoHead()

        try:
            # 初始化相机
            self.cam1 = imageio.get_reader('<video%d>' % self.cam1_id, size=(self.frame_hw[1], self.frame_hw[0]), fps=30)
            print('use cam success')
            self.no_cam = False
        except AttributeError:
            msg = 'use cam failure, cam1 status: %d' % (self.cam1.isOpened(),)
            print(msg)
            self.cam1 = None
            self.no_cam = True

        if self.no_cam and not _allow_no_cam:
            raise AttributeError('No cam!!!')

        # 第一张图像初始化为全黑图像
        self.cam_img = np.zeros([self.frame_hw[0], self.frame_hw[1]*2, 1], np.uint8)
        # self.cam_img = cv2.randu(self.cam_img, 10, 250)

        # 初始化各个网络端口
        self.ctx = zmq.Context(4)
        self.cam_img_send_socket = self.ctx.socket(zmq.PUSH)    # 用于发送图像信息
        self.ctrl_recv_socket = self.ctx.socket(zmq.PULL)       # 用于接收控制信息
        self.msg_send_socket = self.ctx.socket(zmq.PUSH)        # 用于发送消息

        self.cam_img_send_socket.setsockopt(zmq.LINGER, 0)      # 设定关闭端口时立即清空队列，不设定此项将会卡住
        self.ctrl_recv_socket.setsockopt(zmq.LINGER, 0)
        self.msg_send_socket.setsockopt(zmq.LINGER, 0)

        # 设定所有接收端口延迟1s
        self.ctrl_recv_socket.setsockopt(zmq.RCVTIMEO, 1000)

        self.cam_img_send_socket.bind('tcp://*:35687')
        self.ctrl_recv_socket.bind('tcp://*:35688')
        self.msg_send_socket.bind('tcp://*:35689')

        # 图像发送端口重要的是实时性，过时的消息不要发送，而是直接丢掉
        # # 设定图像发送端口只缓存最多2条信息，系统发送缓冲区最大为1MB
        # self.cam_img_send_socket.setsockopt(zmq.SNDHWM, 2)
        # self.cam_img_send_socket.setsockopt(zmq.SNDBUF, 1024*512*1)
        # 这个可以替代以上功能，只保留消息队列中最后一个消息，其余消息会被丢弃
        self.cam_img_send_socket.setsockopt(zmq.CONFLATE, True)
        # 这个可以保证在连接断开或没有建立时，消息会被直接丢弃，而不是在消息队列里面排队
        self.cam_img_send_socket.setsockopt(zmq.IMMEDIATE, True)

        self.cam_standby = False    # 相机待机
        self.has_standby = True    # 相机是否已经待机？

        # 消息发送线程
        self.msg_send_thread = threading.Thread(target=self.msg_send_run)
        self.msg_send_thread.start()

        # 如果允许没有相机的情况下运行
        if not self.no_cam:
            self.capture_thread = threading.Thread(target=self.capture_run)
            self.cam_img_send_thread = threading.Thread(target=self.cam_img_send_run)

            self.capture_thread.start()
            self.cam_img_send_thread.start()

    def set_framehw(self, framehw):
        '''
        设定分辨率，格式(height, width)
        :param framehw:
        :return:
        '''
        self.cam_standby = True
        while not self.has_standby:
            time.sleep(0.1)
        self.frame_hw = framehw
        self.cam1.close()
        self.cam1 = imageio.get_reader('<video%d>' % self.cam1_id, size=(self.frame_hw[1], self.frame_hw[0]), fps=30)
        self.cam_standby = False

    def send_msg(self, msg_id, msg):
        '''
        发送消息
        :param msg_id:
        :param msg:
        :return:
        '''
        # 发送消息，与op的相反，这里需要op发来消息的id
        data = [msg_id]
        data.extend(msg)
        self.wait_to_send.append(data)
        return msg_id

    def recv_msg(self):
        '''
        接收消息
        :return:
        '''
        # 获取消息后，将id和值设定为None，代表清除消息
        # 超时后，返回None
        msg = None
        try:
            msg = self.ctrl_recv_socket.recv_pyobj()
        except zmq.error.Again:
            pass
        return msg

    def capture_run(self):
        '''
        相机线程，不断从硬件获取图像
        :return:
        '''
        # 获取图像
        while not self.is_quit:
            # 是否要求暂停获取图像
            if self.cam_standby:
                self.has_standby = True
                time.sleep(1.)
            else:
                self.has_standby = False
                get_frame_start_time = time.time()
                self.cam_img = self.cam1.get_next_data()
                need_sleep_delay = 1 / self.fps - (time.time() - get_frame_start_time)
                if need_sleep_delay > 0:
                    time.sleep(need_sleep_delay)
                self.real_fps = 1 / (time.time() - get_frame_start_time)

    def cam_img_send_run(self):
        '''
        图像发送线程，同时，烟雾探测器状态也由这里发送
        :return:
        '''
        # 检测烟雾的代码交给摄像机发送线程来做
        while not self.is_quit:
            self.found_smoke = self.smoke_detector.detect()
            if self.cam_standby:
                time.sleep(1.)
            else:
                _, data = cv2.imencode('.jpg', self.cam_img, (cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality))
                # 消息包头一个字节是烟雾探测情况
                data = bytes([self.found_smoke]) + bytes(data)
                try:
                    self.cam_img_send_socket.send(data, zmq.NOBLOCK, copy=False)
                except zmq.error.Again:
                    pass
            time.sleep(1/self.fps)

    def msg_send_run(self):
        '''
        消息发送队列
        :return:
        '''
        # 负责发送消息队列里面的消息
        while not self.is_quit:
            if len(self.wait_to_send) > 0:
                self.msg_send_socket.send_pyobj(self.wait_to_send.pop())
            time.sleep(1/self.fps)

    def run(self):
        '''
        主消息循环，需手动调用，此循环不会退出
        :return:
        '''
        # 这是消息循环，由主线程执行
        while not self.is_quit:
            # 获取消息
            msg = self.recv_msg()
            if msg is None:
                print('no msg')
                continue
            msg_id = msg[0]
            msg_data = msg[1:]

            # 消息处理
            # cmd get
            if msg_data[0] == control_code.msg_get_fps:
                self.send_msg(msg_id, [self.fps])
            elif msg_data[0] == control_code.msg_get_jpeg_quality:
                self.send_msg(msg_id, [self.jpeg_quality])
            elif msg_data[0] == control_code.msg_get_framehw:
                self.send_msg(msg_id, [self.frame_hw[0], self.frame_hw[1]])
            elif msg_data[0] == control_code.msg_get_real_fps:
                self.send_msg(msg_id, [self.real_fps])

            # cmd set
            elif msg_data[0] == control_code.msg_set_fps:
                self.fps = int(msg_data[1])
            elif msg_data[0] == control_code.msg_set_jpeg_quality:
                self.jpeg_quality = int(msg_data[1])
            elif msg_data[0] == control_code.msg_set_framehw:
                self.set_framehw(msg_data[1])
            elif msg_data[0] == control_code.msg_set_cam_standby:
                self.cam_standby = bool(msg_data[1])

            # cam motor control
            elif msg_data[0] == control_code.msg_cam_motor_turn_left:
                self.servo_head.watch_left()
            elif msg_data[0] == control_code.msg_cam_motor_turn_right:
                self.servo_head.watch_right()
            elif msg_data[0] == control_code.msg_get_cam_motor_angle:
                self.send_msg(msg_id, [self.servo_head.get_current_angle()])
            elif msg_data[0] == control_code.msg_set_cam_motor_angle:
                self.servo_head.watch_angle(float(msg_data[1]))

            print(msg_id, msg_data)


if __name__ == '__main__':
    oper = smart_cam_publisher()
    oper.run()
