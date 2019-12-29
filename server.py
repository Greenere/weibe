from gevent.pywsgi import WSGIServer
from weibeServer import app
from weiboLoader import main,getLogger
from threading import Thread

weibeloader=Thread(target=main)
weibeloader.start()

host:str='0.0.0.0'
host:str='localhost'
port:int=8880

servelog=getLogger('./logs/server.log')

print('SERVING ON: ','http://'+host+':'+str(port))

http_server = WSGIServer((host, port), app,log=servelog)
http_server.serve_forever()