from time import sleep , time
from datetime import datetime, timedelta
from argparse import ArgumentParser
import os, json, platform
from obsremote import OBSRemote
from BlinkyTape import BlinkyTape
from twitch_handler import TwitchHandler
import logging
from pprint import pformat
if platform.system() == "Windows":
    from win32event import CreateMutex
    from win32api import CloseHandle, GetLastError
    from winerror import ERROR_ALREADY_EXISTS
    from usbbuttons import *

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
    def __init__(self,config=None,preview_only=False):
        self.logger = logging.getLogger("Button_Manager")
        self.logger.debug("Config:\n" + pformat(config))
        self.config = config
        self.logger.info("Initializing")
        self.profiles = self.config["streamers"]
        self.state = 'idle'
        if self.config["button_type"] == "usbbuttonbutton":
            self.button = UsbButtonButton()
        elif self.config["button_type"] == "avermedia":
            self.button = AvrMediaButton()
        elif self.config["button_type"] == "keyboard":
            self.button = KeyboardButton()
        self.obsremote = OBSRemote("ws://%s:4444" %self.config["obs_ip"])
        self.current_profile = 0
        self.nextstate = []
        self.current_color = (0,0,0)
        self.highlights = []
        self.starttime = datetime.now()
        self.preview = preview_only
        self.last_recover_attempt = 0
        self.tape = BlinkyTape(self.config["blinky_port"])
        names = [x["twitch_name"] for x in self.config["streamers"]]
        self.twitch_handler = TwitchHandler(names,self.new_follower)
        return

    def set_color(self,color,devices):
        for device in devices:
            if device == "tape" or device == "all":
                self.tape.displayColor(color[0],color[1],color[2])
            if device == "button" or device == "all":
                self.button.send_color(color)
            if device == "hue" or device == "all":
                self.logger.warn("Hue not yet implmented")

    def flash_color(self,color_1,color_2,devices,ntimes=10,interval=0.5):
        old_colors = {}
        for device in devices:
            old_colors[device] = device.current_color
        for x in range (ntimes):
            for device in devices:
                device.set_color(color_1)
            sleep(interval)
            for device in devices:
                device.set_color(color_2)
        for device in devices:
            device.set_color(old_colors[device])

    def new_follower(self,name):
        if self.get_twitch_name() == name:
            self.set_color((100,100,100), 'all')
            sleep(0.5) ,,,,,,, mkopp
            self.set_color((200, 200, 200), 'all')
            sleep(0.5)
            self.set_color((100,100,100), 'all')
            sleep(0.5)
            self.set_color((200, 200, 200), 'all')
            sleep(0.5)
            self.set_color((100,100,100), 'all')
            sleep(0.5)
            self.set_color((200, 200, 200), 'all')
            sleep(0.5)
            self.set_color((100,100,100), 'all')
            sleep(0.5)
            self.set_color((200, 200, 200), 'all')
            sleep(0.5)
            self.tape.displayColor(0, 255, 0)

    def run(self):
        self.logger.info("Running")
        self.obsremote.start()
        self.button.start()
        self.button.send_color(self.get_color())
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
            self.twitch_handler.stop()
            self.tape.displayColor(0, 0, 0)
            self.tape.close()

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
            self.set_color((0,255,0),["tape"])
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
        elif self.button.current_color != self.get_color():
            self.button.send_color(self.get_color())

    def handle_profileselect(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                self.logger.info("Streaming starting with profile: %s" %self.profiles[self.current_profile]["obs_profile"])
                self.obsremote.set_profile(self.profiles[self.current_profile]["obs_profile"])
                self.obsremote.start_streaming(self.preview)
                self.starttime = datetime.now()
                self.state = 'waitunpressed'
                self.nextstate.append('streaming_idle')
                self.nextstate.append('wait_streaming')
                self.button.flash((255,0,0),(0,255,0),count=10)
        else:
            self.next_profile();
            self.button.send_color(self.get_color())
            self.logger.info('Selected next profile : %s' %self.profiles[self.current_profile]["obs_profile"])
            self.state = 'idle'

    def handle_waitunpressed(self):
        if not self.button.pressed:
            self.state = self.nextstate.pop()

    def handle_wait_streaming(self):
        if self.obsremote.streaming:
            self.tape.displayColor(0, 255, 0)
            self.state = self.nextstate.pop()

    def handle_wait_stop_streaming(self):
         if not self.obsremote.streaming:
            self.tape.displayColor(0, 0, 0)
            self.state = self.nextstate.pop()

    def handle_streaming_idle(self):
        if not self.twitch_handler.running:
            self.twitch_handler.start()
        if self.button.pressed:
            self.state = 'streaming_pressed'
            self.button.send_color(self.get_color())
        if not self.obsremote.streaming:
            self.finish_stream()
            self.state = 'idle'
            self.button.send_color(self.get_color())
            self.tape.displayColor(0, 0, 0)
        elif round(time()) % 2 == 0:
            if not self.twitch_handler.streamers[self.get_twitch_name()] and self.button.current_color != self.get_color():
                self.button.send_color(self.get_color())
                self.tape.displayColor(0, 255, 0)
            elif self.button.current_color != self.get_color():
                self.button.send_color(self.get_color())
                self.tape.displayColor(0, 255, 0)
        elif round(time()) % 2 == 1:
            if not self.twitch_handler.streamers[self.get_twitch_name()] and self.button.current_color != [255,0,0]:
                self.button.send_color((255,0,0))
                self.tape.displayColor(255, 0, 0)
            elif self.button.current_color != (0,255,0):
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
                self.button.flash(self.get_color(),(255,0,0),count=10)
        else:
            self.state = 'streaming_idle'
            self.logger.info("Highlight created @ %s" %self.obsremote.streamTime)
            self.highlights.append(self.obsremote.streamTime)

    def finish_stream(self):
        if self.twitch_handler.running:
            self.twitch_handler.stop()
        if self.highlights:
            self.logger.info("Writing highlight times to file")
            h_file = open("%s\%s_highlights.txt"%(self.config["highlights_dir"], self.starttime.strftime('%Y-%m-%d-%H%M-%S')),'a')
            for highlight in self.highlights:
                h_file.write(str(timedelta(milliseconds=highlight)) + '\n')
            h_file.close()
            self.highlights = []

    def get_color(self):
        return self.profiles[self.current_profile]["button_color"]

    def get_twitch_name(self):
        return self.profiles[self.current_profile]["twitch_name"]

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--debug", "-d",
                        action="store_const", dest="loglevel",const=logging.DEBUG,
                        default=logging.WARNING,
                        help="Enable ALL THE MESSAGES")
    parser.add_argument("--verbose", "-v",
                       action="store_const", dest="loglevel", const=logging.INFO,
                       help="Enable messages that might be useful but not ALL THE MESSAGES")
    parser.add_argument("--preview_only", "-p",
                       action="store_true",
                       dest="preview",
                       default=False,
                       help="Preview stream only, useful for testing")
    args = parser.parse_args()
    if not platform.system() == "Windows":
        print("WINDOWS ONLY - UNIX USERS KEEP OUT!!")
        exit(0)
    instance = singleinstance()
    if instance.alreadyrunning():
        logging.fatal("Can't run multiple instances of this script!")
        exit(0)
    logging.basicConfig(level=args.loglevel,format="%(asctime)s.%(msecs)d %(levelname)s %(name)s : %(message)s",datefmt="%H:%M:%S")
    configpath = os.path.join(os.path.dirname(__file__), 'config.json')
    config_file = open(configpath,"r")
    config = json.loads(config_file.read())
    y = Manager(config,preview_only=args.preview)
    y.run()
