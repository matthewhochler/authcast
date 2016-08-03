from StringIO import StringIO
import urllib
import urlparse
from xml.etree import ElementTree

from flask import Flask, make_response, request
import requests
from requests.exceptions import InvalidSchema


__version__ = '0.1.0'


class InvalidContentType(Exception):
    pass


class ContentAuth(object):
    RSS_NAMESPACES = {
        'content': "http://purl.org/rss/1.0/modules/content/",
        'atom': "http://www.w3.org/2005/Atom",
        'itunes': "http://www.itunes.com/dtds/podcast-1.0.dtd",
        'media': "http://search.yahoo.com/mrss/",
    }

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def url(self, url):
        username = urllib.quote(self.username)
        password = urllib.quote(self.password)
        url = urlparse.urlsplit(url)
        netloc = '{username}:{password}@{netloc}'.format(
            username=username,
            password=password,
            netloc=url.netloc,
        )
        url = url._replace(netloc=netloc)
        return url.geturl()

    def xml(self, xml_str, namespaces=None):
        if namespaces:
            for namespace, url in namespaces.iteritems():
                ElementTree.register_namespace(namespace, url)
        xml_element = ElementTree.fromstring(xml_str)

        enclosures = xml_element.findall('.//enclosure')
        for enclosure in enclosures:
            enclosure.attrib['url'] = self.url(enclosure.attrib['url'])

        xml_tree = ElementTree.ElementTree(xml_element)
        xml_file = StringIO()
        xml_tree.write(xml_file)
        xml_file.seek(0)
        return xml_file.read()

    def rss(self, url):
        url = self.url(url)
        response = requests.get(url, stream=True)

        # Verify response is XML before requesting data
        if 'xml' not in response.headers.get('Content-Type', ''):
            response.close()
            raise InvalidContentType()

        return self.xml(response.content, namespaces=self.RSS_NAMESPACES)


app = Flask(__name__)


@app.route('/')
def root():
    return make_response('authcast v{}'.format(__version__))


@app.route('/rss/')
def rss():
    required_params = [u'url', u'username', u'password']
    missing_params = filter(lambda p: not request.args.get(p), required_params)
    if missing_params:
        response = make_response(u', '.join(missing_params) + u' required')
        response.status_code = 400
        return response

    username = request.args['username']
    password = request.args['password']
    url = request.args['url']

    content_auth = ContentAuth(username, password)
    try:
        rss_body = content_auth.rss(url)
    except (InvalidSchema, InvalidContentType):
        response = make_response(u'url invalid')
        response.status_code = 400
        return response

    response = make_response(rss_body)
    response.mimetype = u'application/rss+xml'
    return response


if __name__ == '__main__':
    app.run()
