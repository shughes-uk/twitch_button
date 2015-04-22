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

    def start_streaming(self):
        if self.streaming == False:
            print "OBSREMOTE : Starting stream"       
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            #msg["preview-only"] = True
            self.ws.send(json.dumps(msg))
            self.streaming = True
        return

    def stop_streaming(self):
        if self.streaming:
            print "OBSREMOTE : Stopping stream"        
            msg = {}
            msg['message-id'] = "123123d"
            msg['request-type'] = "StartStopStreaming"
            #msg["preview-only"] = True
            self.ws.send(json.dumps(msg))
            self.streaming = False
        return