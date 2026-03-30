"""BM25 sparse encoding for hybrid retrieval with aviation corpus bootstrapping."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

CORPUS_PATH = Path(__file__).resolve().parent.parent.parent / "bm25_corpus.json"

# Seed corpus for BM25 initialization when no documents have been ingested yet.
# These phrases cover common aviation terminology to give the encoder a baseline.
AVIATION_SEED_CORPUS = [
    "aerodrome operating minima visibility ceiling RVR runway visual range",
    "ICAO Annex 14 aerodrome design requirements obstacle limitation surfaces",
    "EASA regulation easy access rules air operations flight crew licensing",
    "AIP aeronautical information publication approach procedure SID STAR",
    "separation minima radar procedural control area terminal manoeuvring area",
    "NOTAM notice to airmen aerodrome closure runway inspection FOD",
    "instrument approach procedure ILS VOR DME RNAV RNP GNSS",
    "air traffic control clearance instruction altitude flight level transition",
    "meteorological conditions METAR TAF SIGMET AIRMET wind shear turbulence",
    "emergency procedure engine failure go-around missed approach holding pattern",
    "unit manual local instructions letter of agreement coordination procedure",
    "obstacle clearance height decision altitude minimum descent altitude",
    "runway incursion hot spot taxiway marking lighting aerodrome chart",
    "flight information service alerting service search and rescue SARPS",
    "airspace classification controlled uncontrolled special use restricted prohibited",
]


class BM25Encoder:
    """Thin wrapper around pinecone-text BM25 encoder with corpus management."""

    def __init__(self):
        from pinecone_text.sparse import BM25Encoder as _BM25

        self._encoder = _BM25()
        self._fitted = False

    def fit(self, corpus: list[str]) -> None:
        """Fit the BM25 encoder on a text corpus."""
        if not corpus:
            corpus = AVIATION_SEED_CORPUS
        self._encoder.fit(corpus)
        self._fitted = True
        logger.info("BM25 encoder fitted on %d documents", len(corpus))

    def encode_documents(self, texts: list[str]) -> list[dict]:
        """Encode document texts to sparse vectors.

        Returns list of dicts with 'indices' and 'values' keys.
        """
        self._ensure_fitted()
        results = []
        for text in texts:
            sparse = self._encoder.encode_documents(text)
            results.append({
                "indices": sparse["indices"],
                "values": sparse["values"],
            })
        return results

    def encode_queries(self, texts: list[str]) -> list[dict]:
        """Encode query texts to sparse vectors."""
        self._ensure_fitted()
        results = []
        for text in texts:
            sparse = self._encoder.encode_queries(text)
            results.append({
                "indices": sparse["indices"],
                "values": sparse["values"],
            })
        return results

    def save_corpus(self, corpus: list[str]) -> None:
        """Save the training corpus to disk for persistence."""
        CORPUS_PATH.write_text(json.dumps(corpus, ensure_ascii=False, indent=2))
        logger.info("Saved BM25 corpus (%d documents) to %s", len(corpus), CORPUS_PATH)

    def load_corpus(self) -> list[str] | None:
        """Load a previously saved corpus from disk."""
        if not CORPUS_PATH.exists():
            return None
        try:
            corpus = json.loads(CORPUS_PATH.read_text())
            logger.info("Loaded BM25 corpus (%d documents) from %s", len(corpus), CORPUS_PATH)
            return corpus
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load BM25 corpus: %s", e)
            return None

    def _ensure_fitted(self) -> None:
        """Ensure the encoder is fitted, using saved or seed corpus if needed."""
        if self._fitted:
            return
        corpus = self.load_corpus()
        if corpus is None:
            corpus = AVIATION_SEED_CORPUS
        self.fit(corpus)


@lru_cache
def get_encoder() -> BM25Encoder:
    """Get the singleton BM25 encoder instance."""
    encoder = BM25Encoder()
    return encoder
