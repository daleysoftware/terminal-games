import subprocess
import sys
import unittest
from pathlib import Path


class MainTest(unittest.TestCase):
    def test_main_exits_successfully_without_output(self) -> None:
        game = Path(__file__).resolve().parents[1] / "main.py"
        result = subprocess.run(
            [sys.executable, str(game)], capture_output=True, text=True, check=False
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
