#!/usr/bin/python
# -*- coding: utf_8 -*-

from medium import Medium
from release_img import ReleaseImg
from track import Track, TYPE_AUDIO, TYPE_DATA, TYPE_VIDEO, TYPE_IDX
from track_artist import TrackArtist
from xml.dom import minidom
import cStringIO
import gzip
import re
import sys
import urllib2
import utils

reload(sys)
sys.setdefaultencoding('utf-8')

URL = "http://www.discogs.com/release/$REL_ID$?f=xml&api_key=$API_KEY$"

class Discogs(object):
    """
    The Discogs class allows you to supply a discogs "release ID", and obtain the 
    following attributes .

        Album artist  : artist
        Album title   : title
        Release year  : year
        Record label  : label 
        Cat number    : getCatNo
        Track list    : track_list

    Discogs requires you to obtain your own API key 
    (see http://www.discogs.com/users/api_key). 
    Please see their API wiki (http://www.discogs.com/help/api) for more information.
    Sample code :

    The following code obtains release information for Discogs release 40522,
    Blunted Dummies - House for All

    $ python
    >>> from discogs import Discogs
    >>> r = Discogs('40522')
    >>> print r.artist + '-' + r.title
    Blunted Dummies-House For All

    >>> for c, a, t in r.track_list:
        ...     print "%d : %s - %s" % (c, a, t)
        ...

    1 : Blunted Dummies - House For All (Original Mix)
    2 : Blunted Dummies - House For All (House 4 All Robots Mix)
    3 : Blunted Dummies - House For All (Eddie Richard's Mix)
    4 : Blunted Dummies - House For All (J. Acquaviva's Mix)
    5 : Blunted Dummies - House For All (Ruby Fruit Jungle Mix)

    A wrapper script (py_tag.py) is also available, that implements the discogs class for
    directory/file tagging.

    jesse @ housejunkie . ca
    """

    def __init__(self, relId, API_KEY, build = 1):
        self.API_KEY = API_KEY
        self.relId = relId
        self.url = URL.replace("$REL_ID$", relId, 1)
        self.url = self.url.replace('$API_KEY$', self.API_KEY, 1)
        self.relxml = self.load_xml()
        self.artist = ''
        self.title = ''
        self.year = ''
        self.date = ''
        self.label = ''
        self.cat_num = ''
        self.genre = ''
        self.track_list = []
        self.format = []
        self.note = ''
        self.style = ''
        # marks that release is Various Artists release:
        self.VArelease = False
        self.taggedVarious = self.various_tag()
        self.imglist = []
        self.discogs_data = ''


        # instanciating Discogs automatically populates all
        # records from the releaseId
        if build:
            self.artist = self.parse_artists()
            self.title = self.parse_title()
            self.year = self.parse_year()
            self.date = self.parse_year(0)
            self.label = self.parse_label()
            self.cat_num = self.parse_cat_num()
            self.track_list = self.parse_track_list()
            self.genre = self.parse_genre()
            self.format = self.parse_format()
            self.note = self.parse_note()
            self.style = self.parse_style()
            self.imglist = self.parse_imglist()
            self.discogs_data = self.parse_ddata()

    def load_xml(self):
        """
        fetches a copy of the response XML provided by the discogs
        api. See here http://www.discogs.com/help/api for docs.
        """
        print 'request: ' + self.url

        request = urllib2.Request(self.url)
        request = utils.req_add_headers(request)
        try:
          response = urllib2.urlopen(request)
          data = response.read()
          relxml = minidom.parseString(gzip.GzipFile(fileobj = \
                           cStringIO.StringIO(data)).read())
        except Exception:
          try:
            # retrying to get the XML, but treating the result as plain text,
            # not gzipped
            response = urllib2.urlopen(request)
            data = response.read()
            relxml = minidom.parseString(data)
          except Exception:
            sys.stderr.write(("err: unable to obtain Discogs release id%s" +
                ", wrong API key?\n")
              % self.relId)
            sys.exit(1)
        return relxml

    def prettyJoin(self, joinStr):
      """
      processes Discogs 'join'. e.g ',' -> ', '
      """

      subst = {
          "," : ", ",
          "/" : " / ",
          "&" : " & ",
          "+" : " + ",
          "and" : " and ",
          "And" : " And ",
          "ANd" : " ANd ",
          "AND" : " AND ",
          "aND" : " aND ",
          "anD" : " anD ",
          "Feat." : " Feat. "
          }

      for a, b in subst.iteritems():
        joinStr = joinStr.replace(a, b)
      return joinStr

    def various_tag(self):
      return self.parse_artists().artstLst[0].discogsName == "Various"

    def parse_label(self):
        label = self.relxml.getElementsByTagName('label')[0]
        return self.clean_name(unicode(label.attributes["name"].value))

    def parse_cat_num(self):
        catno = self.relxml.getElementsByTagName('label')[0]
        return unicode(catno.attributes["catno"].value)

    def parse_title(self, node = None):
        if node == None:
            node = self.relxml
        return \
            unicode(node.getElementsByTagName('title')[0].firstChild.data)

    def parse_year(self, format = 1):
        """
        Parse year of release from xml feed. Currently
        Exits if data is not present. May want to set a
        default value and remove the sys.exit(), if the
        year isn't a requirement for your needs.
        """ 
        try:
            year = unicode(\
                self.relxml.\
                getElementsByTagName('released')[0].firstChild.data)
        except IndexError:
            print "[ERROR] unable to obtain release year for : %s" %self.relId
            sys.exit()
        if format:
            return self.clean_year(year)
        else:
            year = year.replace('-', '.')
            r = re.compile('\.00$')
            return r.sub('', year)

    def parse_artists(self, node = None):
        """
        retrieve both the album/release artists
        or the individual artists of each track
        """
        if node == None:
            node = self.relxml
        try:
            artists = node.getElementsByTagName('artists')[0]
        except IndexError:
            return TrackArtist(self.clean_name(\
                unicode(self.artist.artistString)),\
                self.artist.discogsNameLst, self.API_KEY)
        # a list of names of artists as seen in Discogs db(see commenst about it
        # in TrackArtist class and in Artist classes
        discogsArtstNmeLst = []
        count = 0
        for artst in artists.getElementsByTagName('artist'):
            if count == 0:
                # check if there is an artist name variation
                try:
                    name = self.clean_name(\
                        unicode(\
                        artst.getElementsByTagName('anv')[0].firstChild.data))
                # if there is no any anv
                except:
                    name = self.clean_name(\
                        unicode(\
                        artst.getElementsByTagName('name')[0].firstChild.data))
                # extend the list of Discogs artist names by one
                discogsArtstNmeLst.append(\
                    unicode(\
                    artst.getElementsByTagName('name')[0].firstChild.data))
            else:
                self.VArelease = True
                try:
                    nextname = \
                        self.clean_name(\
                        unicode(\
                        artst.getElementsByTagName('anv')[0].firstChild.data))
                except:
                    nextname = \
                        self.clean_name(\
                        unicode(\
                        artst.getElementsByTagName('name')[0].firstChild.data))
                name = name + \
                self.\
                prettyJoin(artists.getElementsByTagName('join')[count - 1]\
                .firstChild.data) + nextname

                discogsArtstNmeLst.append(\
                    unicode(\
                    artst.getElementsByTagName('name')[0].firstChild.data))
            count += 1
        # construct and return a TrackArtist class instance
        return TrackArtist(name, discogsArtstNmeLst, self.API_KEY)

    def parse_format(self):
        """
        parse format of the releases
        """
        formats = self.relxml.getElementsByTagName('formats')[0]
        mediums = []
        reissue = False
        for frmt in formats.getElementsByTagName('format'):
            length = ''
            diameter = ''
            try:
                # getting descriptions tag:
                descriptions =\
                        frmt.getElementsByTagName('descriptions')[0]
                # iterating throuhg 'description' tags:
                for description in\
                        descriptions.getElementsByTagName('description'):
                    # checking length of the medium:
                    if description.firstChild.data == "LP" or\
                            description.firstChild.data == "EP" or\
                            description.firstChild.data == "Single" or\
                            description.firstChild.data == "Maxi-Single" or\
                            description.firstChild.data == "Mini-Album" or\
                            description.firstChild.data == "Album":
                        length = unicode(description.firstChild.data)
                    # checking diameter of the medium:
                    elif str(description.firstChild.data).endswith("\""):
                        diameter = unicode(description.firstChild.data)
                    elif description.firstChild.data == "Reissue":
                        reissue = True
            except IndexError:
                pass
            mediums.extend([Medium(unicode(frmt.getAttribute('name')),\
                    unicode(frmt.getAttribute('qty')),\
                    diameter,\
                    length, reissue)])
        return mediums

    def parse_position(self, node = None):
           """
           parses position of the track
           """
           if node == None:
               node = self.relxml
           if len(re.findall(r'\d*',\
                   node.getElementsByTagName('position')[0].firstChild.data))\
                   == 4:
                   # if position looks lile 3-27 or 3.27 or smth:
             return re.findall(r'\d*',\
                 node.getElementsByTagName('position')[0].firstChild.data)[2]
           else:
             return node.getElementsByTagName('position')[0].firstChild.data

    def parse_discnum(self, node = None):
            """
            parses disc/cassete/vinyl number of the track
            """
            if node == None:
                    node = self.relxml
            if len(re.findall(r'\d*', node.getElementsByTagName('position')[0].\
                firstChild.data)) == 4:
              return re.findall(r'\d*', node.getElementsByTagName('position')[0].\
                firstChild.data)[0]
            else:
              return -1

    def parse_track_list(self):
        """
        returns a list (tlist) of Track objects

        """
        tlist = []
        count = 1
        skipcount = 0
        trackList = self.relxml.getElementsByTagName('tracklist')[0]
        for track in trackList.getElementsByTagName('track'):
            if track.getElementsByTagName('position')[0].hasChildNodes() == \
                            False:
                    print "idx track detected at position", str(count)
                    # for VA release artists of idx tracks will be empty, cause
                    # there is no way to determine who did perform 'that'
                    idxArtist = ""
                    # otherwise for 'not-va-release' index track artist would be
                    # artist of the release
                    if self.VArelease == False:
                      idxArtist = self.parse_artists(track)

                    tlist.append(Track(count,\
                        idxArtist,\
                        self.parse_title(track),\
                        -1,\
                        -1,\
                        TYPE_IDX))
                    continue
            elif \
            re.search('(video)', \
                            str(track.getElementsByTagName('position')[0].\
                            firstChild.data.lower())) and \
                            re.search('(video)', \
                            str(track.getElementsByTagName('position')[0].\
                            firstChild.data.lower())).group(0) == "video": 
                    skipcount += 1
                    print "video track detected at position", \
                        str(count + skipcount)
                    tlist.append(Track(count,\
                        "",\
                        self.parse_title(track),\
                        -1,\
                        -1,\
                        TYPE_VIDEO))
                    continue
            tlist.append(   Track(count,\
                            self.parse_artists(track),\
                            self.parse_title(track),\
                            self.parse_position(track),\
                            self.parse_discnum(track),\
                            TYPE_AUDIO))
            count += 1
        return tlist

    def parse_genre(self):
        """
        Obtains <genre></genre> within the <genres> tag
        """
        count = 0
        genres = self.relxml.getElementsByTagName('genres')[0]
        for gnr in genres.getElementsByTagName('genre'):
                if count == 0:
                        genre = unicode(gnr.firstChild.data)
                else:
                        genre = genre + ", " + unicode(gnr.firstChild.data)
                count = count + 1
        return genre

    def parse_note(self):
        """
        Returns release notes
        """
        try:
            return unicode(\
                self.relxml.getElementsByTagName('notes')[0].firstChild.data)
        except:
            return ""

    def parse_style(self):
        """
        Composes the style string from styles given on Discogs
        """
        if len(self.relxml.getElementsByTagName('styles')) == 0:
          return ""
        styles = self.relxml.getElementsByTagName('styles')[0]
        stlstr = ""
        for stl in styles.getElementsByTagName('style'):
            if len(stlstr) == 0:
                stlstr = unicode(stl.firstChild.data)
            else:
                stlstr = stlstr + ", " + unicode(stl.firstChild.data)
        return stlstr

    def parse_imglist(self):
        """
        Composes a list of url to release imgs for downloading them later
        """
        imgstr = []
        try:
            images = self.relxml.getElementsByTagName('images')[0]
        except IndexError:
            return ''
        for img in images.getElementsByTagName('image'):
            imgstr.extend([ ReleaseImg(img.getAttribute('uri'),\
                img.getAttribute('type')) ])
        return imgstr

    def parse_ddata(self):
        """
        Returns just xml text
        """
        return self.relxml.toprettyxml()

    def clean_name(self, name):
        """
        Cleans up the formatting of artist/label names.
        Discogs orders duplicate names by appending a counter to each dupe
        eg : http://www.discogs.com/search?type=artists&q=goldie&btn=Search
        Goldie
        Goldie (1)
        Goldie (16)
        """
        r = re.compile('\s\(\d+\)')
        return utils.filterThe(r.sub('', name))

    def clean_year(self, year):
        """'

        Returns the release year in the format : YYYY
        """
        save = re.compile('(\d\d\d\d)')
        return save.match(year).group(1)
