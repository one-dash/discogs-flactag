#!/usr/bin/env python

import re

def filterThe(title):
  """
  transforms artist name from "Kinik, The" to "The Klinik"
  """
  try:
    title = 'The ' + re.search('^(.*)(, The)$', title).group(1)
    return title
  except AttributeError:
    return title

def req_add_headers(orig_request):
  """
  this function just adds some headers to the HTTP request and returns it back
  """
  orig_request.add_header('Host', 'www.discogs.com')
  orig_request.add_header('User-Agent',
      'Mozilla/5.0 (X11; U; Linux x86_64; en-US; rv:1.9.2.13) Gecko/20101209 Firefox/3.6.13')
  orig_request.add_header('Accept',\
      'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
  orig_request.add_header('Accept-Encoding', 'gzip,deflate')
  orig_request.add_header('Accept-Charset', 'UTF-8,*')
  return orig_request


