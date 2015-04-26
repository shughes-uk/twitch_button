from time import sleep , clock
from msvcrt import kbhit
import websocket
import pywinusb.hid as hid
import thread
import json
from obsremote import OBSRemote
import pythoncom, pyHook , sys

class UsbButtonButton(object):
    def __init__(self,pressed_callback):
        self.callback = pressed_callback
        self.pressed = False
        self.pressedTime = 0
        return

    def get_elapsed_time(self):
        if pressed:
            return clock() - self.pressedTime()
        else:
            return 0

    def req_status(self):
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

    def set_color(self,rgb):
        self.report[self.target_usage] = ALL_OFF[0]
        self.report.send()
        return

class Manager(object):
    def __init__(self):
        self.profiles = ["Maggie","Amy","Bryan"]
        self.state = 'idle'
        self.streaming = False
        self.button = UsbButtonButton(None)
        self.obsRemote = None
        self.current_profile = 0
        self.last_button_pstate = False
        return

    def next_profile(self):
        self.current_profile = (self.current_profile + 1) % len(self.profiles)
        return self.current_profile

    def handle_state(self):
        if self.state == 'idle':
            if self.button.pressed:
                self.state = 'profileselect_orstream'
        elif self.state == 'profileselect_orstream':
            if self.button.pressed:
               if self.button.get_elapsed_time() > 5:
                    print "STARTING STREAM WITH PROFILE %s" %self.current_profile
                    self.state = 'waitunpressed'
                    self.nextstate = 'streaming_idle'
            elif:
                self.next_profile();
                self.state == 'idle'
        elif self.state == 'waitunpressed':
            if not self.buttonpressed:
                self.state = self.nextstate()
        elif self.state == 'streaming_idle':
            if self.buttonpressed:
                self.state = 'streaming_pressed':
        elif self.state == 'streaming_pressed':
            if self.buttonpressed:
                if self.button.get_elapsed_time() > 2:
                    print "STOPPING STREAMING"
                    self.state = 'waitunpressed'
                    self.nextstate = 'idle'

def OnKeyboardEvent(event):
    print "Key: ", event.KeyID
    return True


buttonpressed = False
def callbk():
    global buttonpressed
    buttonpressed = True

if __name__ == '__main__':
    y = UsbButtonButton(callbk)
    #obsRemote = OBSRemote("ws://192.168.1.107:4444")
    #obsRemote.start()
    y.start()

    hm = pyHook.HookManager()
    hm.KeyDown = OnKeyboardEvent
    hm.HookKeyboard()
    #pythoncom.PumpMessages()
    try:
        while True:
            sleep(0.1)
            y.get_status()
            pythoncom.PumpWaitingMessages()
    except KeyboardInterrupt:
        pass
    finally:
        #obsRemote.stop()
        y.stop()
