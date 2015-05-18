from time import sleep , time
from datetime import datetime, timedelta
from argparse import ArgumentParser
from obsremote import OBSRemote
from usbbuttons import *
import logging
from win32event import CreateMutex
from win32api import CloseHandle, GetLastError
from winerror import ERROR_ALREADY_EXISTS

class singleinstance:
    """ Limits application to single instance """

    def __init__(self):
        self.mutexname = "twitch_button_mutex"
        self.mutex = CreateMutex(None, False, self.mutexname)
        self.lasterror = GetLastError()
    
    def alreadyrunning(self):
        return (self.lasterror == ERROR_ALREADY_EXISTS)
        
    def __del__(self):
        if self.mutex:
            CloseHandle(self.mutex)


class Manager(object):
    def __init__(self,obs_ip="127.0.0.1",button_type="usbbuttonbutton",preview_only=False):
        self.logger = logging.getLogger("Button_Manager")
        self.logger.info("Args  obs_ip = %s button_type = %s preview = %s" %(obs_ip,button_type,str(preview_only)))
        self.logger.info("Initializing")
        self.profiles = [("Maggie",(0,0,255)),("Amy",(255,0,255)),("Bryan",(255,255,0)),("Youtube",(255,128,0))]
        self.state = 'idle'
        if button_type == "usbbuttonbutton":
            self.button = UsbButtonButton()
        elif button_type == "avermedia":
            self.button = AvrMediaButton()
        elif button_type == "keyboard":
            self.button = KeyboardButton()
        self.obsremote = OBSRemote("ws://%s:4444" %obs_ip)
        self.current_profile = 0
        self.nextstate = []
        self.current_color = (0,0,0)
        self.highlights = []
        self.starttime = datetime.now()
        self.preview = preview_only
        self.last_recover_attempt = 0
        return

    def run(self):
        self.logger.info("Running")
        self.obsremote.start()
        self.button.start()
        self.button.send_color(self.profiles[self.current_profile][1])
        statecache = ''
        try:
            while True:
                sleep(0.01)
                self.tick()
                if statecache != self.state:
                    self.logger.info('CurrentState: ' + y.state)
                    statecache = self.state
        except KeyboardInterrupt:
            pass
        finally:
            self.logger.info("Shutting down")
            self.obsremote.stop_streaming(self.preview)
            self.obsremote.stop()
            self.button.send_color((0,0,0))
            self.button.stop()

    def next_profile(self):
        self.current_profile = (self.current_profile + 1) % len(self.profiles)
        return self.current_profile

    def tick(self):        
        if not self.button.connected and self.state != 'error':
            self.state = 'error'
            self.logger.warn("Button appears to be disconnected , will try to find it again in 10 seconds")
        elif not self.obsremote.connected and self.state != 'error':
            self.state = 'error'
            self.logger.warn("OBSRemote not connected, will retry in aprox 20 seconds")
        elif self.obsremote.streaming and self.state not in ['streaming_idle', 'wait_stop_streaming', 'wait_streaming', 'waitunpressed', 'streaming_pressed']:
            self.state = 'streaming_idle'
            self.starttime = datetime.now()
        self.button.update()
        self.handle_state()

    def handle_state(self):
        if self.state == 'error':
            self.handle_error()
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

    def handle_error(self):
        if self.obsremote.connected and self.button.connected:
            self.state = 'idle'
        if time() - self.last_recover_attempt > 20:
            self.logger.warn("Attempting recovery")
            self.last_recover_attempt = time()
            if not self.obsremote.connected:
                self.obsremote.start()
                if self.button.connected:
                    if round(time()) % 2 == 0 and self.button.current_color != (0,0,0):
                        self.button.send_color((0,0,0))
                    elif round(time()) % 2 == 1 and self.button.current_color != (255,0,0):
                        self.button.send_color((255,0,0))
            if not self.button.connected:
                self.button.start()

    def handle_idle(self):
        if self.button.pressed:
                self.state = 'profileselect'
        elif self.button.current_color != self.profiles[self.current_profile][1]:
            self.button.send_color(self.profiles[self.current_profile][1])

    def handle_profileselect(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                self.logger.info("Streaming starting with profile: %s" %self.profiles[self.current_profile][0])
                self.obsremote.set_profile(self.profiles[self.current_profile][0])
                self.obsremote.start_streaming(self.preview)
                self.starttime = datetime.now()
                self.state = 'waitunpressed'                
                self.nextstate.append('streaming_idle')
                self.nextstate.append('wait_streaming')
                self.button.flash((255,0,0),(0,255,0),count=10)
        else:
            self.next_profile();
            self.button.send_color(self.profiles[self.current_profile][1])
            self.logger.info('Selected next profile : %s' %self.profiles[self.current_profile][0])
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
            self.button.send_color(self.profiles[self.current_profile][1])
        if not self.obsremote.streaming:
            self.finish_stream()
            self.state = 'idle'       
            self.button.send_color(self.profiles[self.current_profile][1])
        elif round(time()) % 2 == 0 and self.button.current_color != self.profiles[self.current_profile][1]:
            self.button.send_color(self.profiles[self.current_profile][1])
        elif round(time()) % 2 == 1 and self.button.current_color != (0,255,0):
            self.button.send_color((0,255,0))
        

    def handle_streaming_pressed(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                self.logger.info("Stopping stream")
                self.obsremote.stop_streaming(self.preview)
                self.state = 'waitunpressed'
                self.nextstate.append('idle')
                self.nextstate.append('wait_stop_streaming')               
                self.finish_stream()
                self.button.flash(self.profiles[self.current_profile][1],(255,0,0),count=10)
        else:
            self.state = 'streaming_idle'
            self.logger.info("Highlight created @ %s" %self.obsremote.streamTime)
            self.highlights.append(self.obsremote.streamTime)

    def finish_stream(self):
        if self.highlights:
            self.logger.info("Writing highlight times to file")
            h_file = open("H:\stream backups\%s\%s_highlights.txt" %(self.profiles[self.current_profile][0], self.starttime.strftime('%Y-%m-%d-%H%M-%S')),'a')
            for highlight in self.highlights:
                h_file.write(str(timedelta(milliseconds=highlight)) + '\n')
            h_file.close()
            self.highlights = []


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--obsip", "-o",
                        default="127.0.0.1",
                        dest="obs_ip",
                        help="IP Address for OBS")
    parser.add_argument("--button", "-b",
                        default="usbbuttonbutton",
                        dest="button",
                        help="Set type of USB Button, valid values are :  usbbuttonbutton , avermedia , keyboard")
    parser.add_argument("--debug", "-d",
                        action="store_const", dest="loglevel",const=logging.DEBUG,
                        default=logging.WARNING,
                        help="Enable debug messages")
    parser.add_argument("--verbose", "-v",
                       action="store_const", dest="loglevel", const=logging.INFO,
                       help="Enable messages that might be useful but not ALL THE MESSAGES")
    parser.add_argument("--preview_only", "-p",
                       action="store_true",
                       dest="preview",
                       default=False,
                       help="Preview stream only, useful for testing")
    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel,format="%(asctime)s.%(msecs)d %(levelname)s %(name)s : %(message)s",datefmt="%H:%M:%S")
    instance = singleinstance()
    if instance.alreadyrunning():
        logging.fatal("Can't run multiple instances of this script!")
        exit(0)
    y = Manager(obs_ip=args.obs_ip,button_type=args.button,preview_only=args.preview)
    y.run()