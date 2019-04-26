import numpy as np
import cv2
from collections import deque
import imageio


class FrameDiffMoveDetector():
    # 有空时再进一步升级，采用逐像素处理
    # 取过去N张图像的每颗像素的平均变化幅度，得到变化上下限，根据新图像的每颗像素是否在平均变化幅度内时决定是否激活
    pix_thresh = 40

    def __init__(self, *, debug_show=False):
        self.frame_buffer = deque(maxlen=3)
        self.debug_show = debug_show

    def load(self, cfg: dict):
        self.pix_thresh = cfg['pix_thresh']

    def save(self):
        cfg = {
            'pix_thresh': self.pix_thresh
        }
        return cfg

    def push_frame(self, frame):
        self.frame_buffer.append(frame)

    def detect(self):

        # 确保缓冲区有足够的帧
        if len(self.frame_buffer) < 3:
            return []

        img1 = self.frame_buffer[0]
        img2 = self.frame_buffer[2]

        # 切换分辨率时，帧大小不同
        if img1.shape != img2.shape:
            return []

        # 求差值
        diff_img = cv2.absdiff(img1, img2)
        if self.debug_show:
            cv2.imshow("diff_img", diff_img)

        # 二分阀值，像素差值大于50，标记为变化点
        ret, bin_img = cv2.threshold(diff_img, self.pix_thresh, 255, cv2.THRESH_BINARY)
        if self.debug_show:
            cv2.imshow('diff_thresh', bin_img)

        # 中值滤波
        bin_img = cv2.medianBlur(bin_img, 5)

        # 腐蚀操作，去除可能的噪点
        kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (4, 4))
        erode_img = cv2.erode(bin_img, kernel_erode)
        if self.debug_show:
            cv2.imshow("erode", erode_img)

        # 膨胀操作，当变化区域大小足够大时，激活一片区域
        kernel_dilate = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (16, 16))
        dilate_img = cv2.dilate(erode_img, kernel_dilate)
        if self.debug_show:
            cv2.imshow("dilate", dilate_img)

        # 处理后图像
        pro_img = dilate_img

        # 如果是rgb图像，对三幅激活图做并联处理
        if pro_img.ndim > 2:
            pro_img = np.max(pro_img, -1)

        contours, _hierarchy = cv2.findContours(pro_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        if self.debug_show:
            contours_img = cv2.cvtColor(img2, cv2.COLOR_RGB2BGR)
            cv2.drawContours(contours_img, contours, -1, (0, 0, 255), 2)
            cv2.imshow("contours", contours_img)

        bound_rects = [cv2.boundingRect(it) for it in contours]
        if self.debug_show:
            rects_img = cv2.cvtColor(img2, cv2.COLOR_RGB2BGR)
            for r in bound_rects:
                rects_img = cv2.rectangle(rects_img, r, (255, 0, 0))
            cv2.imshow("rects", rects_img)
            cv2.waitKey(1)

        # 返回变化区域的矩形框
        return bound_rects

# 根据关键点的移动监测
# def move_detection2(frames):
#     img1 = frames[0]
#     img2 = frames[2]
#     orb = cv2.xfeatures2d.SURF_create()
#     kp1, des1 = orb.detectAndCompute(img1, None)
#     kp2, des2 = orb.detectAndCompute(img2, None)
#     kp1_img = cv2.drawKeypoints(img1, kp1, None, color=(0, 255, 0), flags=0)
#     kp2_img = cv2.drawKeypoints(img2, kp2, None, color=(0, 255, 0), flags=0)
#     cv2.imshow('kp1', kp1_img)
#     cv2.imshow('kp2', kp2_img)
#
#     bm = cv2.FlannBasedMatcher_create()
#     matches = bm.knnMatch(des1, des2, 2)
#
#     good_matches = []
#     for m1, m2 in matches:
#         if m1.distance < 0.7*m2.distance:
#             good_matches.append(m1)
#
#     matches = good_matches
#
#     img3 = cv2.drawMatches(img1, kp1, img2, kp2, matches[:], None, flags=2)
#     cv2.imshow('viewer', img3)
#
#     pts1 = np.float32([kp1[m.queryIdx].pt for m in good_matches])
#     pts2 = np.float32([kp2[m.trainIdx].pt for m in good_matches])
#
#     homo = cv2.findHomography(pts1, pts2, cv2.RANSAC)
#     imageTransform1 = cv2.warpPerspective(img1, homo[0], (img1.shape[1], img1.shape[0]))
#     imgpeizhun = cv2.absdiff(frames[0], imageTransform1)
#     _, imgerzhi = cv2.threshold(imgpeizhun, 50, 255.0, cv2.THRESH_BINARY)
#     se = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
#
#     temp = imgerzhi #cv2.cvtColor(imgerzhi, cv2.COLOR_RGB2GRAY)
#     temp = cv2.morphologyEx(temp, cv2.MORPH_DILATE, se)
#
#     contours, _ = cv2.findContours(temp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
#
#     cv2.drawContours(img2, contours, -1, (0, 0, 255), 2)
#     cv2.imshow("contours", img2)


if __name__ == '__main__':

    cam = imageio.get_reader('<video0>', size=(640, 480), fps=30)

    md = FrameDiffMoveDetector(debug_show=True)

    while True:
        img = cam.get_next_data()
        # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        md.push_frame(img)
        rt = md.detect()
        if len(rt) > 0:
            print('found move!')
        else:
            print('no found')
        cv2.waitKey(1000//30)
