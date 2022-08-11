"""This module implements a ngram language model."""

# imports standard python libraries
import random
from random import shuffle
from typing import Union, Tuple, Iterator
import json
import logging
from pathlib import Path
from itertools import tee
from collections import defaultdict
from argparse import ArgumentParser

# import installed packages
import numpy as np


random.seed(1798)

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

Ngram = Tuple[str]
class NGramLanguageModel:
    """
    This class implements a ngram language model with
    add-delta smoothing.

    Parameters
    ----------
    - pad_utterance: bool
        Whether or not pad utterances by adding\
        fake tokens in the beginning and ending of\
        each utterance.
    - ngram_size: int
        The size of the ngrams.
    - smooth: flot, int
        The value for smoothing. Default=1e-3
    """
    def __init__(self,
                    language=None,
                    pad_utterances: bool=True,
                    ngram_size: int=3,
                    smooth: Union[float, int]=1e-3):
        self.language = language
        self.pad_utterances = pad_utterances
        self.ngram_size = ngram_size
        self.smooth = smooth
        self.ngram_counter = defaultdict(lambda: defaultdict(int))
        self.denominator_smoother = None

    def get_ngrams(self, utterance: str) -> Iterator[Ngram] :
        """
        Return the ngrams of a given utterance.

        Parameters
        ----------
        - splitted_utterance: list of strings
            The utterance from which to extract the ngrams.

        Return
        -------
        - list:
            List of ngrams extracted from the utterance.
        """
        if self.pad_utterances :
            # add '<' for start token padding and '>' for\
            # end token padding
            utterance = (["<"] * (self.ngram_size - 1)) \
                + list(utterance) + ([">"] * (self.ngram_size - 1))
        iterables = tee(utterance, self.ngram_size)
        for number_of_shifts, iterator in enumerate(iterables) :
            for _ in range(number_of_shifts) :
                next(iterator, None)
        # This returned iterable will be empty if the length of the utterance
        # is smaller than the ngram size.
        return zip(*iterables)

    def estimate(self, train_file: str) -> None:
        """
        Estimate the language model from raw text file.

        Parameters
        ----------
        - train_file: str
            The path of the file containing train sentences\
            with one sentence per line.
        """
        LOGGER.info("Training the model...")
        with open(train_file, mode="r", encoding="utf-8") as sentences_file:
            vocabulary = set()
            for utterance in sentences_file :
                utterance = utterance.strip()
                for ngram in self.get_ngrams(utterance):
                    *context_tokens, next_token = ngram
                    self.ngram_counter[tuple(context_tokens)][next_token] += 1
                    vocabulary.add(next_token)

            # will be used to smooth the probability distribution
            # by adding the 'smooth' value to each token
            # in the vocabulary
            self.denominator_smoother = len(vocabulary) * self.smooth
        LOGGER.info("Model trained!")
        
    def save_model(self, out_dirname: str, out_filename: str) -> None:
        """
        Save the estimated parameters and the hyperparameters of\
        the language model in a JSON file.

        Parameters
        ----------
        - out_dirname: str
            The directory where the model will be stored.
        - out_filename: str
            The filename of the model.
        """
        LOGGER.info("Saving the model...")
        model = [(" ".join(ngram), dict(next_token))
                    for ngram, next_token in self.ngram_counter.items()]
        shuffle(model)
        model = dict(model)
        model["language"] = self.language
        model["pad_utterances"] = self.pad_utterances
        model["denominator_smoother"] = self.denominator_smoother
        model["smooth"] = self.smooth
        model["ngram_size"] = self.ngram_size
        out_directory = Path(out_dirname)
        out_directory.mkdir(parents=True, exist_ok=True)
        with open(out_directory / f"{out_filename}.json",
                    "w", encoding="utf-8") as out_model_file:
            json.dump(model, out_model_file)
        LOGGER.info("Modle saved!")

    def load_model(self, path: str) -> None:
        """
        Load a stored language model in a JSON file.

        Parameters
        ----------
        - path: str
            Path to where the language model is stored in a JSON file.
        """
        LOGGER.info("Loading the model...")
        with open(path, mode="r", encoding="utf-8") as parameters:
            model = json.load(parameters)
            self.language = model["language"]
            self.pad_utterances = model["pad_utterances"]
            self.denominator_smoother = model["denominator_smoother"]
            self.smooth = model["smooth"]
            self.ngram_size = model["ngram_size"]
            del model["language"]
            del model["pad_utterances"]
            del model["denominator_smoother"]
            del model["smooth"]
            del model["ngram_size"]
            self.ngram_counter = {tuple(ngram.split(" ")) : next_tokens \
                                    for ngram, next_tokens in model.items()}
        LOGGER.info("Modele loaded.")

    def ngram_probability(self, ngram: Ngram) -> float:
        """
        Assign a probability of a given ngram by using\
        the estimated counts of the ngram language model.

        Paramerers
        ----------
        - ngram: Tuple of str
            The ngram for which you want to assign a probability.

        Return
        ------
        - float:
            The assigned probability to the given ngram.
        """
        *left_context, next_token = ngram
        left_context = tuple(left_context)
        left_context_seen = self.ngram_counter.get(left_context, False)
        if not left_context_seen:
            # unknown left_context, return smoothed probability
            # (very small probability) instead of returning 0 probability
            return self.smooth / self.denominator_smoother
        denominator = sum(left_context_seen.values()) + self.denominator_smoother
        # add also the smooth to the numerator, so all sums up to one.
        numerator = self.ngram_counter[left_context].get(next_token, 0.0) + self.smooth
        return numerator / denominator

    def assign_logprob(self, utterance: str) -> float:
        """
        This function will assign a normalised log proabability
        of give utterance.

        Parameters
        ----------
        - utterance: str
            The utterance for which to compute the log probability

        Return
        ------
        - flot:
            The log probability of the utterance.
        """
        ngrams_of_the_utterance = list(self.get_ngrams(utterance))
        if not ngrams_of_the_utterance:
            # This condition can holds only in the case pad_utterances\
            # is set to False.
            return False
        ngram_values = np.array([self.ngram_probability(ngram)
                                    for ngram in ngrams_of_the_utterance])
        return np.sum(np.log(ngram_values)) / len(ngrams_of_the_utterance)

