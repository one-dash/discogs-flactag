#!/usr/bin/python

import ConfigParser
import hashlib
import io
import mutagen
import mutagen.id3
import os
import pdb
import re
import shutil
import sys
import urllib2
from discogs import Discogs
from mutagen.flac import FLAC
from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCOM, TPUB, TRCK, TDRC, TXXX, \
                        TCON, COMM
from optparse import OptionParser

# Character substitutions in file name
FILE_NAME = {
                '/' : '-'
           }
# lenghth of tracnumber when naming files:
TRACNUM_LEN = 2

# the name of the file where discogs xml data will be stored for a backup:
DISCOGS_DATA_FILENAME = "discogs_releasedata.xml"
ARTIST_DATA_FILENAME = "discogs_artistdata.xml"

# supported file types.
FILE_TYPE = ['.mp3', '.flac', '.ogg']

class Config:
  """
  discribes simple configuration
  """
  def __init__(self, filename):
    """
    constructor

    filename --- filename(with path) of configuration file
    """
    default_settings = """
[discogs]
API_KEY: 00000000000
"""
    self.cp = ConfigParser.SafeConfigParser()
    self.cp.readfp(io.BytesIO(default_settings))
    self.cp.read(filename)
    self.apiKey = self.cp.get('discogs', 'API_KEY').strip()
  def getApiKey(self):
    """
    returns discogs API key from the config
    """
    return self.apiKey

def removeEndingSlash(string):
  """
  removes ending slash from a string if it ends with it
  """
  # if the last character is '/', we need to cut it off
  if string.endswith('/') == True:
    string = string.rpartition('/')[0]
  return string

def mkReleaseSymlinks(pathToRelease, artstPathsLst):
  """
  will make symlinks to release for in ach of artists dirs
  """
  if len(artstPathsLst) == 0:
    pass
  else:
    for artstDir in artstPathsLst:
      print "speaking about", artstDir
      print "making symlink to \"" + \
          "../" + \
          pathToRelease.rpartition('/')[0].rpartition('/')[2] + \
          "/" + pathToRelease.rpartition('/')[2] + \
          "\" in \"" + artstDir + '/' + pathToRelease.rpartition('/')[2] + \
          "\""
      os.symlink('../' + \
          pathToRelease.rpartition('/')[0].rpartition('/')[2] + \
          "/" + pathToRelease.rpartition('/')[2], \
          artstDir + '/' + pathToRelease.rpartition('/')[2])

def isVaCompilation(release):
  """
  check if release is VA compilation
  """
  va = False
  counter = 0
  for counter in range(len(disc.track_list)):
    if((counter + 1) > len(disc.track_list) - 1):
      break
    if((disc.track_list[counter].isAudio() != True) or\
        (disc.track_list[counter + 1].isAudio() != True)):
      continue
    # idx tracks are supposed not to have artists
    if disc.track_list[counter].isIdx == True:
      continue
    if str(\
        unicode(disc.track_list[counter].artist.artistString).encode("utf-8"))\
                 != \
                 str(unicode(disc.track_list[counter + 1].artist.artistString).\
                 encode("utf-8")):
      va = True
      break
  return va

def hashtblFilesInDir(dirPath):
  """
  builds a list of hashes of files in given directory
  """

  hList = []

  for name in os.listdir(dirPath):
    filePath = dirPath + '/' + name
    if os.path.isfile(dirPath + '/' + name) != True:
      #print "\"" + filePath + "\" is not a file, skipping hash procedure"
      continue
    else:
      # adding a hash to table of file hashes
      fileCntnts = open(filePath, "rb").read()
      hList.append(hashlib.sha256(fileCntnts).digest())
  
  return hList

def fetchImg(pathPrefix, uri, newName):
    """
    fetches an image to pathPrefix from uri, optionally giving it newName

    before saving it will check if a file with a such hash as at the uri already
    exists in pathPrefix
    """
    request = urllib2.Request(uri)
    try:
      o = urllib2.urlopen(request)
    except Exception:
      print "cannot fetch img " + uri
      return
    a = o.read()

    imgHash = hashlib.sha256(a).digest()
    if (len(hashtblFilesInDir(pathPrefix)) == 0) or\
        (hashtblFilesInDir(pathPrefix).count(imgHash) == 0):
      # saving a file

      # output filename
      if len(newName) != 0:
        outptFn = pathPrefix + '/' + newName
      else:
        outptFn = pathPrefix + '/' + uri.rpartition('/')[2].encode('utf-8')
      outpt = open(outptFn, "w")
      outpt.write(a)
      outpt.close()
    else:
      print "file with such hash already exists in directory \"" +\
          pathPrefix +\
          "\", not saving"

