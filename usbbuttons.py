#Led Sequences for Avermedia Button!
#FLASH CIRCLE
CIRCLE_FLASH = [
    [0x12, 0x00, 0x00, 0x00, 0x06, 0x82, 0x00, 0x00],
    [0x12, 0x14, 0x00, 0x00, 0x06, 0x81, 0x00, 0x00],
    [0x12, 0x00, 0x00, 0x00, 0x06, 0x82, 0x00, 0x00],
    [0x22, 0x14, 0x00, 0x00, 0x06, 0x83, 0x00, 0x00],
    [0x22, 0x00, 0x00, 0x00, 0x06, 0x84, 0x00, 0x00],
    [0x42, 0x14, 0x00, 0x00, 0x06, 0x85, 0x00, 0x00],
    [0x42, 0x00, 0x00, 0x00, 0x06, 0x86, 0x00, 0x00],
    [0x82, 0x14, 0x00, 0x00, 0x06, 0x87, 0x00, 0x00],
    [0x82, 0x00, 0x00, 0x00, 0x06, 0x88, 0x00, 0x00],
]
#GLOW PULSE
CIRCLE_FLASH = [
    [0xf3, 0x00, 0x14, 0x00, 0x00, 0x41, 0x00, 0x00],
    [0xf3, 0x14, 0x64, 0x00, 0x00, 0x42, 0x00, 0x00],
    [0xf3, 0x64, 0x2d, 0x00, 0x32, 0x43, 0x00, 0x00],
    [0xf3, 0x2d, 0x14, 0x00, 0x32, 0x44, 0x00, 0x00],
]
#SOLID ON
#the first four bits of the first byte corespond to the LEDs/LED you want to turn on/off!
ALL_ON = [[0b11110001, 0x23, 0x00, 0x00, 0x00, 0x11, 0x00, 0x00]]
#TURNS OFF
ALL_OFF = [[0b11110001, 0x00, 0x00, 0x00, 0x00, 0x11, 0x00, 0x00]]



import pywinusb.hid as hid
from time import time, sleep
import pythoncom, pyHook , threading, win32event, logging

#used for debugging without access to a usb button mostly
class KeyboardButton(threading.Thread):
    def __init__(self):
        super(KeyboardButton, self).__init__()
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        self.daemon = True
        self.logger = logging.getLogger("Keyboard_button")


    def run(self):
        self.running = True
        self.hm = pyHook.HookManager()
        self.hm.KeyDown = self.onkeyboardevent
        self.hm.KeyUp = self.onkeyboardevent
        self.hm.HookKeyboard()
        self.current_color = (0,0,0)
        event = win32event.CreateEvent(None, 0, 0, None)
        while self.running:
            pythoncom.PumpWaitingMessages()
            win32event.MsgWaitForMultipleObjects([event],0,1,win32event.QS_ALLEVENTS)

    def stop(self):
        self.running = False
        self.join()

    def get_elapsed_time(self):
        if self.pressed:
            return time() - self.pressedTime
        else:
            return 0

    def send_color(self,rgb):
        self.logger.debug("Sending color R%i,G%i,B%i" %rgb)
        self.current_color = rgb

    def update(self):
        return

    def onkeyboardevent(self,event):
        if event.KeyID == 101 and event.MessageName == 'key down' and not self.pressed:
            self.pressed = True
            self.pressedTime = time()
        if event.KeyID == 101 and event.MessageName == 'key up' and self.pressed:
            self.pressed = False
            self.pressedTime = 0
        return True
    



class UsbButtonButton(object):
    def __init__(self):
        self.logger = logging.getLogger("UsbButtonButton")
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        self.current_color = (0,0,0)
        self.report = None
        self.device = None
        self.connected = False
        return

    def get_elapsed_time(self):
        if self.pressed:
            return time() - self.pressedTime
        else:
            return 0

    def update(self):
        if self.device:
            if not self.device.is_plugged():
                self.connected = False
                self.report = None
                self.device = None
                self.logger.warn("Usb Button possibly unplugged")
                return
            self.report.send([0x00,0x02,0x00,0x00,0x00])

    def send_color(self,rgb):
        if self.device:
            if not self.device.is_plugged():
                self.connected = False
                self.report = None
                self.device = None
                self.logger.warn("Usb Button possibly unplugged")
                return
            self.logger.debug("Sending color R%i,G%i,B%i" %rgb)
            self.report.send([0,80,221,0,0])
            self.report.send([0,rgb[0],rgb[1],rgb[2],rgb[0]])
            self.report.send([0,rgb[1],rgb[2],0,0])
            for x in range(1,14):
                self.report.send([0,0,0,0,0])
            self.current_color = rgb

    def start(self):
        self.logger.info("Searching for button")
        filter = hid.HidDeviceFilter(vendor_id = 0xd209)
        self.hid_devices = filter.get_devices()        
        for device in self.hid_devices:
            device.open()
            device.set_raw_data_handler(self.raw_handler)
            for report in device.find_feature_reports() + device.find_output_reports():
                self.report = report
                self.device = device
                self.logger.debug("Found report and button")
                self.connected = True
        if not self.hid_devices or not self.report:
            self.logger.warn("Couldn't find button or something is wrong")
        return

    def stop(self):
        self.logger.info("Tidying up")
        for device in self.hid_devices:
            device.close()
        self.connected = False
        return

    def raw_handler(self,data):
        if len(data) == 5:
            if data[1] == 1 and not self.pressed:
                self.pressed = True
                self.pressedTime = time()
                self.logger.debug('pressed')
            elif data[1] == 0 and self.pressed:
                self.pressed = False
                self.pressedTime = 0
                self.logger.debug('unpressed')
    
    def flash(self,color1,color2,interval=0.2,count=5):
        if self.device:
            if not self.device.is_plugged():
                self.connected = False
                self.report = None
                self.device = None
                self.logger.warn("Usb Button possibly unplugged")
                return
            for x in range(0,count):
                self.send_color(color1)
                sleep(interval)
                self.send_color(color2)
                sleep(interval)


class AvrMediaButton(object):
    def __init__(self,pressed_callback):
        self.logger = logging.getLogger("AvrMediaButton")
        self.logger.info("AvrMediaButton initializing")
        self.callback = pressed_callback
        return

    def start(self):
        self.logger.info("Searching for button")
        filter = hid.HidDeviceFilter(vendor_id = 1994, product_id = 38992)
        hid_device = filter.get_devices()
        self.device = hid_device[0]
        self.device.open()
        self.device.set_raw_data_handler(self.press_handler)
        self.target_usage = hid.get_full_usage_id(0xffa0, 0x02)
        self.report = self.device.find_output_reports()[0]
        self.logger.info("Found button")
        return

    def stop(self):
        self.logger.info("Tidying up")
        self.turn_off()
        self.device.close()
        return

    def press_handler(self,data):
        if data[2] == 1:
            self.logger.info("Button pressed")
            self.callback()
        return

    def turn_on(self):
        self.logger.info("LEDs ON")
        self.report[self.target_usage] = ALL_ON[0]
        self.report.send()
        return

    def turn_off(self):
        self.logger.info("LEDs OFF")
        self.report[self.target_usage] = ALL_OFF[0]
        self.report.send()
        return
