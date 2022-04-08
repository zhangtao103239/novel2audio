import getopt
import sys
import requests


if __name__ == '__main__':
    opts, _ = getopt.getopt(sys.argv[1:], 'u:p:', [""])
    user = ''
    password = ''
    for opt, value in opts:
        if opt in ['-u']:
            user = value
        elif opt in ['-p']:
            password = value

    if user == '' or password == '':
        print('参数有误！')
        exit(1)
    url = "https://seafile.ynotme.cn/api2/auth-token/"
    data = {
        'username': user,
        'password': password
    }
    response = requests.request("POST", url, data=data)

    print(response.text)
    
