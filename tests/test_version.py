import re
import unittest
from pathlib import Path

from stb_rdc.config import ADAPTER_VERSION


ROOT = Path(__file__).resolve().parents[1]


class VersionTests(unittest.TestCase):
    def test_readme_and_changelog_match_runtime_version(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"当前版本为 `{ADAPTER_VERSION}`", readme)
        self.assertRegex(changelog, rf"(?m)^## v{re.escape(ADAPTER_VERSION)}\b")


if __name__ == "__main__":
    unittest.main()
