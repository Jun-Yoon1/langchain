from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")


@dataclass
class ApiCallLimiter:
    max_calls_per_api: int = 2
    _counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def check(self, api_name: str) -> None:
        if self._counts[api_name] >= self.max_calls_per_api:
            raise RuntimeError(f"{api_name} API call limit exceeded")
        self._counts[api_name] += 1

    def run(self, api_name: str, func: Callable[[], T]) -> T:
        self.check(api_name)
        return func()

    def reset(self) -> None:
        self._counts.clear()

    def snapshot(self) -> dict[str, int]:
        return dict(self._counts)


def create_query_limiter() -> ApiCallLimiter:
    return ApiCallLimiter(max_calls_per_api=2)
