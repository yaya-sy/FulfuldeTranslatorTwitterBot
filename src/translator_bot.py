"""This module implements a twitter bot able to translate\
    from Fulfulde to French, English, and Arabic and in the\
    other direction too"""

# python standard packages
from typing import Tuple, Dict
import os
from pathlib import Path
import time
import logging
from collections import Counter

# installed packages
import requests
import tweepy
from tweepy.models import Status

# local modules
from ngram_lm import NGramLanguageModel

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
    - api_key: str
        The twitter API key.
    - api_secret_key: str
        The twitter API secret key.
    - access_token: str
        The access token for the twitter API.
    - secret_access_token: str
        The secret token for the twitter API.
    """
    def __init__(self,
                    api_key: str,
                    api_secret_key: str,
                    access_token: str,
                    secret_access_token: str,
                    ngram_models_folder: str):

            self.languages: Dict[str, str]  = {
                                                "ff" : "fuv_Latn",
                                                "fr" : "fra_Latn",
                                                "en" : "eng_Latn",
                                                "ar" : "arb_Arab"
                                                }
            self.api_key: str = api_key
            self.api_secret_key: str = api_secret_key
            self.access_token: str = access_token
            self.secret_access_token: str = secret_access_token
            self.ngram_models = [NGramLanguageModel() for _ in self.languages]
            trained_models = list(Path(ngram_models_folder).glob("*.json"))
            for trained_model, model in zip(trained_models, self.ngram_models):
                model.load_model(trained_model)
            self._init_twitter_api()

    def _init_twitter_api(self) -> None:
        """Authentificate the twitter API given according to the given token"""
        auth: tweepy.OAuthHandler = tweepy.OAuthHandler(self.api_key, self.api_secret_key)
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
    
    def language_identifier(self, text) -> str:
        """
        Try identifying language by using ngram language.
        Next version : using a neural model for this task.

        Parameters
        ----------
        - text: str
            Text for which to identify the language.
        
        Return
        ------
        - str:
            The identified language.
        """
        return max((model.assign_logprob(text), model.language)
                    for model in self.ngram_models)[1]
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
            src: str = self.language_identifier(tweet_status.full_text.strip())
            src: str = self.languages[src]
            tgt: str = self.get_user_language(user_id)
            # if the target language id not in the considered languages,
            # then we translate the tweet in french by default.
            if tgt not in self.languages:
                tgt: str = "fra_Latn"
                return src, tgt
            tgt: str = self.languages[tgt]
        return src, tgt

    def check_mentions(self) -> Dict[str, str]:
        """The bot check its mentions timeline and collect\
        all the needed informations to perform his task."""
        mentions: str = list(self.api.mentions_timeline(count = 1,
                                                            tweet_mode='extended'))
        if not mentions:
            return None
        last_mention = mentions[0]
        if last_mention.in_reply_to_status_id:
            source_tweet_status: Status = self.api.get_status(last_mention.in_reply_to_status_id,
                                                                tweet_mode="extended")
            mention_username: str = last_mention.user.screen_name
            src, tgt = self.get_src_tgt_languages(source_tweet_status, last_mention.user.id_str)
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

        inputs = {"data": [text_to_translate, src_language, tgt_language, 250]}
        response = requests.post("https://hf.space/embed/yaya-sy/FulfuldeTranslator/+/api/predict",
                                json=inputs)
        try : 
            return response.json()["data"][0]
        except :
            return None
        
        
    def rereply_to_the_tweet(self,
                                text_to_reply: str,
                                tweet_to_reply: str) -> str:
        """
        Function that reply to a given tweet by mentioning\
        the user of the tweet.

        Parameters
        ----------
        - text_to_reply: str
            The text to reply to the user.
        - tweet_to_reply: str
            The tweet id for which to reply.
        
        Return
        ------
        - str:
            The tweet id for which to reply.
        """
        try:
            self.api.update_status(status=text_to_reply,
                                    in_reply_to_status_id=tweet_to_reply,
                                    auto_populate_reply_metadata=True)
            return tweet_to_reply
        except:
            return tweet_to_reply
    
    def run_bot(self) -> None:
        """Run the bot by calling all the necessary functions here!"""
        last_reply = None
        while True:
            mention_data = self.check_mentions()
            if not mention_data :
                continue
            traslated_tweet = self.translate(
                                src_language=mention_data["src_language"],
                                tgt_language=mention_data["tgt_language"],
                                text_to_translate=mention_data["translate_this_text"]
                                )
            if mention_data["reply_to_this_tweet"] == last_reply or not traslated_tweet:
                continue
            last_reply = self.rereply_to_the_tweet(
                            text_to_reply=traslated_tweet,
                            tweet_to_reply=mention_data["reply_to_this_tweet"]
                            )
            logging.info("Waiting...")
            time.sleep(1800)

def main() -> None:
    """Instanciate a translator bot and runs it."""

    translator_bot = TranslatorTwitterBot(
                        api_key=os.environ["api_key"],
                        api_secret_key=os.environ["api_secret_key"],
                        access_token=os.environ["access_token"],
                        secret_access_token=os.environ["secret_access_token"],
                        ngram_models_folder="ngram_language_models"
                    )
    translator_bot.run_bot()

if __name__ == "__main__" :
    main()