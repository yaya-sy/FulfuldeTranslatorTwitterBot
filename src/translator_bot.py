"""This module implements a twitter bot able to translate\
    from Fulfulde to French, English, and Arabic and in the\
    other direction too"""
# python standard packages
from typing import Tuple, Set
import os
import time

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

      self.languages: Set[str, str]  = {
                                        "fr" : "fra_Latn",
                                        "en" : "eng_Latn",
                                        "ar" : "arb_Arab"
                                        }
      self.api_key: str = api_key
      self.secret_key: str = secret_key
      self.access_token: str = access_token
      self.secret_access_token: str = secret_access_token
      self._init_twitter_api()
  
  def get_twitter_api(self) -> None:
      """Authentificate the twitter API given according to the given token"""
      auth: tweepy.OAuthHandler = tweepy.OAuthHandler(self.api_key, self.secret_key)
      auth.set_access_token(self.access_token, self.secret_access_token)
      self.api: tweepy.API = tweepy.API(auth, wait_on_rate_limit=True)
  
  def get_src_tgt_languages(self, tweet_status: Status) -> Tuple[str]:
      """
      This function will determinate the direction of the translation\
      depending the language in which the tweet is written.

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
          src: str = "fuv_Latn"
          tgt: str = self.languages[language]
      return src, tgt
