import torch
import time
import imageio
import threading
from collections import deque
import sys
import const_define
sys.path.append('yolov3')

from yolov3.models import *
from yolov3.utils.utils import *
from yolov3.utils.parse_config import *


class Yolov3HumanDetector:
    img_size = 416
    conf_thresh = 0.5
    nms_thresh = 0.7

    _lock_load_cfg = threading.Lock()

    def __init__(self, net_cfg_path='yolov3/cfg/yolov3-spp.cfg', weights_path='yolov3/weights/yolov3-spp.weights', *, debug_show=False):
        '''
        初始化函数
        :param net_cfg_path: yolo网络结构文件的路径
        :param weights_path: yolo网络权重文件的路径
        :param debug_show: 是否启动debug模式
        '''
        self.frame_buffer = deque(maxlen=1)
        self.debug_show = debug_show
        self.net_cfg_path = net_cfg_path
        self.weights_path = weights_path

        self.device = torch_utils.select_device()
        # Initialize model
        self.model = Darknet(net_cfg_path, self.img_size)
        load_darknet_weights(self.model, weights_path)
        self.model.to(self.device).eval()

        # Get classes and colors
        self.classes = load_classes(parse_data_cfg(const_define.yolo_coco_data)['names'])
        self.colors = [[random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)] for _ in range(len(self.classes))]

    def load(self, cfg: dict):
        with self._lock_load_cfg:
            old_img_size = cfg['img_size']
            self.img_size = cfg['img_size']
            if old_img_size != self.img_size:
                # 如果新图像大小与就图像大小不同，需要重建网络
                self.model = Darknet(self.net_cfg_path, self.img_size)
                load_darknet_weights(self.model, self.weights_path)
                self.model.to(self.device).eval()

        self.conf_thresh = cfg['conf_thresh']
        self.nms_thresh = cfg['nms_thresh']

    def save(self):
        cfg = {
            'img_size': self.img_size,
            'conf_thresh': self.conf_thresh,
            'nms_thresh': self.nms_thresh
        }
        return cfg

    def push_frame(self, frame):
        self.frame_buffer.append(frame)

    def detect(self):
        '''
        检测函数，检测到人类时，将会返回人类的包围框的坐标
        :return:
        '''
        with torch.no_grad(), self._lock_load_cfg:
            img = self.frame_buffer[0].copy()

            run_img = cv2.resize(img, (self.img_size, self.img_size), interpolation=cv2.INTER_AREA)
            run_img = np.float32(np.transpose(run_img, [2, 0, 1])) / 255.

            # Get detections
            run_img = torch.from_numpy(run_img).unsqueeze(0).to(self.device)
            pred = self.model(run_img)
            pred = pred[pred[:, :, 4] > self.conf_thresh]  # remove boxes < threshold

            human_bound_rects = []

            if len(pred) > 0:
                # Run NMS on predictions
                detections = non_max_suppression(pred.unsqueeze(0), self.conf_thresh, self.nms_thresh)[0]

                # Rescale boxes from 416 to true image size
                scale_coords(self.img_size, detections[:, :4], img.shape).round()

                if self.debug_show:
                    # Pint results to screen
                    unique_classes = detections[:, -1].cpu().unique()
                    for c in unique_classes:
                        n = (detections[:, -1].cpu() == c).sum()
                        print('%g %ss' % (n, self.classes[int(c)]), end=', ')

                # Draw bounding boxes and labels of detections
                for x1, y1, x2, y2, conf, cls_conf, cls in detections:
                    if self.classes[int(cls)] != 'person':
                        continue
                    human_bound_rects.append([x1, y1, x2, y2])
                    if self.debug_show:
                        # Add bbox to the image
                        label = '%s %.2f' % (self.classes[int(cls)], conf)
                        plot_one_box([x1, y1, x2, y2], img, label=label, color=self.colors[int(cls)])
            if self.debug_show:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                cv2.imshow('show', img)
                cv2.waitKey(1)
        return human_bound_rects


if __name__ == '__main__':

    cam = imageio.get_reader('<video0>', size=(1280, 720), fps=30)

    # cam.set(cv2.CAP_PROP_SETTINGS, 0)

    hd = Yolov3HumanDetector(debug_show=True)

    while True:
        img = cam.get_next_data()
        # frame = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        hd.push_frame(img)
        rt = hd.detect()
        if len(rt) > 0:
            print('found human!')
        else:
            print('no found')
        cv2.waitKey(1000 // 30)
