from twitch import TwitchTV
import threading, logging
from time import sleep
class TwitchHandler(threading.Thread):
    def __init__(self,name_list):
        super(TwitchHandler, self).__init__()
        self.logger = logging.getLogger("TwitchHandler")
        self.streamers = {}
        for name in name_list:
            self.streamers[name] = False
        self.twitch = TwitchTV(logger=logging.getLogger("TwitchAPI"))
        self.running = False

    def run(self):
        self.logger.info("Starting twitch api polling")
        self.running = True
        while self.running:
            for name in self.streamers.keys():
                result = [x for x in self.twitch.searchStreams(name) if x['channel']['name'] == name]
                if result:
                    if not self.streamers[name]:
                        self.logger.info("%s is now live on twitch" %name)
                        self.streamers[name] = True
                else:
                    if self.streamers[name]:
                        self.logger.info("%s is no longer live on twitch" %name)
                        self.streamers[name] = False
            sleep(2)

    def stop(self):
        self.logger.info("Closing comms with OBS")
        self.running = False
        self.join()
