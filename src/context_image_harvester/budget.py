from __future__ import annotations


class RequestBudget:
    def __init__(self, maximum: int):
        self.maximum = max(0, maximum)
        self.used = 0

    def consume(self) -> bool:
        if self.used >= self.maximum:
            return False
        self.used += 1
        return True

    @property
    def remaining(self) -> int:
        return max(0, self.maximum - self.used)
