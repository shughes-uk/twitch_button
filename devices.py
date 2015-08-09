
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


import platform
import pywinusb.hid as hid
from time import time, sleep
import pythoncom, pyHook , threading, win32event, logging

class Device(object):
    def __init__(self):
        super(Device, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_color = (0,0,0)

    def set_color(self,color):
        raise Exception("Function not implemented , whoops")

    def flash(self,color_1,color_2,ntimes=10,interval=0.2):
        old_color = self.current_color
        for x in range (ntimes):
            self.set_color(color_1)
            sleep(interval)
            self.set_color(color_2)
            sleep(interval)
        self.set_color(old_color)

    def start(self):
        raise Exception("Function not implemented, whoops")

    def stop(self):
        raise Exception("Function not implemented, whoops")


#used for debugging without access to a usb button mostly
class KeyboardButton(threading.Thread,Device):
    def __init__(self):
        super(KeyboardButton, self).__init__()
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        self.daemon = True
        #self.logger = logging.getLogger("Keyboard_button")


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


class UsbButtonButton(Device):
    def __init__(self):
        super(UsbButtonButton, self).__init__()
        self.logger = logging.getLogger("UsbButtonButton")
        self.pressed = False
        self.pressedTime = 0
        self.status_queue = []
        self.current_color = (0,0,0)
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
            self.report.send([0x00,0x02,0x00,0x00,0x00])

    def set_color(self,rgb):
        if self.device:
            if not self.device.is_plugged():
                self.connected = False
                self.report = None
                self.device = None
                self.logger.warn("Usb Button possibly unplugged")
                return
            self.logger.debug("Sending color R%i,G%i,B%i" %(rgb[0], rgb[1], rgb[2]))
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

import serial

# For Python3 support- always run strings through a bytes converter
import sys
if sys.version_info < (3,):
    def encode(x):
        return x
else:
    import codecs
    def encode(x):
        return codecs.latin_1_encode(x)[0]


class BlinkyTape(Device):
    def __init__(self, port, ledCount=60, buffered=True):
        """Creates a BlinkyTape object and opens the port.

        Parameters:
          port
            Required, port name as accepted by PySerial library:
            http://pyserial.sourceforge.net/pyserial_api.html#serial.Serial
            It is the same port name that is used in Arduino IDE.
            Ex.: COM5 (Windows), /dev/ttyACM0 (Linux).
          ledCount
            Optional, total number of LEDs to work with,
            defaults to 60 LEDs. The limit is enforced and an
            attempt to send more pixel data will throw an exception.
          buffered
            Optional, enabled by default. If enabled, will buffer
            pixel data until a show command is issued. If disabled,
            the data will be sent in byte triplets as expected by firmware,
            with immediate flush of the serial buffers (slower).

        """
        super(BlinkyTape, self).__init__()
        self.port = port
        self.ledCount = ledCount
        self.position = 0
        self.buffered = buffered
        self.buf = ""

    def start(self):
        self.serial = serial.Serial(self.port, 115200)
        self.show()  # Flush any incomplete data

    def stop(self):
        """Safely closes the serial port."""
        self.serial.close()

    def send_list(self, colors):
        if len(colors) > self.ledCount:
            raise RuntimeError("Attempting to set pixel outside range!")
        for r, g, b in colors:
            self.sendPixel(r, g, b)
        self.show()

    def send_list(self, colors):
        data = ""
        for r, g, b in colors:
            if r >= 255:
                r = 254
            if g >= 255:
                g = 254
            if b >= 255:
                b = 254
            data += chr(r) + chr(g) + chr(b)
        self.serial.write(encode(data))
        self.show()

    def sendPixel(self, r, g, b):
        """Sends the next pixel data triplet in RGB format.

        Values are clamped to 0-254 automatically.

        Throws a RuntimeException if [ledCount] pixels are already set.
        """
        data = ""
        if r < 0:
            r = 0
        if g < 0:
            g = 0
        if b < 0:
            b = 0
        if r >= 255:
            r = 254
        if g >= 255:
            g = 254
        if b >= 255:
            b = 254
        data = chr(r) + chr(g) + chr(b)
        if self.position < self.ledCount:
            if self.buffered:
                self.buf += data
            else:
                self.serial.write(encode(data))
                self.serial.flush()
            self.position += 1
        else:
            raise RuntimeError("Attempting to set pixel outside range!")

    def show(self):
        """Sends the command(s) to display all accumulated pixel data.

        Resets the next pixel position to 0, flushes the serial buffer,
        and discards any accumulated responses from BlinkyTape.
        """
        control = chr(255)
        if self.buffered:
            # Fix an OS X specific bug where sending more than 383 bytes of data at once
            # hangs the BlinkyTape controller. Why this is???
            # TODO: Test me on other platforms
            CHUNK_SIZE = 300

            self.buf += control
            for i in range(0, len(self.buf), CHUNK_SIZE):
                self.serial.write(encode(self.buf[i:i+CHUNK_SIZE]))
                self.serial.flush()

            self.buf = ""
        else:
            self.serial.write(encode(control))
        self.serial.flush()
        self.serial.flushInput()  # Clear responses from BlinkyTape, if any
        self.position = 0

    def set_color(self, rgb):
        """Fills [ledCount] pixels with RGB color and shows it."""
        for i in range(self.ledCount):
            self.sendPixel(rgb[0], rgb[1], rgb[2])
        self.current_color = rgb
        self.show()

    def resetToBootloader(self):
        """Initiates a reset on BlinkyTape.

        Note that it will be disconnected.
        """
        self.serial.setBaudrate(1200)
        self.close()
