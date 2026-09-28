"""Knowledge base loading and BM25 retrieval.

Pure Python on purpose: the demo is about routing, cost and evals, so retrieval
is kept small enough to read in one sitting.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STOPWORDS = frozenset(
    """a an and are as at be been but by can could do does for from had has have how i if in
    is it its me my of on or our so than that the their them then there these they this to
    was we what when where which who why will with would you your yours i'm i'd i'll""".split()
)

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = []
    for tok in _TOKEN.findall(text.lower()):
        if tok in STOPWORDS:
            continue
        # Crude plural folding so "bags" matches "bag" without a stemmer dependency.
        if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
            tok = tok[:-1]
        tokens.append(tok)
    return tokens


@dataclass(frozen=True)
class Chunk:
    id: str  # "<doc_id>#<section-slug>"
    doc_id: str
    title: str
    text: str


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_kb(kb_dir: Path) -> list[Chunk]:
    """Split every markdown file into one chunk per `##` section."""
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        doc_id = path.stem
        sections = re.split(r"^## ", path.read_text(encoding="utf-8"), flags=re.M)
        for section in sections[1:]:
            title, _, body = section.partition("\n")
            body = body.strip()
            if body:
                chunks.append(Chunk(f"{doc_id}#{_slug(title)}", doc_id, title.strip(), body))
    return chunks


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(f"{c.title} {c.text}")) for c in chunks]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(len(self.lengths), 1)
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def search(self, query: str, k: int = 3) -> list[Hit]:
        terms = tokenize(query)
        scored = []
        for i, doc in enumerate(self.docs):
            score = 0.0
            for t in terms:
                tf = doc.get(t, 0)
                if not tf:
                    continue
                norm = tf + self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_len)
                score += self.idf[t] * tf * (self.k1 + 1) / norm
            if score > 0:
                scored.append(Hit(self.chunks[i], score))
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]
