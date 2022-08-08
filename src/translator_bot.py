"""This module implements a twitter bot able to translate\
    from Fulfulde to French, English, and Arabic and in the\
    other direction too"""

# python standard packages
from typing import Tuple, Dict, Union
import os
import time
from collections import Counter

# installed packages
import tweepy
from tweepy.models import Status

class TranslatorTwitterBot:
  """
  This class implements a translator twitter bot\
  from Fulfulde to French, English and Arabic and in the\
  other direction too.
  More specifically, the twitter user mention this bot\
  under a tweet and the bot translate this latter tweet\
  in Fulfulde if this tweet is written in English, French or\
  in Arabic. However, if the tweet is written in Fulfulde, the bot\
  will translate it in English, French or Arabic depending\
  on the language the user uses most often in twitter.

  Parameters
  ----------
  # TODO
  """
  def __init__(self,
              api_key: str,
              secret_key: str,
              access_token: str,
              secret_access_token: str):

      self.languages: Dict[str, str]  = {
                                        "fr" : "fra_Latn",
                                        "en" : "eng_Latn",
                                        "ar" : "arb_Arab"
                                        }
      self.api_key: str = api_key
      self.secret_key: str = secret_key
      self.access_token: str = access_token
      self.secret_access_token: str = secret_access_token
      self.last_translation: str = ""
      self._init_twitter_api()
  
  def get_twitter_api(self) -> None:
      """Authentificate the twitter API given according to the given token"""
      auth: tweepy.OAuthHandler = tweepy.OAuthHandler(self.api_key, self.secret_key)
      auth.set_access_token(self.access_token, self.secret_access_token)
      self.api: tweepy.API = tweepy.API(auth, wait_on_rate_limit=True)
  
  def get_user_language(self, user_id: int) -> str:
      """
      Will return the language the most used\
      by a twitter user.

      Parameters
      ----------
      - user_id: int
          The user id for which to get the language
      
      Return
      ------
      - str
          The language the most used by the twitter user.
      """
      tweets = self.api.user_timeline(user_id=user_id,
                                      count=1_000,
                                      include_rts = False,
                                      exclude_replies=False,
                                      tweet_mode = 'extended')
      
      return Counter(tweet.lang for tweet in tweets).most_common(1)[0][0]

  
  def get_src_tgt_languages(self,
                            tweet_status: Status,
                            user_id: int,
                            ) -> Tuple[str]:
      """
      This function will determinate the direction of the translation\
      depending the language in which the tweet is written and the tweets\
      of the user calling the bot.

      Parameters
      ----------
      - tweet_status: Status
          The tweet for which to determine the translation direction\
          for translating it.
        
      Returns
      -------
      - Tuple of strs:
          The first element of the tuple is the source language of the\
          translation and the second element is the language in which\
          the tweet is to be translated.
      """
      language: str = tweet_status.lang
      if language in self.languages :
          src: str = self.languages[language]
          tgt: str = "fuv_Latn"
      else :
          # we assume the source language of the tweet to translate
          # is in Fulfulde
          src: str = "fuv_Latn"
          tgt: str = self.get_user_language(user_id)
          # if the target language id not in the considered languages,
          # then we translate the tweet in french by default.
          if tgt not in self.languages:
              tgt: str = "fra_Latn"
      return src, tgt

  def check_mentions(self) -> Dict[str, str]:
      """The bot check its mentions timeline and collect\
          all the needed informations to perform his task."""
      last_mention: str = list(self.api.mentions_timeline(count = 1,
                                                          tweet_mode='extended'))[0]
      if last_mention.in_reply_to_status_id:
          source_tweet_status: Status = self.api.get_status(last_mention.in_reply_to_status_id,
                                                            tweet_mode="extended")
          src, tgt = self.get_src_tgt_languages(source_tweet_status)
          mention_username: str = last_mention.user.screen_name
          source_text_tweet: str = source_tweet_status.full_text.strip()
          tweet_id_str: str = last_mention.id_str

          return {
              "src_language" : src,
              "tgt_language" : tgt,
              "reply_to_this_username" : mention_username,
              "reply_to_this_tweet" : tweet_id_str,
              "translate_this_text" : source_text_tweet
          }

  def translate(self, src_language: str, tgt_language: str, text_to_translate: str) -> str:
      """Translate a given text from source language to a target language."""

      pass
  
  def rereply_to_the_tweet(self,
                            username: str,
                            text_to_reply: str,
                            tweet_to_reply: str) -> Union[None, str]:
      """
      """
      try:
          self.api.update_status(status=f'@{username} {text_to_reply}',
                                 in_reply_to_status_id=tweet_to_reply,
                                 auto_populate_reply_metadata=True)
      except:
          return text_to_reply
  
  def run_bot(self) -> None:
      pass
