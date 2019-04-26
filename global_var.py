import threading
import time

# 从/smart_cam_main.py中导入启动检测器的主模块
from smart_cam.smart_cam_main import SmartCam


class sc_m(object):
    instance = None
    init_flag = False
    sc = None

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance
    
    def __init__(self):
        if sc_m.init_flag:
            return  
        sc_thread = threading.Thread(target=self.cam_run)
        sc_thread.start()
        print('检测器启动成功')
        while True:
            if self.sc is not None:
                break
            time.sleep(1)
        sc_m.init_flag = True
    
        pass

    def cam_run(self):
        self.sc = SmartCam(-1, debug_show=False)
        self.sc.load()
        # exit(0)
        self.sc.run()

