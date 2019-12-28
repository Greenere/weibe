from gevent.pywsgi import WSGIServer
from weibeServer import app

host:str='0.0.0.0'
host:str='localhost'
port:int=8880

print('SERVING ON: ','http://'+host+':'+str(port))

http_server = WSGIServer((host, port), app)
http_server.serve_forever()