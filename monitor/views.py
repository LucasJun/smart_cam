from django.shortcuts import render
from django.http import HttpResponse, StreamingHttpResponse
import time
import os
from global_var import sc_m

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
    return render(request, 'index.html')

def adjust(request):
    return render(request, 'adjust.html')

def setting(request):
    return render(request, 'setting.html')

def manual(request):
    return render(request, 'manual.html')

def about(request):
    return render(request, 'about.html')