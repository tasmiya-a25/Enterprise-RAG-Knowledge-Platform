"""
Cross-encoder reranking.

Takes the union of vector + BM25 candidates and rescoring them with a
cross-encoder that jointly attends over (query, chunk) pairs -- much
more precise than the bi-encoder similarity used for first-pass
retrieval, at the cost of being too slow to run over the whole corpus.
Runs fully locally (no API key needed).
"""
from functools import lru_cache


@lru_cache
def _get_reranker():
    from sentence_transformers import CrossEncoder
    from app.config.settings import get_settings

    settings = get_settings()
    # See app/rag/embeddings/embedder.py for why low_cpu_mem_usage=False is
    # needed here -- avoids a meta-tensor loading error on some
    # transformers/accelerate version combinations.
    return CrossEncoder(settings.RERANKER_MODEL, automodel_args={"low_cpu_mem_usage": False})


def rerank(query: str, candidates: list[dict], top_k: int) -> list[dict]:
    """
    candidates: list of dicts each containing at least {"chunk_id", "content"}
    returns: candidates re-sorted by cross-encoder score, truncated to top_k,
             each augmented with a "rerank_score" field.
    """
    if not candidates:
        return []

    model = _get_reranker()
    pairs = [(query, c["content"]) for c in candidates]
    scores = model.predict(pairs)

    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)

    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:top_k]
