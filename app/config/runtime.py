from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.enums import DeliveryMode


@dataclass(slots=True)
class RuntimeOptions:
    mode: DeliveryMode | None = None
    source_keys: tuple[str, ...] = field(default_factory=tuple)
    dry_run: bool = False

