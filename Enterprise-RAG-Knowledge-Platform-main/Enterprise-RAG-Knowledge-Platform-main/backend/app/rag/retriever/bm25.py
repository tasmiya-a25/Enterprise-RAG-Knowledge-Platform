"""
BM25 keyword retrieval.

Builds an in-memory BM25 index at query time from the candidate chunk
set (scoped to the user's accessible documents). This is the right
tradeoff for a day-1 build and moderate corpora; at real production
scale (100k+ chunks) swap this for a persistent inverted index
(Elasticsearch/OpenSearch/Whoosh) behind the same `bm25_search`
interface -- the hybrid retriever doesn't need to know the difference.
"""
import re
import uuid

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def bm25_search(query: str, corpus: list[tuple[uuid.UUID, str]], top_k: int) -> list[dict]:
    """
    corpus: list of (chunk_id, chunk_text)
    returns: list of {"chunk_id", "score"} sorted by score desc
    """
    if not corpus:
        return []

    tokenized_corpus = [_tokenize(text) for _, text in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))

    # NOTE: we intentionally do NOT filter by `score > 0` here. BM25's IDF term
    # can be near-zero or negative when a query term appears in most/all
    # documents of a *small* corpus (e.g. a single uploaded document) -- that's
    # expected BM25 behavior, not a signal that the match is irrelevant.
    # Relevance filtering is the reranker's job (see reranker.py), not this
    # first-pass retrieval stage.
    ranked = sorted(zip(corpus, scores), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"chunk_id": cid, "score": float(score)} for (cid, _text), score in ranked]
