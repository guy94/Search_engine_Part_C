import math

from spellchecker import SpellChecker
from ranker import Ranker
import utils


# DO NOT MODIFY CLASS NAME
class Searcher:
    # DO NOT MODIFY THIS SIGNATURE
    # You can change the internal implementation as you see fit. The model 
    # parameter allows you to pass in a precomputed model that is already in 
    # memory for the searcher to use such as LSI, LDA, Word2vec models. 
    # MAKE SURE YOU DON'T LOAD A MODEL INTO MEMORY HERE AS THIS IS RUN AT QUERY TIME.
    def __init__(self, parser, indexer, model=None):
        self._parser = parser
        self._indexer = indexer
        self._ranker = Ranker()
        self._model = model
        self._docs_dict = {}
        self.number_of_documents = len(indexer.inverted_idx)

        self.spell = SpellChecker(local_dictionary='spell_dict.json', distance=1)

    # DO NOT MODIFY THIS SIGNATURE
    # You can change the internal implementation as you see fit.
    def search(self, query, k=None):
        """ 
        Executes a query over an existing index and returns the number of 
        relevant docs and an ordered list of search results (tweet ids).
        Input:
            query - string.
            k - number of top results to return, default to everything.
        Output:
            A tuple containing the number of relevant search results, and 
            a list of tweet_ids where the first element is the most relavant 
            and the last is the least relevant result.
        """
        query_object = self._parser.parse_query(query)

        relevant_docs = self._relevant_docs_from_posting(query_object)
        normalized_query = self.normalized_query(query_object)
        n_relevant = len(relevant_docs)
        ranked_doc_ids = Ranker.rank_relevant_docs(relevant_docs, normalized_query, self._indexer.docs_dict)
        return n_relevant, ranked_doc_ids

    # feel free to change the signature and/or implementation of this function 
    # or drop altogether.
    def _relevant_docs_from_posting(self, query_object):
        """
        This function loads the posting list and count the amount of relevant documents per term.
        :param query_as_list: parsed query tokens
        :return: dictionary of relevant documents mapping doc_id to document frequency.
        """
        query_dict = query_object.query_dict
        query_dict = self.spell_correction(query_dict)
        for term in query_dict:
            if term in self._indexer.inverted_idx:
                continue

            elif term.isupper() and term not in self._indexer.inverted_idx:
                if term.lower() in self._indexer.inverted_idx:
                    query_dict[term.lower()] = query_dict.pop(term)

            elif term.islower() and term not in self._indexer.inverted_idx:
                if term.upper() in self._indexer.inverted_idx:
                    query_dict[term.upper()] = query_dict.pop(term)

        relevant_posting_lists = {}
        for term in query_dict:
            if term in self._indexer.postingDict:
                relevant_posting_lists[term] = self._indexer.postingDict[term]

        self.document_dict_init(relevant_posting_lists, query_object.query_length)

        query_object.query_dict = query_dict

        print(self._docs_dict)
        return self._docs_dict

    def spell_correction(self, query_dict):
        """
        This function finds a misspelled word and finds its closest similarity.
        first by tracking all of its candidates. the candidate with the most appearances in the inverted index
        will be the "replacer"
        :param query: query dictionary
        :return: query dictionary with replaced correct words.
        """

        for term in query_dict:

            if term.lower() not in self._indexer.inverted_idx and term.upper() not in self._indexer.inverted_idx:

                misspelled_checker = self.spell.unknown([term])

                if len(misspelled_checker) != 0:
                    candidates = list(self.spell.edit_distance_1(term))

                    super_candidates = list(self.spell.candidates(term))
                    candidates.extend(super_candidates)

                    max_freq_in_corpus = 0
                    max_freq_name = ''

                    for i, candidate in enumerate(candidates):
                        if candidate in self._indexer.inverted_idx:
                            curr_freq = self._indexer.inverted_idx[candidate][0]
                            if curr_freq > max_freq_in_corpus:
                                max_freq_in_corpus = curr_freq
                                max_freq_name = candidate

                        elif candidate.upper() in self._indexer.inverted_idx:
                            curr_freq = self._indexer.inverted_idx[candidate.upper()][0]
                            if curr_freq > max_freq_in_corpus:
                                max_freq_in_corpus = curr_freq
                                max_freq_name = candidate

                    if max_freq_name != '':
                        query_dict[max_freq_name] = query_dict.pop(term)
                    else:
                        continue

        return query_dict

    def document_dict_init(self, postingDict, query_length):
        tf_idf_list = [0] * query_length

        for idx, (term, doc_list) in enumerate(postingDict.items()):
            for doc_tuple in doc_list:
                if doc_tuple[0] not in self._docs_dict:
                    self._docs_dict[doc_tuple[0]] = tf_idf_list

                try:
                    dfi = self._indexer.inverted_idx[term]
                except:
                    dfi = self._indexer.inverted_idx[term.lower()]

                idf = math.log(self.number_of_documents / dfi, 10)
                tf_idf = idf * doc_tuple[2]

                self._docs_dict[doc_tuple[0]][idx] = tf_idf
                tf_idf_list = [0] * query_length

    def normalized_query(self, query):
        """
       This function normalizes each term in the auery by the max term freq in the SORTED query dict.
       :param query: a query object
       :return: normalized query values
       """

        normalized = []
        max_freq_term = query.max_freq_term

        for key in query.query_dict:
            tf = query.query_dict[key]
            normalized.append(tf / max_freq_term)

        return normalized
