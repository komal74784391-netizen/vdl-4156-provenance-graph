"""Provenance-aware summarization of graph streams.

Reference implementation accompanying the ICDE 2025 paper.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass
class StreamEdge:
    source: int
    target: int
    segment: int
    weight: float = 1.0


class ProvenanceSketch:
    """Count-min style sketch that retains stream segment lineage."""

    def __init__(self, width: int = 1024, depth: int = 4):
        self.width = width
        self.depth = depth
        self.counts = [[0] * width for _ in range(depth)]
        self.lineage: Dict[Tuple[int, int], List[int]] = {}

    def _positions(self, key: Tuple[int, int]) -> Iterable[Tuple[int, int]]:
        base = (key[0] * 73856093) ^ (key[1] * 19349663)
        for row in range(self.depth):
            yield row, (base ^ (row * 83492791)) % self.width

    def add(self, edge: StreamEdge) -> None:
        key = (edge.source, edge.target)
        for row, col in self._positions(key):
            self.counts[row][col] += 1
        segments = self.lineage.setdefault(key, [])
        if not segments or segments[-1] != edge.segment:
            segments.append(edge.segment)
            if len(segments) > 16:
                del segments[0]

    def estimate(self, key: Tuple[int, int]) -> int:
        return min(self.counts[row][col] for row, col in self._positions(key))

    def summarize(self, top_k: int = 20) -> List[dict]:
        ranked = sorted(self.lineage.items(), key=lambda kv: self.estimate(kv[0]), reverse=True)
        summary = []
        for (source, target), segments in ranked[:top_k]:
            summary.append({
                "source": source,
                "target": target,
                "estimated_count": self.estimate((source, target)),
                "provenance_segments": list(segments),
            })
        return summary
