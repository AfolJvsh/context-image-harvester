from __future__ import annotations

from collections.abc import Callable


class RequestBudget:
    def __init__(
        self,
        maximum: int,
        used: int = 0,
        on_change: Callable[[int], None] | None = None,
    ):
        self.maximum = max(0, maximum)
        self.used = min(self.maximum, max(0, used))
        self.on_change = on_change

    def consume(self) -> bool:
        if self.used >= self.maximum:
            return False
        self.used += 1
        if self.on_change is not None:
            self.on_change(self.used)
        return True

    @property
    def remaining(self) -> int:
        return max(0, self.maximum - self.used)