def main(args) -> None:
    """This function will train and save the ngram language model."""
    ngram_lm = NGramLanguageModel(language=args.language,
                                    pad_utterances=args.pad_utterances,
                                    ngram_size=args.ngram_size,
                                    smooth=args.smooth)
    ngram_lm.estimate(args.train_file)
    ngram_lm.save_model(args.out_directory, args.out_filename)

if __name__ == "__main__" :
    parser = ArgumentParser()
    parser.add_argument("--train_file",
                        type=str,
                        help="The directory containing the train files.",
                        required=True)
    parser.add_argument("--language",
                        type=str,
                        help="The language to be modeled.",
                        required=True)
    parser.add_argument("--ngram_size",
                        type=int,
                        default=3,
                        help="The size of the the ngrams.",
                        required=False)
    parser.add_argument("--smooth",
                        type=float,
                        default=1e-6,
                        help="The value for smoothing the probability\
                            distribution of the language model.",
                        required=False)
    parser.add_argument('--pad_utterances',
                        help="Pad the utterances by adding fake tokens at the\
                            beginning and ending of each utterance.",
                        action='store_true')
    parser.add_argument('--no-pad_utterances',
                        dest='pad_utterances',
                        action='store_false')
    parser.add_argument("--out_directory",
                        type=str,
                        help="The directory where the model will be stored.",
                        required=True)
    parser.add_argument("--out_filename",
                        help="The filename for the model.",
                        required=True)
    main(parser.parse_args())
