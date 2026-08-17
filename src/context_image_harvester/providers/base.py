from __future__ import annotations

from abc import ABC, abstractmethod

from requests import Session

from ..cache import SearchCache
from ..metrics import Metrics
from ..models import Candidate, Item


class Provider(ABC):
    name = "base"

    def __init__(self, session: Session, cache: SearchCache, metrics: Metrics, timeout: int = 35):
        self.session = session
        self.cache = cache
        self.metrics = metrics
        self.timeout = timeout

    @abstractmethod
    def search(self, item: Item, limit: int) -> list[Candidate]:
        raise NotImplementedError
