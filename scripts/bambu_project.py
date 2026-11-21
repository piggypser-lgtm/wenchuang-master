"""Offline Bambu project adapter. No printer connection or print-send command.
Python 3.10+, standard library. See references/bambu-adapter.md.
"""
from __future__ import annotations
import argparse
from collections import Counter
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from bambu_3mf import (
    Bambu3MFError, SUPPORTED_VERSION, inspect_project, prepare_project,
    compare_projects, compare_project_inventories, make_preview,
)

PACKAGE = Path(__file__).resolve().parents[1]


def writable_destination(path: Path) -> Path:
    path = path.resolve()
    if path.is_relative_to(PACKAGE):
        raise Bambu3MFError("Write project outputs outside the installed skill directory.")
    return path


def write_json(path: Path, value: dict, *, replace: bool = False) -> None:
    path = writable_destination(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w" if replace else "x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def executable_version(path: Path) -> str:
    """Read Windows file metadata, without executing the application."""
    if os.name != "nt":
        raise Bambu3MFError("The CLI version probe requires Windows; have the agent use the local Bambu Studio interface.")
    from ctypes import wintypes
    lib = ctypes.WinDLL("version", use_last_error=True)
    lib.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    lib.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    lib.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    lib.GetFileVersionInfoW.restype = wintypes.BOOL
    lib.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    lib.VerQueryValueW.restype = wintypes.BOOL
    unused = wintypes.DWORD()
    size = lib.GetFileVersionInfoSizeW(str(path), ctypes.byref(unused))
    if not size:
        raise Bambu3MFError("Cannot read Bambu executable version.")
    buffer = ctypes.create_string_buffer(size)
    if not lib.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise Bambu3MFError("Cannot read Bambu executable version data.")
    pointer, length = ctypes.c_void_p(), wintypes.UINT()
    if not lib.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)) or length.value < 52:
        raise Bambu3MFError("Missing fixed executable version information.")
    data = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD * 13)).contents
    if data[0] != 0xFEEF04BD:
        raise Bambu3MFError("Invalid executable version signature.")
    return ".".join(f"{n:02d}" for n in (data[2] >> 16, data[2] & 65535, data[3] >> 16, data[3] & 65535))


def resolve_executable(path: Path) -> Path:
    exe = path.resolve(strict=True)
    if not exe.is_file() or exe.name.lower() not in ("bambu-studio.exe", "bambustudio", "bambu-studio"):
        raise Bambu3MFError("Provide the actual Bambu Studio executable, not a shell or wrapper.")
    return exe


def probe_slice_options(exe: Path, run: Path, env: dict, timeout: float) -> dict:
    """Inspect the installed CLI. Some Windows GUI builds return empty help."""
    options = {"--arrange", "--slice", "--export-3mf", "--outputdir"}
    try:
        help_process = subprocess.run([str(exe), "--help"], cwd=run, env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      timeout=min(timeout, 15), check=False,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "help_unavailable", "reason": str(exc)}
    data = help_process.stdout or b""
    (run / "cli-help.log").write_bytes(data)
    encoding = "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    help_text = data.decode(encoding, errors="replace")
    listed = set(re.findall(r"(?m)^[ \t]*(?:-[\w?][,|]?[ \t]+)?(--[\w-]+)", help_text))
    if not listed:
        return {"status": "help_unavailable", "exit_code": help_process.returncode}
    missing = sorted(options - listed)
    return {"status": "missing_options" if missing else "options_listed",
            "missing_options": missing, "exit_code": help_process.returncode}


def selected_plates(value: str, inventory: dict) -> list[int]:
    ids = sorted(int(p["id"]) for p in inventory["plates"])
    if not ids or len(ids) != len(set(ids)):
        raise Bambu3MFError("Project plate identifiers are empty or ambiguous.")
    if value == "all":
        return ids
    if not re.fullmatch(r"[1-9][0-9]*", value) or int(value) not in ids:
        raise Bambu3MFError("Select 'all' explicitly or one existing positive plate ID.")
    return [int(value)]


