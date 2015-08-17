from time import sleep , time
from datetime import datetime, timedelta
from argparse import ArgumentParser
import os, json, platform
from obsremote import OBSRemote
from twitch_handler import TwitchHandler
import logging
from pprint import pformat
if platform.system() == "Windows":
    from win32event import CreateMutex
    from win32api import CloseHandle, GetLastError
    from winerror import ERROR_ALREADY_EXISTS
    from devices import *

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
        self.logger.info("Initializing")
        self.logger.debug("Config:\n" + pformat(config))
        self.config = config
        self.state = 'idle'
        self.current_profile = 0
        self.nextstate = []
        self.current_color = (0,0,0)
        self.starttime = datetime.now()
        self.preview = preview_only
        self.last_recover_attempt = 0
        self.setup_twitch()
        self.setup_devices()
        self.setup_obs()

    def setup_twitch(self):
        if self.config["twitch_integration"]["enabled"]:
            names = [x["twitch_name"] for x in self.config["streamers"]]
            self.twitch_handler = TwitchHandler(names,self.new_follower)

    def setup_devices(self):
        self.devices = []
        if self.config["ultimarc_button"]["enabled"]:
            self.button = UsbButtonButton()
            self.devices.append(self.button)
            self.highlights = []
        else:
            self.button = None
        if self.config["blinky_tape"]["enabled"]:
            self.tape = BlinkyTape(self.config["blinky_tape"]["port"])
            self.devices.append(self.tape)
        else:
            self.tape = None
        if self.config["phillips_hue"]["enabled"]:
            self.hue = Hue(config["phillips_hue"]["bridge_ip"])

    def setup_obs(self):
        self.obsremote = OBSRemote("ws://%s:4444" %self.config["obs_integration"]["ip"])
        self.profiles = self.config["streamers"]

    def set_color(self,color,device):
        if device == "all":
            for device in devices:
                device.set_color(color)
        if device == "tape" and self.tape:
            self.tape.set_color(color)
        if device == "button" and self.button:
            self.button.set_color(color)
        if device == "hue" or device == "all":
            self.logger.warn("Hue not yet implmented")

    def new_follower(self,name):
        if self.get_twitch_name() == name:
            if self.tape:
                self.tape.flash((255,20,147),(255,0,0),20,0.1,True)
            if self.hue:
                self.hue.flash((255,20,147),(255,0,0),20,0.1)


    def run(self):
        self.logger.info("Running")
        self.obsremote.start()
        if self.tape:
            self.tape.start()
        if self.button:
            self.button.start()
        self.set_color(self.get_color(),"button")
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
            #self.obsremote.stop_streaming(self.preview)
            self.obsremote.stop()
            if self.button:
                self.set_color((0,0,0),"button")
                self.button.stop()
            if self.twitch_handler:
                self.twitch_handler.stop()
            if self.tape:
                self.set_color((0, 0, 0),"tape")
                self.tape.stop()

    def next_profile(self):
        self.current_profile = (self.current_profile + 1) % len(self.profiles)
        return self.current_profile

    def tick(self):
        if self.button:
            if not self.button.connected and self.state != 'error':
                self.state = 'error'
                self.logger.warn("Button appears to be disconnected , will try to find it again in 10 seconds")
                return
        if not self.obsremote.connected and self.state != 'error':
            self.state = 'error'
            self.logger.warn("OBSRemote not connected, will retry in aprox 20 seconds")
            return
        elif self.obsremote.streaming and self.state not in ['streaming_idle', 'wait_stop_streaming', 'wait_streaming', 'waitunpressed', 'streaming_pressed']:
            self.state = 'streaming_idle'
            self.starttime = datetime.now()
            self.set_color((0,255,0),["tape"])
        if self.button:
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
        if self.button:
            if self.obsremote.connected and self.button.connected:
                self.state = "idle"
                return
        else:
            if self.obsremote.connected:
                self.state = "idle"
                return

        if time() - self.last_recover_attempt > 20:
            self.logger.warn("Attempting recovery")
            self.last_recover_attempt = time()
            if not self.obsremote.connected:
                self.obsremote.start()
                if self.button.connected:
                    if round(time()) % 2 == 0 and self.button.current_color != (0,0,0):
                        self.set_color((0,0,0),"all")
                    elif round(time()) % 2 == 1 and self.button.current_color != (255,0,0):
                        self.set_color((255,0,0),"all")
            if self.button:
                if not self.button.connected:
                    self.button.start()

    def handle_idle(self):
        if self.button:
            if self.button.pressed:
                self.state = 'profileselect'
            elif self.button.current_color != self.get_color():
                self.set_color(self.get_color(),"button")
        if self.tape:
            if self.tape.current_color != (0,0,0):
                self.set_color((0,0,0),"tape")

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
                self.button.flash((255,0,0),(0,255,0))
        else:
            self.next_profile();
            self.set_color(self.get_color(),"button")
            self.logger.info('Selected next profile : %s' %self.profiles[self.current_profile]["obs_profile"])
            self.state = 'idle'

    def handle_waitunpressed(self):
        if not self.button.pressed:
            self.state = self.nextstate.pop()

    def handle_wait_streaming(self):
        if self.obsremote.streaming:
            self.set_color((0,255,0), 'tape')
            self.state = self.nextstate.pop()

    def handle_wait_stop_streaming(self):
         if not self.obsremote.streaming:
            self.set_color((0,0,0), 'tape')
            self.state = self.nextstate.pop()

    def handle_streaming_idle(self):
        if self.twitch_handler:
            if not self.twitch_handler.running:
                self.twitch_handler.start()
        if self.button:
            if self.button.pressed:
                self.state = 'streaming_pressed'
                self.set_color(self.get_color(),"button")
        if not self.obsremote.streaming:
            self.finish_stream()
            self.state = 'idle'
            self.set_color(self.get_color(),"button")
            self.set_color((0, 0, 0),"tape")
        elif round(time()) % 2 == 0:
            if self.twitch_handler:
                if not self.twitch_handler.streamers[self.get_twitch_name()]:
                    if self.button.current_color != self.get_color():
                        self.set_color(self.get_color(),"button")
                        self.set_color((67, 162, 202),"tape")
                elif self.button.current_color != self.get_color():
                    self.set_color(self.get_color(),"button")
                    self.set_color((67, 162, 202),"tape")
            elif self.button.current_color != self.get_color():
                self.set_color(self.get_color(),"button")
                self.set_color((67, 162, 202),"tape")
        elif round(time()) % 2 == 1:
            if self.twitch_handler:
                if not self.twitch_handler.streamers[self.get_twitch_name()]:
                    if self.button.current_color != (255,0,0):
                        self.set_color((255,0,0),"button")
                        self.set_color((255, 0, 0),"tape")
                elif self.button.current_color != (0,125,0):
                    self.set_color((0,125,0),"button")
                    self.set_color((67, 162, 202),"tape")
            elif self.button.current_color != self.get_color():
                self.set_color(self.get_color(),"button")
                self.set_color((67, 162, 202),"tape")

    def handle_streaming_pressed(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                self.logger.info("Stopping stream")
                self.obsremote.stop_streaming(self.preview)
                self.state = 'waitunpressed'
                self.nextstate.append('idle')
                self.nextstate.append('wait_stop_streaming')
                self.finish_stream()
                self.button.flash(self.get_color(),(255,0,0))
        else:
            self.state = 'streaming_idle'
            self.logger.info("Highlight created @ %s" %self.obsremote.streamTime)
            self.highlights.append(self.obsremote.streamTime)

    def finish_stream(self):
        if self.twitch_handler:
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
        return self.profiles[self.current_profile]["color"]

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