def makeArtstDirsLinksImgs(path, release, fetchImages):
  """
  makes artists subdirectories + anv symlinks, fetch their images
  """
  # first collect all desired artist names into a list
  artstNmes = constructUniqueArtstLst(release)

  # temp variable. part of path w/o artist name
  pathNA = path

  artstDirsLst = []
  if len(artstNmes) != 0:
    if release.taggedVarious == True:
      path = path + '/' + 'VA'
    else:
      # the release itself will go to the first artist's in the list folder
      path = path + '/' + artstNmes[0].cleanArtistName
    for artist in artstNmes:
      newPath = pathNA + '/' + clean_file(artist.cleanArtistName)
      if os.path.exists(newPath) and\
          (os.path.isdir(newPath) or os.path.islink(newPath)):
        print "dir or symlink \"" + newPath + "\" already exists, not creating"
      else:
        print "making dir \"" + newPath + "\"..."
        os.mkdir(newPath)

      # collect paths to artists dirs into a list
      if newPath == path:
        pass
      else:
        artstDirsLst.append(newPath)

      if len(artist.artstImgsLst) != 0:
        if artist.pseudo == False:
          print "fetching artist images:"
          for img in artist.artstImgsLst:
            print "\t" + img
            fetchImg(newPath, img, "")

      if artist.pseudo == False:
        print "writing discogs artist data..."
        dscgsXml = open(newPath + '/' + clean_file(ARTIST_DATA_FILENAME), "w")
        dscgsXml.write(unicode(
          artist.artstXml.toprettyxml()).encode("utf-8"))
        dscgsXml.close()

  # creating symlinks for anvs
  for artist in artstNmes:
    for anv in artist.anvList:
      newSl = pathNA + u'/' + clean_file(anv)
      if os.path.exists(newSl) and\
          (os.path.isdir(newSl) or os.path.islink(newSl)):
        print "dir or symlink \"" + newSl + "\" already exists, not creating"
      else:
        print u"making symlink \"" + newSl + \
            u"\" -> \"./" + artist.cleanArtistName + u"\""
        os.symlink(u'./' + artist.cleanArtistName,\
            pathNA + u'/' + clean_file(anv))

  # the path where a release should be placed is returned
  return {"np" : path, "artstDirs" : artstDirsLst }


def constructUniqueArtstLst(release):
  """
  creates a unique list of artists, involved in each track creation
  """

  # very stupid and slow
  artstNmeLst = []
  for trk in disc.track_list:
    if trk.isAudio() != True:
      continue
    for artst in trk.artist.artstLst:
      if len(artstNmeLst) == 0:
        # if the of artists is empty
        artstNmeLst.append(artst)
      else:
        counter = 0
        occurrenceFound = False
        while counter < len(artstNmeLst):
          if artst.cleanArtistName == artstNmeLst[counter].cleanArtistName:
            occurrenceFound = True
            break
          counter += 1
        if occurrenceFound == False:
          artstNmeLst.append(artst)

  return artstNmeLst

def composeDestDirName(sourcedirname):
  """
  cuts the path of the source dir from start to the last slash and returns it
  """

  if len(sourcedirname) == 0:
    sys.stderr.write("err: zero source path, exiting...")

  sourcedirname = removeEndingSlash(sourcedirname)

  return sourcedirname.rpartition('/')[0]

def ensureAllTracks(tracklist, numberOfFiles):
  """
  ensure that source directory has as many audio files as there are in the track
  list
  """
  
  # number of TRUE tracks, i.e. audio tracks in tracklist
  numTrueTracks = 0

  # count them
  for i in range(len(tracklist)):
    if tracklist[i].isAudio() == True:
      numTrueTracks += 1
    else:
      pass
  
  if numberOfFiles != numTrueTracks:
    errstr = "err: local tracklist(%s file(s)) does not match discogs " \
          % (numberOfFiles) + \
              "tracklist(%s track(s)), aborting\n" % (str(numTrueTracks))
    sys.stderr.write(errstr)
    sys.exit(1)

