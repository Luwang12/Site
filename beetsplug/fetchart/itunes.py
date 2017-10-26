#!/usr/bin/python
"""A python interface to search iTunes Store"""
import urllib.error
import urllib.parse
import urllib.request

try:
    import simplejson as json
except ImportError:
    import json


ITUNES_API_VERSION = '2'
COUNTRY = 'US'           # ISO Country Store

HOST_NAME = 'http://itunes.apple.com/'


def clean_json(data):
    return data.decode().replace('\\\\', r'//').replace(r"\'", '\"').replace(r'\"', '').replace(r'\u', '')


class ServiceException(Exception):
    """Exception related to the web service."""

    def __init__(self, type, message):
        self._type = type
        self._message = message

    def __str__(self):
        return self._type + ': ' + self._message

    def get_message(self):
        return self._message

    def get_type(self):
        return self._type


class _Request(object):
    """Representing an abstract web service operation."""

    def __init__(self, method_name, params):
        self.params = params
        self.method = method_name

    def _download_response(self):
        """Returns a response"""
        data = []
        for name in list(self.params.keys()):
            value = self.params[name]
            if isinstance(value, int) or isinstance(value, float) or isinstance(value, int):
                value = str(value)
            try:
                data.append('='.join((name, urllib.parse.quote_plus(value.replace('&amp;', '&').encode('utf8')))))
            except UnicodeDecodeError:
                data.append('='.join((name, urllib.parse.quote_plus(value.replace('&amp;', '&')))))
        data = '&'.join(data)

        url = HOST_NAME
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme:
            url = "http://" + url
        url += self.method + '?'
        url += data

        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
        return response.read()

    def execute(self):
        try:
            response = self._download_response()
            response = clean_json(response)
            return json.loads(response)
        except urllib.error.HTTPError as e:
            raise self._get_error(e.fp.read())

    def _get_error(self, text):
        return ServiceException(type='Error', message=text)
        raise


class _BaseObject(object):
    """An abstract webservices object."""

    def __init__(self, method):
        self._method = method
        self._search_terms = dict()

    def _request(self, method_name=None, params=None):
        if not method_name:
            method_name = self._method
        if not params:
            params = self._get_params()
        return _Request(method_name, params).execute()

    def _get_params(self):
        params = {}
        for key in list(self._search_terms.keys()):
            params[key] = self._search_terms[key]
        return params

    def get(self):
        self._json_results = self._request()
        if 'errorMessage' in self._json_results:
            raise ServiceException(type='Error', message=self._json_results['errorMessage'])
        self._num_results = self._json_results['resultCount']
        l = []
        for result in self._json_results['results']:
            type = None
            if 'wrapperType' in result:
                type = result['wrapperType']
            elif 'kind' in result:
                type = result['kind']

            if type == 'artist':
                id = result['artistId']
                item = Artist(id)
            elif type == 'collection':
                id = result['collectionId']
                item = Album(id)
            elif type == 'track':
                id = result['trackId']
                item = Track(id)
            else:
                if 'collectionId' in result:
                    id = result['collectionId']
                elif 'artistId' in result:
                    id = result['artistId']
                item = Item(id)
            item._set(result)
            l.append(item)
        return l


class Search(_BaseObject):
    """ Search iTunes Store """

    def __init__(self, query, country=COUNTRY, media='all', entity=None,
                 attribute=None, offset=0, limit=50, order=None,
                 lang='en_us', version=ITUNES_API_VERSION, explicit='Yes'):
        """
        @param order: The results are returned in this order. Possible values
            are 'rank' or 'popular.'
        @param offset: Return search results starting at this offset. Useful
            because there is a cap of 500 results per query.
        @param limit: Return no more than this many results. Regardless of what
            you specify, iTunes will never return more than 500 results.
        """
        _BaseObject.__init__(self, 'search')

        self._search_terms = dict()
        self._search_terms['term'] = query
        self._search_terms['country'] = country
        self._search_terms['media'] = media
        if entity:
            self._search_terms['entity'] = entity
        if attribute:
            self._search_terms['attribute'] = attribute
        self._search_terms['limit'] = limit
        if offset > 0:
            self._search_terms['offset'] = offset
        if order is not None:
            self._search_terms['order'] = order
        self._search_terms['lang'] = lang
        self._search_terms['version'] = version
        self._search_terms['explicit'] = explicit

        self._json_results = None
        self._num_results = None

    def num_results(self):
        return self._num_results


