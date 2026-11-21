"""检查公开技能包并按明确清单生成 ZIP；仅使用 Python 标准库。"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

CONTACT_QR = "assets/wechat-qr.jpg"

RELEASE_FILES = (
    ".gitignore", "LICENSE", "README.md", "SKILL.md", "WORKFLOW.md",
    "agents/openai.yaml", "assets/project-config.example.json", CONTACT_QR,
    "references/setup.md", "references/products.md", "references/blender.md",
    "references/bambu.md", "references/project-record.md",
    "references/design-rules.md", "references/feasibility.md",
    "references/multiview-design.md", "references/interaction.md",
    "references/parameter-research.md",
    "references/co-design.md", "references/product-library.md",
    "references/desktop-digital-accessories.md",
    "references/tripo.md", "references/resource-library.md",
    "references/parametric-structures.md", "references/fidget-edc.md",
    "references/mechanism-reuse.md", "references/mechanism-library.md",
    "references/toy-mechanisms.md", "references/mechanism-candidates.md",
    "references/modeling-plan.md", "references/slicing-parameters.md",
    "references/hybrid-modeling.md", "references/slicing-automation.md",
    "references/modeling-tools.md", "references/sand3d.md", "references/bambu-adapter.md",
    "assets/bambu-changes.example.json",
    "scripts/bambu_3mf.py", "scripts/bambu_project.py",
    "scripts/tests/test_bambu_3mf.py", "scripts/tests/test_bambu_project.py",
    "scripts/check_package.py", "scripts/tests/test_check_package.py",
    "scripts/read_feasibility.py", "scripts/read_stage.py", "scripts/tests/test_read_feasibility.py",
)
# 只识别常见本机信息；不能替代发布者的人工审查。
PRIVATE_PATTERNS = (
    ("Windows 绝对路径", re.compile(r"\b[A-Za-z]:[\\/]")),
    ("用户主目录绝对路径", re.compile(r"/(?:Users|home)/[^\s/]+/")),
    ("私有聊天链接", re.compile(r"codex://threads/[0-9a-f-]{16,}", re.I)),
)


class ImageSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "img":
            self.sources.extend(value for key, value in attrs if key == "src" and value)


def check(root: Path) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    root = root.resolve()
    for name in RELEASE_FILES:
        path = root / name
        if not path.is_file():
            errors.append(f"缺少发布文件：{name}")
            continue
        if not path.resolve().is_relative_to(root):
            errors.append(f"发布文件指向包外：{name}")
            continue
        try:
            if name == CONTACT_QR:
                image = path.read_bytes()
                scan = image.find(b"\xff\xda", 3)
                if not image.startswith(b"\xff\xd8\xff") or scan < 0 or image.find(b"\xff\xd9", scan + 2) < 0:
                    errors.append(f"二维码文件缺少完整 JPEG 起止标记：{name}")
                continue
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"发布文件无法读取：{name}（{type(exc).__name__}）")
            continue
        except UnicodeError as exc:
            errors.append(f"文件不可作为 UTF-8 文本读取：{name}（{type(exc).__name__}）")
            continue
        for label, pattern in PRIVATE_PATTERNS:
            if pattern.search(content):
                errors.append(f"发现{label}：{name}；请在本地审查内容")
        if path.suffix == ".md":
            images = ImageSources()
            images.feed(content)
            images.close()
            targets = re.findall(r"\]\(([^)]+)\)", content) + images.sources
            for target in targets:
                target = target.strip().strip("<>").split("#", 1)[0]
                if not target or target.startswith(("https://", "http://", "mailto:")):
                    continue
                dest = (path.parent / unquote(target)).resolve()
                if not dest.is_relative_to(root):
                    errors.append(f"Markdown 引用超出技能包：{name}")
                elif not dest.is_file():
                    errors.append(f"Markdown 引用的文件不存在：{name} -> {target}")
                elif dest.relative_to(root).as_posix() not in RELEASE_FILES:
                    errors.append(f"Markdown 引用的文件未列入发布清单：{name} -> {target}")
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if ".git" in rel.parts or "__pycache__" in rel.parts or not path.is_file():
            continue
        if path.name.endswith(".local.json") or path.name == ".env" or path.name.startswith(".env."):
            errors.append("技能目录含个人配置或凭据文件；请移到项目目录")
        elif rel.as_posix() not in RELEASE_FILES:
            warnings.append(f"不在发布清单中，ZIP 将排除：{rel.as_posix()}")
    try:
        config = json.loads((root / "assets/project-config.example.json").read_text(encoding="utf-8"))
        if config["config_version"] != 1:
            errors.append("配置模板版本不受支持")
        if any(v not in (None, []) for v in config["printer"].values()):
            errors.append("公开模板包含设备或材料默认值")
        if any(v is not None for section in ("blender", "bambu_studio") for v in config[section].values()):
            errors.append("公开模板包含本机执行路径或控制方式")
        output = Path(config["output_dir"])
        if output.is_absolute() or ".." in output.parts:
            errors.append("模板输出目录必须是项目内相对路径")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(f"配置模板无法读取：{type(exc).__name__}")
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="技能包根目录")
    parser.add_argument("--zip", type=Path, help="可选：包目录外的 ZIP 输出位置")
    parser.add_argument("--overwrite", action="store_true", help="已获授权时，校验临时包后覆盖指定 ZIP")
    args = parser.parse_args()
    if args.overwrite and not args.zip:
        parser.error("--overwrite 必须与 --zip 一起使用")
    root = args.root.resolve()
    errors, warnings = check(root)
    for warning in warnings:
        print("提示：" + warning)
    if errors:
        for error in errors:
            print("错误：" + error, file=sys.stderr)
        return 1
    if args.zip:
        archive = args.zip.resolve()
        if archive.is_relative_to(root):
            print("错误：ZIP 必须位于技能包之外", file=sys.stderr)
            return 1
        if archive.exists() and not args.overwrite:
            print("错误：ZIP 已存在；经授权覆盖时使用 --overwrite", file=sys.stderr)
            return 1
        archive.parent.mkdir(parents=True, exist_ok=True)
        if args.overwrite:
            fd, temporary_name = tempfile.mkstemp(prefix=archive.stem + "-", suffix=".tmp", dir=archive.parent)
            os.close(fd)
            temporary = Path(temporary_name)
            try:
                with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as z:
                    for name in RELEASE_FILES:
                        z.write(root / name, "wenchuang-master/" + name)
                with zipfile.ZipFile(temporary) as z:
                    if z.testzip() is not None:
                        raise ValueError("临时发布包校验失败")
                    for name in RELEASE_FILES:
                        if z.read("wenchuang-master/" + name) != (root / name).read_bytes():
                            raise ValueError("发布源在打包时发生变化：" + name)
                os.replace(temporary, archive)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
                for name in RELEASE_FILES:
                    z.write(root / name, "wenchuang-master/" + name)
        print("发布包已创建或更新：" + str(archive))
    print(f"检查通过：{len(RELEASE_FILES)} 个发布文件；未执行建模、切片或打印。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
