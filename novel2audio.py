import getopt
import sys
import requests
from ws4py.client.threadedclient import WebSocketClient
import re
import threading
from multiprocessing import cpu_count



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


def login_sf(sf_host_url, sf_username, sf_password):
    sf_url = sf_host_url + "/api2/auth-token/"
    data = {
        'username': sf_username,
        'password': sf_password
    }
    response = requests.request("POST", sf_url, data=data)
    if response.ok:
        return response.json()['token']


def download_novel(novel_url, novel_name):
    response = requests.get(novel_url)
    with open(novel_name + '.txt', 'wb') as f:
        f.write(response.content)
    with open(novel_name + '.txt', 'r', encoding='utf-8') as f:
        return f.read()


def spilt_chapter(novel_content):
    chapter_pattern = re.compile(r'(?<=[　\s])(?:序章|序言|卷首语|扉页|楔子|正文(?![完结])'
                                 r'|终章|后记|尾声|番外|第?\s{0,4}[\d〇零一二两三四五六七八九十百千万壹贰叁肆伍陆柒捌玖拾佰仟]'
                                 r'+?\s{0,4}(?:章|节(?!课)|卷|集(?![合和])|部(?![分赛游])|篇(?!张))).{0,30}$', flags=re.MULTILINE)
    result = chapter_pattern.finditer(novel_content)
    if result is None:
        yield '', novel_content
    else:
        chapter_title = None
        begin = 0
        for m in result:
            if chapter_title is None:
                chapter_title = m.group()
                begin = m.end()
            else:
                end = m.start()
                chapter_content = chapter_title + novel_content[begin: end]
                old_title = chapter_title
                chapter_title = m.group()
                begin = m.end()
                yield old_title, chapter_content
        if chapter_title is None:
            chapter_title = ''
        yield chapter_title, chapter_title + novel_content[begin:]


def transfrom2Audio(speech_url, chapter_name, chapter_content, index):
    ws = WSClient(speech_url, chapter_content, index + "_" + chapter_name + '.mp3')
    ws.connect()
    ws.run_forever()


if __name__ == '__main__':
    opts, _ = getopt.getopt(sys.argv[1:], 'u:p:t:n:k:h:', [""])
    user = ''
    password = ''
    host_url = ''
    txt_url = ''
    txt_name = ''
    clientToken = ''
    for opt, value in opts:
        if opt in ['-u']:
            user = value
        elif opt in ['-p']:
            password = value
        elif opt in ['-t']:
            txt_url = value
        elif opt in ['-n']:
            txt_name = value
        elif opt in ['-k']:
            clientToken = value
        elif opt in ['-h']:
            host_url = value

    if user == '' or password == '':
        print('参数有误！')
        exit(1)
    cpus = cpu_count()
    print('CPU count is %d' % cpus)
    if cpus < 6:
        cpus = 6
    threads = []

    # login_sf(sf_host_url=host_url, sf_username=user, sf_password=password)
    txt_content = download_novel(txt_url, txt_name)
    index = 0
    speech_url = 'wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=' + clientToken
    for chapter_name, chapter in spilt_chapter(txt_content):
        index += 1
        print('开始处理第%d章' % index)
        t1 = threading.Thread(target=transfrom2Audio, args=(speech_url, chapter_name, chapter, "{:0>3}".format(index)))
        t1.start()
        threads.append(t1)
        if index % cpus == 0:
            for t in threads:
                t.join()