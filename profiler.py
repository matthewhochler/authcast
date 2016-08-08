from gevent.wsgi import WSGIServer
from werkzeug.contrib.profiler import ProfilerMiddleware

from authcast import app


app.config['PROFILE'] = True
app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
