from datetime import datetime
import dateutil
from pprint import pprint
from bs4 import BeautifulSoup, SoupStrainer
from vidscraper.suites import BaseSuite, registry, SuiteMethod

TAG_NAMES = set(['title', ])
CONTENT_IDS = set(['description', ])
CONTENT_CLASSES = set(['video-content-metadata', 'video-content-download'])


def _strain_filter(name, attrs):
    return name in TAG_NAMES or\
           any((key == 'id' and value in CONTENT_IDS or
                key == 'class' and value in CONTENT_CLASSES
                for key, value in attrs.iteritems()))


class GoDjangoScrapeMethod(SuiteMethod):
    fields = set(['link', 'title', 'description', 'guid',
                  'thumbnail_url', 'publish_datetime',
                  'file_url', 'file_url_mimetype',
                  'duration'])
    
    def get_url(self, video):
        return video.url

    def process(self, response):
        strainer = SoupStrainer(_strain_filter)
        soup = BeautifulSoup(response.text, parse_only=strainer)
        soup = soup.find_all(True, recursive=False)
        data = {}
        data['link'] = response.url
        
        # Find episode # from URL to build thumbnail URL and GUID
        suite = GoDjangoSuite()
        slug = suite.video_regex.match(response.url).group('slug')
        data['guid'] = "showmedo:%s" % slug

        end_episode_index = slug.find('-')
        episode_num = slug[:end_episode_index]
        data['thumbnail_url'] = "http://assets.godjango.com/episode-%s/episode-%s-thumbnail.png" % (episode_num, episode_num)
        
        for tag in soup:
            if tag.name == 'title':
                end_index = tag.string.find(" - GoDjango.com")
                if end_index > -1:
                    data['title'] = unicode(tag.string[:end_index])
            elif tag.name == 'div':
                if tag.has_key('id') and tag['id'] == "description":
                    data['description'] = tag.string.strip()
                elif tag.has_key('class') and "video-content-metadata" in tag['class']:
                    # March 20, 2012, 5:30 p.m. | 10 minutes
                    separator = " | "
                    separator_index = tag.string.find(separator)
                    date_string = tag.string[:separator_index].strip()
                    data['publish_datetime'] = dateutil.parser.parse(date_string)

                    duration_string = tag.string[separator_index+len(separator):]
                    end_duration_index = duration_string.find(" minutes")
                    duration_minutes = int(duration_string[:end_duration_index])
                    duration_seconds = duration_minutes * 60;
                    data['duration'] = duration_seconds
                elif tag.has_key('class') and "video-content-download" in tag['class']:
                    download_tags = tag.find_all('a')
                    file_urls = []
                    file_urls_mimetypes = []
                    for download_tag in download_tags:
                        file_urls.append(download_tag['href'])
                        file_urls_mimetypes.append("video/%s" % download_tag.string)
                    data['file_url'] = file_urls
                    data['file_url_mimetype'] = file_urls_mimetypes
        
        # Statically add one tag (theme of the site)
        tags = ['django', ]
        data['tags'] = tags
        
#        pprint(data)
        return data


class GoDjangoSuite(BaseSuite):
    """
    Suite for GoDjango.com
    
    """
    video_regex = r'^https?://(www\.)?godjango.com/(?P<slug>[0-9a-z\-]+)/?$'
    # Example URLs:
    #    http://godjango.com/13-django-social-auth-101/
    
    feed_regex = r'^http://feeds.feedburner.com/GoDjango$'
    # Example URLs:
    #    http://feeds.feedburner.com/GoDjango

    methods = (GoDjangoScrapeMethod(), )

registry.register(GoDjangoSuite)