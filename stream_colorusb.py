from time import sleep
import thread
from obsremote import OBSRemote
from usbbuttons import KeyboardButton, UsbButtonButton

class Manager(object):
    def __init__(self):
        self.profiles = [("Maggie",(80,201,255)),("Amy",(255,115,100)),("Bryan",(0,255,0))]
        self.state = 'idle'
        self.button = UsbButtonButton()
        self.obsremote = OBSRemote("ws://127.0.0.1:4444")
        self.current_profile = 0        
        self.nextstate = []
        return

    def start(self):
        self.obsremote.start()
        self.button.start()

    def stop(self):
        self.obsremote.stop_streaming()
        self.obsremote.stop()
        self.button.stop()

    def next_profile(self):
        self.current_profile = (self.current_profile + 1) % len(self.profiles)
        return self.current_profile

    def tick(self):
        self.button.update()
        self.handle_state()

    def handle_state(self):
        if self.state == 'idle':
            self.handle_idle()
        elif self.state == 'profileselect':
           self.handle_profileselect()
        elif self.state == 'waitunpressed':
            self.handle_waitunpressed()
        elif self.state == 'wait_streaming':
           self.handle_wait_streaming()
        elif self.state == 'wait_stop_streaming':
           self.handle_wait_stop_streaming()
        elif self.state == 'streaming_idle':
            self.handle_streaming_idle()
        elif self.state == 'streaming_pressed':
            self.handle_streaming_pressed()

    def handle_idle(self):
        if self.button.pressed:
                self.state = 'profileselect'

    def handle_profileselect(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 5:
                print "STARTING STREAM WITH PROFILE %s" %self.profiles[self.current_profile][0]
                self.obsremote.set_profile(self.profiles[self.current_profile])
                self.obsremote.start_streaming(preview=True)
                self.state = 'waitunpressed'                    
                self.nextstate.append('streaming_idle')
                self.nextstate.append('wait_streaming')
        else:
            self.next_profile();
            self.button.send_color(self.profiles[self.current_profile][1])
            print 'Selected next profile : %s' %self.profiles[self.current_profile][0]
            self.state = 'idle'

    def handle_waitunpressed(self):
        if not self.button.pressed:
                self.state = self.nextstate.pop()

    def handle_wait_streaming(self):
         if self.obsremote.streaming:
                self.state = self.nextstate.pop()

    def handle_wait_stop_streaming(self):
         if not self.obsremote.streaming:
                self.state = self.nextstate.pop()

    def handle_streaming_idle(self):
        if self.button.pressed:
            self.state = 'streaming_pressed'
        if not self.obsremote.streaming:
            self.state = 'idle'

    def handle_streaming_pressed(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                print "STOPPING STREAMING"
                self.obsremote.stop_streaming(preview=True)
                self.state = 'waitunpressed'                    
                self.nextstate.append('idle')
                self.nextstate.append('wait_stop_streaming')

        else:
            self.state = 'streaming_idle'

if __name__ == '__main__':
    y = Manager()
    statecache = ''
    try:
        y.start()
        while True:
            sleep(0.01)
            y.tick()
            if statecache != y.state:
                print y.state
                statecache = y.state
    except KeyboardInterrupt:
        pass
    finally:
        y.stop()
        pass
