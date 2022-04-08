import getopt
import sys
import requests
from ws4py.client.threadedclient import WebSocketClient


class WSClient(WebSocketClient):
    def __init__(self, url, text, filename):
        self.fp = open(filename, 'wb')
        self.text = text
        super(WSClient, self).__init__(url)

    def opened(self):
        self.send(
            'Content-Type:application/json; charset=utf-8\r\n\r\nPath:speech.config\r\n\r\n{"context":{"synthesis":{"audio":{"metadataoptions":{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"true"},"outputFormat":"audio-24khz-160kbitrate-mono-mp3"}}}}\r\n')
        self.send(
            "X-RequestId:fe83fbefb15c7739fe674d9f3e81d38f\r\nContent-Type:application/ssml+xml\r\nPath:ssml\r\n\r\n<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice  name='Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)'><prosody pitch='+0Hz' rate ='+0%' volume='+0%'>" + self.text + "</prosody></voice></speak>\r\n")

    def received_message(self, m):
        if b'turn.end' in m.data:
            self.close()
            self.fp.close()
        elif b'Path:audio\r\n' in m.data:
            song_bytes = m.data.split(b'Path:audio\r\n')[1]
            self.fp.write(song_bytes)


def login_sf(sf_username, sf_password):
    sf_url = "https://seafile.ynotme.cn/api2/auth-token/"
    data = {
        'username': sf_username,
        'password': sf_password
    }
    response = requests.request("POST", sf_url, data=data)
    if response.ok:
        return response.json()['token']


if __name__ == '__main__':
    opts, _ = getopt.getopt(sys.argv[1:], 'u:p:t:k:', [""])
    user = ''
    password = ''
    txt = ''
    clientToken = ''
    for opt, value in opts:
        if opt in ['-u']:
            user = value
        elif opt in ['-p']:
            password = value
        elif opt in ['-t']:
            txt = value
        elif opt in ['-k']:
            clientToken = value

    if user == '' or password == '':
        print('参数有误！')
        exit(1)
    speech_url = 'wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=' + clientToken
    ws = WSClient(speech_url, txt, 'test.mp3')
    ws.connect()
    ws.run_forever()
    
    
    
