#!/usr/bin/env python
"""Generate tweets based on what comes in along in the tweet stream."""

import sys
import os

import tweepy

import common
import time
import multiprocessing
import signal
import random

try:
  import credentials
except ImportError:
  raise StandardError("Please copy credentials_template.py to credentials.py and fill in the missing elements.")

from collections import Counter, defaultdict

TWEET_INTERVAL = 3600 * 3

SAMPLE_SIZE = 3
QUESTION_WORDS = {'where', 'what', 'who', 'what', 'how', 'why'}
SECOND_WORDS = {'is', 'was', 'were', 'should', 'do', 'does'}
REFLECT ={'you': 'I',
          'yours': 'mine',
          'your': 'my',
          'i': 'you',
          'mine': 'yours',
          'my': 'your'}
CONNETIONS = {'where': 'in',
              'why': 'because'}

def get_next_token(api, key, hash_tag_counter, length_so_far):
  sample_counters = defaultdict(common.SampleCounter)
  max_count = 0
  max_key = None
  tweet_count = 0
  seen = set()
  for tweet in tweepy.Cursor(api.search,
                             q='"%s" -filter:retweets' % (' '.join(key)),
                             rpp=100,
                             result_type="recent",
                             include_entities=True).items():
    tokens = common.tokenize_tweet(tweet.text)
    filtered = ''.join((tk for idx, tk in enumerate(tokens) if idx % 2 == 1))
    if filtered in seen:
      continue
    tweet_count += 1
    seen.add(filtered)
    for token in tokens:
      if token.startswith('#'):
        hash_tag_counter[token] += 1

    for idx in range(1, len(tokens) - len(key) * 2, 2):
      for offset, token in enumerate(key):
        if tokens[idx + offset * 2].lower() != token.lower():
          break
      else:
        next_token = tokens[idx + offset * 2 + 2]
        sample = tokens[idx + offset * 2 + 1]
        sample_weight = 1
        if idx + offset * 2 + 4 == len(tokens):
          sample += 'X'
          if length_so_far < 50:
            sample_weight = 0.5
          elif length_so_far > 70:
            sample_weight = float(length_so_far) / 50
        sample_counters[next_token].count += 1
        sample_counters[next_token].sample[sample] += sample_weight
        if sample_counters[next_token].count > max_count:
          max_key = next_token
          max_count = sample_counters[next_token].count
          print 'best', max_key, max_count
          if max_count >= SAMPLE_SIZE:
            break
    if max_count >= SAMPLE_SIZE:
      break
    if tweet_count % 25 == 0:
      time.sleep(1)
    if tweet_count > 150:
      return True, '', ''
  if max_key is None:
    # Dead end
    return True, '', ''

  sample = sample_counters[max_key].sample.most_common(1)[0][0]
  done = sample.endswith('X')
  if done:
    sample = sample[:-1]
  return done, max_key, sample


def generate_new_tweet(auth, tokens):
  key = tuple(x.lower() for idx, x in enumerate(tokens) if idx % 2 == 1)
  tweet = ''.join(tokens)

  tweepy_api = tweepy.API(auth)

  hash_tag_counter = Counter()
  done = False
  first = True
  while not done and len(tweet) < 140:
    done, token, text = get_next_token(tweepy_api, key, hash_tag_counter, len(tweet))
    if first and done and len(key) > 2:
      key = key[1:]
      done = False
      continue
    first = False

    key += (token,)
    while len(key) > 4:
      key = key[1:]
    tweet += text + token
    print key, tweet

  while len(tweet) > 140 and '.' in tweet:
    tweet = tweet[:tweet.rfind('.')].strip()
  if len(tweet) > 140:
    return None

  if not '#' in tweet:
    for ht, cnt in hash_tag_counter.most_common():
      if cnt <= 1:
        print ht, cnt
        break
      if len(tweet) + len(ht) < 139:
        print ht, cnt
        tweet += ' ' + ht
        break
  return tweet

