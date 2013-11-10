Twitte Stream
==============

A twitter robot that listens to the general twitter stream and generates automatically new tweets by recombining fragments.

In order to make it run, you need to register an account at twitter, create a twitter app and 
authorize this app to manage the account. Then copy the credentials_template.py file to credentials.py and fill in the 
keys and secrets.

Then first run harvest_tweet_starts.py. It will listen to the tweet stream until it finds 1000 unique starts of tweets
each occurring at least twice. Well, really, it will store duplicates for each power of two a start reaches to give
common starts more of chance to occur but to avoid having them dominate the stream.

After this you can run generate_tweets. By default it will send out a new tweet every three hours. It also attempts
to answer simple questions though this is very much a work in progress.
