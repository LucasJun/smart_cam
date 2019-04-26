import cv2
import numpy as np
from collections import deque
import imageio


class ColorFireDetector:
    '''
    检测原理：火焰的颜色，以及火焰是运动的
    '''
    # 红色阀值
    red_thresh = 160  # 50~135
    # 对比度阀值
    saturation_thresh = 45  # 55~65

    def __init__(self, *, debug_show=False):
        self.debug_show = debug_show
        self.frame_buffer = deque(maxlen=3)

    def load(self, cfg: dict):
        self.red_thresh = cfg['fire_red_thresh']
        self.saturation_thresh = cfg['fire_saturation_thresh']

    def save(self):
        cfg = {'fire_red_thresh': self.red_thresh,
               'fire_saturation_thresh': self.saturation_thresh}
        return cfg

    def push_frame(self, frame):
        assert frame.shape[2] == 3, 'Frame must is RGB frame'
        self.frame_buffer.append(frame)

    def detect(self):
        if len(self.frame_buffer) < 3:
            return []

        # 检测火焰运动，运动的像素才会进一步识别
        img1 = self.frame_buffer[0]
        img2 = self.frame_buffer[2]

        # 切换分辨率时，帧大小不同
        if img1.shape != img2.shape:
            return []

        diff_img = cv2.absdiff(img1, img2)
        if self.debug_show:
            cv2.imshow("fire_diff_img", diff_img)

        # 二分阀值，像素差值大于40，标记为变化点
        ret, move_mask = cv2.threshold(diff_img, 40, 1, cv2.THRESH_BINARY)
        if self.debug_show:
            cv2.imshow('fire_move_mask', move_mask)

        img = self.frame_buffer[0]

        # 过滤掉不会动的像素
        img = img * move_mask

        img = cv2.medianBlur(img, 3)

        hls = cv2.cvtColor(img, cv2.COLOR_RGB2HLS)
        H, L, S = np.split(hls, 3, 2)
        R, G, B = np.split(img, 3, 2)  # 将图片拆分成R,G,B,三通道的颜色

        isfire_rgb = (R > self.red_thresh) * (R > R.mean()) * (R >= G) * (G >= B)
        isfire_hls = (20 >= S) * (160 <= L) * (H <= 28)  # * (S <= 255) * (0 < H)  * (L <= 255)

        isfire = isfire_rgb * isfire_hls
        isfire = isfire.astype(np.uint8)
        isfire = cv2.medianBlur(isfire, 5)
        isfire = cv2.erode(isfire, (5, 5))
        isfire = cv2.dilate(isfire, (7, 7))

        fire_img = np.where(isfire, 255, 0)
        fire_img = fire_img.astype(np.uint8)

        contours, hierarchy = cv2.findContours(fire_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = [it for it in contours if cv2.contourArea(it) > 20]

        bound_rects = [cv2.boundingRect(it) for it in contours]

        if self.debug_show:
            out_img = cv2.drawContours(img[..., ::-1], contours, -1, (255, 0, 0))

            rect_img = img[..., ::-1]
            for r in bound_rects:
                rect_img = cv2.rectangle(rect_img, r, (255, 0, 0))

            cv2.imshow('H', H)
            cv2.imshow('S', S)
            cv2.imshow('L', L)

            out_img = cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
            rect_img = cv2.cvtColor(rect_img, cv2.COLOR_RGB2BGR)

            cv2.imshow('fire_pixel', fire_img)
            cv2.imshow('out_img', out_img)
            cv2.imshow('rect_img', rect_img)
            cv2.waitKey(1)

        return bound_rects


if __name__ == '__main__':
    cam = imageio.get_reader('<video0>', size=(640, 480), fps=30)

    cv2.namedWindow("Control", cv2.WINDOW_AUTOSIZE)

    fd = ColorFireDetector(debug_show=True)

    def _callback_redThresh(x):
        fd.red_thresh = x

    def _callback_satThresh(x):
        fd.saturation_thresh = x

    cv2.createTrackbar("red_thresh", "Control", fd.red_thresh, 255, _callback_redThresh)
    cv2.createTrackbar("saturation_thresh", "Control", fd.saturation_thresh, 255, _callback_satThresh)
    cv2.namedWindow("Control", cv2.WINDOW_AUTOSIZE)
    # cv2.resizeWindow('Control', 400, 400)


    while True:
        frame = cam.get_next_data()
        show_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        cv2.imshow('v', show_frame)
        fd.push_frame(frame)
        r = fd.detect()
        if len(r) > 0:
            print('found fire!')
        else:
            print('no found')
        cv2.waitKey(1000//30)
