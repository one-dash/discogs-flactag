#!/usr/bin/env python
# -*- coding: utf_8 -*-

################
# TRACK TYPES
# do not reassign this variables, or you'll mess up something
################
TYPE_AUDIO = 0
TYPE_DATA = 1
TYPE_VIDEO = 2
TYPE_IDX = 3
################

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

