# Copyright 2009 - Participatory Culture Foundation
# 
# This file is part of vidscraper.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
# NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
# THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from datetime import datetime
import dateutil
import json
import re
import urllib
import urlparse

import feedparser

from vidscraper.exceptions import UnhandledURL
from vidscraper.suites import BaseSuite, registry, SuiteMethod, OEmbedMethod
from vidscraper.utils.feedparser import get_entry_thumbnail_url, \
                                        get_first_accepted_enclosure
from vidscraper.utils.http import clean_description_html


class BlipApiMethod(SuiteMethod):
    fields = set(['guid', 'link', 'title', 'description', 'file_url', 'file_url_mimetype',
                  'embed_code', 'thumbnail_url', 'tags', 'publish_datetime',
                  'user', 'license', 'view_count', 'duration_seconds'])

    def get_url(self, video):
        return video.url + '?skin=json&version=3&no_wrap=1'

    def build_embed_code(self, embed_url):
        return '<iframe src=\"%s\" width=\"640\" height=\"456\" frameborder=\"0\" allowfullscreen></iframe>' % embed_url

    def process(self, response):
        response_json = json.loads(response.text)['Post']

        data = {'guid': 'blip:%s' % response_json['item_id'],
            'title': response_json['title'],
            'link': response_json['url'],
            'description': response_json['description'],
            'embed_code': self.build_embed_code(response_json['embedUrl']),
            'file_url': [m['url'] for m in response_json['additionalMedia']],
            'file_url_mimetype': [m['mime_type'] for m in response_json['additionalMedia']],
            'publish_datetime': dateutil.parser.parse(response_json['datestamp']),
            'thumbnail_url': response_json['thumbnailUrl'],
            'tags': [tag['name'] for tag in response_json['tags']],
            'user': response_json['display_name'],
            'license': response_json['licenseUrl'],
            'view_count': response_json['views'],
            'duration_seconds': response_json['media']['duration'],
#            'language': response_json['languageName']
        }
        return data


class BlipSuite(BaseSuite):
    provider_name = 'Blip.tv'
    video_regex = r'^https?://(?P<subsite>[a-zA-Z]+\.)?blip.tv(?:/.*)?(?<!.mp4)$'
    feed_regex = video_regex

    new_video_path_re = re.compile(r'^/[\w-]+/[\w-]+-(?P<post_id>\d+)/?$')
    old_video_path_re = re.compile(r'^/file/\d+/?$', re.I)

    methods = (OEmbedMethod(u"http://blip.tv/oembed/"), BlipApiMethod())

    def handles_video_url(self, url):
        parsed_url = urlparse.urlsplit(url)
        if parsed_url.scheme not in ('http', 'https'):
            return False

        if (not parsed_url.netloc == 'blip.tv' and
            not parsed_url.netloc.endswith('.blip.tv')):
            return False

        if (self.new_video_path_re.match(parsed_url.path) or
            self.old_video_path_re.match(parsed_url.path)):
            return True

        return False

    def get_feed_url(self, url):
        if not '/rss' in url:
            if url.endswith('/'):
                return url + 'rss'
            else:
                return url + '/rss'
        return url

    def parse_feed_entry(self, entry):
        return self.parse_blip_feed_entry(entry)

    def get_next_feed_page_url(self, feed, feed_response):
        parsed = urlparse.urlparse(feed_response.href)
        params = urlparse.parse_qs(parsed.query)
        try:
            page = int(params.get('page', ['1'])[0])
        except ValueError:
            page = 1
        params['page'] = unicode(page + 1)
        return "%s?%s" % (urlparse.urlunparse(parsed[:4] + (None, None)),
                          urllib.urlencode(params, True))

    def parse_blip_feed_entry(self, entry):
        """
        Parses a feedparser entry from a blip rss feed into a dictionary mapping
        :class:`.Video` fields to values. This is used for blip feeds and blip API
        requests (since those can also be done with feeds.)

        """
        enclosure = get_first_accepted_enclosure(entry)

        data = {
            'guid': entry['id'],
            'link': entry['link'],
            'title': entry['title'],
            'description': clean_description_html(
                entry['blip_puredescription']),
            'file_url': enclosure['url'],
            'embed_code': entry['media_player']['content'],
            'publish_datetime': datetime.strptime(entry['blip_datestamp'],
                                                  "%Y-%m-%dT%H:%M:%SZ"),
            'thumbnail_url': get_entry_thumbnail_url(entry),
            'tags': [tag['term'] for tag in entry['tags']
                     if tag['scheme'] is None][1:],
            'user': entry['blip_safeusername'],
            'user_url': entry['blip_showpage']
        }
        if 'license' in entry:
            data['license'] = entry['license']
        if 'blip_runtime' in entry and entry['blip_runtime']:
            data['duration_seconds'] = int(entry['blip_runtime'])
        return data

registry.register(BlipSuite)
