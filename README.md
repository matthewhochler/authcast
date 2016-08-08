# authcast
Wrap podcast feed enclosures in a local proxy with server-side HTTP authentication. Prevents the need for HTTP authentication support in podcast clients.

## Usage
### Feed
`http(s)://AUTHCAST_HOST:5000/feed?url=FEED_URL&username=USERNAME&password=PASSWORD`
### File
`http(s)://AUTHCAST_HOST:5000/file?url=FEED_URL&username=USERNAME&password=PASSWORD`
