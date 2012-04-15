import json
from vidscraper.suites import BaseSuite, registry, SuiteMethod


class ParleysApiMethod(SuiteMethod):
    fields = set(['link', 'title', 'description', 'guid',
                  'thumbnail_url', 'tags', 'embed_code',
                  'flash_enclosure_url', 'duration_seconds',
                  'view_count'])
    
    def get_url(self, video):
        presentation_id = video.suite.video_regex.match(video.url).group('video_id')
#        return u"http://server.parleys.com/rest/v2/presentations/%s.json" % presentation_id

        # TODO: For testing only!  Waiting for update to REST api to remove space-id and channel-id
        print u"API URL: http://server.parleys.com/rest/v2/spaces/189/channels/102998/presentations/%s.json" % presentation_id
        return         u"http://server.parleys.com/rest/v2/spaces/189/channels/102998/presentations/%s.json" % presentation_id
#                        http://server.parleys.com/rest/v2/spaces/189/channels/102998/presentations/2985.json

    def process(self, response):
        parsed = json.loads(response.text)
        video_id = parsed['id']
        data = {
            'title': parsed['title'],
            'link': ParleysSuite.website_url_from_id(video_id),
            'description': parsed['summary'],
            'thumbnail_url': parsed['thumbnail'],
            'tags': [tag['name'] for tag in parsed['keywords']],
            'flash_enclosure_url': ParleysSuite.flash_enclosure_url_from_id(video_id),
            'embed_code': ParleysSuite.embed_code_from_id(video_id),
            'guid': 'parleys:%i' % (parsed['id']),
            'duration_seconds': int(parsed['duration']),
            'view_count': parsed['totalViews']
#            'speakers': [speaker['fullname'] for speaker in parsed['speakers']]
        }
        return data


class ParleysSuite(BaseSuite):
    """
    Suite for Parleys.com.
    Supports REST interface [http://code.google.com/p/parleys-rest/wiki/RESTInterface].
    No API key is required.
    
    """
    video_regex = r'^https?://(www\.)?parleys.com/#st=5&id=(?P<video_id>\d+)(&sl=[\d]+)?$'
    # Example URLs:
    #    http://www.parleys.com/#id=2229&st=5
    #    http://www.parleys.com/parleysserver/indexing/presentation.form?id=2234
    
    feed_regex = r'^https?://(www\.)?parleys.com/#st=4&id=(?P<channel_id>\d+)$'
#    feed_regex = r'^https?://server.parleys.com/rss/presentations.form?id=(?P<channel_id>\d+)$'
    # Example feed URLs:
    #    http://server.parleys.com/rss/presentations.form?id=56141
    #    http://www.parleys.com/#st=4&id=1839

    methods = (ParleysApiMethod(), )
    
    @classmethod
    def embed_code_from_id(self, video_id, size='square'):
        """
        Embed code from Parleys.com is offered in 3 standard sizes.
        """
        square = {'width': 395, 'height': 395}
        vertical = {'width': 480, 'height': 780}
        horizontal = {'width': 850, 'height': 400}
        
        valid_sizes = ('square', 'vertical', 'hortizontal')
        if size not in valid_sizes:
            size = 'square'
        embed_size = locals()[size]
        
        return u"""
<object width="%i" height="%i">
  <param name="movie" value="http://www.parleys.com/dist/share/parleysshare.swf"/>
  <param name="allowFullScreen" value="true"/>
  <param name="wmode" value="direct"/>
  <param name="bgcolor" value="#222222"/>
  <param name="flashVars" value="sv=true&amp;pageId=%s"/>
  <embed src="http://www.parleys.com/dist/share/parleysshare.swf" 
      type="application/x-shockwave-flash" flashVars="sv=true&amp;pageId=%s" 
      allowfullscreen="true" bgcolor="#222222" width="%i" height="%i"/>
</object>
        """ % (embed_size['width'], embed_size['height'], video_id, video_id, embed_size['width'], embed_size['height'])

    @classmethod
    def flash_enclosure_url_from_id(self, video_id):
        return u'http://www.parleys.com/dist/share/parleysshare.swf?sv=true&pageId=%s' % video_id

    @classmethod
    def website_url_from_id(self, video_id):
        return u'http://www.parleys.com/?st=5&id=%s' % video_id

registry.register(ParleysSuite)
