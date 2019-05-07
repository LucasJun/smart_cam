from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
import time
import os
from global_var import sc_m
import json

# 此迭代生成器生成mjpeg流注入httpresponse中
def genframe(sc):
    # 手动制作一个生成器将frame迭代,没写什么时候停,理论上没yield就停了
    print(sc)
    while True:
        time.sleep(.1)
        frame = sc.get_current_jpg()
        line = b'Content-Type: image/jpeg\r\n\r\n' + bytes(frame) + b'\r\n\r\n'
        yield (b'--frame\r\n' + line)

def video_feed(request):
    scm = sc_m()
    return StreamingHttpResponse(genframe(scm.sc), content_type="multipart/x-mixed-replace; boundary=frame")

def index(request):
    status_list = sc_m().sc.get_recent_msg()
    with open('smart_cam/config.json', 'r') as config_file:
        config_dict = json.loads(config_file.read())
        notifier = config_dict["Notifier"]
    status_list = sc_m().sc.get_recent_msg()
    return render(request, 'index.html', {
        'Notifier':json.dumps(notifier),
        'status_list': status_list,
    })

# def ajax_status_table(request):
#     # 读取record文件夹中的log文件
#     ts = time.strftime('%Y_%m_%d', time.localtime())
#     record_file_path = 'smart_cam/record/' + ts + '.log'
#     status_list =[]
#     with open(record_file_path,'r') as record_file:
#         lines = record_file.readlines()
#         for i in range(-8, 0, 2):
#             status_list.append(lines[i].split(';'))
#     return HttpResponse(content=status_list)

def adjust(request):
    return render(request, 'adjust.html')

def setting(request):
    return render(request, 'setting.html')

def manual(request):
    return render(request, 'manual.html')

def about(request):
    return render(request, 'about.html')
