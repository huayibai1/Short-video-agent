from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .config_store import PROJECT_ROOT
from .embedding_client import EmbeddingError, create_embeddings, create_embeddings_batched


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


def chunk_text(text: str, chunk_size: int = 420, overlap: int = 60) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        start += max(1, chunk_size - overlap)
    return chunks


class VectorStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else PROJECT_ROOT / "knowledge" / "vector_store.json"
        self.documents: list[dict[str, Any]] = []
        self.idf: dict[str, float] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.documents = data.get("documents", [])
            self.idf = data.get("idf", {})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"documents": self.documents, "idf": self.idf}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def rebuild_tfidf(self) -> None:
        doc_freq: Counter[str] = Counter()
        tokenized_docs = []
        for doc in self.documents:
            tokens = tokenize(doc["text"])
            tokenized_docs.append(tokens)
            doc_freq.update(set(tokens))

        total = max(1, len(self.documents))
        self.idf = {token: math.log((total + 1) / (freq + 1)) + 1 for token, freq in doc_freq.items()}
        for doc, tokens in zip(self.documents, tokenized_docs):
            counts = Counter(tokens)
            vector = {token: counts[token] * self.idf.get(token, 1.0) for token in counts}
            norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
            doc["vector"] = vector
            doc["norm"] = norm

    def add_text(
        self,
        text: str,
        source: str = "manual",
        embedding_config: dict[str, Any] | None = None,
    ) -> int:
        chunks = chunk_text(text)
        before = len(self.documents)
        embeddings: list[list[float]] = []
        embedding_error = ""
        if embedding_config and embedding_config.get("enabled"):
            try:
                embeddings = create_embeddings(
                    chunks,
                    api_key=embedding_config.get("api_key", ""),
                    base_url=embedding_config.get("base_url", ""),
                    model=embedding_config.get("model", ""),
                    encoding_format=embedding_config.get("encoding_format", "float"),
                )
            except EmbeddingError as exc:
                embedding_error = str(exc)

        for idx, chunk in enumerate(chunks, start=1):
            doc = {
                "id": f"{source}-{before + idx}",
                "source": source,
                "text": chunk,
                "embedding_model": embedding_config.get("model", "") if embedding_config else "",
                "embedding_error": embedding_error,
            }
            if idx <= len(embeddings):
                doc["embedding"] = embeddings[idx - 1]
                doc["embedding_dim"] = len(embeddings[idx - 1])
            self.documents.append(doc)
        self.rebuild_tfidf()
        self.save()
        return len(chunks)

    def add_file(self, file_path: str | Path, embedding_config: dict[str, Any] | None = None) -> int:
        file_path = Path(file_path)
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        return self.add_text(text, file_path.name, embedding_config)

    def _search_by_embedding(
        self,
        query: str,
        embedding_config: dict[str, Any],
        top_k: int,
    ) -> list[dict[str, Any]]:
        docs = [doc for doc in self.documents if doc.get("embedding")]
        if not docs:
            return []
        query_embedding = create_embeddings(
            [query],
            api_key=embedding_config.get("api_key", ""),
            base_url=embedding_config.get("base_url", ""),
            model=embedding_config.get("model", ""),
            encoding_format=embedding_config.get("encoding_format", "float"),
        )[0]
        query_norm = math.sqrt(sum(value * value for value in query_embedding)) or 1.0
        scored = []
        for doc in docs:
            vector = doc["embedding"]
            doc_norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            score = sum(a * b for a, b in zip(query_embedding, vector)) / (query_norm * doc_norm)
            scored.append(
                {
                    "score": round(score, 4),
                    "source": doc["source"],
                    "text": doc["text"],
                    "retrieval": "embedding",
                }
            )
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]

    def search(
        self,
        query: str,
        top_k: int = 4,
        embedding_config: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.documents:
            return []
        if embedding_config and embedding_config.get("enabled"):
            try:
                hits = self._search_by_embedding(query, embedding_config, top_k)
                if hits:
                    return hits
            except EmbeddingError:
                pass
        query_counts = Counter(tokenize(query))
        query_vector = {token: query_counts[token] * self.idf.get(token, 1.0) for token in query_counts}
        query_norm = math.sqrt(sum(value * value for value in query_vector.values())) or 1.0
        scored = []
        for doc in self.documents:
            vector = doc.get("vector", {})
            score = sum(query_vector.get(token, 0.0) * vector.get(token, 0.0) for token in query_vector)
            score = score / (query_norm * float(doc.get("norm") or 1.0))
            if score > 0:
                scored.append(
                    {
                        "score": round(score, 4),
                        "source": doc["source"],
                        "text": doc["text"],
                        "retrieval": "tfidf",
                    }
                )
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]

    def context_for(
        self,
        query: str,
        top_k: int = 4,
        embedding_config: dict[str, Any] | None = None,
    ) -> tuple[str, list[dict[str, Any]]]:
        hits = self.search(query, top_k, embedding_config)
        context = "\n\n".join(
            f"[来源：{hit['source']}，相关度：{hit['score']}]\n{hit['text']}" for hit in hits
        )
        return context, hits

    def rebuild_embeddings(self, embedding_config: dict[str, Any]) -> dict[str, Any]:
        if not embedding_config.get("enabled"):
            return {"ok": False, "message": "Embedding 模型未启用。", "updated": 0, "total": len(self.documents)}
        if not self.documents:
            return {"ok": True, "message": "知识库为空。", "updated": 0, "total": 0}

        texts = [doc["text"] for doc in self.documents]
        try:
            embeddings = create_embeddings_batched(
                texts,
                api_key=embedding_config.get("api_key", ""),
                base_url=embedding_config.get("base_url", ""),
                model=embedding_config.get("model", ""),
                encoding_format=embedding_config.get("encoding_format", "float"),
                batch_size=int(embedding_config.get("batch_size", 16) or 16),
            )
        except EmbeddingError as exc:
            return {"ok": False, "message": str(exc), "updated": 0, "total": len(self.documents)}

        for doc, embedding in zip(self.documents, embeddings):
            doc["embedding"] = embedding
            doc["embedding_model"] = embedding_config.get("model", "")
            doc["embedding_dim"] = len(embedding)
            doc["embedding_error"] = ""
        self.rebuild_tfidf()
        self.save()
        return {
            "ok": True,
            "message": "向量索引已重建。",
            "updated": len(embeddings),
            "total": len(self.documents),
            "model": embedding_config.get("model", ""),
            "dimension": len(embeddings[0]) if embeddings else 0,
        }
