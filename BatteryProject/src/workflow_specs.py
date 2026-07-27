"""Shared configuration contracts for canonical workflow notebooks."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .data_registry import HITHIUM_ROOT, query_datasets


@dataclass(frozen=True)
class DatasetQuery:
    """Declarative dataset selector used by canonical notebook config cells."""

    cell: str
    temperature_c: float | None = None
    rate: str | None = None
    test_type: str | None = None
    kind: str = "raw"
    format: str | None = None
    path_contains: str | None = None
    require_unique: bool = True

    def resolve(self, root: Path = HITHIUM_ROOT) -> list[dict[str, Any]]:
        """Resolve this selector against datasets.json."""
        return query_datasets(
            root=root,
            cell=self.cell,
            temp=self.temperature_c,
            rate=self.rate,
            test=self.test_type,
            kind=self.kind,
            fmt=self.format,
            path_contains=self.path_contains,
            require_unique=self.require_unique,
        )


@dataclass(frozen=True)
class WorkflowSpec:
    """Base contract shared by all headless canonical workflows."""

    workflow_id: str
    cell: str
    run_mode: str = "smoke"
    output_name: str | None = None
    datasets: tuple[DatasetQuery, ...] = ()
    overrides: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.workflow_id or not self.workflow_id.replace("_", "").isalnum():
            raise ValueError("workflow_id must contain only letters, digits, and underscores")
        if not self.cell:
            raise ValueError("cell is required")
        if self.run_mode not in {"smoke", "study"}:
            raise ValueError("run_mode must be 'smoke' or 'study'")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable configuration snapshot."""
        return asdict(self)
