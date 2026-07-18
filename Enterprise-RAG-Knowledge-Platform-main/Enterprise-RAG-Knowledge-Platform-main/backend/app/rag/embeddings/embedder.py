"""
Embedding provider abstraction.

Default provider is fully local (sentence-transformers / BGE), so the
platform runs end-to-end with zero API keys. Switching to OpenAI
embeddings is a one-line config change (EMBEDDING_PROVIDER=openai).
"""
from functools import lru_cache

from app.config.settings import get_settings

settings = get_settings()


class BaseEmbedder:
    dim: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


class LocalEmbedder(BaseEmbedder):
    """Wraps a local sentence-transformers / BGE model. No network calls at inference time."""

    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        # `model_kwargs={"low_cpu_mem_usage": False}` forces eager weight
        # loading straight onto CPU. Without this, some transformers/
        # accelerate version combinations load weights onto a "meta" device
        # first (a memory-saving trick meant for huge models) and then fail
        # to move them to CPU with: "Cannot copy out of meta tensor... use
        # torch.nn.Module.to_empty()". Forcing eager loading sidesteps that
        # entirely -- these models are small enough that the memory-saving
        # trick isn't needed anyway.
        self._model = SentenceTransformer(model_name, model_kwargs={"low_cpu_mem_usage": False})
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        # BGE models recommend a query instruction prefix for retrieval; we keep it
        # simple here and apply the same encoding to both docs and queries.
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return vectors.tolist()


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, model_name: str = "text-embedding-3-small"):
        from openai import OpenAI

        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for EMBEDDING_PROVIDER=openai")
        self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._model_name = model_name
        self.dim = 1536

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model_name, input=texts)
        return [d.embedding for d in response.data]


@lru_cache
def get_embedder() -> BaseEmbedder:
    """Cached singleton -- avoids reloading the model on every request."""
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbedder()
    return LocalEmbedder(settings.EMBEDDING_MODEL)