def form_formatstr(formats):
    """
    constructs a string of a format
    """
    formatstr = ""
    thisIsRe = False
    #pdb.set_trace()
    for medium in formats:
        qtystr = ""
        lenstr = ""
        if medium.reissue == True:
          thisIsRe = True
        if str(medium.qty) != "1" and str(medium.qty) != "-1":
            qtystr = str(medium.qty) + "x"
        else:
            # if quantity string equals to reserved default value or to a single
            # --- why should we use it?
            qtystr = ""
        if len(formats) == 1\
                and str(medium.name) == "CD":
            if len(medium.duration) == 0 and\
                medium.qty == 1:
                return ''

            if len(qtystr) != 0:
                formatstr = qtystr + medium.name

            if len(medium.duration) != 0:
              if len(formatstr) == 0:
                  # if this release has a single medium, and it is and ordinary
                  # cd -- print just it's duration:
                  formatstr = str(medium.duration)
              else:
                  formatstr = formatstr + ", " + str(medium.duration)

            if len(formatstr) == 0:
                break
            if medium.reissue == False:
                return ' [' + formatstr + ']'
            else:
                return ' [' + formatstr + ', RE' + ']'
        else:
            # if this is a 'Single'-type release, why should we use such a long
            # word in the format string? no way
            lenstr = ""
        if qtystr == "1" and str(medium.name) == "CD":
            # if we have only one medium and it is a CD --- we do not need the
            # format string at all
            break
        if formatstr == "":
            formatstr = " [" + qtystr + str(medium.name)
        else:
            formatstr = formatstr + "+" + qtystr + str(medium.name)
    # add a closing bracket to a format str:
    if len(formatstr) > 0:
        if len(formats[0].duration) != 0:
            formatstr = formatstr + ', ' + formats[0].duration
        if thisIsRe == True:
            formatstr = formatstr + ', RE' + "]"
        formatstr = formatstr + "]"
    return formatstr

def disc_debug(release):
    """
    Debug method to dump all attributes assigned to current Discogs object
    """
    formatstr = ''
    for medium in release.format:
        if len(formatstr) == 0:
            formatstr = str(medium.qty) + "x" +\
                    str(medium.name)
        else:
            formatstr = formatstr + "+" + str(medium.qty) + "x" +\
                    str(medium.name)
    div = "_ _______________________________________________ _ _\n"
    r = div
    r += "  Name : %s - %s\n" % (release.artist.artistString, release.title)
    r += " Label : %s\n" % (release.label)
    r += " Genre : %s\n" % (release.genre)
    r += " Style : %s\n" % (release.style)
    r += " Catno : %s\n" % (release.cat_num)
    r += "  Date : %s\n" % (release.date)
    r += "Format : %s\n" % (formatstr)
    r += "   URL : http:/www.discogs.com/release/%s\n" % (release.relId)
    r += div
    for i in range(len(release.track_list)):
        if release.track_list[i].isIdx() == True:
          # this is how index tracks are outputed
          r += "\t%s\n" % (release.track_list[i].title)
        else:
          # ordinary tracks are outputed like that
          if release.VArelease == True:
            # this is format for a VA release
            r += "%s - %s - %s\n" % (str(release.track_list[i].position), \
                release.track_list[i].artist.artistString,\
                release.track_list[i].title)
          else:
            # output for not VA release
            r += "%s - %s\n" % (str(release.track_list[i].position), \
                release.track_list[i].title)
    r += div
    return r


def prep_files(dir, rem=0):
    """
    Places file names into a list, and removes unwanted
    """
    fL = []
    try:
      dList = os.listdir(dir)
      dList.sort()
    except OSError:
      sys.stderr.write("err: no such directory\n")
      sys.exit(1)
    # the script will work only if audio files in directory are in sigle format,
    # not mixed, i.e. there are only flacs, or there are only oggs, etc.
    #
    # variable for checking:
    extension = ""
    for f in dList:
        f = unicode(f)
        for t in FILE_TYPE:
            if f.lower().endswith(t):
                # checking against equal files:
                if extension == "":
                    extension = t
                elif extension != t:
                    sys.stderr.write("audio files in directory are not\n" + \
                            "in equal formats\n")
                    sys.exit(1)
                fL.extend([dir + '/' + f])
            elif rem == 1:
                os.remove(dir + "/" + f)
    return fL

def clean_file(f):
    """
        Removes unwanted characters from file names
    """
    #a = unicode(f).encode('utf-8')
    a = f

    for k,v in FILE_NAME.iteritems():
        a = a.replace(k, v)

    #return a.decode('utf-8')
    return a
    #cf = re.compile(r'[^-\w.\(\)_]')
    #return unicode(cf.sub('', str(a)))

