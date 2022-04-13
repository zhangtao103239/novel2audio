import getopt
import os
import sys
import requests
from ws4py.client.threadedclient import WebSocketClient
import re
import threading
from multiprocessing import cpu_count
import json
import re
from xml.sax.saxutils import escape

from search_book import get_chapters, search_book


class WSClient(WebSocketClient):
    def __init__(self, url, text, filename):
        self.fp = open(filename, 'wb')
        self.text = text
        # self.narrator = '<voice name="zh-CN-YunyeNeural">{text}</voice>'
        # self.voices = [
        #     '<voice name="zh-CN-XiaoxiaoNeural">{text}</voice>',
        #     '<voice name="zh-CN-YunxiNeural">{text}</voice>',
        #     '<voice name="zh-CN-YunyangNeural">{text}</voice>']
        self.narrator = '<prosody rate="0%" pitch="0%">{text}</prosody>'
        self.voices = [
            '<prosody rate="0%" pitch="-20%">{text}</prosody>', 
            '<prosody rate="0%" pitch="20%">{text}</prosody>',
             '<prosody rate="0%" pitch="40%">{text}</prosody>'
        ]
        super(WSClient, self).__init__(url)

    def opened(self):
        self.send(
            'Content-Type:application/json; charset=utf-8\r\n\r\nPath:speech.config\r\n\r\n{"context":{"synthesis":{"audio":{"metadataoptions":{"sentenceBoundaryEnabled":"false","wordBoundaryEnabled":"true"},"outputFormat":"audio-24khz-160kbitrate-mono-mp3"}}}}\r\n')
        self.mod_text = ''
        mod = 0
        last_index = 0
        index = 0
        voice_index = -1
        for index in range(len(self.text)):
            if self.text[index] == '“':
                rt = escape(self.text[last_index: index])
                if len(rt.strip()) > 0 and mod == 0:
                    if index == 0 or self.text[index-1] in "，。： \n,.?!？！;； ":
                        rt = re.sub('\n+','<break strength="medium"/>', rt)
                        self.mod_text = self.mod_text + \
                            self.narrator.format(text=rt)
                        last_index = index
                        mod = 1
            elif self.text[index] == '”':
                rt = escape(self.text[last_index: index + 1])
                if len(rt.strip()) > 0 and mod == 1:
                    rt = re.sub('\n+','<break strength="medium"/>', rt)
                    voice_index = (voice_index + 1) % len(self.voices)
                    self.mod_text = self.mod_text + \
                        self.voices[voice_index].format(text=rt)
                    last_index = index + 1
                    mod = 0
        rt = escape(self.text[last_index:])
        if len(rt.strip()) > 0:
            rt = re.sub('\n+','<break strength="medium"/>', rt)
            if mod == 0:
                self.mod_text = self.mod_text + self.narrator.format(text=rt)
            else:
                voice_index = (voice_index + 1) % len(self.voices)
                self.mod_text = self.mod_text + \
                    self.voices[voice_index].format(text=rt)
        self.mod_text = '<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xmlns:emo="http://www.w3.org/2009/10/emotionml" version="1.0" xml:lang="cn"><voice name="zh-CN-YunyeNeural">' + self.mod_text + "</voice></speak>"
        print(self.mod_text)
        self.send("X-RequestId:fe83fbefb15c7739fe674d9f3e81d389\r\nContent-Type:application/ssml+xml\r\nPath:ssml\r\n\r\n" + self.mod_text + "\r\n")

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
        print('登录SF成功')
        return response.json()['token']


def is_uploaded_to_sf(token, host_url, repo_id, path, novel_name, filename):
    headers = {
        'Authorization': 'Token ' + token
    }
    url = host_url + '/api2/repos/' + repo_id + '/dir/'
    r = requests.get(url, headers=headers, params={'p': path+'/' + novel_name})
    if r.ok:
        for file in r.json():
            if file['name'] == filename and file['size'] > 0:
                return True
    return False


def upload_to_sf(token, host_url, repo_id, path, novel_name, filename):
    headers = {
        'Authorization': 'Token ' + token
    }
    url = host_url + '/api2/repos/' + repo_id + '/upload-link/'
    r = requests.get(url, headers=headers, params={'p': path})
    if r.ok:
        upload_url = r.text.replace('"', '')
        f = {'file': open(filename, 'rb')}
        data = {
            "parent_dir": path,
            "relative_path": novel_name,
            "replace": 1
        }

        response = requests.post(
            upload_url, data=data, files=f,
            params={'ret-json': 1}, headers=headers)
        if response.ok:
            print(json.dumps(response.json(), ensure_ascii=False, indent=2))


def download_novel(novel_url, novel_name):
    if not os.path.exists(novel_name + '.txt'):
        response = requests.get(novel_url)
        with open(novel_name + '.txt', 'wb') as f:
            f.write(response.content)
    print('下载文本成功')
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


def transfrom2Audio(speech_url, chapter_name, chapter_content, index, sf_config):
    filename = index + "_" + chapter_name + '.mp3'
    if is_uploaded_to_sf(sf_config['token'], sf_config['host_url'], sf_config['repo_id'],
                         sf_config['path'], sf_config['novel_name'], filename):
        return True
    ws = WSClient(speech_url, chapter_content, filename)
    ws.connect()
    ws.run_forever()
    upload_to_sf(sf_config['token'], sf_config['host_url'], sf_config['repo_id'],
                 sf_config['path'], sf_config['novel_name'], filename)


if __name__ == '__main__':
    opts, _ = getopt.getopt(sys.argv[1:], 'u:p:t:n:k:h:r:d:m:', [""])
    user = ''
    password = ''
    host_url = ''
    repo_id = ''
    upload_dir = ''
    txt_url = ''
    txt_name = ''
    clientToken = ''
    txt_host_url = ''
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
        elif opt in ['-d']:
            upload_dir = value
        elif opt in ['-r']:
            repo_id = value
        elif opt in ['-m']:
            txt_host_url = value

    if user == '' or password == '':
        print('参数有误！')
        exit(1)
    cpus = cpu_count()
    print('CPU count is %d' % cpus)
    threads = []
    token = login_sf(sf_host_url=host_url,
                     sf_username=user, sf_password=password)
    if token is None:
        print('登录SF失败！')
        exit(1)
    index = 0
    speech_url = 'wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=' + clientToken
    if txt_url.startswith('http'):
        txt_content = download_novel(txt_url, txt_name)
        chapters = spilt_chapter(txt_content)
    else:
        book_url = search_book(txt_host_url, txt_name)
        if book_url is not None:
            chapters = get_chapters(txt_host_url, book_url)
        else:
            exit(1)
    for chapter_name, chapter in chapters:
        sf_config = {
            "token": token,
            "host_url": host_url,
            "repo_id": repo_id,
            "path": upload_dir,
            "novel_name": txt_name
        }
        index += 1
        print('开始处理第%d章' % index)
        t1 = threading.Thread(target=transfrom2Audio, args=(
            speech_url, chapter_name, chapter, "{:0>4}".format(index), sf_config))
        t1.start()
        threads.append(t1)
        if index % cpus == 0:
            for t in threads:
                t.join()
