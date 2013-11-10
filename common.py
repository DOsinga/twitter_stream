from collections import Counter


SPLITTERS = """!"$%&'()*+,-./:;<=>?[\]^_`{|}~^"\' '"""
TWEET_START_PATH = '~/.tweet_starts'

def tokenize_tweet(text):
  """Split the tweet up in searchables and non searchables.

  >>> tokenize_tweet('hello #world')
  ['', 'hello', ' ', '#world']

  >>> tokenize_tweet('hello url: http://bit.ly/1ebTTBa')
  ['', 'hello', ' ', 'url', ': ', 'http://bit.ly/1ebTTBa']

  """
  res = ['']
  was_searchable = False
  in_url = False
  for ch in text:
    if ch == ' ' and in_url:
      in_url = False
      was_searchable = True
    if not in_url:
      searchable = not ch in SPLITTERS
      if was_searchable != searchable:
        if res[-1].lower() in ('http', 'https'):
          in_url = True
        else:
          res.append('')
      was_searchable = searchable
    res[-1] += ch
  return res


class SampleCounter(object):
  def __init__(self):
    self.count = 0
    self.sample = Counter()
    self.last_token = False
