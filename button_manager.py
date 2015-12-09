from time import sleep
from datetime import datetime, timedelta
from argparse import ArgumentParser
import os
import json
import platform
from obsremote import OBSRemote
from twitcher import twitcher
import logging
from pprint import pformat
if platform.system() == "Windows":
    from win32event import CreateMutex
    from win32api import CloseHandle, GetLastError
    from winerror import ERROR_ALREADY_EXISTS
    from devices import UsbButtonButton

RGB_RED = (255, 0, 0)
RGB_GREEN = (0, 255, 0)
RGB_BLUE = (0, 0, 255)
RGB_WHITE = (255, 255, 255)
RGB_OFF = (0, 0, 0)
TICK_FREQUENCY = 30  # milliseconds
# button/state frequency cannot be faster than tick frequency
BUTTON_CHECK_FREQUENCY = 30  # milliseconds
STATE_CHECK_FREQUENCY = 100  # milliseconds

STREAMING_STATES = ['streaming_idle', 'wait_stop_streaming', 'wait_streaming', 'waitunpressed', 'streaming_pressed']


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

    def __init__(self, config=None, preview_only=False):
        self.logger = logging.getLogger("Button_Manager")
        self.logger.info("Initializing")
        self.logger.debug("Config:\n" + pformat(config))
        self.config = config
        self.state = 'idle'
        self.current_profile = 0
        self.nextstate = []
        self.current_color = RGB_OFF
        self.alternate_color1_time = datetime.now()
        self.alternate_color2_time = datetime.now()
        self.starttime = datetime.now()
        self.preview = preview_only
        self.last_recover_attempt = datetime.now()
        self.setup_twitch()
        self.setup_devices()
        self.setup_obs()

    def setup_twitch(self):
        names = [x["twitch_name"] for x in self.config["streamers"]]
        self.streaming_statuses = {}
        for name in names:
            self.streaming_statuses[name] = False
        self.twitch_handler = twitcher(names)
        self.twitch_handler.subscribe_streaming_start(self.streaming_start_callback)
        self.twitch_handler.subscribe_streaming_stop(self.streaming_stop_callback)

    def streaming_start_callback(self, name):
        self.streaming_statuses[name] = True

    def streaming_stop_callback(self, name):
        self.streaming_statuses[name] = False

    def setup_devices(self):
        self.devices = []
        self.button = UsbButtonButton()
        self.devices.append(self.button)
        self.highlights = []

    def setup_obs(self):
        self.obsremote = OBSRemote("ws://%s:4444" % self.config["obs_integration"]["ip"])
        self.profiles = self.config["streamers"]

    def set_color(self, color):
        self.button.set_color(color)

    def alternate_colors(self, color1, color2, interval=1):
        if datetime.now() > self.alternate_color1_time:
            self.set_color(color1)
            self.alternate_color1_time = datetime.now() + timedelta(seconds=interval * 2)
        elif datetime.now() > self.alternate_color2_time:
            self.set_color(color2)
            self.alternate_color2_time = datetime.now() + timedelta(seconds=interval * 2)

    def run(self):
        self.logger.info("Running")
        self.obsremote.start()
        if self.button:
            self.button.start()
        self.set_color(self.get_color())
        self.main_loop()

    def main_loop(self):
        statecache = ''
        self.next_button_check = datetime.now() + timedelta(microseconds=BUTTON_CHECK_FREQUENCY * 1000)
        self.next_state_check = datetime.now() + timedelta(microseconds=STATE_CHECK_FREQUENCY * 1000)
        try:
            while True:
                sleep(TICK_FREQUENCY / 1000)
                if self.next_button_check < datetime.now():
                    self.handle_button()
                    self.next_button_check = datetime.now() + timedelta(microseconds=BUTTON_CHECK_FREQUENCY * 1000)
                if self.next_state_check < datetime.now():
                    self.tick()
                    self.next_state_check = datetime.now() + timedelta(microseconds=STATE_CHECK_FREQUENCY * 1000)

                if statecache != self.state:
                    self.logger.info('CurrentState: ' + y.state)
                    statecache = self.state
        finally:
            self.logger.info("Shutting down")
            self.obsremote.stop()
            if self.button:
                self.set_color(RGB_OFF)
                self.button.stop()
            if self.twitch_handler:
                self.twitch_handler.stop()

    def next_profile(self):
        self.current_profile = (self.current_profile + 1) % len(self.profiles)
        return self.current_profile

    def handle_button(self):
        if not self.button.connected and self.state != 'error':
            self.state = 'error'
            self.logger.warn("Button appears to be disconnected , will try to find it again in 10 seconds")
        else:
            self.button.update()

    def tick(self):
        if not self.obsremote.connected and self.state != 'error':
            self.state = 'error'
            self.logger.warn("OBSRemote not connected, will retry in aprox 20 seconds")
            return
        elif self.obsremote.streaming and self.state not in STREAMING_STATES:
            self.state = 'streaming_idle'
            self.starttime = datetime.now()
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
            self.state = "idle"
        else:
            self.attempt_recovery()

    def attempt_recovery(self):
        if datetime.now() > self.next_recover_attempt:
            self.logger.warn("Attempting recovery")
            self.next_recover_attempt = datetime.now() + timedelta(seconds=20)
            if not self.obsremote.connected:
                self.obsremote.start()
                if self.button.connected:
                    self.alternate_colors(RGB_OFF, RGB_RED)
            if not self.button.connected:
                self.button.start()

    def handle_idle(self):
        if self.button:
            if self.button.pressed:
                self.state = 'profileselect'
            elif self.button.current_color != self.get_color():
                self.set_color(self.get_color(), "button")

    def handle_profileselect(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                self.logger.info("Streaming starting with profile: %s" %
                                 self.profiles[self.current_profile]["obs_profile"])
                self.obsremote.set_profile(self.profiles[self.current_profile]["obs_profile"])
                self.obsremote.start_streaming(self.preview)
                self.starttime = datetime.now()
                self.state = 'waitunpressed'
                self.nextstate.append('streaming_idle')
                self.nextstate.append('wait_streaming')
                self.button.flash(RGB_RED, RGB_GREEN)
        else:
            self.next_profile()
            self.set_color(self.get_color(), "button")
            self.logger.info('Selected next profile : %s' % self.profiles[self.current_profile]["obs_profile"])
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
        if not self.twitch_handler.running:
            self.twitch_handler.start()
        if self.button.pressed:
            self.state = 'streaming_pressed'
            self.set_color(self.get_color())
        if not self.obsremote.streaming:
            self.finish_stream()
            self.state = 'idle'
            self.set_color(self.get_color())
        if not self.twitch_handler.online_status[self.get_twitch_name()]:
            self.alternate_colors(self.get_color(), RGB_RED)
        else:
            self.alternate_colors(self.get_color(), RGB_GREEN)

    def handle_streaming_pressed(self):
        if self.button.pressed:
            if self.button.get_elapsed_time() > 2:
                self.logger.info("Stopping stream")
                self.obsremote.stop_streaming(self.preview)
                self.state = 'waitunpressed'
                self.nextstate.append('idle')
                self.nextstate.append('wait_stop_streaming')
                self.finish_stream()
                self.button.flash(self.get_color(), RGB_RED)
        else:
            self.state = 'streaming_idle'
            self.logger.info("Highlight created @ %s" % self.obsremote.streamTime)
            self.highlights.append(self.obsremote.streamTime)

    def finish_stream(self):
        if self.twitch_handler:
            if self.twitch_handler.running:
                self.twitch_handler.stop()
        if self.highlights:
            self.logger.info("Writing highlight times to file")
            h_file = open("%s\%s_highlights.txt" % (self.config["obs_integration"]["highlights_dir"],
                                                    self.starttime.strftime('%Y-%m-%d-%H%M-%S')), 'a')
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
    parser.add_argument("--debug",
                        "-d",
                        action="store_const",
                        dest="loglevel",
                        const=logging.DEBUG,
                        default=logging.WARNING,
                        help="Enable ALL THE MESSAGES")
    parser.add_argument("--verbose",
                        "-v",
                        action="store_const",
                        dest="loglevel",
                        const=logging.INFO,
                        help="Enable messages that might be useful but not ALL THE MESSAGES")
    parser.add_argument("--preview_only",
                        "-p",
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
    logging.basicConfig(level=args.loglevel,
                        format="%(asctime)s.%(msecs)d %(levelname)s %(name)s : %(message)s",
                        datefmt="%H:%M:%S")
    configpath = os.path.join(os.path.dirname(__file__), 'config.json')
    config_file = open(configpath, "r")
    config = json.loads(config_file.read())
    y = Manager(config, preview_only=args.preview)
    y.run()