def make_sortable(istr):
    """
      Makes the string look so that the filenames will be sortable

      for now it only makes numbers go like 2 -> 02 or so
    """
    
    istr = unicode(istr).encode("utf-8")
    try:
      return str(re.match("\A(\D+)(\d+)\Z", istr).group(1)) +\
          str(re.match("\A(\D+)(\d+)\Z", istr).group(2).zfill(2))
    except AttributeError:
      return istr

def add_Replaygain(filesdir):
    # add Replay gain
    if os.system("which metaflac") == 0:
      print "adding Replaygain..."
      os.system("metaflac --add-replay-gain \"" + filesdir + "\"/*.flac")
    else:
      print "you have no metaflac, no Replaygain added"


if __name__ == "__main__":
  usage = "usage: %prog [options] " +\
      "<folder of audio files to tag> <discogs release id>"
  optParser = OptionParser(usage)
  optParser.add_option("-a", "--artist-subdirs", action="store_true",\
      dest="crtArtstSbs",\
      help="create artist subdirs within music directory")
  optParser.add_option("-d", "--dest-dir", dest="destdir",\
      help="destination directory to move files to")
  optParser.add_option("-i", "--images", action="store_true",\
      dest="fetchImages",\
      help="fetch artist and release images")
  (options, args) = optParser.parse_args()

  if len(args) == 0:
    optParser.print_usage()
    sys.exit(0)
