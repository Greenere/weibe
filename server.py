from gevent.pywsgi import WSGIServer
from gevent import monkey
monkey.patch_all()

from weibeServer import app
from weiboLoader import getLogger
from weiboLoader import main
#from multiprocessing import Process
from threading import Thread

if __name__ == '__main__':
    # weibeloader = Process(target=main)
    # weibeloader.start()
    # weibeloader=Thread(target=main)
    # weibeloader.start()

    host: str = '0.0.0.0'
    host: str = 'localhost'
    port: int = 8880
    servelog = getLogger('./logs/server.log')

    print('SERVING ON: ', 'http://' + host + ':' + str(port))

    http_server = WSGIServer((host, port), app, log=servelog)
    http_server.serve_forever()

