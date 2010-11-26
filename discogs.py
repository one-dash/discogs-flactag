#!/usr/bin/python
# -*- coding: utf_8 -*-


from xml.dom import minidom
import urllib2
import gzip
import cStringIO
import sys
import re

reload(sys)
sys.setdefaultencoding('utf-8')

API_KEY = ""
URL = "http://www.discogs.com/release/$REL_ID$?f=xml&api_key=$API_KEY$"

class ReleaseImg:
    """
    Describes an image for a release
    """
    def __init__(self, uri, type):
        self.uri = uri
        self.type = type

class Medium:
        """
        Describes a single(or a group of unique) medium(s)
        """
        def __init__(self, name, qty = 1, diameter = '', duration = '', \
          reissue = False):
            # quantity of the mediums:
            self.qty = qty
            # name of the medium: CD, CDr, Vinyl, so on...
            self.name = name
            # diameter of the medium: 7", 3", 12", so on...
            self.diameter = diameter
            # duration of the medium: LP, EP, Single, so on...
            self.duration = duration
            # if this is a reissue
            self.reissue = reissue

################
# TRACK TYPES
# do not reassign this variables, or you'll mess up something
################
TYPE_AUDIO = 0
TYPE_DATA = 1
TYPE_VIDEO = 2
TYPE_IDX = 3
################

pseudoArtist = [ "Various", "Unknown Artist" ]

class Artist:
  """
  Describes an artist, fetching information from Discogs db
  """
  def __init__(self, discogsName):
    # an artist name on Discogs(primary). i.e. "Klima (4)"
    self.discogsName = discogsName
    print "Artist:", self.discogsName
    self.pseudo = False
    # if this is a pseudo artist. e.g. 'Various' on Discogs is a pseudo artist
    for pa in pseudoArtist:
      if self.discogsName == pa:
        self.pseudo = True
        print "is pseudo artist"
        break
    # a polished artist primary name
    self.cleanArtistName = self.polishName(self.discogsName)
    # all anvs in clean artist name without ending commas
    self.cleanAnvs = []

    if self.pseudo == False:
      # a url to artist data
      self.url = self.constructUrl()
      # artist XML data
      self.artstXml = self.loadXml()

      # all artist's name variations are kept here
      self.anvList = self.fillAnvLst()
      # here urls to artist's images are kept
      self.artstImgsLst = self.fillImgsLst()

      # fill the clean anvs list
      if len(self.anvList) != 0:
        for anv in self.anvList:
          self.cleanAnvs.append(self.polishName(anv))

  def constructUrl(self):
    """
    contructs a url to artist place in the Discogs db from it's name
    """
    artistUrl = "http://www.discogs.com/artist/" +\
        unicode(self.discogsName.replace(' ', '+')) +\
        "?f=xml&api_key=" + API_KEY
    print "Artist URL:", artistUrl
    return unicode(artistUrl).encode('utf-8')

  def loadXml(self):
    """
    fetches a copy of discogs xml for further processing
    """
    request = urllib2.Request(self.url)
    request.add_header('Accept-Encoding', 'gzip')
    try:
      response = urllib2.urlopen(request)
      data = response.read()
      axml = minidom.parseString(gzip.GzipFile(fileobj =\
          cStringIO.StringIO(data)).read())
    except IOError:
      axml = minidom.parseString(data)
    except Exception:
      sys.stderr.write(u"err: unable to fetch artist \"%s\"" %\
          self.discogsName.decode('utf-8')\
          +\
          u" information from discogs db\n")
      sys.exit(1)
    return axml

  def fillAnvLst(self):
    """
    returns a list of artist's name variations
    """
    try:
      anvs = self.artstXml.getElementsByTagName('namevariations')[0]
    except IndexError:
      # if there are no name variations, return empty list
      return []

    anvLst = []
    for anv in anvs.getElementsByTagName('name'):
      anvLst.append(unicode(anv.firstChild.data))
      print "Found ANV:", anvLst[len(anvLst) - 1]
    
    return anvLst

  def fillImgsLst(self):
    """
    returns a list of urls to artist images
    """
    urlLst = []
    try:
      images = self.artstXml.getElementsByTagName('images')[0]
    except:
      return urlLst

    for image in images.getElementsByTagName('image'):
      urlLst.append(unicode(image.getAttribute('uri')))
      print "Artist image:", urlLst[len(urlLst) - 1]

    return urlLst

  def polishName(self, name):
    """
    TODO
    """
    r = re.compile('\s\(\d+\)')
    return r.sub('', name)

class TrackArtist:
  """
  Describes a track's artist
  """
  def __init__(self, releaseArtist, discogsNameLst):
    # artist name as it is stated on a release. as it should be written to a tag
    # field
    self.artistString = releaseArtist
    # artists names list on discogs(each of artists name is something like
    # "Klima (4)")
    self.discogsNameLst = discogsNameLst
    # here each of artist's information is kept
    self.artstLst = []

    for artistName in self.discogsNameLst:
      self.artstLst.append(Artist(unicode(artistName)))


class Track:
  """
  Describes a single track
  """
  def __init__(self, id, artist,\
      title, position, discNumber, trackType):
    # track id differs from position, for now it is number in _Discogs_
    # tracklist, i.e. absolute position in it
    self.id = id
    # contains an instance of TrackArtist class
    self.artist = artist
    # title of the release
    self.title = title
    # track position differs from id. it is the track position on a medium
    self.position = position
    # which of the mediums does this track belong to?
    self.discNumber = discNumber
    # is this an audio track? (there are data tracks and also video ones...)
    self.trackType = trackType
  def isAudio(self):
    if self.trackType == TYPE_AUDIO:
      return True
    else:
      return False
  def isIdx(self):
    if self.trackType == TYPE_IDX:
      return True
    else:
      return False

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

    def __init__(self, relId, build = 1):
        self.relId = relId
        self.url = URL.replace("$REL_ID$", relId, 1)
        self.url = self.url.replace('$API_KEY$', API_KEY,1)
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
        request.add_header('Accept-Encoding', 'gzip')
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
            sys.stderr.write("err: unable to obtain Discogs release : %s\n"\
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
          "+" : " + "
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
                self.artist.discogsNameLst)
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
        return TrackArtist(name, discogsArtstNmeLst)

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
        return r.sub('', name)

    def clean_year(self, year):
        """'

        Returns the release year in the format : YYYY
        """
        save = re.compile('(\d\d\d\d)')
        return save.match(year).group(1)
