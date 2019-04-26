import numpy as np
import cv2
import zmq
import time
import threading
from collections import deque
import control_code
from copy import deepcopy


class smart_cam_receiver:
    target_addr = '192.168.137.211'
    _is_quit = False
    img = None
    delay = 0.1

    fps = 30
    jpeg_quality = 80
    frame_hw = [480, 640]

    offline = True

    _wait_to_send = deque(maxlen=500)
    _recv_msg_quene = deque(maxlen=5000)

    _current_msg_id = 1

    found_smoke = False

    def __init__(self):
        self.ctx = zmq.Context(4)  # zmq 上下文
        self.ctrl_send_socket = self.ctx.socket(zmq.PUSH)  # 用于发送控制信息
        self.cam_img_recv_socket = self.ctx.socket(zmq.PULL)  # 用于接收图像信息
        self.msg_recv_socket = self.ctx.socket(zmq.PULL)  # 用于接收消息

        # 所有接收端口设定0.5s延迟
        self.cam_img_recv_socket.setsockopt(zmq.RCVTIMEO, 500)  # 设置控制0.5s超时
        self.msg_recv_socket.setsockopt(zmq.RCVTIMEO, 500)  # 设置控制0.5s超时

        self.cam_img_recv_socket.setsockopt(zmq.LINGER, 0)  # 设定关闭端口时立即清空队列，不设定此项将会卡住
        self.ctrl_send_socket.setsockopt(zmq.LINGER, 0)
        self.msg_recv_socket.setsockopt(zmq.LINGER, 0)

        # # 设定端口不缓存信息
        # self.cam_img_recv_socket.setsockopt(zmq.RCVHWM, 1)

        self.cam_img_recv_socket.connect('tcp://%s:35687' % self.target_addr)
        self.ctrl_send_socket.connect('tcp://%s:35688' % self.target_addr)
        self.msg_recv_socket.connect('tcp://%s:35689' % self.target_addr)

        # 启动工作线程
        self.ctrl_send_thread = threading.Thread(target=self._ctrl_send_run)
        self.msg_recv_thread = threading.Thread(target=self._msg_recv_run)
        self.viewer_thread = threading.Thread(target=self._cam_img_recv_run)

        self.ctrl_send_thread.start()
        self.msg_recv_thread.start()
        self.viewer_thread.start()

    def load(self, cfg: dict):
        self.target_addr = cfg['target_addr']
        self.cam_img_recv_socket.connect('tcp://%s:35687' % self.target_addr)
        self.ctrl_send_socket.connect('tcp://%s:35688' % self.target_addr)
        self.msg_recv_socket.connect('tcp://%s:35689' % self.target_addr)

    def save(self):
        cfg = {
            'target_addr': self.target_addr,
        }
        return cfg

    def _send_msg(self, msg):
        # 发送消息后，返回消息id，需凭借消息id接收消息
        msg_id = self._current_msg_id
        self._current_msg_id += 1
        data = [msg_id]
        data.extend(msg)
        self._wait_to_send.append(data)
        return msg_id

    def _recv_msg(self, msg_id, timeout=2.):
        # 获取消息后，将id和值设定为None，代表清除消息
        # 超时后，返回None
        msg = None
        for _ in range(int(timeout * 100)):
            time.sleep(0.01)
            for it in list(self._recv_msg_quene)[::-1]:
                if it[0] == msg_id:
                    msg = deepcopy(it[1:])
                    it[0] = None
                    break
            if msg is not None:
                break
        return msg

    def _ctrl_send_run(self):
        while not self._is_quit:
            if len(self._wait_to_send) > 0:
                msg = self._wait_to_send.pop()
            else:
                time.sleep(1)
                continue
            try:
                self.ctrl_send_socket.send_pyobj(msg, zmq.NOBLOCK)
            except zmq.error.Again:
                pass
            time.sleep(0.01)

    def _msg_recv_run(self):
        while not self._is_quit:
            try:
                msg = self.msg_recv_socket.recv_pyobj()
                self._recv_msg_quene.append(msg)
            except zmq.error.Again:
                pass

    def _cam_img_recv_run(self):
        while not self._is_quit:
            # 获取远程机上烟雾状态和图像
            try:
                msg = self.cam_img_recv_socket.recv()
                smoke_status = msg[0]
                img_data = msg[1:]
                self.found_smoke = bool(smoke_status)
                self.img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)

                # 如果之前掉线了，为了保险，将会自动再次设定fps，quality，framehw
                if self.offline:
                    self.ctrl_fps(self.fps)
                    self.ctrl_framehw(self.frame_hw)
                    self.ctrl_jpeg_quality(self.jpeg_quality)
                    self.offline = False
            except zmq.error.Again:
                self.offline = True

    def get_cam_img(self):
        return self.img

    def get_real_fps(self):
        msg = [control_code.msg_get_real_fps]
        msg_id = self._send_msg(msg)
        return self._recv_msg(msg_id)

    def ctrl_standby(self, is_standby: bool):
        self._send_msg([control_code.msg_set_cam_standby, is_standby])

    def ctrl_fps(self, fps=None):
        if fps is None:
            msg = [control_code.msg_get_fps]
            msg_id = self._send_msg(msg)
            return self._recv_msg(msg_id)
        else:
            self.fps = fps
            msg = [control_code.msg_set_fps, fps]
            self._send_msg(msg)

    def ctrl_jpeg_quality(self, jpeg_quality=None):
        if jpeg_quality is None:
            msg = [control_code.msg_get_jpeg_quality]
            msg_id = self._send_msg(msg)
            jpeg_quality = self._recv_msg(msg_id)
            return jpeg_quality
        else:
            self.jpeg_quality = jpeg_quality
            msg = [control_code.msg_set_jpeg_quality, jpeg_quality]
            self._send_msg(msg)

    def ctrl_framehw(self, framehw=None):
        if framehw is None:
            msg = [control_code.msg_get_framehw]
            msg_id = self._send_msg(msg)
            framehw = self._recv_msg(msg_id)
            return framehw
        else:
            self.frame_hw = framehw
            msg = [control_code.msg_set_framehw, framehw]
            self._send_msg(msg)

    def cleanup(self):
        self._is_quit = True
        self.viewer_thread.join()
        self.msg_recv_thread.join()
        self.ctrl_send_thread.join()
        time.sleep(0.3)
        self.ctrl_send_socket.close()
        self.cam_img_recv_socket.close()
        self.msg_recv_socket.close()
        self.ctx.destroy()
        print('Cleanup finish')


