import getopt
import sys

if __name__ == '__main__':
    opts, _ = getopt.getopt(sys.argv[1:], 'u:p:', [""])
    for opt, value in opts:
        print(opt, value)