def reply_to(auth, text):
  tokens = [REFLECT.get(t.lower(), t) for idx, t in enumerate(common.tokenize_tweet(text)) if idx % 2 == 1]
  if tokens[0][0] == '@':
    del tokens[0]
  if len(tokens) < 4 or not tokens[0].lower() in QUESTION_WORDS or not (tokens[1].lower() in SECOND_WORDS or tokens[2].lower() in SECOND_WORDS):
    reply = "I only understand simple questions. Yours I did not recognize: %s" % text
    return reply[:120]
  if not tokens[1].lower() in SECOND_WORDS:
    del tokens[1]
  if tokens[1].lower() in ('do', 'does'):
    text = ' '.join(tokens[2:])
  else:
    text = ' '.join(tokens[2:]) + ' ' + tokens[1]
  if tokens[0] in CONNETIONS:
    text += ' ' + CONNETIONS[tokens[0]]
  tokens = common.tokenize_tweet(text)
  return generate_new_tweet(auth, tokens)


def post_tweets(queue):
  starts = file(os.path.expanduser(common.TWEET_START_PATH)).read().splitlines()
  auth = tweepy.OAuthHandler(credentials.CONSUMER_KEY, credentials.CONSUMER_SECRET)
  auth.set_access_token(credentials.ACCESS_KEY, credentials.ACCESS_SECRET)
  tweepy_api = tweepy.API(auth)
  last_post = 0
  while True:
    if not queue.empty():
      tweet = queue.get(block=False)
      if tweet:
        print 'got tweet from %s: %s' % (tweet.text, tweet.user)

      new_tweet = reply_to(auth, tweet.text)
      if not new_tweet:
        new_tweet = "I could not find that."
      tweepy_api.update_status(status='@%s: %s' % (tweet.user.screen_name, new_tweet), in_reply_to_status_id=tweet.id)

    if time.time() - last_post > TWEET_INTERVAL:
      a_start = random.choice(starts)
      print 'starting from:', a_start
      tokens = common.tokenize_tweet(a_start)
      new_tweet = generate_new_tweet(auth, tokens)
      if new_tweet:
        tweepy_api.update_status(status=new_tweet)

      last_post = time.time()
    time.sleep(1)


class UserListener(tweepy.StreamListener):
  def __init__(self, queue, screen_name):
    super(UserListener, self).__init__()
    self._queue = queue
    self._screen_name = screen_name

  def on_status(self, status):
    text = status.text
    print text
    if text.startswith('@' + self._screen_name):
      self._queue.put(status)

  def on_error(self, status_code):
    print >> sys.stderr, 'Encountered error with status code:', status_code
    return True

  def on_timeout(self):
    print >> sys.stderr, 'Timeout...'
    return True

  def on_connect(self):
    print 'Connected.'
    return True


def watch_user(queue):
  auth = tweepy.OAuthHandler(credentials.CONSUMER_KEY, credentials.CONSUMER_SECRET)
  auth.set_access_token(credentials.ACCESS_KEY, credentials.ACCESS_SECRET)
  tweepy_api = tweepy.API(auth)
  me = tweepy_api.me()
  listener = UserListener(queue, me.screen_name)
  sapi = tweepy.streaming.Stream(auth, listener)
  sapi.filter(follow=[me.id])


if __name__ == '__main__':
  reply_queue = multiprocessing.Queue()
  watch_user_process = multiprocessing.Process(target=watch_user, args=(reply_queue,))
  post_tweets_process = multiprocessing.Process(target=post_tweets, args=(reply_queue,))

  watch_user_process.start()
  post_tweets_process.start()

  def signal_handler(signal, frame):
    print 'Exiting'
    watch_user_process.terminate()
    post_tweets_process.terminate()

  signal.signal(signal.SIGINT, signal_handler)
  print 'Press Ctrl+C to abort'
  signal.pause()


