from argparse import ArgumentParser
from typing import Optional

from adbutils import adb
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPixmap, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox

import scrcpy
import cv2
from threading import Thread
import time
from time import sleep
from ui_main import Ui_MainWindow
import queue
import logging
import sys

if not QApplication.instance():
    app = QApplication([])
else:
    app = QApplication.instance()

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)
class MainWindow(QMainWindow):
    def __init__(
        self,
        max_width: Optional[int],
        serial: Optional[str] = None,
        encoder_name: Optional[str] = None,
        frame_queue: Optional[queue.Queue] = None,
    ):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.max_width = max_width        
        self.frame_queue = frame_queue
        self.stop = False
        self.mouse_touch_id=-2
        self.screen_status = True
        self.take_screenshot_request=False

        # Setup devices
        self.devices = self.list_devices()
        if serial:
            self.choose_device(serial)
        self.device = adb.device(serial=self.ui.combo_device.currentText())
        self.alive = True

        # Setup client
        self.client = scrcpy.Client(
            device=self.device,
            flip=self.ui.flip.isChecked(),
            # bitrate=1000000000,
            bitrate=8000000,
            encoder_name=encoder_name,
            # max_fps=10,
        )
        self.client.add_listener(scrcpy.EVENT_INIT, self.on_init)
        self.client.add_listener(scrcpy.EVENT_FRAME, self.on_frame)

        # Bind controllers
        self.ui.button_home.clicked.connect(self.on_click_home)
        self.ui.button_back.clicked.connect(self.on_click_back)
        self.ui.button_stop.clicked.connect(self.on_click_stop)
        self.ui.button_turn_off_screen.clicked.connect(self.button_turn_off_screen)
        self.ui.button_take_screenshot.clicked.connect(self.on_click_take_screenshot)

        # Bind config
        self.ui.combo_device.currentTextChanged.connect(self.choose_device)
        self.ui.flip.stateChanged.connect(self.on_flip)

        # Bind mouse event
        self.ui.label.mousePressEvent = self.on_mouse_event(scrcpy.ACTION_DOWN)
        self.ui.label.mouseMoveEvent = self.on_mouse_event(scrcpy.ACTION_MOVE)
        self.ui.label.mouseReleaseEvent = self.on_mouse_event(scrcpy.ACTION_UP)

        # Keyboard event
        self.keyPressEvent = self.on_key_event(scrcpy.ACTION_DOWN)
        self.keyReleaseEvent = self.on_key_event(scrcpy.ACTION_UP)

    def choose_device(self, device):
        if device not in self.devices:
            msgBox = QMessageBox()
            msgBox.setText(f"Device serial [{device}] not found!")
            msgBox.exec()
            return

        # Ensure text
        self.ui.combo_device.setCurrentText(device)
        # Restart service
        if getattr(self, "client", None):
            self.client.stop()
            self.client.device = adb.device(serial=device)

    def list_devices(self):
        self.ui.combo_device.clear()
        items = [i.serial for i in adb.device_list()]
        self.ui.combo_device.addItems(items)
        return items

    def on_flip(self, _):
        self.client.flip = self.ui.flip.isChecked()

    def on_click_home(self):
        self.client.control.keycode(scrcpy.KEYCODE_HOME, scrcpy.ACTION_DOWN)
        self.client.control.keycode(scrcpy.KEYCODE_HOME, scrcpy.ACTION_UP)

    def on_click_back(self):
        self.client.control.back_or_turn_screen_on(scrcpy.ACTION_DOWN)
        self.client.control.back_or_turn_screen_on(scrcpy.ACTION_UP)
    
    def get_stop(self):
        return self.stop

    def on_click_take_screenshot(self):
        self.take_screenshot_request=True        

    def button_turn_off_screen(self):
        """
        toggel screen off/on
        """
        if(self.screen_status):
            mode = scrcpy.POWER_MODE_OFF            
        else:
            mode = scrcpy.POWER_MODE_NORMAL

        self.screen_status = not self.screen_status
        self.client.control.set_screen_power_mode(mode)


    def on_click_stop(self):
        logger.info('stop click')
        self.stop = not self.stop

    def on_mouse_event(self, action=scrcpy.ACTION_DOWN):
        def handler(evt: QMouseEvent):
            focused_widget = QApplication.focusWidget()
            if focused_widget is not None:
                focused_widget.clearFocus()
            ratio = self.max_width / max(self.client.resolution)
            self.client.control.touch(
                evt.position().x() / ratio, evt.position().y() / ratio, action,self.mouse_touch_id
            )

        return handler

    def on_key_event(self, action=scrcpy.ACTION_DOWN):
        def handler(evt: QKeyEvent):
            code = self.map_code(evt.key())
            if code != -1:
                self.client.control.keycode(code, action)

        return handler

    def map_code(self, code):
        """
        Map qt keycode ti android keycode

        Args:
            code: qt keycode
            android keycode, -1 if not founded
        """

        if code == -1:
            return -1
        if 48 <= code <= 57:
            return code - 48 + 7
        if 65 <= code <= 90:
            return code - 65 + 29
        if 97 <= code <= 122:
            return code - 97 + 29

        hard_code = {
            32: scrcpy.KEYCODE_SPACE,
            16777219: scrcpy.KEYCODE_DEL,
            16777248: scrcpy.KEYCODE_SHIFT_LEFT,
            16777220: scrcpy.KEYCODE_ENTER,
            16777217: scrcpy.KEYCODE_TAB,
            16777249: scrcpy.KEYCODE_CTRL_LEFT,
        }
        if code in hard_code:
            return hard_code[code]

        print(f"Unknown keycode: {code}")
        return -1

    def on_init(self):
        self.setWindowTitle(f"Serial: {self.client.device_name}")

    def on_frame(self, frame):
        app.processEvents()
        if frame is not None:
            #     self.frame_queue.queue.clear()
            self.frame_queue.put(frame,block=False)
            if(self.take_screenshot_request):                
                time_string=time.strftime("%Y%m%d_%H%M%S",time.gmtime())
                file_name = 'D:\\Projects\\Python\\my-py-scrcpy-client\\scrcpy_ui\\simulator\\screenshot\\'+time_string+'.png'
                logger.info('screenshot name:%s',file_name)
                cv2.imwrite(file_name,frame)
                self.take_screenshot_request=False

            ratio = self.max_width / max(self.client.resolution)
            image = QImage(
                frame,
                frame.shape[1],
                frame.shape[0],
                frame.shape[1] * 3,
                QImage.Format_BGR888,
            )
            pix = QPixmap(image)
            pix.setDevicePixelRatio(1 / ratio)
            self.ui.label.setPixmap(pix)
            self.resize(1, 1)

    def closeEvent(self, _):
        self.client.stop()
        self.alive = False