if __name__ == '__main__':
    op = smart_cam_receiver()

    while True:
        key = cv2.waitKey(1000 // 30)
        if op.get_cam_img() is None:
            continue
        cv2.imshow('viewer', cv2.cvtColor(op.get_cam_img(), cv2.COLOR_RGB2BGR))
        time.sleep(0.01)
        last_time = time.time()

        if key == ord('y'):
            op.ctrl_jpeg_quality(20)
        elif key == ord('u'):
            op.ctrl_jpeg_quality(80)
        elif key == ord('i'):
            print(op.ctrl_jpeg_quality())

        elif key == ord('h'):
            op.ctrl_fps(60)
        elif key == ord('j'):
            op.ctrl_fps(15)
        elif key == ord('k'):
            print(op.ctrl_fps())
        elif key == ord('l'):
            print(op.get_real_fps())

        elif key == ord('g'):
            op.ctrl_standby(True)
        elif key == ord('b'):
            op.ctrl_standby(False)

        elif key == ord('a'):
            op.ctrl_framehw([720, 1280])
        elif key == ord('s'):
            op.ctrl_framehw([480, 640])
        elif key == ord('d'):
            print(op.ctrl_framehw())

        elif key == ord('f'):
            print(op.found_smoke)

        elif key == ord('t'):
            op.cleanup()
            break

    cv2.destroyAllWindows()