#  if len(args) != 2:
#    print """
#Originally developed by jesse@housejunkie.ca http://code.google.com/p/jwsandbox/
#2009.07 modified by ivvmm <unachievable@gmail.com>
#
#---------------------------------------------------------------------
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
#---------------------------------------------------------------------
#
#"""
#    sys.exit(1)

  if options.destdir != None:
    # determine music directory
    if os.path.isdir(options.destdir) == False:
      sys.stderr.write("err: the destination music directory \"" +\
          options.destdir + "\" does not exist or is not a directory.\n")
      sys.exit(1)

  # check if the given first argument is a real directory
  if os.path.isdir(args[0]) == False:
    sys.stderr.write("given argument \"" + args[0] +\
            "\" does not exist or is not a directory\n")
    sys.exit(1)

  if args[1].isdigit() == False:
    sys.stderr.write("err: discogs release id should be a number\n")
    sys.exit(1)

  sourceDirname = args[0].decode('utf-8')
  files = prep_files(sourceDirname,0)
  config = Config(os.path.expanduser('~') + "/.discogs-flactag")
  disc = Discogs(args[1], config.getApiKey())
  tot = str(len(disc.track_list))

  # ensure length of tracks on disk match length
  # of tracks obtained from the discogs API
  ensureAllTracks(disc.track_list, len(files))

  c = 0
  # check against various artists release
  va = isVaCompilation(disc)

  discnumber = 1
  discnumId = disc.track_list[0].discNumber
  multidisc = False
  print "removing old tags, adding new entries, renaming files..."
  for f in files:
    # check if it is an audio track that is at counter position
    while disc.track_list[c].isAudio() == False:
      c += 1

    if disc.track_list[c].discNumber != discnumId:
      discnumber += 1
      discnumId = disc.track_list[c].discNumber 
    # filetype:
    ft = ""
    if f.endswith(u'.mp3'):
      ft = u'mp3'
    elif f.endswith(u'.ogg'):
      ft = u'ogg'
    elif f.endswith(u'.flac'):
      ft = u'flac'

    if ft == u'mp3':
      # remove tags in audio files
      try:
        audio = ID3(f)
        audio.delete()
      except mutagen.id3.ID3NoHeaderError:
        pass
    elif ft == u'flac':
      audio = FLAC(f)
      # remember the encoding settings before deleting all tags:
      try:
        encoding = audio["ENCODING"]
      except:
        encoding = ""
        audio.delete()
    if ft == u'mp3':
      # add new ID3 tags
      try:
        id3 = mutagen.id3.ID3(f)
      except mutagen.id3.ID3NoHeaderError:
        id3 = mutagen.id3.ID3()

    if ft == u'mp3':
      # adding new id3 frames
      id3.add(TIT2(encoding=3, text=disc.track_list[c].title))
      id3.add(TPE1(encoding=3, text=disc.track_list[c].artist))
      id3.add(TALB(encoding=3, text=disc.title))
      id3.add(TCOM(encoding=3, text=disc.artist))
      id3.add(TPUB(encoding=3, text=disc.label))
      id3.add(TDRC(encoding=3, text=disc.year))
      id3.add(TXXX(encoding=3, desc='Catalog #', text=disc.cat_num))
      id3.add(TCON(encoding=3, text=disc.genre))
      id3.add(TRCK(encoding=3, text=str(disc.track_list[c][0]) + "/" + tot))
      id3.pprint()
      id3.save(f,0)
    elif ft == u'flac':
      disc.track_list[c].title
      audio["TITLE"] = disc.track_list[c].title
      audio["ARTIST"] = disc.track_list[c].artist.artistString
      audio["ALBUM"] = disc.title
      audio["COMPOSER"] = disc.artist.artistString
      audio["ORGANIZATION"] = disc.label
      audio["CATALOGNUM"] = disc.cat_num
      audio["GENRE"] = disc.genre
      if(len(disc.style) != 0):
        audio["STYLE"] = disc.style
      audio["YEAR"] = disc.year
      audio["DATE"] = disc.date
      audio["TRACKNUMBER"] = str(disc.track_list[c].position)
      audio["TRACKTOTAL"] = tot
      if(disc.track_list[c].discNumber != -1):
        audio["DISCNUMBER"] = str(disc.track_list[c].discNumber)
        multidisc = True
      if(len(encoding) != 0):
        audio["ENCODING"] = encoding
      if(len(disc.note) != 0):
        audio["DESCRIPTION"] = disc.note
      # write remembered encoding string:
      audio.pprint()
      audio.save()

    # composing new file name:
    if va == True:
      # if it is VA release and not a collaboration one the name of
      # the release is prepend by the artist name string
      artist_gap = "- " +\
          clean_file(disc.track_list[c].artist.artistString) + " "
    else:
      artist_gap = ""

    # if release consists of multiple mediums each track is being prepend by
    # the number of medium
    if multidisc == True:
      discprepend = str(disc.track_list[c].discNumber) + u'-'
    else:
      discprepend = ""
    nf = unicode(sourceDirname) + u"/" + \
                    unicode(discprepend) + \
                    make_sortable(\
                      clean_file(disc.track_list[c].position).\
                      zfill(TRACNUM_LEN)) \
                    + u" " + unicode(artist_gap) + u"-" + u" " + \
                    clean_file(disc.track_list[c].title) +\
                    u"." + ft
    shutil.move(f, nf)
    c += 1

  add_Replaygain(sourceDirname)

  # composing new directory name:
  if disc.VArelease == True:
    # if it is VA release the name of the release is prepend by the
    # artist name string
    VAgap = u"VA - "
  else:
    VAgap = ""
  # composing disc format part:
  formatstr = form_formatstr(disc.format)

  # determine where to move new directory, whether to the same place as the
  # source or to the new supplied
  prefixDir = composeDestDirName(unicode(sourceDirname).encode("utf-8"))
  if options.destdir != None:
    prefixDir = removeEndingSlash(options.destdir)
  
  artstNmes = []
  # if the user wants artist subdir and anv lymlinks to be created
  if options.crtArtstSbs != None:
    values = \
        makeArtstDirsLinksImgs(unicode(prefixDir), disc, options.fetchImages)
    prefixDir = values['np']
    artstDirs = values['artstDirs']

  # new destination
  nd = unicode(prefixDir).encode('utf-8') +\
      u"/" + u"[" + clean_file(disc.date) + u"]" + " " + VAgap + \
      clean_file(unicode(disc.title)) +\
      clean_file(unicode(formatstr))

  # check if there is no already such directory
  if os.access(nd, os.F_OK) == True:
    sys.stderr.write("destination folder \"" + \
            nd + \
            "\" already exists, exiting\n")
    sys.exit(1)
  print "moving directory: \"" +\
      sourceDirname + "\" -> \"" + nd + "\""
  shutil.move(sourceDirname, nd)

  if options.crtArtstSbs != None:
    mkReleaseSymlinks(nd, artstDirs)
        
  # write formatted xml to a file:
  discogs_xml = open(nd + "/" + clean_file(DISCOGS_DATA_FILENAME), "w")
  discogs_xml.write(unicode(disc.discogs_data).encode("utf-8"))
  discogs_xml.close()

  # get release images and write them:
  if options.fetchImages != None:
    if len(disc.imglist) == 0:
      print "there are no images for this release"
    else:
      print "fetching release images:"
      gotCover = False
      for image in disc.imglist:
        print "\t", unicode(image.uri).encode("utf-8")
        
        if str(image.type) == 'primary':
          fetchImg(nd, image.uri, 'cover' + '.' +\
              unicode(image.uri.rpartition(".")[2]).encode("utf-8"))
        else:
          fetchImg(nd, image.uri, "")

  print disc_debug(disc)
  print "output directory:", nd
