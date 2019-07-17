from tweepy import API
from tweepy import Cursor
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream

from textblob import TextBlob
import re

import numpy as np
import pandas as pd

import creds


class TwitterClient:
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator().authenticate()
        self.twitter_client = API(self.auth)
        self.twitter_user = twitter_user

    def get_twitter_client_api(self):
        return self.twitter_client

    # retrieve user's tweets
    def get_user_timeline_tweets(self, num_tweets):
        tweets = []
        # if id has not been specified or is None, it'll fetch my tweets by default
        for tweet in Cursor(self.twitter_client.user_timeline, id=self.twitter_user).items(num_tweets):
            tweets.append(tweet)

        return tweets

    def get_friends(self, num_friends):
        friend_list = []
        for friend in Cursor(self.twitter_client.friends).items(num_friends):
            friend_list.append(friend)

        return friend_list


class TwitterAuthenticator:

    def authenticate(self):
        # authentication using ACCESS TOKEN snf ACCESS SECRET
        auth = OAuthHandler(creds.APP_KEY, creds.APP_SECRET)
        # complete authentication process
        auth.set_access_token(creds.ACCESS_TOKEN, creds.ACCESS_SECRET)
        return auth


class TwitterStreamer:
    """
    This class streams live tweets.
    """

    def __init__(self):
        self.twitter_auth = TwitterAuthenticator()

    def stream_tweets(self, fetched_tweets_filename, hash_tag_list):
        # it basically is responsible for how we deal with data and errors
        listener = TwitterListener(fetched_tweets_filename)

        auth = self.twitter_auth.authenticate()
        stream = Stream(auth, listener)  # , tweet_mode='extended')
        # only stream tweets containing specified hash tags
        stream.filter(track=hash_tag_list)


class TwitterListener(StreamListener):

    def __init__(self, fetched_tweets_filename):
        super().__init__()
        # this is where we'll store tweets
        self.fetched_tweets_filename = fetched_tweets_filename

    def on_data(self, raw_data):
        try:
            print(raw_data)
            with open(self.fetched_tweets_filename, 'a', encoding='utf-8') as fp:
                fp.write(raw_data)
                return True

        except BaseException as e:
            print('Error on data: %s' % str(e))
        return True

    def on_error(self, status_code):
        # if rate limit is reached, return false
        if status_code == 420:
            print('Rate limit exhausted')
            return False
        print(status_code)


class TweetAnalyzer:
    """
    Analyzes and categorizes content form tweet
    """

    def clean_tweet(self, tweet):
        """
        returns clean tweet, i.e., removes hyperlinks and special chars
        """
        return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())

    def analyze_sentiment(self, tweet):
        analysis = TextBlob(self.clean_tweet(tweet))

        # polarity is positive
        if analysis.sentiment.polarity > 0:
            return 1
        # polarity is neutral
        elif analysis.sentiment.polarity == 0:
            return 0
        # polarity is negative
        else:
            return -1

    def tweets_to_data_frame(self, tweets):

        # add option to not truncate data in the dataframe, None = unlimited
        pd.set_option('display.max_colwidth', -1)

        # here we are extracting text of each tweet and adding it to data frame
        # while checking if it is a retweet or not
        df = pd.DataFrame(
            data=[tweet.retweeted_status.full_text if tweet.retweeted else tweet.full_text for tweet in tweets],
            columns=['Tweets'])

        # numpy array object: it'll create a new field in data frame
        # df['id'] = np.array([tweet.id for tweet in tweets])
        # df['source'] = np.array([tweet.source for tweet in tweets])
        # df['date'] = np.array([tweet.created_at for tweet in tweets])
        # df['len'] = np.array([len(tweet.full_text) for tweet in tweets])
        return df


if __name__ == '__main__':
    twitter_client = TwitterClient()
    tweet_analyzer = TweetAnalyzer()

    api = twitter_client.get_twitter_client_api()

    # this allows us to specify the user from which we want to extract the tweet
    # along the total umber of tweets
    tweets = api.user_timeline(screen_name='amannv2', count=20, tweet_mode="extended")

    # all possible things that we can extract from a tweet
    # print(dir(tweets[0]))
    # print(tweets[0].text)

    # print(tweets[0].retweeted_status.full_text)
    # print(tweets[0].retweeted)

    df = tweet_analyzer.tweets_to_data_frame(tweets)
    df['sentiment'] = np.array([tweet_analyzer.analyze_sentiment(tweet) for tweet in df['Tweets']])
    print(df.head(20))
    # print(np.mean(df['len']))
