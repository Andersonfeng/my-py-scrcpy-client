import logging
import sys
import cv2

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


frame = cv2.imread("D:\\Projects\\Python\\my-py-scrcpy-client\\scrcpy_ui\\simulator\\screenshot\\20220807_044505.png")
file_ab_path="D:\\Projects\\Python\\my-py-scrcpy-client\\scrcpy_ui\\simulator\\enemy_healthbar_2.png"
match_latest_frame(frame,file_ab_path)