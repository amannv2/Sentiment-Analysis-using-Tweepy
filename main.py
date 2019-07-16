import creds

from tweepy import API
from tweepy import Cursor
from tweepy.streaming import StreamListener
from tweepy import OAuthHandler
from tweepy import Stream


class TwitterClient:
    def __init__(self, twitter_user=None):
        self.auth = TwitterAuthenticator().authenticate()
        self.twitter_client = API(self.auth)
        self.twitter_user = twitter_user

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
        stream = Stream(auth, listener)
        # only stream tweets containing specified hastags
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


if __name__ == '__main__':
    hash_tags = input('Enter hash tag(s) you want to search <usage: hello, world, bye>: ')

    import re
    hash_tags = list(re.split(', |,', hash_tags))

    fetched_tweets_filename = "tweets.json"

    # retrieve someone's specific details
    # twitter_client = TwitterClient()
    # print(twitter_client.get_user_timeline_tweets(1))
    # print(twitter_client.get_friends(100))

    # start streaming tweets
    twitter_streamer = TwitterStreamer()
    twitter_streamer.stream_tweets(fetched_tweets_filename, hash_tags)
