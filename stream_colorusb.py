from time import sleep , clock
from msvcrt import kbhit
import websocket
import pywinusb.hid as hid
import thread
import json
from obsremote import OBSRemote
from usbbuttons import KeyboardButton

class Manager(object):
    def __init__(self):
        self.profiles = ["Maggie","Amy","Bryan"]
        self.state = 'idle'
        self.streaming = False
        self.button = KeyboardButton()
        self.obsremote = None
        self.current_profile = 0
        
        self.nextstate = []
        return

    def next_profile(self):
        self.current_profile = (self.current_profile + 1) % len(self.profiles)
        return self.current_profile

    def tick(self):
        self.button.update()
        self.handle_state()

    def handle_state(self):
        if self.state == 'idle':
            if self.button.pressed:
                self.state = 'profileselect_orstream'

        elif self.state == 'profileselect_orstream':
            if self.button.pressed:
               if self.button.get_elapsed_time() > 5:
                    print "STARTING STREAM WITH PROFILE %s" %self.profiles[self.current_profile]
                    self.state = 'waitunpressed'
                    self.nextstate.append('streaming_idle')
            else:
                self.next_profile();
                print 'Selected next profile : %s' %self.profiles[self.current_profile]
                self.state = 'idle'
        elif self.state == 'waitunpressed':
            if not self.button.pressed:
                self.state = self.nextstate.pop()
        elif self.state == 'streaming_idle':
            if self.button.pressed:
                self.state = 'streaming_pressed'
        elif self.state == 'streaming_pressed':
            if self.button.pressed:
                if self.button.get_elapsed_time() > 2:
                    print "STOPPING STREAMING"
                    self.state = 'waitunpressed'
                    self.nextstate.append('idle')
            else:
                self.state = 'streaming_idle'
    
    def start_stream(self):
        pass



buttonpressed = False
def callbk():
    global buttonpressed
    buttonpressed = True

if __name__ == '__main__':
    y = Manager()
    y.button.daemon = True
    y.button.start()
    statecache = ''

    try:
        while True:
            sleep(0)
            y.tick()
            if statecache != y.state:
                print y.state
                statecache = y.state
    except KeyboardInterrupt:
        pass
    finally:
        #obsRemote.stop()
        y.button.stop()
        pass
