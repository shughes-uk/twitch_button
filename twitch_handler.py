from twitch import TwitchTV
import threading, logging
from time import sleep
from urllib import quote_plus
from pprint import pprint
class TwitchTV_b(TwitchTV):
    def getLatestFollower(self, username):
        acc = []
        quotedUsername = quote_plus(username)
        url = "https://api.twitch.tv/kraken/channels/%s/follows/?direction=DESC&limit=1&offset=0" %username
        acc = self._fetchItems(url, 'follows')
        return acc

class TwitchHandler(object):
    def __init__(self,name_list,new_follower_callback = None,watch_streaming = True):
        super(TwitchHandler, self).__init__()
        self.nf_callback = new_follower_callback
        self.watch_streaming = watch_streaming
        self.logger = logging.getLogger("TwitchHandler")
        self.streamers = {}
        self.follower_cache = {}
        self.thread = threading.Thread(target=self.run)
        self.twitch = TwitchTV_b()
        self.running = False
        for name in name_list:
            self.streamers[name] = False
            self.follower_cache[name]  = self.twitch.getLatestFollower(name)[0]['user']['_id']

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        self.logger.info("Starting twitch api polling")
        self.running = True
        while self.running:
            for name in self.streamers.keys():
                if self.watch_streaming:
                    result = [x for x in self.twitch.searchStreams(name) if x['channel']['name'] == name]
                    if result:
                        if not self.streamers[name]:
                            self.logger.info("%s is now live on twitch" %name)
                            self.streamers[name] = True
                    else:
                        if self.streamers[name]:
                            self.logger.info("%s is no longer live on twitch" %name)
                            self.streamers[name] = False
                if self.nf_callback:
                    lastFollower_id = self.twitch.getLatestFollower(name)[0]['user']['_id']
                    if lastFollower_id != self.follower_cache[name]:
                        self.logger.info("%s has a new follower!" %name)
                        self.follower_cache[name] = lastFollower_id
                        self.nf_callback(name)
            sleep(2)

    def stop(self):
        self.logger.info("Attempting to stop twitch api polling")
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
