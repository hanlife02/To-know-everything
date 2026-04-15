import unittest

from app.domain.models import SourceFetchResult
from app.sources.base import SourceAdapter
from app.sources.registry import SourceRegistry


class StubSource(SourceAdapter):
    key = "stub"
    name = "Stub Source"

    def fetch(self) -> SourceFetchResult:
        return SourceFetchResult(source_key=self.key, items=[])


class SourceRegistryTestCase(unittest.TestCase):
    def test_registry_returns_enabled_sources(self) -> None:
        registry = SourceRegistry()
        registry.register(StubSource())

        enabled = registry.enabled()

        self.assertEqual(len(enabled), 1)
        self.assertEqual(enabled[0].key, "stub")


if __name__ == "__main__":
    unittest.main()