class Lookup(_BaseObject):
    """ Loookup """

    def __init__(self, id, entity=None, country=None, limit=500):
        _BaseObject.__init__(self, 'lookup')

        self.id = id
        self._search_terms['id'] = id
        if entity:
            self._search_terms['entity'] = entity
        if country:
            self._search_terms['country'] = country
        self._search_terms['limit'] = limit


class Item(object):
    """ Item result class """

    def __init__(self, id):
        self.id = id
        self.name = None
        self.url = None

    def _set(self, json):
        self.json = json
        # print json
        if 'kind' in json:
            self.type = json['kind']
        else:
            self.type = json['wrapperType']
        # Item information
        self._set_genre(json)
        self._set_release(json)
        self._set_country(json)
        self._set_artwork(json)
        self._set_url(json)

    def _set_genre(self, json):
        self.genre = json.get('primaryGenreName', None)

    def _set_release(self, json):
        self.release_date = None
        if 'releaseDate' in json and json['releaseDate']:
            self.release_date = json['releaseDate'].split('T')[0]

    def _set_country(self, json):
        self.country_store = json.get('country', None)

    def _set_artwork(self, json):
        self.artwork = dict()
        if 'artworkUrl30' in json:
            self.artwork['30'] = json['artworkUrl30']
        if 'artworkUrl60' in json:
            self.artwork['60'] = json['artworkUrl60']
        if 'artworkUrl100' in json:
            self.artwork['100'] = json['artworkUrl100']
        if 'artworkUrl512' in json:
            self.artwork['512'] = json['artworkUrl512']
        if 'artworkUrl1100' in json:
            self.artwork['1100'] = json['artworkUrl1100']

    def _set_url(self, json):
        self.url = None
        if 'trackViewUrl' in json:
            self.url = json['trackViewUrl']
        elif 'collectionViewUrl' in json:
            self.url = json['collectionViewUrl']
        elif 'artistViewUrl' in json:
            self.url = json['artistViewUrl']

    def __repr__(self):
        if not self.name:
            if 'collectionName' in self.json:
                self._set_name(self.json['collectionName'])
            elif 'artistName' in self.json:
                self._set_name(self.json['artistName'])
        return self.name

    def __eq__(self, other):
        if other is None:
            return False
        return self.id == other.id

    def __ne__(self, other):
        if other is None:
            return False
        return self.id != other.id

    def _set_name(self, name):
        self.name = name

    def get_id(self):
        if not self.id:
            if 'collectionId' in self.json:
                self.id = self.json['collectionId']
            elif 'artistId' in self.json:
                self.id = self.json['artistId']
        return self.id

    def get_name(self):
        """ Returns the Item's name """
        return self.__repr__()

    def get_type(self):
        """ Returns the type of the Item """
        return self.type

    def get_url(self):
        """ Returns the iTunes Store URL of the Item """
        return self.url

    def get_genre(self):
        """ Returns the primary genre of the Item """
        return self.genre

    def get_release_date(self):
        """ Returns the release date of the Item """
        return self.release_date

    def get_artwork(self):
        """ Returns the artwork (a dict) of the item """
        return self.artwork

    def get_songs(self, limit=500):
        """ Just an alias for get_tracks """
        return self.get_tracks(limit)

    def get_tracks(self, limit=500):
        """ Returns the tracks of the Item """
        if self.type == 'song':
            return self
        items = Lookup(id=self.id, entity='song', limit=limit).get()
        if not items:
            raise ServiceException(type='Error', message='Nothing found!')
        return items[1:]

    def get_music_videos(self, limit=500):
        """ Returns the tracks of the Item """
        if self.type == 'musicVideo':
            return self
        items = Lookup(id=self.id, entity='musicVideo', limit=limit).get()
        if not items:
            raise ServiceException(type='Error', message='Nothing found!')
        return items[1:]

    def get_albums(self, limit=500):
        """ Returns the albums of the Item """
        if self.type == 'collection':
            return self
        if self.type == 'song':
            return self.get_album()
        items = Lookup(id=self.id, entity='album', limit=limit).get()[1:]
        if not items:
            raise ServiceException(type='Error', message='Nothing found!')
        return items[1:]

    def get_album(self):
        """ Returns the album of the Item """
        if self.type == 'collection':
            return self
        items = Lookup(id=self.id, entity='album', limit=1).get()
        if not items or len(items) == 1:
            raise ServiceException(type='Error', message='Nothing found!')
        return items[1]


