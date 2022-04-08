import getopt
import sys
import requests


if __name__ == '__main__':
    opts, _ = getopt.getopt(sys.argv[1:], 'u:p:', [""])
    for opt, value in opts:
        print(opt, value)

    url = "https://seafile.ynotme.cn/api2/auth-token/"
    data = {
        'username': opts['-u'],
        'password': opts['-p']
    }
    response = requests.request("POST", url, data=data)

    print(response.text)
