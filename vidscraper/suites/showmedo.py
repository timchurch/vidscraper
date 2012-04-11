from datetime import datetime
from pprint import pprint
import urlparse
from bs4 import BeautifulSoup, SoupStrainer
from vidscraper.suites import BaseSuite, registry, SuiteMethod

TAG_NAMES = set(['title', ])
CONTENT_IDS = set(['embed', 'free', 'downloadFLV'])
CONTENT_CLASSES = set(['authorTitle', 'document', 'taglist'])
CONTENT_NAMES = set(['url', ])


def _strain_filter(name, attrs):
    return name in TAG_NAMES or\
           any((key == 'id' and value in CONTENT_IDS or
                key == 'class' and value in CONTENT_CLASSES or
                key == 'name' and value in CONTENT_NAMES
                for key, value in attrs.iteritems()))

class ShowMeDoScrapeMethod(SuiteMethod):
    fields = set(['link', 'title', 'description', 'guid',
                  'thumbnail_url', 'tags', 'embed_code', 
                  'user', 'user_url', 
                  'file_url', 'file_url_mimetype'])
    
    def get_url(self, video):
        video_id = video.suite.video_regex.match(video.url).group('video_id')
        return u"http://showmedo.com/videotutorials/video?name=%s" % video_id

    def process(self, response):
        strainer = SoupStrainer(_strain_filter)
        soup = BeautifulSoup(response.text, parse_only=strainer)
        soup = soup.find_all(True, recursive=False)
        data = {}
        
        # Find video id from URL to build thumbnail URL
        url, url_vars = response.url.split('?', 1)
        url_vars_dict = urlparse.parse_qs(url_vars)
        video_id = url_vars_dict['name'][0]
        data['thumbnail_url'] = "http://showmedo.com/static/thumbnails/%s.png" % video_id
        data['guid'] = "showmedo:%s" % video_id
        
        for tag in soup:
            if tag.name == 'title':
                end_index = tag.string.find(" video tutorial")
                if end_index > -1:
                    data['title'] = unicode(tag.string[:end_index])
            elif tag.name == 'input':
                if tag.has_key('name') and tag['name'] == "url":
                    if not tag.has_key('id') or not tag['id'] == "curl":
                        data['link'] = unicode(tag['value'])
                elif tag.has_key('id') and tag['id'] == "embed":
                    data['embed_code'] = unicode(tag['value'])
            elif tag.name == 'h2':
                if tag.has_key('id') and tag['id'] == "free":
                    for string_ in tag.stripped_strings:
                        date_string = string_
                    date_string = date_string[-5:]
                    data['publish_datetime'] = datetime.strptime(date_string, "%m/%y")
                    
                    # Also find user info in embedded tag 
                    subtag = tag.find('a')
                    if subtag.has_key('class') and "authorTitle" in subtag['class']:
                        data['user'] = unicode(subtag.string)
                        data['user_url'] = unicode(subtag['href'])
            elif tag.name == 'div':
                if tag.has_key('class') and "document" in tag['class']:
                    tags_html = []
                    for tag in tag.contents:
                        tags_html.append(unicode(tag))
                    data['description'] = ''.join(tags_html)
                elif tag.has_key('class') and "taglist" in tag['class']:
                    htmltags = tag.find_all('a')
                    tags = []
                    for htmltag in htmltags:
                        tags.append(unicode(htmltag.string))
                    data['tags'] = tags
            elif tag.name == 'a':
                if tag.has_key('id') and tag['id'] == "downloadFLV":
                    data['file_url'] = tag['href']
                    data['file_url_mimetype'] = "video/x-flv"
#        pprint(data)
        return data


class ShowMeDoSuite(BaseSuite):
    """
    Suite for ShowMeDo.com
    
    """
    video_regex = r'^https?://(www\.)?showmedo.com/videotutorials/video\?name=(?P<video_id>[0-9a-zA-Z\-]+)(&fromSeriesID=(?P<series_id>\d+))?$'
    # Example URLs:
    #    http://showmedo.com/videotutorials/video?name=1100000
    #    http://showmedo.com/videotutorials/video?name=1100000&fromSeriesID=110
    
    feed_regex = r'^https?://(www\.)?showmedo.com/latestVideoFeed/rss2.0(\?tag=(?P<tag>\w+))?$'
    # Example URLs:
    #    http://showmedo.com/latestVideoFeed/rss2.0
    #    http://showmedo.com/latestVideoFeed/rss2.0?tag=java

    methods = (ShowMeDoScrapeMethod(), )

registry.register(ShowMeDoSuite)