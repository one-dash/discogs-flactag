#!/usr/bin/python
# -*- coding: utf_8 -*-

from xml.dom import minidom
import cStringIO
import gzip
import re
import sys
import urllib2
import utils

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
    artistUrl = "http://api.discogs.com/artist/" +\
        unicode(self.discogsName.replace(' ', '+')) + "?f=xml"
    print "Artist URL:", artistUrl
    return unicode(artistUrl).encode('utf-8')

  def loadXml(self):
    """
    fetches a copy of discogs xml for further processing
    """
    request = urllib2.Request(self.url)
    request = utils.req_add_headers(request)
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
    return utils.filterThe(r.sub('', name))

