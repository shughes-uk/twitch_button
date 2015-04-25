from time import sleep
from msvcrt import kbhit
import websocket
import pywinusb.hid as hid
import thread
import json
from obsremote import OBSRemote
import pythoncom, pyHook , sys

class UsbButtonButton:
    def __init__(self,pressed_callback):
        self.callback = pressed_callback
        return

    def find_devices(self):
        all_devices = hid.HidDeviceFilter(vendor_id = 0xd209).get_devices()
        if not all_devices:
            print("Can't find any non system HID device connected")
        else:
            try:
                for device in all_devices:
                    device.open()
                    device.set_raw_data_handler(self.raw_handler)

                for device in all_devices:
                    print device
                    # browse feature reports
                    for report in device.find_feature_reports() + device.find_output_reports():
                        report.send([0x02,0x00,0x00,0x00,0x00])
            finally:
                for device in all_devices:
                    device.close()
            # if not usage_found:
            #     print("The target device was found, but the requested usage does not exist!\n")

    def get_status(self):
        for device in self.hid_devices:
            for report in device.find_feature_reports() + device.find_output_reports():
                report.send([0x00,0x02,0x00,0x00,0x00])

    def start(self):
        #init
        filter = hid.HidDeviceFilter(vendor_id = 0xd209)
        self.hid_devices = filter.get_devices()
        for device in self.hid_devices:
            device.open()
            device.set_raw_data_handler(self.raw_handler)
        return

    def stop(self):
        #stoppit
        for device in self.hid_devices:
            device.close()
        return

    def raw_handler(self,data):
        print data

    def press_handler(self,data):
        if data[2] == 1:
            self.callback()
        #elif data[2] == 0:
        return

    def set_color(self,rgb):
        self.report[self.target_usage] = ALL_OFF[0]
        self.report.send()
        return

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
