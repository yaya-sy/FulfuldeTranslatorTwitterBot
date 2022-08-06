""" """
from typing import Tuple 
import os
import time
import tweepy 

class TranslatorTwitterBot:
  """
  """
  def __init__(self,
              api_key: str,
              secret_key: str,
              access_token: str,
              access_token_secret):
      self.languages = {
          "fr" : "fra_Latn",
          "en" : "eng_Latn",
          "ar" : "arb_Arab"
        }
      pass
  
  def get_twitter_api(self) -> tweepy.API:
      """
      """
      pass
  
  def get_src_tgt_languages(self, language) -> Tuple[str]:
      """
      """

      if language in self.languages :
        src = self.languages[language]
        tgt = "fuv_Latn"
      else :
          src = "fuv_Latn"
          tgt = self.languages[language]
      return src, tgt