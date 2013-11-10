#!/usr/bin/env python
"""Listens to the tweet stream until it finds 1000 unique starts of tweets each occurring at least twice."""

import os

try:
  import credentials
except ImportError:
  raise StandardError("Please copy credentials_template.py to credentials.py and fill in the missing elements.")

import common

import tweepy
import sys

from collections import defaultdict

SAMPLE_SIZE = 3

class SampleStreamListener(tweepy.StreamListener):
  def __init__(self, started_with):
    self._count = 0
    self._starts = defaultdict(common.SampleCounter)
    self._started_with = started_with
    self.sapi = None
    super(SampleStreamListener, self).__init__()

  def on_status(self, status):
    self._count += 1
    text = status.text
    if text[0] == '@':
      return
    if text[0] == '#':
      return
    tokens = common.tokenize_tweet(text)
    if len(tokens) < 4:
      return True
    key = (tokens[1].lower(), tokens[3].lower())
    self._starts[key].count += 1
    sample = ''.join(tokens[:4])

    try:
      sample = str(sample)
    except UnicodeEncodeError:
      return True

    self._starts[key].sample[sample] += 1
    if self._starts[key].count > 1 and (self._starts[key].count & (self._starts[key].count - 1)) == 0:
      sys.stdout.write('\r%s (%d)\n' % (sample, self._starts[key].count))
      sys.stdout.flush()
      self._started_with.append(sample)
      self._starts[key].sample[sample] += 0
    if self._count > 15000:
      self.sapi.disconnect()
    sys.stdout.write('\r' + str(self._count))
    sys.stdout.flush()

  def on_error(self, status_code):
    print >> sys.stderr, 'Encountered error with status code:', status_code
    return True

  def on_timeout(self):
    print >> sys.stderr, 'Timeout...'
    return True


def main():
  auth = tweepy.OAuthHandler(credentials.CONSUMER_KEY, credentials.CONSUMER_SECRET)
  auth.set_access_token(credentials.ACCESS_KEY, credentials.ACCESS_SECRET)
  started_with = []
  started_with_file_name = os.path.expanduser(common.TWEET_START_PATH)
  listener = SampleStreamListener(started_with)
  sapi = tweepy.streaming.Stream(auth, listener)
  listener.sapi = sapi
  try:
    sapi.filter(locations=[-124.7625, 24.5210, -66.9326, 49.3845])
  except StopIteration:
    pass

  with file(started_with_file_name, 'w') as f:
    for l in sorted(started_with):
      f.write(l + '\n')


if __name__ == '__main__':
  main()



