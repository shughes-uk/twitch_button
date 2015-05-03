

from time import sleep
import thread
import os
from obsremote import OBSRemote
from usbbuttons import AvrMediaButton

buttonpressed = False
def callbk():
    global buttonpressed
    buttonpressed = True

if __name__ == '__main__':
    try:
        x = OBSRemote("ws://192.168.1.107:4444")
        x.start()
        y = AvrMediaButton(callbk)
        y.start()
        old_streaming = False
        y.turn_off()
        print "Button Ready!"
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
    except IndexError:
        print 'ERROR: Check button plugged in'
    finally:
        try:
            x.stop()
            y.turn_off()
            y.stop()
        except:
            pass
    os.system("pause")
    
