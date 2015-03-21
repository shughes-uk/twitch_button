#Led Sequences!
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



from time import sleep
from msvcrt import kbhit
import websocket
import pywinusb.hid as hid
import thread
import json

buttonstate = 0

class TwitchFollowerMonitor:
    def __init__(self,usr):
        #poop
        return

    def start(self,callbk):
        #start
        return

    def stop(self):
        #stop
        return


class OBSRemote:
    def __init__(self,url):
        self.url = url
        self.streaming = False

    def start(self):
        #dothing
        self.ws = websocket.WebSocketApp(self.url,
                              on_message = self.on_message,
                              on_error = self.on_error,
                              on_close = self.on_close,
                              subprotocols=["obsapi"])
        thread.start_new_thread( self.ws.run_forever, () )

    def stop(self):
        #stopthing
        self.ws.close()

    def on_message(self,ws,msg):
        #recv msg
        try:
            decoded = json.loads(msg)
            if 'streaming' in decoded:
                self.streaming = decoded['streaming']
        except Exception, E:
            print 'Bad thing happened parsing obsremote message'
            print E
        return

    def on_error(self,ws,error):
        #error
        print 'OBSRemoteError'
        print error
        return

    def on_close(self,ws):
        #closed
        print 'OBSRemote Socket closed'
        return

    def start_streaming(self):
        if self.streaming == False:
            print "OBSREMOTE : Starting stream"       
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            #msg["preview-only"] = True
            self.ws.send(json.dumps(msg))
            self.streaming = True
        return

    def stop_streaming(self):
        if self.streaming:
            print "OBSREMOTE : Stopping stream"        
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            #msg["preview-only"] = True
            self.ws.send(json.dumps(msg))
            self.streaming = False
        return


class AvrMediaButton:
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



buttonpressed = False
def callbk():
    global buttonpressed
    buttonpressed = True

if __name__ == '__main__':
    x = OBSRemote("ws://192.168.1.107:4444")
    x.start()
    y = AvrMediaButton(callbk)
    y.start()
    old_streaming = False
    y.turn_off()
    print "Button Ready!"
    try:
        while True:
            if buttonpressed:
                if x.streaming:
                    x.stop_streaming()
                    buttonpressed = False
                else:
                    x.start_streaming()
                    buttonpressed = False
            if old_streaming != x.streaming:
                if x.streaming:
                    print "Now streaming"
                    y.turn_on()
                else:
                    y.turn_off()
                    print "Stream ended"
                old_streaming = x.streaming
    except KeyboardInterrupt:
        pass
    finally:
        x.stop()
        y.turn_off()
        y.stop()

