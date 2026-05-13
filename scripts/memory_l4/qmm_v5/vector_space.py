"""VectorSpace: 记忆向量空间 + 简单聚类 (V5)。

基于 qmm-v5-vision.md Section 3.2.2 设计。
支持:
- 余弦相似度检索
- K-Means 聚类（离线研究用途）
- 最近邻查找
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.cluster import KMeans

from .types import QMMEvent


class VectorSpace:
    """记忆向量空间。

    核心: 相似事件在向量空间中距离更近。
    定位: 离线研究/召回辅助（见 constraints 0.8）。
    """

    def __init__(self, random_state: int = 42):
        self.memory_vectors: Dict[str, np.ndarray] = {}
        self.memory_events: Dict[str, QMMEvent] = {}
        self.labels: Dict[str, int] = {}
        self.cluster_centers: Optional[np.ndarray] = None
        self.random_state = random_state

    def add_event(self, event: QMMEvent) -> None:
        """添加事件到向量空间。"""
        vec = np.array(event.to_feature_vector(), dtype=np.float64)
        self.memory_vectors[event.event_id] = vec
        self.memory_events[event.event_id] = event

    def add_batch(self, events: List[QMMEvent]) -> None:
        """批量添加。"""
        for ev in events:
            self.add_event(ev)

    def similarity(self, event_a: str, event_b: str) -> float:
        """计算两个事件的余弦相似度。"""
        vec_a = self.memory_vectors.get(event_a)
        vec_b = self.memory_vectors.get(event_b)
        if vec_a is None or vec_b is None:
            return 0.0
        return self._cosine_similarity(vec_a, vec_b)

    def find_similar(
        self, query_vector: np.ndarray, top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """查找最相似的 K 个事件。"""
        similarities = {
            eid: self._cosine_similarity(query_vector, vec)
            for eid, vec in self.memory_vectors.items()
        }
        sorted_sims = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        return sorted_sims[:top_k]

    def find_similar_by_event(
        self, event_id: str, top_k: int = 5,
    ) -> List[Tuple[str, float]]:
        """基于某个事件找相似事件。"""
        vec = self.memory_vectors.get(event_id)
        if vec is None:
            return []
        return self.find_similar(vec, top_k)

    def cluster(
        self, n_clusters: int = 10,
    ) -> Dict:
        """K-Means 聚类（离线研究）。

        返回:
        {
            "labels": {event_id: cluster_id},
            "centers": np.ndarray (K x dim),
            "inertia": float,
        }
        """
        if not self.memory_vectors:
            return {"labels": {}, "centers": None, "inertia": 0}

        event_ids = list(self.memory_vectors.keys())
        vectors = np.array([self.memory_vectors[eid] for eid in event_ids])

        k = min(n_clusters, len(vectors))
        kmeans = KMeans(
            n_clusters=k,
            random_state=self.random_state,
            n_init="auto",
            max_iter=100,
        )
        labels = kmeans.fit_predict(vectors)

        self.labels = {eid: int(labels[i]) for i, eid in enumerate(event_ids)}
        self.cluster_centers = kmeans.cluster_centers_

        return {
            "labels": self.labels,
            "centers": kmeans.cluster_centers_,
            "inertia": float(kmeans.inertia_),
            "n_clusters": k,
        }

    def assign_to_cluster(self, new_vector: np.ndarray) -> int:
        """将新向量分配到最近的聚类。"""
        if self.cluster_centers is None:
            return -1
        distances = np.linalg.norm(self.cluster_centers - new_vector, axis=1)
        return int(np.argmin(distances))

    def get_cluster_events(self, cluster_id: int) -> List[str]:
        """获取某个聚类中的所有事件 ID。"""
        return [eid for eid, cid in self.labels.items() if cid == cluster_id]

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """余弦相似度。"""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
