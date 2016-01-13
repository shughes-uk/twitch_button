import json
import logging
import threading

import websocket


class OBSRemote(object):

    def __init__(self, url):
        self.logger = logging.getLogger("OBSRemote")
        self.url = url
        self.streaming = False
        self.streamTime = 0
        self.connected = False

    def start(self):
        self.logger.info("Attempting to open comms with OBS")
        self.ws = websocket.WebSocketApp(self.url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close,
                                         subprotocols=["obsapi"])
        self.run_thread = threading.Thread(target=self.ws.run_forever)
        self.run_thread.start()

    def stop(self):
        self.logger.info("Closing comms with OBS")
        self.ws.close()

    def on_open(self, *args):
        self.logger.info("Communication with obs established")
        self.connected = True

    def on_message(self, ws, msg):
        try:
            decoded = json.loads(msg)
            # self.logger.debug("Received: " + str(decoded))
            if 'update-type' in decoded:
                if decoded['update-type'] == 'StreamStatus':
                    self.streamTime = decoded['total-stream-time']
                    self.streaming = decoded['streaming']
                elif decoded['update-type'] == "StreamStarting":
                    self.streaming = True
                elif decoded['update-type'] == "StreamStopping":
                    self.streaming = False

        except Exception as E:
            self.logger.warn('Bad thing happened parsing obsremote message')
            self.logger.warn(str(E))
        return

    def on_error(self, ws, error):
        if error.errno == 10061:
            self.logger.warn("Error, connection to OBS refused, check OBS is running.")
            self.connected = False
        else:
            self.logger.warn('Error ' + str(error))
            self.connected = False
        return

    def on_close(self, ws):
        self.logger.info('Socket closed')
        self.connected = False
        self.streaming = False
        return

    def set_profile(self, name):
        self.logger.info("Setting profile to : %s" % name)
        msg = {}
        msg['message-id'] = 'ffff34234'
        msg['request-type'] = "SetProfile"
        msg['profileName'] = name
        self.ws.send(json.dumps(msg))

    def start_streaming(self, preview=False):
        if not self.streaming:
            self.logger.info("Sending StartStream")
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            if preview:
                msg["preview-only"] = True
            self.ws.send(json.dumps(msg))

    def stop_streaming(self, preview=False):
        if self.streaming:
            self.logger.info("Sending StopStream")
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            if preview:
                msg["preview-only"] = True
            self.ws.send(json.dumps(msg))
        return
