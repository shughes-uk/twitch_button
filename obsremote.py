import websocket, thread, json, logging, time

class OBSRemote(object):
    def __init__(self,url):
        self.logger = logging.getLogger("OBSRemote")
        self.url = url
        self.streaming = False
        self.streamTime = 0
        self.connected = True
        self.last_connect_attempt = 0

    def start(self):
        if time.time() - self.last_connect_attempt > 20:
            self.last_connect_attempt = time.time()
            self.logger.info("Attempting to open comms with OBS")
            self.ws = websocket.WebSocketApp(self.url,
                                  on_message = self.on_message,
                                  on_error = self.on_error,
                                  on_close = self.on_close,
                                  subprotocols=["obsapi"])
            thread.start_new_thread( self.ws.run_forever, () )
            self.connected = True

    def stop(self):
        self.logger.info("Closing comms with OBS")
        self.ws.close()

    def on_message(self,ws,msg):
        try:
            decoded = json.loads(msg)
            #self.logger.debug("Received: " + str(decoded))
            if 'update-type' in decoded:
                if decoded['update-type'] == 'StreamStatus':
                    self.streamTime = decoded['total-stream-time']
                    self.streaming = decoded['streaming'] 
                elif decoded['update-type'] == "StreamStarting":
                    self.streaming = True
                elif decoded['update-type'] == "StreamStopping":
                    self.streaming = False

        except Exception, E:
            self.logger.warn('Bad thing happened parsing obsremote message')
            self.logger.warn(str(E))
        return

    def on_error(self,ws,error):
        if error.errno == 10061:
            self.logger.warn("Error, connection to OBS refused, check OBS is running.")
        else:
            self.logger.warn('Error ' + str(error))
        return

    def on_close(self,ws):
        self.logger.info('Socket closed')
        self.connected = False
        self.streaming = False
        return

    def set_profile(self,name):
        self.logger.info("Setting profile to : %s" %name)
        msg = {}
        msg['message-id'] = 'ffff34234'
        msg['request-type'] = "SetProfile"
        msg['profileName'] = name
        self.ws.send(json.dumps(msg))

    def start_streaming(self, preview=False):
        if self.streaming == False:
            self.logger.info("Sending StartStream")
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            if preview:
                msg["preview-only"] = True
            response = self.ws.send(json.dumps(msg))

    def stop_streaming(self, preview=False):
        if self.streaming:
            self.logger.info("Sending StopStream")
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            if preview:
                msg["preview-only"] = True
            response = self.ws.send(json.dumps(msg))
        return
