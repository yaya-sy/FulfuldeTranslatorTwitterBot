"""This module implements a twitter bot able to translate\
    from Fulfulde to French, English, and Arabic and in the\
    other direction too"""
# python standard packages
from typing import Tuple, Dict
import logging
import os
import time

# installed packages
import tweepy
from tweepy.models import Status
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

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
      self.model = AutoModelForSeq2SeqLM.from_pretrained("facebook/nllb-200-distilled-1.3B")
      self.tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-1.3B")
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

  def check_mentions(self) -> Dict[str, str]:
      """
      """
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

  def translate(src_language: str, tgt_language: str, text_to_translate: str) -> str:
      """
      """