def classify_slice_differences(comparison: dict, inventory: dict, expected: list[int],
                               *, source_inventory: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Keep an audit of expected derived additions; unknown changes need review."""
    issues, observations = [], []
    new_members = {f"Metadata/plate_{p}.{suffix}" for p in expected for suffix in ("gcode", "gcode.md5", "json")}
    for item in comparison.get("differences", []):
        category, path = item.get("category"), item.get("path", "")
        expected_change = False
        if category == "gcode" and path == "/gcode" and item.get("before") == []:
            expected_change = True  # Content, coverage and checksums are checked separately.
        elif category == "member_bytes" and path.startswith("/members/"):
            member = path.removeprefix("/members/")
            expected_change = (member in new_members and item.get("before_present") is False)
            if member in ("Metadata/slice_info.config", "Metadata/slice_info.config/size", "Metadata/slice_info.config/sha256"):
                expected_change = True  # Auxiliary metadata is validated separately.
            if member in ("Metadata/project_settings.config/size", "Metadata/project_settings.config/sha256"):
                expected_change = True  # The complete parsed settings differences remain issues.
        elif category == "plate":
            match = re.fullmatch(r"/plates/([0-9]+)/metadata/gcode_file", path)
            if match and item.get("before_present") is False:
                index = int(match[1])
                if index < len(inventory["plates"]):
                    plate = int(inventory["plates"][index]["id"])
                    expected_change = plate in expected and item.get("after") == f"Metadata/plate_{plate}.gcode"
        entry = {"kind": "derived_output_difference" if expected_change else "output_difference", "detail": item}
        # A /plates/N path uses an array position; N is not the plate ID.
        match = re.match(r"^/plates/(\d+)(?:/|$)", path) if category == "plate" else None
        if match and source_inventory is not None:
            pos = int(match[1])
            prior, current = source_inventory["plates"], inventory["plates"]
            if pos < len(prior) and pos < len(current) and str(prior[pos]["id"]) == str(current[pos]["id"]):
                entry["plate"] = int(current[pos]["id"])
        (observations if expected_change else issues).append(entry)
    return issues, observations


def review_guidance(finding: dict) -> dict:
    """Describe a finding without suppressing it or deciding to run another slice."""
    kind = finding.get("kind")
    category = "unknown_issue"
    if kind == "derived_output_difference":
        category = "expected_derived_output"
    elif kind == "output_difference":
        detail = finding.get("detail", {})
        difference_type, path = detail.get("category"), detail.get("path", "")
        if difference_type == "global" or (difference_type == "object" and
                "/metadata/" in path and not path.endswith("/metadata/name")):
            category = "configuration_blocker"
        elif difference_type in ("geometry", "gcode", "role"):
            category = "path_integrity_blocker"
        else:
            # Different archive bytes or object IDs do not prove changed geometry.
            category = "unknown_difference"
    elif kind in ("missing_output", "slicer_result", "plate_coverage", "gcode_coverage",
                  "gcode_md5", "gcode_version", "missing_motion_or_extrusion",
                  "standalone_gcode_mismatch", "invalid_output", "input_inventory_mismatch"):
        category = "path_integrity_blocker"
    elif kind in ("missing_printer_model_id", "missing_slice_metadata", "slice_metadata_coverage"):
        category = "send_metadata_gap"
    elif kind in ("invalid_total_estimate", "invalid_first_layer_time"):
        category = "auxiliary_statistic"
    elif kind == "slicer_warning":
        category = "slicer_warning"
    elif kind == "version_compatibility_trial":
        category = "compatibility_review"
    guidance = {
        "compatibility_review": (
            ["slice_review", "print_send"],
            "Compare the accepted setup with the actual output and inspect this run's toolpaths in the installed Studio. "
            "Record what worked for this exact version and project before asking for acceptance."),
        "configuration_blocker": (
            ["configuration_review", "slice_review", "print_send"],
            "Identify the effective setting and scope against the accepted configuration. "
            "Re-slice only after a justified correction; repeated drift needs a verified fallback, not the same retry."),
        "path_integrity_blocker": (
            ["slice_review", "print_send"],
            "Locate the input, coverage or path-integrity failure before accepting or sending. "
            "Correct the identified cause before deciding whether new slicing is necessary."),
        "send_metadata_gap": (
            ["print_send"],
            "Verify the missing or conflicting handoff data against this run and the target device. "
            "Regenerate the formal artifact only when needed for a valid handoff; a metadata gap alone does not prove bad paths."),
        "auxiliary_statistic": (
            ["estimate_reporting"],
            "Cross-check this run's available estimates and preview; mark unverifiable values unknown. "
            "Do not re-slice solely to clear an auxiliary statistic, and do not infer path failure from it."),
        "slicer_warning": (
            ["slice_review", "print_send"],
            "Read the full warning, locate affected objects and determine its impact. "
            "An unclassified warning is not harmless; do not retry slicing without a diagnosed cause or correction."),
        "unknown_difference": (
            ["slice_review", "print_send"],
            "Compare the changed data and its actual scope. Keep the difference unresolved until explained; "
            "do not infer damaged geometry from changed bytes or re-slice merely to remove the difference."),
        "expected_derived_output": (
            [], "Retain this derived-output audit; separate path, configuration and metadata checks still apply."),
        "unknown_issue": (
            ["slice_review", "print_send"],
            "Determine this unclassified finding's impact before acceptance or sending. "
            "Do not treat it as harmless or repeat slicing without new evidence."),
    }
    stages, action = guidance[category]
    return {**finding, "category": category, "affected_stages": stages,
            "recommended_action": action}


def with_review_guidance(report: dict) -> dict:
    """Schema 2 adds guidance; legacy findings, differences and exit rules remain intact."""
    result = dict(report)
    counts = {}
    for group in ("issues", "observations"):
        result[group] = [review_guidance(item) for item in report.get(group, [])]
        counts[group] = {}
        for item in result[group]:
            name = item["category"]
            counts[group][name] = counts[group].get(name, 0) + 1
    result["verification_schema"] = 2
    result["review_summary"] = {
        "counts_by_category": counts,
        "automatic_reslice": False,
        "next_action": "Review each finding by impact and inspect the actual paths. "
                       "needs_review requests diagnosis, not automatic re-slicing; GUI preview and user acceptance remain required.",
    }
    return result


def issue_id_ranges(ids: list[int]) -> list[str]:
    ranges = []
    start = end = ids[0]
    for value in ids[1:]:
        if value == end + 1:
            end = value
        else:
            ranges.append(str(start) if start == end else f"{start}-{end}")
            start = end = value
    ranges.append(str(start) if start == end else f"{start}-{end}")
    return ranges


def issue_index(issues: list[dict], *, full: bool = False) -> dict:
    """Navigation over original 1-based issue rows. Never changes their disposition."""
    groups = {}
    changes = []
    for number, issue in enumerate(issues, 1):
        category = issue.get("category") or review_guidance(issue)["category"]
        detail = issue.get("detail") or {}
        path = detail.get("path")
        key = (category, issue.get("kind"), detail.get("category"), issue.get("plate"))
        if key not in groups:
            groups[key] = ([], path)
        groups[key][0].append(number)
        if category == "configuration_blocker":
            change = {"id": number, "path": path}
            if not full and path and len(path) > 180:
                change["path"] = path[:177] + "..."
            for field in ("before", "after"):
                if field not in detail:
                    continue
                value = detail[field]
                if len(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) <= 160:
                    change[field] = value
                else:
                    change.setdefault("read_from_issue", []).append(field)
            for flag in ("before_present", "after_present"):
                if flag in detail:
                    change[flag] = detail[flag]
            changes.append(change)
    rows = []
    for (category, kind, family, plate), (ids, path) in groups.items():
        ranges = issue_id_ranges(ids)
        row = {"category": category, "kind": kind, "field_family": family, "plate": plate,
               "count": len(ids), "issue_ids": ",".join(ranges if full else ranges[:12])}
        if not full and len(ranges) > 12:
            row["omitted_ranges"] = len(ranges) - 12
        if path is not None:
            row["sample_path"] = path if full or len(path) <= 180 else path[:177] + "..."
        rows.append(row)
    result = {"issue_count": len(issues), "groups": rows if full else rows[:24],
              "configuration_changes": changes if full else changes[:24]}
    if len(result["groups"]) < len(rows):
        result["omitted_groups"] = len(rows) - len(result["groups"])
    if len(result["configuration_changes"]) < len(changes):
        result["omitted_configuration_changes"] = len(changes) - len(result["configuration_changes"])
    return result


def read_review(path: Path, number: int | None, full: bool) -> dict:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    issues = report.get("issues") if isinstance(report, dict) else None
    if not isinstance(issues, list) or any(not isinstance(i, dict) or not isinstance(i.get("detail", {}), dict)
                                           for i in issues):
        raise Bambu3MFError("Expected a verification report with its original issues array.")
    if number is not None:
        if not 1 <= number <= len(issues):
            raise Bambu3MFError("Issue ID is outside this report's 1-based issues array.")
        return {"id": number, "issue": issues[number - 1]}
    return issue_index(issues, full=full)


def validate_slice(snapshot: Path, output: Path, expected: list[int], version: str,
                   *, snapshot_inventory: dict | None = None) -> dict:
    """A clean result still requires GUI preview and user acceptance."""
    issues: list[dict] = []
    result_file, archive = output / "result.json", output / "sliced.3mf"
    if not result_file.is_file() or not archive.is_file():
        return with_review_guidance({"issues": [{"kind": "missing_output", "message": "result.json or sliced.3mf is missing"}]})
    try:
        result = json.loads(result_file.read_text(encoding="utf-8-sig"))
        json.dumps(result, allow_nan=False)  # Reject non-finite literals and overflow before storing reports.
        if not isinstance(result, dict):
            raise ValueError("result.json must contain an object")
        if result.get("return_code") != 0:
            issues.append({"kind": "slicer_result", "message": str(result.get("error_string", result))})
        plates = result.get("sliced_plates", [])
        actual = [int(p["id"]) for p in plates]
        if sorted(actual) != sorted(expected):
            issues.append({"kind": "plate_coverage", "expected": expected, "actual": actual})
        for plate in plates:
            if plate.get("warning_message"):
                issues.append({"kind": "slicer_warning", "plate": plate["id"], "message": plate["warning_message"]})
            t = plate.get("total_predication")
            if not isinstance(t, (int, float)) or not math.isfinite(t) or t <= 0:
                issues.append({"kind": "invalid_total_estimate", "plate": plate["id"]})
        if snapshot_inventory is None:
            snapshot_inventory = inspect_project(snapshot)
        elif snapshot_inventory.get("sha256") != hashlib.sha256(snapshot.read_bytes()).hexdigest():
            issues.append({"kind": "input_inventory_mismatch",
                           "message": "The reused inventory does not match the current accepted snapshot."})
            return with_review_guidance({"issues": issues})
        inventory = inspect_project(archive)
        difference = compare_project_inventories(snapshot_inventory, inventory)
        changed, observations = classify_slice_differences(difference, inventory, expected, source_inventory=snapshot_inventory)
        issues.extend(changed)
        gcode_reports = []
        with zipfile.ZipFile(archive) as z:
            names = z.namelist()
            found_ids = sorted(int(m[1]) for n in names if (m := re.fullmatch(r"Metadata/plate_([0-9]+)\.gcode", n)))
            if found_ids != sorted(expected):
                issues.append({"kind": "gcode_coverage", "expected": expected, "actual": found_ids})
            for plate in expected:
                name = f"Metadata/plate_{plate}.gcode"
                if name not in names:
                    continue
                content = z.read(name)
                md5_name = name + ".md5"
                sha = hashlib.sha256(content).hexdigest()
                md5_ok = md5_name in names and z.read(md5_name).decode("ascii").strip().lower() == hashlib.md5(content).hexdigest()
                if not md5_ok:
                    issues.append({"kind": "gcode_md5", "plate": plate})
                producer = re.search(rb"\bBambuStudio\s+(\d+\.\d+\.\d+\.\d+)(?![\w.+-])", content[:4096])
                if not producer or list(map(int, producer[1].split(b"."))) != list(map(int, version.split("."))):
                    issues.append({"kind": "gcode_version", "plate": plate})
                if not re.search(rb"(?m)^G[01]\s+[^\r\n]*[XY][\-0-9.]+", content) or not re.search(rb"(?m)^G[01]\s+[^\r\n]*E[\-0-9.]+", content):
                    issues.append({"kind": "missing_motion_or_extrusion", "plate": plate})
                standalone = output / f"plate_{plate}.gcode"
                if standalone.exists() and standalone.read_bytes() != content:
                    issues.append({"kind": "standalone_gcode_mismatch", "plate": plate})
                gcode_reports.append({"plate": plate, "bytes": len(content), "sha256": sha, "md5_valid": md5_ok})
            slice_info = "Metadata/slice_info.config"
            if slice_info not in names:
                issues.append({"kind": "missing_slice_metadata"})
            else:
                raw = z.read(slice_info)
                if re.search(rb"<!\s*(DOCTYPE|ENTITY)", raw, re.I):
                    raise Bambu3MFError("DTD/entity declarations are not supported.")
                meta = ET.fromstring(raw)
                totals = {int(p["id"]): p.get("total_predication") for p in plates}
                metadata_ids = []
                for node in meta.findall("plate"):
                    md = {m.get("key"): m.get("value") for m in node.findall("metadata")}
                    plate = int(md["index"])
                    metadata_ids.append(plate)
                    if plate not in expected:
                        continue
                    if not md.get("printer_model_id"):
                        issues.append({"kind": "missing_printer_model_id", "plate": plate})
                    try:
                        first, total = float(md["first_layer_time"]), float(totals[plate])
                        if not math.isfinite(first) or first <= 0 or first > total:
                            raise ValueError("Invalid first layer estimate")
                    except (ValueError, TypeError, KeyError):
                        issues.append({"kind": "invalid_first_layer_time", "plate": plate, "raw_value": md.get("first_layer_time")})
                selected_metadata_ids = [p for p in metadata_ids if p in expected]
                if sorted(selected_metadata_ids) != sorted(expected):
                    issues.append({"kind": "slice_metadata_coverage", "expected": expected, "actual": selected_metadata_ids})
        return with_review_guidance({"issues": issues, "observations": observations, "result": result,
                                     "configuration_comparison": difference, "gcode": gcode_reports,
                                     "output_sha256": inventory["sha256"]})
    except (Bambu3MFError, ValueError, OSError, KeyError, TypeError, ET.ParseError, zipfile.BadZipFile) as exc:
        issues.append({"kind": "invalid_output", "message": str(exc)})
        return with_review_guidance({"issues": issues})


def run_slice(args: argparse.Namespace) -> tuple[dict, int]:
    source = args.input.resolve(strict=True)
    payload = source.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if not re.fullmatch(r"[a-fA-F0-9]{64}", args.accepted_sha256) or digest != args.accepted_sha256.lower():
        raise Bambu3MFError("Input differs from the declared accepted SHA-256; do not slice.")
    exe = resolve_executable(args.bambu)
    version = executable_version(exe)
    run = writable_destination(args.run_dir)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        raise Bambu3MFError("Timeout must be a finite positive number.")
    # mkdir is the run reservation: even an existing empty directory is rejected.
    run.mkdir(parents=True, exist_ok=False)
    snapshot = run / "accepted-input.3mf"
    snapshot.write_bytes(payload)
    info = inspect_project(snapshot)
    if info["sha256"] != digest:
        raise Bambu3MFError("Snapshot inspection differs from the accepted input SHA-256.")
    if info["preview_marker"] is not None:
        raise Bambu3MFError("A preview-only package cannot be used for slicing.")
    if info.get("gcode"):
        raise Bambu3MFError("Use an accepted unsliced project; stale G-code is not allowed.")
    project_version = info["version"]
    if (info["file_role"] != "editable_project" or not isinstance(project_version, str)
            or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}", project_version)
            or info.get("application") != ["BambuStudio-" + project_version]):
        raise Bambu3MFError("Slice requires an unsliced editable Bambu Studio project with consistent "
                            "application and version metadata. Have the agent inspect a native copy in Studio.")
    trial = version != SUPPORTED_VERSION or project_version != SUPPORTED_VERSION
    expected = selected_plates(args.plates, info)
    output, temp = run / "output", run / "temp"
    output.mkdir(); temp.mkdir()
    command = [str(exe), "--arrange", "0", "--slice", "0" if args.plates == "all" else str(expected[0]),
               "--export-3mf", "sliced.3mf", "--outputdir", str(output), str(snapshot)]
    state = {"command": command, "input_source": str(source), "input_snapshot": str(snapshot),
             "input_sha256": digest, "executable_version": version, "project_version": project_version,
             "compatibility_trial": trial, "selected_plates": expected,
             "status": "starting", "print_send_supported": False, "print_sent": False,
             "acceptance": "Caller declares this exact input accepted; the flag does not prove user consent.",
             "gui_preview": "not_verified", "user_result_acceptance": "not_verified"}
    manifest = run / "run.json"
    write_json(manifest, state)
    env = os.environ.copy()
    env["TEMP"] = env["TMP"] = env["TMPDIR"] = str(temp)
    if version != SUPPORTED_VERSION:
        probe = probe_slice_options(exe, run, env, args.timeout)
        state["cli_probe"] = probe
        if probe["status"] == "missing_options":
            state.update(status="cli_options_missing", next_action=(
                "Have the agent check the installed CLI syntax or operate Studio on a copy "
                "within the approved plate and settings scope."))
            write_json(manifest, state, replace=True)
            return state, 2
        # A GUI binary may expose no help. The isolated slice and its artifacts are the actual test.
        write_json(manifest, state, replace=True)
    started = time.monotonic()
    with (run / "stdout.log").open("wb") as out, (run / "stderr.log").open("wb") as err:
        try:
            process = subprocess.Popen(command, cwd=run if trial else exe.parent, env=env, stdout=out, stderr=err,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            state.update({"pid": process.pid, "status": "running"})
            write_json(manifest, state, replace=True)
            try:
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                state.update({"status": "timeout_check_existing_process", "process_may_be_running": process.poll() is None,
                              "elapsed_seconds": round(time.monotonic()-started, 3),
                              "next_action": "Inspect this PID and directory before any retry; no automatic retry or termination."})
                write_json(manifest, state, replace=True)
                return state, 4
        except OSError as exc:
            state.update({"status": "launch_failed", "error": str(exc)})
            write_json(manifest, state, replace=True)
            return state, 4
    state.update({"exit_code": code, "elapsed_seconds": round(time.monotonic()-started, 3)})
    if code != 0:
        state["status"] = "process_failed"
        write_json(manifest, state, replace=True)
        return state, 4
    verification = validate_slice(snapshot, output, expected, version, snapshot_inventory=info)
    if trial:
        trial_issue = {"kind": "version_compatibility_trial", "project_version": project_version,
                       "executable_version": version}
        verification = with_review_guidance({**verification, "issues": [*verification["issues"], trial_issue]})
    write_json(run / "verification.json", verification)
    state["counts_by_category"] = verification["review_summary"]["counts_by_category"]
    if verification["issues"]:
        state["issue_index"] = issue_index(verification["issues"])
    state.update({"status": "needs_review" if verification["issues"] else "generated_pending_preview",
                  "issue_count": len(verification["issues"]), "verification": str(run / "verification.json"),
                  "output": str(output / "sliced.3mf")})
    write_json(manifest, state, replace=True)
    return state, 3 if verification["issues"] else 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("inspect", "open"):
        c = commands.add_parser(name)
        c.add_argument("--input", type=Path, required=True)
        c.add_argument("--report", type=Path)
        if name == "open":
            c.add_argument("--bambu", type=Path, required=True)
            c.add_argument("--mode", choices=("project", "preview"), required=True)
    c = commands.add_parser("prepare")
    c.add_argument("--input", type=Path, required=True)
    c.add_argument("--output", type=Path, required=True)
    c.add_argument("--changes", type=Path, required=True)
    c.add_argument("--report", type=Path)
    c = commands.add_parser("compare")
    c.add_argument("--before", type=Path, required=True)
    c.add_argument("--after", type=Path, required=True)
    c.add_argument("--report", type=Path)
    c = commands.add_parser("preview")
    c.add_argument("--input", type=Path, required=True)
    c.add_argument("--output", type=Path, required=True)
    c.add_argument("--report", type=Path)
    c = commands.add_parser("review", help="Read a grouped issue index or one exact issue from verification.json.")
    c.add_argument("--input", type=Path, required=True)
    detail = c.add_mutually_exclusive_group()
    detail.add_argument("--issue", type=int, help="Read an original issue by its 1-based ID.")
    detail.add_argument("--all", action="store_true", help="Include every group and all ID ranges.")
    c = commands.add_parser("slice")
    c.add_argument("--input", type=Path, required=True)
    c.add_argument("--bambu", type=Path, required=True)
    c.add_argument("--run-dir", type=Path, required=True)
    c.add_argument("--accepted-sha256", required=True)
    c.add_argument("--plates", required=True, help="'all' or one existing positive plate ID")
    c.add_argument("--timeout", type=float, default=600)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        code = 0
        report = getattr(args, "report", None)
        if report is not None:
            report = writable_destination(report)
            if report.exists():
                raise Bambu3MFError("Report already exists; choose a new path.")
        if args.command == "inspect":
            result = inspect_project(args.input)
            summary = {"status": "inspected", "version": result["version"], "sha256": result["sha256"],
                       "file_role": result["file_role"],
                       "objects": len(result["objects"]), "plates": len(result["plates"]),
                       "plate_ids": [plate["id"] for plate in result["plates"]],
                       "geometry_equivalence_unverified": result["geometry_equivalence_unverified"],
                       "gcode_files": len(result.get("gcode", [])),
                       "supported_for_mutation": result["supported_for_mutation"]}
        elif args.command == "review":
            summary = read_review(args.input, args.issue, args.all)
        elif args.command == "prepare":
            output = writable_destination(args.output)
            plan = json.loads(args.changes.read_text(encoding="utf-8-sig"))
            if not isinstance(plan, list) or not plan:
                raise Bambu3MFError("Changes must be a nonempty JSON list with explicit from/to values.")
            result = prepare_project(args.input, output, plan)
            summary = {"status": "prepared_pending_gui_verification", "output": str(output),
                       "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "change_count": len(plan),
                       "full_roundtrip_current_reasons": result["gui_validation"]["full_roundtrip_current_reasons"]}
        elif args.command == "compare":
            result = compare_projects(args.before, args.after)
            code = 0 if result["equal"] else 3
            differences = result["differences"]
            summary = {"status": "equal" if code == 0 else "needs_review", "difference_count": len(differences),
                       "difference_counts_by_category": dict(Counter(item["category"] for item in differences)),
                       "geometry_equivalence_verified": result["geometry_equivalence_verified"],
                       "geometry_equivalence_unverified": result["geometry_equivalence_unverified"]}
        elif args.command == "preview":
            result = make_preview(args.input, writable_destination(args.output))
            summary = {"status": "preview_package_created_pending_gui", "output": str(args.output.resolve()),
                       "preview_only": True, "print_send_supported": False}
        elif args.command == "open":
            source = args.input.resolve(strict=True)
            info = inspect_project(source)
            role = info["file_role"]
            if args.mode == "project" and role not in ("editable_project", "mixed_project"):
                raise Bambu3MFError(f"File role {role}: project mode requires editable geometry, plate instances "
                                    "and project settings. Open the source project to change material or parameters.")
            if args.mode == "preview" and role not in ("sliced_toolpath", "preview_copy"):
                raise Bambu3MFError(f"File role {role}: preview mode requires a pure sliced/viewing package. "
                                    "A mixed project's existing paths require independent preview verification.")
            exe = resolve_executable(args.bambu)
            proc = subprocess.Popen([str(exe), str(source)], cwd=exe.parent)
            result = {"status": "launch_requested", "pid": proc.pid, "mode": args.mode, "file_role": role, "input": str(source),
                      "loaded_or_previewed": "not_verified", "print_sent": False}
            summary = result.copy()
        else:
            result, code = run_slice(args)
            keys = ("status", "selected_plates", "pid", "elapsed_seconds", "issue_count",
                    "counts_by_category", "issue_index", "verification", "output", "compatibility_trial",
                    "cli_probe", "next_action")
            summary = {k: result[k] for k in keys if k in result}
            summary["run_manifest"] = str(args.run_dir.resolve() / "run.json")
        if report is not None:
            write_json(report, result)
            summary["report"] = str(report)
        print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
        return code
    except (Bambu3MFError, ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc), "print_sent": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
