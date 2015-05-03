import websocket, thread, json

class OBSRemote(object):
    def __init__(self,url):
        self.url = url
        self.streaming = False

    def start(self):
        #dothing
        self.ws = websocket.WebSocketApp(self.url,
                              on_message = self.on_message,
                              on_error = self.on_error,
                              on_close = self.on_close,
                              subprotocols=["obsapi"])
        thread.start_new_thread( self.ws.run_forever, () )

    def stop(self):
        #stopthing
        self.ws.close()

    def on_message(self,ws,msg):
        #recv msg
        try:
            decoded = json.loads(msg)
            if 'streaming' in decoded:
                self.streaming = decoded['streaming']
            elif 'update-type' in decoded:
                if decoded['update-type'] == "StreamStarting":
                    self.streaming = True
                elif decoded['update-type'] == "StreamStopping":
                    self.streaming = False
        except Exception, E:
            print 'Bad thing happened parsing obsremote message'
            print E
        return

    def on_error(self,ws,error):
        #error
        print 'OBSRemoteError'
        print error
        return

    def on_close(self,ws):
        #closed
        print 'OBSRemote Socket closed'
        return

    def set_profile(self,name):
        print "Setting profile to : %s" %name
        msg = {}
        msg['message-id'] = 'ffff34234'
        msg['request-type'] = "SetProfile"
        msg['profileName'] = name
        self.ws.send(json.dumps(msg))

    def start_streaming(self, preview=False):
        if self.streaming == False:
            print "OBSREMOTE : Starting stream"
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            if preview:
                msg["preview-only"] = True
            response = self.ws.send(json.dumps(msg))

    def stop_streaming(self, preview=False):
        if self.streaming:
            print "OBSREMOTE : Stopping stream"
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            if preview:
                msg["preview-only"] = True
            response = self.ws.send(json.dumps(msg))
        return
