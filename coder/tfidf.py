"""Minimal stdlib TF-IDF + cosine similarity. The corpus here is ~450 short
documents — too small to justify a numpy/sklearn dependency, and a plain
implementation keeps the Docker image and build time small. See
skills/clinical-retrieval: this is the generalising similarity method, not
a keyword table."""
from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# A standard English function-word list — reduces noise from words that
# carry no discriminating clinical meaning, not a diagnosis-specific
# filter. Content words (including generic-sounding ones like "symptoms")
# are deliberately left in; see skills/clinical-retrieval for the residual
# noise that remains and why it's a job for the reasoning layer, not
# retrieval, to resolve.
_STOPWORDS = frozenset(
    """a an and are as at be by for from has have had he in is it its of on
    that the to was were will with no not this these those or but if than
    then so such can could would should may might also been being do does
    did his her their they them she we you your i""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class TfidfIndex:
    def __init__(self, documents: list[str]):
        doc_tokens = [tokenize(doc) for doc in documents]
        df: Counter[str] = Counter()
        for tokens in doc_tokens:
            df.update(set(tokens))
        n_docs = max(len(documents), 1)
        self._idf = {
            term: math.log((n_docs + 1) / (count + 1)) + 1.0 for term, count in df.items()
        }
        self._oov_idf = math.log(n_docs + 1) + 1.0
        self._doc_vectors = [self._vectorize(tokens) for tokens in doc_tokens]

    def _vectorize(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        vec = {term: count * self._idf.get(term, self._oov_idf) for term, count in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {term: v / norm for term, v in vec.items()}

    def query(self, text: str, top_k: int) -> list[tuple[int, float]]:
        q_vec = self._vectorize(tokenize(text))
        scores = []
        for idx, doc_vec in enumerate(self._doc_vectors):
            shorter, longer = (q_vec, doc_vec) if len(q_vec) < len(doc_vec) else (doc_vec, q_vec)
            score = sum(v * longer[t] for t, v in shorter.items() if t in longer)
            if score > 0:
                scores.append((idx, score))
        scores.sort(key=lambda pair: pair[1], reverse=True)
        return scores[:top_k]
