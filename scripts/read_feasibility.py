"""Read the four feasibility criteria from the skill, independently of the terminal code page."""

from pathlib import Path
from read_stage import print_section, read_section


HEADING = "## 分别评估外观、功能、整合与制造"
SOURCE = Path(__file__).resolve().parents[1] / "references" / "feasibility.md"


def read_criteria(source):
    return read_section(source, HEADING)


def main():
    return print_section(SOURCE, HEADING)


if __name__ == "__main__":
    raise SystemExit(main())
