"""Registered people: name, priority order, reference photo and embedding.

Pure storage, no model code. Persisted as `data/faces/index.json` plus one
JPEG per person. Embeddings are tagged with the backend that produced them, so
switching models invalidates them explicitly instead of silently mismatching.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field
from typing import Optional

import cv2
import numpy as np


@dataclass
class Person:
    id: str
    name: str
    order: int
    backend: str
    embeddings: list[list[float]] = field(default_factory=list)

    def vectors(self) -> list[np.ndarray]:
        return [np.asarray(e, dtype=np.float32) for e in self.embeddings]


class FaceLibrary:
    def __init__(self, root: str, backend: str):
        self.root = root
        self.backend = backend
        self._lock = threading.Lock()
        self._people: dict[str, Person] = {}
        os.makedirs(root, exist_ok=True)
        self._load()

    @property
    def _index_path(self) -> str:
        return os.path.join(self.root, "index.json")

    def image_path(self, person_id: str) -> str:
        return os.path.join(self.root, f"{person_id}.jpg")

    def _load(self) -> None:
        if not os.path.exists(self._index_path):
            return
        with open(self._index_path, encoding="utf-8") as f:
            for raw in json.load(f):
                self._people[raw["id"]] = Person(**raw)

    def _save(self) -> None:
        tmp = self._index_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump([asdict(p) for p in self.list()], f)
        os.replace(tmp, self._index_path)

    def list(self) -> list[Person]:
        return sorted(self._people.values(), key=lambda p: p.order)

    def get(self, person_id: str) -> Optional[Person]:
        return self._people.get(person_id)

    def add(self, name: str, face_image: np.ndarray, embedding: np.ndarray) -> Person:
        with self._lock:
            pid = uuid.uuid4().hex[:12]
            person = Person(
                id=pid,
                name=name,
                order=len(self._people),
                backend=self.backend,
                embeddings=[embedding.tolist()],
            )
            cv2.imwrite(self.image_path(pid), face_image)
            self._people[pid] = person
            self._save()
            return person

    def rename(self, person_id: str, name: str) -> Person:
        with self._lock:
            person = self._people[person_id]
            person.name = name
            self._save()
            return person

    def delete(self, person_id: str) -> None:
        with self._lock:
            self._people.pop(person_id)
            try:
                os.remove(self.image_path(person_id))
            except FileNotFoundError:
                pass
            for i, p in enumerate(self.list()):
                p.order = i
            self._save()

    def reorder(self, ids: list[str]) -> None:
        with self._lock:
            known = [i for i in ids if i in self._people]
            rest = [p.id for p in self.list() if p.id not in known]
            for i, pid in enumerate(known + rest):
                self._people[pid].order = i
            self._save()

    def usable(self) -> list[Person]:
        """People whose embeddings came from the active backend."""
        return [p for p in self.list() if p.backend == self.backend and p.embeddings]
