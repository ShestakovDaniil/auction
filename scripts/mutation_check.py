"""Real mutation smoke test: change the bid increment rule and demand pytest red."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


TARGET = "return current_highest + min_increment"
MUTATION = "return current_highest - min_increment"


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="auction-mutation-") as temp:
        isolated = Path(temp)
        shutil.copytree(root / "app", isolated / "app", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(root / "tests", isolated / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        source = isolated / "app" / "domain.py"
        original = source.read_text(encoding="utf-8")
        if original.count(TARGET) != 1:
            raise RuntimeError("Expected domain rule not found; review mutation check")
        source.write_text(original.replace(TARGET, MUTATION), encoding="utf-8")
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_domain.py", "-q", "-o", "addopts="],
            cwd=isolated, env=env, capture_output=True, text=True, check=False,
        )
        result = process.stdout + process.stderr
        if process.returncode == 0 or "FAILED tests/test_domain.py::test_bid_minimum" not in result:
            print(result)
            raise RuntimeError("Мутация шага ставки НЕ была обнаружена тестами")
        print("Мутационный тест пройден: изменение '+' на '-' вызвало падение тестов минимальной ставки.")


if __name__ == "__main__":
    main()
