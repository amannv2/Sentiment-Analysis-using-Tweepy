import json

import tweepy
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

    def __init__(self, max=50):
        self.twitter_auth = TwitterAuthenticator()
        self.max = max

    def stream_tweets(self, fetched_tweets_filename, hash_tag_list):
        # it basically is responsible for how we deal with data and errors
        listener = TwitterListener(fetched_tweets_filename, self.max)

        auth = self.twitter_auth.authenticate()
        stream = Stream(auth, listener)  # , tweet_mode='extended')
        # only stream tweets containing specified hash tags
        stream.filter(track=hash_tag_list)


class TwitterListener(StreamListener):

    def __init__(self, fetched_tweets_filename, max=50):
        super(TwitterListener, self).__init__()
        # this is where we'll store tweets
        self.fetched_tweets_filename = fetched_tweets_filename
        self.count = 0
        self.max = max
        self.internal_list = []

    def on_data(self, raw_data):

        # if max count is reached then write all tweets into a JSON file
        if self.count == self.max:
            with open(self.fetched_tweets_filename, 'w', encoding='utf-8') as fp:
                json.dump(self.internal_list, fp)
            return False
        try:
            # convert str to dict
            d = json.loads(raw_data)
            # add that dict to a list
            self.internal_list.append(d)
            # print(d["text"])
            self.count += 1
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

        # add option to not truncate data in the data frame, None = unlimited
        pd.set_option('display.max_colwidth', -1)

        # here we are extracting text of each tweet and adding it to data frame
        # while checking if it is a retweet or not
        df = pd.DataFrame(
            data=[tweet.retweeted_status.full_text if tweet.retweeted else tweet.full_text for tweet in tweets],
            columns=['Tweets'])

        return df


def create_tweet_txt(file_name):

    tweet_txt = open(file_name, "w", encoding="utf-8")

    with open("tweets.json", "r", encoding="utf-8") as fp:
        tweets = json.load(fp)

    count = 1
    for tweet in tweets:
        try:
            text = tweet['text']
        except AttributeError:
            text = tweet['extended_text']

        tweet_txt.write(str(count) + ":\t" + text + "\n")
        count += 1

    tweet_txt.close()


if __name__ == '__main__':

    tweet_file = "tweets.txt"
    fetched_tweets_filename = "tweets.json"

    twitter_client = TwitterClient()
    tweet_analyzer = TweetAnalyzer()

    api = twitter_client.get_twitter_client_api()

    choice = int(input("1. Stream live tweets and analyze sentiment\n"
                       "2. Stream tweets of someone's profile and analyze sentiment\n\n"
                       "Please Enter Your Choice: "))

    if choice == 1:

        hash_tags = input("\nEnter hashtags/keywords <usage: a, b, c>: ")
        import re
        hash_tags = list(re.split(', |,', hash_tags))

        max_tweet = int(input("Enter maximum number of tweets: "))

        print("Sit back and relax while I stream and analyze these tweets as it might take some time\n\n")

        twitter_streamer = TwitterStreamer(max_tweet)
        twitter_streamer.stream_tweets(fetched_tweets_filename, hash_tags)

        with open(fetched_tweets_filename, "r") as fp:
            all_tweets = json.load(fp)

        df = pd.DataFrame(columns=['Tweets'])
        i = 0
        for tweet in all_tweets:
            try:
                tweet_text = tweet['text']
            except AttributeError:
                tweet_text = tweet['extended_text']
            df.loc[i] = tweet_text
            i = i + 1

    elif choice == 2:

        # this allows us to specify the user from which we want to extract the tweet
        # along the total umber of tweets

        name = input("\nEnter Screen Name(username): ")
        max_tweet = int(input("Enter maximum number of tweets: "))

        print("\nSit back and relax while I stream and analyze these tweets as it might take some time\n\n")

        try:
            tweets = api.user_timeline(screen_name=name, count=max_tweet, tweet_mode="extended")

            df = tweet_analyzer.tweets_to_data_frame(tweets)

        except tweepy.error.TweepError:
            print("Something is wrong here. Is that screen name/username correct?")

    else:
        print("Invalid Choice. BYE, NOOB.")
        exit(0)

    # numpy array object: it'll create a new field in data frame
    df['sentiment'] = np.array([tweet_analyzer.analyze_sentiment(tweet) for tweet in df['Tweets']])

    pd.set_option('display.max_colwidth', 50)
    print(df.head(max_tweet))
    polarity = np.sum(df['sentiment'])
    print(f"\nSentiment Analysis Result based on {max_tweet} tweets: ", end='')

    if polarity > 0:
        print(f"Positive({polarity})")
    elif polarity < 0:
        print(f"Negative({polarity})")
    else:
        print(f"Neutral(0)")

    create_tweet_txt(tweet_file)
    print("\nCheck 'tweets.txt' for full tweet texts")
