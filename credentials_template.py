# Twitter credentials for the project

CONSUMER_KEY = ""
CONSUMER_SECRET = ""
ACCESS_KEY = ""
ACCESS_SECRET = ""

if not (CONSUMER_KEY and CONSUMER_SECRET and ACCESS_KEY and ACCESS_SECRET):
  raise StandardError('Please register an app and file in the relevant access tokens and secrets.')
