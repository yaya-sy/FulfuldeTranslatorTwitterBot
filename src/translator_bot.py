"""This module implements a twitter bot able to translate\
    from Fulfulde to French, English, and Arabic and in the\
    other direction too"""

# python standard packages
from typing import Tuple, Dict, Set
import os
from pathlib import Path
import time
import logging
from collections import Counter
import re
from math import inf

# installed packages
import requests
import tweepy
from tweepy.models import Status
from tweepy import Cursor

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
    - translator: str
        The translator model.
    """
    def __init__(self,
                    api_key: str,
                    api_secret_key: str,
                    access_token: str,
                    secret_access_token: str,
                    translator: str,
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
            self.translator = translator
            self.ngram_models = [NGramLanguageModel() for _ in self.languages]
            trained_models = list(Path(ngram_models_folder).glob("*.json"))
            self.since_id = 0
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
        - user_id: int
            The user that produced the tweet.
            
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
            # identify the source language
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
    
    def get_already_replied_mentions(self):
        """Get mentions already replied by the bot."""
        already_replied_mentions: Set[int] = set()
        for status in self.api.user_timeline(count=3_000,
                                                screen_name="firtanam_"):
            if status.in_reply_to_status_id:
                # handle deleted tweet, private accounts, etc.
                try:
                    source_tweet_status: Status = self.api.get_status(
                                                    status.in_reply_to_status_id,
                                                    tweet_mode="extended")
                    already_replied_mentions.add(source_tweet_status.id)
                except:
                    continue
        return already_replied_mentions

    def get_status_data(self, status) -> Dict[str, str]:
        """The bot checks its mentions timeline and collect\
        all the needed informations to perform his task."""

        # not reply to not empty tweet.
        if re.sub("\B\@\w+", "", status.full_text).strip():
            return None
        if status.in_reply_to_status_id:
            try:
                # handle remove tweets, provate accounts, etd.
                source_tweet_status: Status = self.api.get_status(status.in_reply_to_status_id,
                                                                    tweet_mode="extended")
            except:
                return None
            mention_username: str = status.user.screen_name
            # not reply to self mentionning
            if mention_username == "firtanam_":
                return None
            src, tgt = self.get_src_tgt_languages(source_tweet_status, status.user.id_str)
            source_text_tweet: str = source_tweet_status.full_text.strip()

            return {
                "src_language" : src,
                "tgt_language" : tgt,
                "reply_to_this_username" : mention_username,
                "reply_to_this_tweet" : status.id,
                "translate_this_text" : source_text_tweet
            }

    def translate(self, src_language: str, tgt_language: str, text_to_translate: str) -> str:
        """Request translation of given text from source language to a target language."""

        inputs = {"data": [src_language, tgt_language, text_to_translate, 270]}
        for _ in range(10) :
            try:
                response = requests.post(self.translator,
                                        json=inputs)
                return response.json()["data"][0]
            except:
                continue
        return "Mi ronkii firtude 🥲"
        
        
    def reply_to_the_tweet(self,
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
        # to long tweet
        if len(text_to_reply) > 280:
            text_to_reply = "Mi fassiri, amma fassirdu ndu juuti. Ɗu'um ina holla yo fassirdu ndu wooɗaa... 😕"
        try:
            self.api.update_status(status=text_to_reply,
                                    in_reply_to_status_id=tweet_to_reply,
                                    auto_populate_reply_metadata=True)
            return tweet_to_reply
        except:
            logging.info(f"Could not reply this: {text_to_reply}, length: {len(text_to_reply)}")
            return None
    
    def run_bot(self) -> None:
        """Run the bot by calling all the necessary functions here!"""
        since_id = 1585009197304803328
        already_replied_mentions: Set[int] = self.get_already_replied_mentions()
        while True:
            for mention in Cursor(self.api.mentions_timeline,
                                    since_id=since_id,
                                    tweet_mode='extended').items():
                mention_id = mention.id
                condition_to_skeep_this_mention: bool = ((mention_id in already_replied_mentions) or
                                                        (re.sub("\B\@\w+", "", mention.full_text).strip()))
                if condition_to_skeep_this_mention:
                    logging.info(f"Already replied to this mention: {mention_id}. Waiting ...")
                    time.sleep(5)
                    continue
                since_id = max(since_id, mention_id)
                mention_data = self.get_status_data(mention)
                if not mention_data :
                    logging.info("Mentions, but no tweet to translate. Waiting...")
                    time.sleep(15)
                    continue
                traslated_tweet = self.translate(
                                    src_language=mention_data["src_language"],
                                    tgt_language=mention_data["tgt_language"],
                                    text_to_translate=mention_data["translate_this_text"]
                                    )
                self.reply_to_the_tweet(
                    text_to_reply=traslated_tweet,
                    tweet_to_reply=mention_data["reply_to_this_tweet"])
            logging.info("No mentions. Waiting...")
            time.sleep(15)

def main() -> None:
    """Instanciate a translator bot and runs it."""

    translator_bot = TranslatorTwitterBot(
                        api_key=os.environ["api_key"],
                        api_secret_key=os.environ["api_secret_key"],
                        access_token=os.environ["access_token"],
                        secret_access_token=os.environ["secret_access_token"],
                        translator=os.environ["translator"],
                        ngram_models_folder="ngram_language_models"
                    )
    translator_bot.run_bot()

if __name__ == "__main__" :
    main()