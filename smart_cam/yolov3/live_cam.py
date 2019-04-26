import argparse
import shutil
import time
from pathlib import Path
from sys import platform

from models import *
from utils.datasets import *
from utils.utils import *


def detect(
        cfg,
        weights,
        images,
        output='output',  # output folder
        img_size=416,
        conf_thres=0.3,
        nms_thres=0.45,
        save_txt=False,
        save_images=True,
        webcam=False
):
    device = torch_utils.select_device()
    if os.path.exists(output):
        shutil.rmtree(output)  # delete output folder
    os.makedirs(output)  # make new output folder

    # Initialize model
    model = Darknet(cfg, img_size)

    # Load weights
    if weights.endswith('.pt'):  # pytorch format
        if weights.endswith('yolov3.pt') and not os.path.exists(weights):
            if (platform == 'darwin') or (platform == 'linux'):
                os.system('wget https://storage.googleapis.com/ultralytics/yolov3.pt -O ' + weights)
        model.load_state_dict(torch.load(weights, map_location='cpu')['model'])
    else:  # darknet format
        load_darknet_weights(model, weights)

    model.to(device).eval()

    cam1 = cv2.VideoCapture(cv2.CAP_DSHOW + 1)
    cam1.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam1.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Get classes and colors
    classes = load_classes(parse_data_cfg('cfg/coco.data')['names'])
    colors = [[random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)] for _ in range(len(classes))]

    while True:
        t = time.time()

        r, im0 = cam1.read()
        if not r:
            continue
        img = cv2.resize(im0, (416, 416), interpolation=cv2.INTER_AREA)
        img = np.float32(np.transpose(img, [2, 0, 1])) / 255.

        # Get detections
        img = torch.from_numpy(img).unsqueeze(0).to(device)
        pred = model(img)
        pred = pred[pred[:, :, 4] > conf_thres]  # remove boxes < threshold

        if len(pred) > 0:
            # Run NMS on predictions
            detections = non_max_suppression(pred.unsqueeze(0), conf_thres, nms_thres)[0]

            # Rescale boxes from 416 to true image size
            scale_coords(img_size, detections[:, :4], im0.shape).round()

            # Print results to screen
            unique_classes = detections[:, -1].cpu().unique()
            for c in unique_classes:
                n = (detections[:, -1].cpu() == c).sum()
                print('%g %ss' % (n, classes[int(c)]), end=', ')

            # Draw bounding boxes and labels of detections
            for x1, y1, x2, y2, conf, cls_conf, cls in detections:

                # Add bbox to the image
                label = '%s %.2f' % (classes[int(cls)], conf)
                plot_one_box([x1, y1, x2, y2], im0, label=label, color=colors[int(cls)])

        dt = time.time() - t
        print('Done. (%.3fs)' % dt)

        cv2.imshow(weights, im0)
        cv2.waitKey(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cfg', type=str, default='cfg/yolov3-spp.cfg', help='cfg file path')
    parser.add_argument('--weights', type=str, default='weights/yolov3-spp.weights', help='path to weights file')
    parser.add_argument('--images', type=str, default='data/samples', help='path to images')
    parser.add_argument('--frame-size', type=int, default=32 * 13, help='size of each image dimension')
    parser.add_argument('--conf-thres', type=float, default=0.50, help='object confidence threshold')
    parser.add_argument('--nms-thres', type=float, default=0.7, help='iou threshold for non-maximum suppression')
    opt = parser.parse_args()
    print(opt)

    with torch.no_grad():
        detect(
            opt.cfg,
            opt.weights,
            opt.images,
            img_size=opt.img_size,
            conf_thres=opt.conf_thres,
            nms_thres=opt.nms_thres
        )
