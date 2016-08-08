from tempfile import NamedTemporaryFile
import urllib
import urllib2
from xml.etree import ElementTree

from flask import Flask, make_response, request, send_file


__version__ = '0.2.1'


RSS_NAMESPACES = {
    'content': "http://purl.org/rss/1.0/modules/content/",
    'atom': "http://www.w3.org/2005/Atom",
    'itunes': "http://www.itunes.com/dtds/podcast-1.0.dtd",
    'media': "http://search.yahoo.com/mrss/",
}


class ContentAuth(object):
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def file_url(self, url):
        params = urllib.urlencode({
            'url': url,
            'username': self.username,
            'password': self.password,
        })
        return request.host_url + 'file?' + params

    def opener(self, url):
        manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, url, self.username, self.password)
        return urllib2.build_opener(urllib2.HTTPBasicAuthHandler(manager))

    def xml(self, file_obj, namespaces=None):
        if namespaces:
            for namespace, url in namespaces.iteritems():
                ElementTree.register_namespace(namespace, url)
        xml = ElementTree.ElementTree(file=file_obj)

        enclosures = xml.findall('.//enclosure')
        for enclosure in enclosures:
            enclosure.attrib['url'] = self.file_url(enclosure.attrib['url'])

        file_obj = NamedTemporaryFile(suffix='.xml')
        xml.write(file_obj)
        file_obj.seek(0)
        return file_obj


def validate_request():
    required_params = ['url', 'username', 'password']
    missing_params = filter(lambda p: not request.args.get(p), required_params)
    if missing_params:
        return ', '.join(missing_params) + ' required'
    return True


def clean_request():
    data = request.args.copy()
    # Unquote URL if double quoted
    if ':' not in data['url'] and '%' in data['url']:
        data['url'] = urllib.unquote(data['url'])
    return data


def add_content_headers(resp_to, resp_from):
    for key in resp_from.headers:
        if key.lower().startswith('content-'):
            resp_to.headers[key.title()] = resp_from.headers[key]


app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0


@app.route('/')
def root():
    return make_response('authcast v{}'.format(__version__))


@app.route('/file')
def file_():
    is_valid = validate_request()
    if is_valid is not True:
        return make_response(is_valid, 400)
    data = clean_request()

    content_auth = ContentAuth(data['username'], data['password'])

    opener = content_auth.opener(data['url'])
    if 'range' in request.headers:
        file_request = urllib2.Request(data['url'], headers={
            'Range': request.headers['range'],
        })
        file_response = opener.open(file_request)
        response = send_file(file_response, add_etags=False)
        response.status_code = 206
    else:
        file_response = opener.open(data['url'])
        response = send_file(file_response, add_etags=False)

    add_content_headers(response, file_response)
    response.headers['Accept-Ranges'] = 'bytes'
    return response


@app.route('/feed')
def feed():
    is_valid = validate_request()
    if is_valid is not True:
        return make_response(is_valid, 400)
    data = clean_request()

    content_auth = ContentAuth(data['username'], data['password'])

    opener = content_auth.opener(data['url'])
    try:
        feed_response = opener.open(data['url'])
    except ValueError:
        return make_response('url invalid', 400)

    # Return errors
    if not str(feed_response.code).startswith('2'):
        return make_response(feed_response.read(), feed_response.code)

    # Verify content is XML
    content_type = feed_response.headers.get('Content-Type', '')
    if 'xml' not in content_type:
        feed_response.close()
        return make_response('invalid content type: ' + content_type, 415)

    xml = content_auth.xml(feed_response, namespaces=RSS_NAMESPACES)
    response = send_file(xml.name, add_etags=False)
    return response


if __name__ == '__main__':
    from gevent.wsgi import WSGIServer
    http_server = WSGIServer(('', 5000), app)
    http_server.serve_forever()
