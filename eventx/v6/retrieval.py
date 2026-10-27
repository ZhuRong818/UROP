"""Deterministic BM25 candidate retrieval. Scores are not relevance probabilities."""

from collections import Counter, defaultdict
import math
import re


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, documents, k1=1.2, b=0.75):
        self.k1, self.b = k1, b
        self.postings = defaultdict(list)
        self.lengths = []
        for index, text in enumerate(documents):
            counts = Counter(tokens(text))
            self.lengths.append(sum(counts.values()))
            for term, frequency in counts.items():
                self.postings[term].append((index, frequency))
        self.average = sum(self.lengths) / max(1, len(self.lengths)) or 1

    def search(self, text, limit=50):
        if limit < 1:
            raise ValueError("Positive limit required")
        scores = defaultdict(float)
        n = len(self.lengths)
        for term in sorted(set(tokens(text))):
            posting = self.postings.get(term, [])
            idf = math.log(1 + (n - len(posting) + 0.5) / (len(posting) + 0.5))
            for index, tf in posting:
                norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.average)
                scores[index] += idf * tf * (self.k1 + 1) / (tf + norm)
        return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[:limit]
