#!/usr/bin/env python
# -*- coding: utf_8 -*-

from artist import Artist

# in this list artists are being cached for further reuse
# TODO: make it a member of Discogs class and(?) introduce interfaces
artistCache = []

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
      for artist in artistCache:
        # assume all artists in artist cache are unique
        if artist.discogsName == artistName:
          self.artstLst.append(artist)
          break
      else:
        self.artstLst.append(Artist(unicode(artistName)))
        # append last item from self.artstLst to artist cache
        artistCache.append(self.artstLst[len(self.artstLst) - 1])

