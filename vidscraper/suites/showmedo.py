from datetime import datetime, timedelta
from pprint import pprint
import dateutil
import re
import urlparse
from bs4 import BeautifulSoup, SoupStrainer
from vidscraper.suites import BaseSuite, registry, SuiteMethod

TAG_NAMES = set(['title', 'li'])
CONTENT_IDS = set(['embed', 'free', 'downloadFLV'])
CONTENT_CLASSES = set(['authorTitle', 'document', 'taglist'])
CONTENT_NAMES = set(['url', ])


def parseTimeDelta(s):
    """
    Create timedelta object from a string.
    Acceptable formats are: "HH:MM:SS" or "MM:SS" or "X minutes".

    WARNING: THIS IS AN UGLY HACK
    Adapted from: http://kbyanc.blogspot.com/2007/08/python-reconstructing-timedeltas-from.html
    """
    if s is None:
        return None
    d = re.match(r'((?P<hours>\d+):)?(?P<minutes>\d+):(?P<seconds>\d+)', str(s))
    if not d:
        d = re.match(r'(?P<minutes>\d+) minutes', str(s))
        if not d:
            return None

    matchdict = d.groupdict()
    hours = 0
    if 'hours' in matchdict and matchdict['hours']:
        hours = int(matchdict['hours'])
    minutes = int(matchdict['minutes'])
    seconds = 0
    if 'seconds' in matchdict and matchdict['seconds']:
        seconds = int(matchdict['seconds'])
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def _strain_filter(name, attrs):
    return name in TAG_NAMES or\
           any((key == 'id' and value in CONTENT_IDS or
                key == 'class' and value in CONTENT_CLASSES or
                key == 'name' and value in CONTENT_NAMES
                for key, value in attrs.iteritems()))

class ShowMeDoScrapeMethod(SuiteMethod):
    fields = set(['link', 'title', 'description', 'guid',
                  'thumbnail_url', 'tags', 'embed_code', 
                  'user', 'user_url', 'view_count',
                  'file_url', 'file_url_mimetype'])
    
    def get_url(self, video):
        video_id = video.suite.video_regex.match(video.url).group('video_id')
        return u"http://showmedo.com/videotutorials/video?name=%s" % video_id

    def process(self, response):
        data = {}
        
        # Find video id from URL to build thumbnail URL
        url, url_vars = response.url.split('?', 1)
        url_vars_dict = urlparse.parse_qs(url_vars)
        video_id = url_vars_dict['name'][0]
        data['thumbnail_url'] = "http://showmedo.com/static/thumbnails/%s.png" % video_id
        data['guid'] = "showmedo:%s" % video_id
        
        # Parse HTML with BeautifulSoup for the tags we are interested in
        strainer = SoupStrainer(_strain_filter)
        soup = BeautifulSoup(response.text, parse_only=strainer)
        soup = soup.find_all(True, recursive=False)
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

        # Handle view count as special case (have to find by text search...)
        # TODO: find more efficient way to do this without reparsing
        soup = BeautifulSoup(response.text)
        for elem in soup('li', text=re.compile(r'Video plays: ')):
            # Hack our way to the data we want
            video_count_delimiter = 'Video plays: '
            start_index = elem.string.find(video_count_delimiter)
            start_index += len(video_count_delimiter)
            end_index = elem.string.rfind(' (')
            if not end_index:
                end_index = len(elem.string)
            view_count = elem.string[start_index:end_index]
            data['view_count'] = int(view_count)

        # Check if video duration is listed in description
        for elem in soup('p', text=re.compile(r'running time ')):
            # Hack our way to the free-text duration value
            duration_delimiter = 'running time '
            start_index = elem.string.find(duration_delimiter)
            start_index += len(duration_delimiter)
            next_comma = elem.string.find(',', start_index)
            next_period = elem.string.find('.', start_index)
            if not next_comma and not next_period:
                end_index = len(elem.string)
            elif not next_comma:
                end_index = next_period
            elif not next_period:
                end_index = next_comma
            else:
                end_index = min(next_comma, next_period)
            duration_string = elem.string[start_index:end_index]
            duration_timedelta = parseTimeDelta(duration_string)
            if duration_timedelta:
                data['duration_seconds'] = duration_timedelta.total_seconds()

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