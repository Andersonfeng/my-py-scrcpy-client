import logging
import sys
import threading
import cv2
import time
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

def match_latest_frame(frame,file_ab_path):
    """
    match the template image with current frame, if match , return the match location

    Args:
    frame: current frame av decode
    file_ab_path: the template file path need to match
    """
    threshold=0.8
    # start_time = time()
    try:
        target = cv2.imread(file_ab_path)
        theight, twidth = target.shape[:2]
        
        result = cv2.matchTemplate(target, frame,cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        logger.info('match %s max_val:%s result:%s ',file_ab_path,max_val,max_val > threshold)        
        return max_val > threshold, (max_loc[0]+twidth/2, max_loc[1]+theight/2)
        # return False, None
    except Exception as e:
        logger.error('出现异常,并继续%s',e)            
        return False, None

class Job(threading.Thread):

    def __init__(self,*args,**kwargs):
        super(Job,self).__init__(*args,**kwargs)
        self.__flag = threading.Event()
        self.__flag.set()
        self.__running = threading.Event()
        self.__running.set()
    
    def run(self):
        while self.__running.isSet():
            self.__flag.wait()
            logger.info(time.time())
            time.sleep(1)
    
    def pause(self):
        logger.info('pause!')
        self.__flag.clear()

    def resume(self):
        logger.info('resume!')
        self.__flag.set()
    
    def stop(self):
        logger.info('stop!')
        self.__flag.set()
        self.__running.clear()

def thread_demo(thread_name,thread_event):

    while True:
        if(thread_event.wait()):
            continue
        logger.info(thread_name+" is running")
        time.sleep(1)

thread_event = threading.Event()
thread_event_2 = threading.Event()

thread_1 = threading.Thread(target=thread_demo,args=('thread_1',thread_event))
thread_2 = threading.Thread(target=thread_demo,args=('thread_2',thread_event_2))

thread_2.start()
thread_1.start()

while True:
    thread_2.wait()
    time.sleep(3)
    thread_2.notify()
    time.sleep(3)

# start_time = time.time()
# time.sleep(3)
# end_time = time.time()

# logger.info(end_time-start_time)



# 线程暂停