class Artist(Item):
    """ Artist class """

    def __init__(self, id):
        Item.__init__(self, id)

    def _set(self, json):
        super(Artist, self)._set(json)
        self.name = json['artistName']
        self.amg_id = json.get('amgArtistId', None)
        self.url = json.get('artistViewUrl', json.get('artistLinkUrl', None))

    def get_amg_id(self):
        return self.amg_id


class Album(Item):
    """ Album class """

    def __init__(self, id):
        Item.__init__(self, id)

    def _set(self, json):
        super(Album, self)._set(json)
        # Collection information
        self.name = json['collectionName']
        self.url = json.get('collectionViewUrl', None)
        self.amg_id = json.get('amgAlbumId', None)

        self.price = round(json.get('collectionPrice', 0) or 0, 4)
        self.price_currency = json['currency']
        self.track_count = json['trackCount']
        self.copyright = json.get('copyright', None)

        self._set_artist(json)

    def _set_artist(self, json):
        self.artist = None
        if json.get('artistId'):
            id = json['artistId']
            self.artist = Artist(id)
            self.artist._set(json)

    def get_amg_id(self):
        return self.amg_id

    def get_copyright(self):
        return self.copyright

    def get_price(self):
        return self.price

    def get_track_count(self):
        return self.track_count

    def get_artist(self):
        return self.artist


class Track(Item):
    """ Track class """

    def __init__(self, id):
        Item.__init__(self, id)

    def _set(self, json):
        super(Track, self)._set(json)
        # Track information
        self.name = json['trackName']
        self.url = json.get('trackViewUrl', None)
        self.preview_url = json.get('previewUrl', None)
        self.price = None
        if 'trackPrice' in json and json['trackPrice'] is not None:
            self.price = round(json['trackPrice'], 4)
        self.number = json.get('trackNumber', None)
        self.duration = None
        if 'trackTimeMillis' in json and json['trackTimeMillis'] is not None:
            self.duration = round(json.get('trackTimeMillis', 0.0) / 1000.0, 2)
        try:
            self._set_artist(json)
        except KeyError:
            self.artist = None
        try:
            self._set_album(json)
        except KeyError:
            self.album = None

    def _set_artist(self, json):
        self.artist = None
        if json.get('artistId'):
            id = json['artistId']
            self.artist = Artist(id)
            self.artist._set(json)

    def _set_album(self, json):
        if 'collectionId' in json:
            id = json['collectionId']
            self.album = Album(id)
            self.album._set(json)

    def get_preview_url(self):
        return self.preview_url

    def get_disc_number(self):
        return self.number

    def get_duration(self):
        return self.duration

    def get_artist(self):
        return self.artist

    def get_price(self):
        return self.price


def search_song(query, limit=100, offset=0, order=None, store=COUNTRY):
    """ Just an alias for search_track """
    return search_track(query, limit, offset, order, store)


def search_track(query, limit=100, offset=0, order=None, store=COUNTRY):
    return Search(query=query, media='music', entity='song',
                  offset=offset, limit=limit, order=order, country=store).get()


def search_album(query, limit=100, offset=0, order=None, store=COUNTRY):
    return Search(query=query, media='music', entity='album',
                  limit=limit, offset=offset, order=order, country=store).get()


def search_artist(query, limit=100, offset=0, order=None, store=COUNTRY):
    return Search(query=query, media='music', entity='musicArtist',
                  limit=limit, offset=offset, order=order, country=store).get()


def search(query, media='all', limit=100, offset=0, order=None, store=COUNTRY):
    return Search(query=query, media=media, limit=limit,
                  offset=offset, order=order, country=store).get()


def lookup(id, entity=None, country=None, limit=500):
    items = Lookup(id, entity=entity, country=country, limit=limit).get()
    if not items:
        raise ServiceException(type='Error', message='Nothing found!')
    return items[0]
