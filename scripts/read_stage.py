"""Read one stage of the Chinese workflow over a code-page-independent output stream."""

import argparse
import json
from pathlib import Path
import re
import sys


SOURCE = Path(__file__).resolve().parents[1] / "WORKFLOW.md"
STAGES = {
    "rules": "## 逐步确认与上下文使用",
    "1": "### 1. 主体与可行性",
    "2": "### 2. 共创用途，确定参数",
    "3": "### 3. 先确认主视图，再生成其他视图",
    "4": "### 4. 建模、试样与细化",
    "5": "### 5. 按已确认色区拆件，再导出",
    "6": "### 6. 分盘、切片与交付",
    "7": "### 7. 发送打印与实物反馈",
}


def read_section(source, heading):
    depth = len(heading.split(" ", 1)[0])
    lines = []
    with source.open(encoding="utf-8-sig") as doc:
        for line in doc:
            if line.rstrip() == heading:
                break
        else:
            raise ValueError(f"Missing section: {heading}")
        for line in doc:
            next_heading = re.match(r"^(#{1,6}) ", line)
            if next_heading and len(next_heading.group(1)) <= depth:
                break
            lines.append(line)
    body = "".join(lines).strip()
    if not body:
        raise ValueError(f"Empty section: {heading}")
    return heading + "\n\n" + body


def print_section(source, heading):
    try:
        section = read_section(source, heading)
    except (OSError, ValueError) as error:
        print(ascii(str(error)), file=sys.stderr)
        return 1
    print(json.dumps(section, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=STAGES)
    args = parser.parse_args()
    raise SystemExit(print_section(SOURCE, STAGES[args.stage]))
