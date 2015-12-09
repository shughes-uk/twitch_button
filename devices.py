import pywinusb.hid as hid
from time import time, sleep
import threading
import logging


class Device(object):

    def __init__(self):
        super(Device, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_color = (0, 0, 0)
        self.lock = threading.Lock()
        self.flashlock = threading.Lock()

    def set_color(self, color):
        raise Exception("Function not implemented , whoops")

    def flash(self, color_1, color_2, ntimes=10, interval=0.2, nonblocking=False):
        if nonblocking:
            t = threading.Thread(target=self.flash, args=(color_1, color_2, ntimes, interval))
            t.start()
            return
        else:
            with self.flashlock:
                old_color = self.current_color
                for x in range(ntimes):
                    self.set_color(color_1)
                    sleep(interval)
                    self.set_color(color_2)
                    sleep(interval)
                self.set_color(old_color)

    def start(self):
        raise Exception("Function not implemented, whoops")

    def stop(self):
        raise Exception("Function not implemented, whoops")


class UsbButtonButton(Device):

    def __init__(self):
        super(UsbButtonButton, self).__init__()
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        self.current_color = (0, 0, 0)
        self.report = None
        self.device = None
        self.connected = False
        self.thread = None
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
            self.report.send([0x00, 0x02, 0x00, 0x00, 0x00])

    def set_color(self, rgb):
        with self.lock:
            if self.device:
                if not self.device.is_plugged():
                    self.connected = False
                    self.report = None
                    self.device = None
                    self.logger.warn("Usb Button possibly unplugged")
                    return
                self.logger.debug("Sending color R%i,G%i,B%i" % (rgb[0], rgb[1], rgb[2]))
                self.report.send([0, 80, 221, 0, 0])
                self.report.send([0, rgb[0], rgb[1], rgb[2], rgb[0]])
                self.report.send([0, rgb[1], rgb[2], 0, 0])
                for x in range(1, 14):
                    self.report.send([0, 0, 0, 0, 0])
                self.current_color = rgb

    def start(self):
        self.logger.info("Searching for button")
        filter = hid.HidDeviceFilter(vendor_id=0xd209)
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

    def raw_handler(self, data):
        if len(data) == 5:
            if data[1] == 1 and not self.pressed:
                self.pressed = True
                self.pressedTime = time()
                self.logger.debug('pressed')
            elif data[1] == 0 and self.pressed:
                self.pressed = False
                self.pressedTime = 0
                self.logger.debug('unpressed')
