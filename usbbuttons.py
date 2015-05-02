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
from time import time
import pythoncom, pyHook , threading

#used for debugging without access to a usb button mostly
class KeyboardButton(threading.Thread):
    def __init__(self):
        super(KeyboardButton, self).__init__()
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        

    def run(self):
        self.running = True
        self.hm = pyHook.HookManager()
        self.hm.KeyDown = self.onkeyboardevent
        self.hm.KeyUp = self.onkeyboardevent
        self.hm.HookKeyboard()
        while self.running:
            pythoncom.PumpWaitingMessages()

    def stop(self):
        self.running = False
        self.join()

    def get_elapsed_time(self):
        if self.pressed:
            return time() - self.pressedTime
        else:
            return 0

    def send_color(self,rgb):
        print 'sent color , ' , rgb

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
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        return

    def get_elapsed_time(self):
        if self.pressed:
            return time() - self.pressedTime
        else:
            return 0

    def update(self):
        self.report.send([0x00,0x02,0x00,0x00,0x00])

    def send_color(self,rgb):
        self.report.send([0x00, 0x01, hex(rgb[0]), hex(rgb[1]), hex(rgb[2])])

    def start(self):
        filter = hid.HidDeviceFilter(vendor_id = 0xd209)
        self.hid_devices = filter.get_devices()
        for device in self.hid_devices:
            device.open()
            device.set_raw_data_handler(self.raw_handler)
            for report in device.find_feature_reports() + device.find_output_reports():
                self.report = report
                print 'got 1 report'
        return

    def stop(self):
        #stoppit
        for device in self.hid_devices:
            device.close()
        return

    def raw_handler(self,data):
        print data


class AvrMediaButton(object):
    def __init__(self,pressed_callback):
        self.callback = pressed_callback
        return

    def start(self):
        #init
        filter = hid.HidDeviceFilter(vendor_id = 1994, product_id = 38992)
        hid_device = filter.get_devices()
        self.device = hid_device[0]
        self.device.open()
        self.device.set_raw_data_handler(self.press_handler)
        self.target_usage = hid.get_full_usage_id(0xffa0, 0x02)
        self.report = self.device.find_output_reports()[0] 
        return

    def stop(self):
        #stoppit
        self.turn_off()
        self.device.close()
        return

    def press_handler(self,data):
        if data[2] == 1:
            self.callback()         
        #elif data[2] == 0:                       
        return

    def flash(self):
        #doflash
        return

    def glow(self):
        #glow
        return

    def turn_on(self):
        self.report[self.target_usage] = ALL_ON[0]
        self.report.send()
        return

    def turn_off(self):
        self.report[self.target_usage] = ALL_OFF[0]
        self.report.send()
        return