class AutoBattle():
    def __init__(
        self,        
        parent_path: Optional[str] = None,        
        main_window: Optional[MainWindow] = None,        
    ):

        self.in_battle = False
        self.parent_path = parent_path
        self.frame_queue = main_window.frame_queue
        self.client = main_window.client
        self.threshold = 0.8
        self.current_frame = None
        self.main_window = main_window
        self.meet_enemy = False

    def tap(self,x,y,touch_id=-2):
        """
        tap the x,y
        args
        x:x
        y:y
        touch_id: Default using virtual id -1, you can specify it to emulate multi finger touch
        """

        self.client.control.touch(x,y,scrcpy.ACTION_DOWN,touch_id)
        sleep(0.1)
        self.client.control.touch(x,y,scrcpy.ACTION_UP,touch_id)
        logger.info('tap x:%s y:%s touch_id:%s',x,y,touch_id)

    def match_latest_frame(self,frame,file_ab_path):
        """
        match the template image with current frame, if match , return the match location

        Args:
        frame: current frame av decode
        file_ab_path: the template file path need to match
        """
        if(self.main_window.get_stop()):
            logger.info('stop match')
            return False,None
        # start_time = time()
        try:
            target = cv2.imread(file_ab_path)
            theight, twidth = target.shape[:2]
            # frame = cv2.imread("D:\\Projects\\Python\\my-py-scrcpy-client\\scrcpy_ui\\simulator\\screenshot\\screenshot_3.png")     
            result = cv2.matchTemplate(target, frame,cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            # logger.info('match %s result:%s',file_ab_path,max_val > self.threshold)
            # stop_time = time()
            # logger.info('time consume:%s',"{:.2}".format(stop_time-start_time))
            return max_val > self.threshold, (max_loc[0]+twidth/2, max_loc[1]+theight/2)
            # return False, None
        except Exception as e:
            logger.error('出现异常,并继续%s',e)            
            return False, None

    def select_MOJIA_agency(self):
        """
        select the 墨家机关道 and solo ai
        select the 墨家机关道 and match , auto surrender after 2mins
        """
        # self.in_battle = False
        
        # screenshot_list = ['battle', 'solo', 'ai_mode', 'mojiajiguandao', 'hero_list','mage', 'hero_zhugeliang', 'confirm',  'continue', 'return_to_hall', 'giveup', 'confirm_2', 'return_to_hall_fromtaozhuang']
        screenshot_list = ['battle', 'solo', 'matching', 'mojiajiguandao', 'hero_list','mage', 'hero_zhugeliang', 'confirm',  'confirm_match', 'continue', 'again','return_to_hall', 'giveup', 'confirm_2', 'return_to_hall_fromtaozhuang']

        while True:
            if(self.in_battle == False and self.current_frame is not None):
                for filename in screenshot_list:
                    file_ab_path = ""+self.parent_path+filename+'.png'
                    match, location = self.match_latest_frame(self.current_frame,file_ab_path)
                    if(match):
                        self.tap(location[0] , location[1])
                        sleep(1)
                sleep(1)
                logger.info("结束选择墨家机关道")
            sleep(1)

    def detect_battle(self):
        """
        match the tp picture with current frame to detect whether it's in battle mode
        """
        print('Start detect battle mode')
        
        battle_start_time = time.time()
        battle_start = False

        while True:
            if(self.current_frame is not None):
                tp = ""+self.parent_path+'tp.png'
                tp_dead = ""+self.parent_path+'tp-dead.png'            
                is_tp, location = self.match_latest_frame(self.current_frame, tp)  
                is_tp_dead, location = self.match_latest_frame(self.current_frame, tp_dead)                
                self.in_battle = is_tp | is_tp_dead

                if(not self.in_battle):
                    print("not in battle now")
                    battle_start=False

                if(not battle_start and self.in_battle):
                    battle_start = True
                    battle_start_time = time.time()

                if(self.in_battle and time.time() - battle_start_time>120): #2分钟就投降
                    self.surrender()

                sleep(5)

            # sleep(5)

    def surrender(self):
        setting = ""+self.parent_path+'setting.png'
        surrender = ""+self.parent_path+'surrender.png'
        match,location = self.match_latest_frame(self.current_frame, setting)
        if(match):
            self.tap(location[0] , location[1])
            sleep(1)
            
        match,location = self.match_latest_frame(self.current_frame, surrender)
        if(match):
            self.tap(location[0] , location[1])
        
         

    def swipe(self,x1,y1,x2,y2):
        self.client.control.swipe(start_x=x1,start_y=y1,end_x=x2,end_y=y2)        
        return

    def keep_move(self):
        while True:
            if(self.in_battle and not self.meet_enemy):
                self.swipe(400,1300,600,600)        
                sleep(0.1)
            else:
                sleep(1)

    def consume_queue(self):
        while True:
            self.current_frame=self.frame_queue.get()
            # logger.info('queue size:%s',self.frame_queue.qsize())

    def detect_skill_upgrade(self):
        while True:
            if(self.in_battle):
                upgrade_skill = ""+self.parent_path+'upgrade_skill.png'
                match, location = self.match_latest_frame(self.current_frame,upgrade_skill)                
                if(match):
                    self.tap(location[0] , location[1])
                
                upgrade_skill_2 = ""+self.parent_path+'upgrade_skill_2.png'
                match, location = self.match_latest_frame(self.current_frame,upgrade_skill_2)
                if(match):
                    self.tap(location[0] , location[1])                                  
            sleep(2)

    def detect_enemy(self):
        """
        根据地方英雄血条检测敌人
        检测到敌人同时按下123技能以及攻击
        """
        skill_1 = [1800, 1400,10]
        skill_2 = [2000, 1100,20]
        skill_3 = [2200, 1000,30]
        equip_1 = [250,650,5]
        attack = [2200, 1400,40]
        while True:
            if(self.in_battle):            
                enemy_healthbar = ""+self.parent_path+'enemy_healthbar.png'
                match, location = self.match_latest_frame(self.current_frame,enemy_healthbar)
                if(match):
                    logger.info('detect enemy!!! attack')
                    self.meet_enemy = True
                    try:
                        self.tap(equip_1[0] , equip_1[1],equip_1[2])                        

                        for i in range(5):
                                self.tap(skill_1[0] , skill_1[1],skill_1[2])
                                self.tap(skill_2[0] , skill_2[1],skill_2[2])
                                self.tap(skill_3[0] , skill_3[1],skill_3[2])
                                self.tap(attack[0] , attack[1],attack[2])                                
                    except Exception as e:
                        logger.error(e)
                        continue
                else:
                    self.meet_enemy = False
                sleep(0.5)
                
            sleep(2)

    def run_auto_earn_script(self):
        Thread(target=self.select_MOJIA_agency, args=()).start()
        Thread(target=self.detect_battle, args=()).start()
        Thread(target=self.keep_move, args=()).start()
        Thread(target=self.detect_skill_upgrade, args=()).start()
        Thread(target=self.detect_enemy, args=()).start()
        Thread(target=self.consume_queue, args=()).start()
        
        return

def main():
    
    parser = ArgumentParser(description="A simple scrcpy client ref to https://github.com/leng-yue/py-scrcpy-client")
    parser.add_argument(
        "-m",
        "--max_width",
        type=int,
        default=800,
        help="Set max width of the window, default 800",
    )
    parser.add_argument(
        "-d",
        "--device",
        type=str,
        help="Select device manually (device serial required)",
    )
    parser.add_argument("--encoder_name", type=str, help="Encoder name to use")
    args = parser.parse_args()

    m = MainWindow(args.max_width, args.device, args.encoder_name,queue.LifoQueue())    
    m.show()

    battle = AutoBattle(
        parent_path='D:\\Projects\\Python\\my-py-scrcpy-client\\scrcpy_ui\\simulator\\',        
        main_window = m,
    )
    battle.run_auto_earn_script()

    m.client.start()
    while m.alive:
        m.client.start()


if __name__ == "__main__":
    main()
