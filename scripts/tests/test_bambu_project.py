"""Offline CLI boundary tests. No real Bambu process, GUI, or printer is used."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bambu_project as adapter


class AdapterCase(unittest.TestCase):
    def setUp(self):
        # Honor TMP/TEMP supplied by the test runner, outside the skill package.
        self.temp = tempfile.TemporaryDirectory(prefix="bambu-cli-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "accepted source 模型 &.3mf"
        self.source.write_bytes(b"accepted source bytes")
        self.exe = self.root / "Bambu Studio" / "bambu-studio.exe"
        self.exe.parent.mkdir()
        self.exe.write_bytes(b"mock executable; never run")
        self.inventory = {
            "version": adapter.SUPPORTED_VERSION, "application": ["BambuStudio-" + adapter.SUPPORTED_VERSION],
            "sha256": hashlib.sha256(self.source.read_bytes()).hexdigest(),
            "preview_only": False, "preview_marker": None, "file_role": "editable_project",
            "supported_for_mutation": True,
            "geometry_equivalence_unverified": False,
            "objects": [{"id": "1"}],
            "plates": [{"id": 1, "object_ids": ["1"]}, {"id": 2, "object_ids": []}],
            "global_settings": {},
            "gcode": [],
        }

    def args(self, **changes):
        values = dict(input=self.source, bambu=self.exe, run_dir=self.root / "run",
                      accepted_sha256=self.inventory["sha256"], plates="1", timeout=2.0)
        values.update(changes)
        return argparse.Namespace(**values)

    def mocks(self, *, inventory=None, wait=0, verification=None):
        stack = ExitStack()
        self.addCleanup(stack.close)
        inspect = stack.enter_context(patch.object(adapter, "inspect_project", return_value=inventory or self.inventory))
        version = stack.enter_context(patch.object(adapter, "executable_version", return_value=adapter.SUPPORTED_VERSION))
        process = Mock(pid=24680)
        if isinstance(wait, Exception):
            process.wait.side_effect = wait
        else:
            process.wait.return_value = wait
        process.poll.return_value = None
        launch = stack.enter_context(patch.object(adapter.subprocess, "Popen", return_value=process))
        if verification is None:
            verification = adapter.with_review_guidance({"issues": []})
        validate = stack.enter_context(patch.object(adapter, "validate_slice", return_value=verification))
        return inspect, version, process, launch, validate

    def invoke(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = adapter.main(argv)
        return code, out.getvalue(), err.getvalue()

    def make_output(self, *, plates=(1,), metadata=None, result=None, version=None,
                    md5_valid=True, motion=True):
        output = self.root / "validation-output"
        output.mkdir(exist_ok=True)
        if result is None:
            result = {"return_code": 0, "sliced_plates": [
                {"id": i, "total_predication": 120.0, "warning_message": ""} for i in plates]}
        (output / "result.json").write_text(json.dumps(result), encoding="utf-8")
        if metadata is None:
            metadata = "<config>" + "".join(
                f'<plate><metadata key="index" value="{i}"/>'
                '<metadata key="printer_model_id" value="A1"/>'
                '<metadata key="first_layer_time" value="10"/></plate>' for i in plates) + "</config>"
        with zipfile.ZipFile(output / "sliced.3mf", "w") as archive:
            archive.writestr("Metadata/slice_info.config", metadata)
            for plate in plates:
                content = f"; BambuStudio {version or adapter.SUPPORTED_VERSION}\n".encode()
                content += b"G1 X10 Y5 E0.1\n" if motion else b"; no printable paths\n"
                name = f"Metadata/plate_{plate}.gcode"
                archive.writestr(name, content)
                archive.writestr(name + ".md5", hashlib.md5(content).hexdigest() if md5_valid else "0" * 32)
        return output

    def validate_output(self, output, *, expected=None, differences=None):
        with patch.object(adapter, "inspect_project", return_value=self.inventory), patch.object(
                adapter, "compare_project_inventories", return_value={"equal": not differences, "differences": differences or []}):
            return adapter.validate_slice(self.source, output, expected or [1], adapter.SUPPORTED_VERSION)


class SelectionAndParsingTests(AdapterCase):
    def test_explicit_all_and_single_plate(self):
        self.assertEqual(adapter.selected_plates("all", self.inventory), [1, 2])
        self.assertEqual(adapter.selected_plates("2", self.inventory), [2])

    def test_invalid_or_ambiguous_plates(self):
        for value in ("", "0", "-1", "01", "3", "1,2", "1,1", "all --send"):
            with self.subTest(value=value), self.assertRaises(adapter.Bambu3MFError):
                adapter.selected_plates(value, self.inventory)
        for ids in ([], [1, 1]):
            inventory = dict(self.inventory, plates=[{"id": i} for i in ids])
            with self.subTest(ids=ids), self.assertRaises(adapter.Bambu3MFError):
                adapter.selected_plates("all", inventory)

    def test_slice_requires_explicit_acceptance_and_plates(self):
        base = ["slice", "--input", str(self.source), "--bambu", str(self.exe),
                "--run-dir", str(self.root / "run")]
        for argv in (base, base + ["--accepted-sha256", self.inventory["sha256"]],
                     base + ["--plates", "1"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                adapter.parser().parse_args(argv)

    def test_unknown_send_and_extra_options_rejected(self):
        base = ["slice", "--input", str(self.source), "--bambu", str(self.exe),
                "--run-dir", str(self.root / "run"), "--accepted-sha256", self.inventory["sha256"], "--plates", "1"]
        for extra in (["--send"], ["--extra-args", "--arrange 1"], ["--arrange", "1"]):
            with self.subTest(extra=extra), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                adapter.parser().parse_args(base + extra)


class SliceRunTests(AdapterCase):
    def test_hash_mismatch_prevents_launch_and_directory_creation(self):
        _, _, _, launch, _ = self.mocks()
        for digest in ("", "wrong", "0" * 64):
            with self.subTest(digest=digest), self.assertRaises(adapter.Bambu3MFError):
                adapter.run_slice(self.args(accepted_sha256=digest))
        launch.assert_not_called()
        self.assertFalse((self.root / "run").exists())

    def test_new_executable_checks_local_options_and_forces_artifact_review(self):
        _, version, _, launch, validate = self.mocks(
            verification=adapter.with_review_guidance({"issues": [{"kind": "slicer_warning"}]}))
        version.return_value = "02.09.01.71"
        help_text = b"Usage:\n  --arrange N\n  --export-3mf FILE\n  --slice N\n  --outputdir PATH\n"
        with patch.object(adapter.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, help_text)) as help_call:
            state, code = adapter.run_slice(self.args(plates="2"))
        self.assertEqual(help_call.call_args.args[0], [str(self.exe.resolve()), "--help"])
        self.assertEqual(state["cli_probe"]["status"], "options_listed")
        self.assertEqual((state["status"], code, state["compatibility_trial"]), ("needs_review", 3, True))
        self.assertEqual(validate.call_args.args[2:4], ([2], "02.09.01.71"))
        command = launch.call_args.args[0]
        self.assertEqual(command[command.index("--slice") + 1], "2")
        self.assertNotEqual(Path(command[-1]), self.source)
        self.assertEqual(Path(command[-1]).read_bytes(), self.source.read_bytes())
        report = json.loads(Path(state["verification"]).read_text("utf-8"))
        self.assertEqual([item["kind"] for item in report["issues"]], ["slicer_warning", "version_compatibility_trial"])
        self.assertEqual(report["issues"][-1]["category"], "compatibility_review")
        self.assertFalse(state["print_sent"])

    def test_explicit_missing_option_stops_before_slicing(self):
        _, version, _, launch, validate = self.mocks()
        version.return_value = "02.09.01.71"
        listing = b"--arrange N\n--export-3mf FILE\n--slice-all\n--outputdir PATH\n"
        with patch.object(adapter.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, listing)):
            state, code = adapter.run_slice(self.args())
        self.assertEqual((state["status"], code), ("cli_options_missing", 2))
        self.assertEqual(state["cli_probe"]["missing_options"], ["--slice"])
        self.assertIn("agent", state["next_action"])
        launch.assert_not_called()
        validate.assert_not_called()

    def test_silent_windows_gui_help_allows_isolated_trial_without_assuming_success(self):
        _, version, _, launch, _ = self.mocks()
        version.return_value = "02.09.01.71"
        with patch.object(adapter.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, b"")):
            state, code = adapter.run_slice(self.args())
        self.assertEqual(state["cli_probe"]["status"], "help_unavailable")
        self.assertEqual((state["status"], code, state["issue_count"]), ("needs_review", 3, 1))
        launch.assert_called_once()
        self.assertFalse(state["print_sent"])

    def test_old_native_project_can_be_read_by_installed_studio_without_enabling_mutation(self):
        old = "02.08.02.61"
        inventory = dict(self.inventory, version=old, application=["BambuStudio-" + old], supported_for_mutation=False)
        _, _, _, launch, _ = self.mocks(inventory=inventory)
        with patch.object(adapter.subprocess, "run") as help_call:
            state, code = adapter.run_slice(self.args())
        help_call.assert_not_called()
        launch.assert_called_once()
        self.assertEqual((state["status"], code, state["project_version"]), ("needs_review", 3, old))
        self.assertTrue(state["compatibility_trial"])

    def test_non_windows_version_probe_is_read_only_and_blocked(self):
        with patch.object(adapter.os, "name", "posix"), patch.object(adapter.subprocess, "Popen") as launch:
            with self.assertRaises(adapter.Bambu3MFError):
                adapter.executable_version(self.exe)
            launch.assert_not_called()

    def test_existing_run_directory_is_never_reused(self):
        run = self.root / "run"
        run.mkdir()
        marker = run / "user-file.txt"
        marker.write_text("keep", encoding="utf-8")
        _, _, _, launch, _ = self.mocks()
        with self.assertRaises(FileExistsError):
            adapter.run_slice(self.args())
        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
        launch.assert_not_called()

    def test_invalid_timeouts_prevent_run(self):
        _, _, _, launch, _ = self.mocks()
        for timeout in (0, -1, float("nan"), float("inf")):
            with self.subTest(timeout=timeout), self.assertRaises(adapter.Bambu3MFError):
                adapter.run_slice(self.args(timeout=timeout))
        launch.assert_not_called()

    def test_preview_stale_or_inconsistent_native_project_never_launches(self):
        changes_by_input = ({"preview_marker": {"preview_only": True}}, {"gcode": ["old.gcode"]},
                            {"version": "02.08.00.00"}, {"file_role": "unverified"},
                            {"file_role": "mixed_project"}, {"application": []}, {"application": ["Other"]},
                            {"version": "foreign", "application": ["BambuStudio-foreign"]})
        for index, changes in enumerate(changes_by_input):
            with self.subTest(changes=changes):
                _, _, _, launch, _ = self.mocks(inventory=dict(self.inventory, **changes))
                with self.assertRaises(adapter.Bambu3MFError):
                    adapter.run_slice(self.args(run_dir=self.root / f"invalid-{index}"))
                launch.assert_not_called()

    def test_snapshot_and_process_arguments_preserve_accepted_input(self):
        inspect, _, _, launch, validate = self.mocks()
        original = self.source.read_bytes()
        def inspect_snapshot(path):
            self.assertEqual(path.read_bytes(), original)
            self.source.write_bytes(b"source changed after acceptance snapshot")
            return self.inventory
        inspect.side_effect = inspect_snapshot
        state, code = adapter.run_slice(self.args())
        self.assertEqual(code, 0)
        command = launch.call_args.args[0]
        self.assertIsInstance(command, list)
        self.assertEqual(command[command.index("--arrange") + 1], "0")
        self.assertEqual(command[command.index("--slice") + 1], "1")
        self.assertEqual(Path(command[-1]).read_bytes(), original)
        self.assertNotEqual(Path(command[-1]), self.source)
        self.assertNotIn("shell", launch.call_args.kwargs)
        env = launch.call_args.kwargs["env"]
        for key in ("TMP", "TEMP", "TMPDIR"):
            self.assertTrue(Path(env[key]).samefile(self.root / "run" / "temp"), env[key])
        self.assertEqual(state["status"], "generated_pending_preview")
        self.assertEqual(state["gui_preview"], "not_verified")
        self.assertEqual(state["user_result_acceptance"], "not_verified")
        self.assertIn("does not prove user consent", state["acceptance"])
        self.assertFalse(state["print_sent"])
        inspect.assert_called_once()
        self.assertIs(validate.call_args.kwargs["snapshot_inventory"], self.inventory)

    def test_explicit_all_uses_supported_cli_all_value(self):
        _, _, _, launch, validate = self.mocks()
        adapter.run_slice(self.args(plates="all"))
        command = launch.call_args.args[0]
        self.assertEqual(command[command.index("--slice") + 1], "0")
        self.assertEqual(validate.call_args.args[2], [1, 2])

    def test_timeout_records_pid_without_retry_or_validation(self):
        _, _, process, launch, validate = self.mocks(wait=subprocess.TimeoutExpired("mock", 2))
        state, code = adapter.run_slice(self.args())
        self.assertEqual(code, 4)
        self.assertEqual(state["status"], "timeout_check_existing_process")
        self.assertTrue(state["process_may_be_running"])
        self.assertEqual(state["pid"], process.pid)
        launch.assert_called_once()
        validate.assert_not_called()
        process.kill.assert_not_called()
        process.terminate.assert_not_called()
        saved = json.loads((self.root / "run" / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["status"], state["status"])
        with self.assertRaises(FileExistsError):
            adapter.run_slice(self.args())
        launch.assert_called_once()

    def test_launch_failure_and_nonzero_exit_are_not_validated(self):
        for name in ("launch", "exit"):
            with self.subTest(name=name):
                _, _, _, launch, validate = self.mocks(wait=7)
                if name == "launch":
                    launch.side_effect = OSError("simulated launch failure")
                state, code = adapter.run_slice(self.args(run_dir=self.root / name))
                self.assertEqual(code, 4)
                self.assertEqual(state["status"], "launch_failed" if name == "launch" else "process_failed")
                validate.assert_not_called()

    def test_validation_findings_are_needs_review(self):
        self.mocks(verification=adapter.with_review_guidance({"issues": [{"kind": "output_difference"}]}))
        state, code = adapter.run_slice(self.args())
        self.assertEqual((state["status"], code, state["issue_count"]), ("needs_review", 3, 1))
        self.assertFalse(state["print_sent"])


    def test_snapshot_hash_disagreement_blocks_before_process_launch(self):
        _, _, _, launch, _ = self.mocks(inventory=dict(self.inventory, sha256="0" * 64))
        with self.assertRaises(adapter.Bambu3MFError):
            adapter.run_slice(self.args())
        launch.assert_not_called()

    def test_auxiliary_issue_keeps_review_exit_without_retry(self):
        verification = adapter.with_review_guidance({"issues": [{"kind": "invalid_first_layer_time"}]})
        _, _, _, launch, _ = self.mocks(verification=verification)
        state, code = adapter.run_slice(self.args())
        self.assertEqual((state["status"], code), ("needs_review", 3))
        launch.assert_called_once()
        saved = json.loads((self.root / "run" / "verification.json").read_text(encoding="utf-8"))
        self.assertFalse(saved["review_summary"]["automatic_reslice"])
        self.assertEqual(saved["issues"][0]["category"], "auxiliary_statistic")


class OutputValidationTests(AdapterCase):
    def test_missing_outputs_and_non_object_result(self):
        missing = self.validate_output(self.root / "absent")
        self.assertTrue(missing["issues"])
        for value in ([], None, 0, "Success"):
            with self.subTest(value=value):
                output = self.make_output()
                (output / "result.json").write_text(json.dumps(value), encoding="utf-8")
                self.assertTrue(self.validate_output(output)["issues"])

    def test_valid_synthetic_output_and_configuration_difference(self):
        output = self.make_output()
        self.assertEqual(self.validate_output(output)["issues"], [])
        result = self.validate_output(output, differences=[{"path": "filament_prime_volume", "before": [45, 30], "after": [45, 45]}])
        self.assertIn("output_difference", {item["kind"] for item in result["issues"]})

    def test_wrong_plate_and_invalid_gcode_are_flagged(self):
        output = self.make_output(plates=(2,), md5_valid=False, version="old", motion=False)
        kinds = {item["kind"] for item in self.validate_output(output, expected=[2])["issues"]}
        self.assertTrue({"gcode_md5", "gcode_version", "missing_motion_or_extrusion"}.issubset(kinds))
        kinds = {item["kind"] for item in self.validate_output(output, expected=[1])["issues"]}
        self.assertTrue({"plate_coverage", "gcode_coverage"}.issubset(kinds))

    def test_gcode_version_accepts_padding_but_never_a_different_build_with_common_prefix(self):
        for producer, matches in (("2.9.1.70", True), ("02.09.01.701", False), ("02.09.01.70-dev", False)):
            with self.subTest(producer=producer):
                result = self.validate_output(self.make_output(version=producer))
                self.assertEqual("gcode_version" not in {item["kind"] for item in result["issues"]}, matches)

    def test_standalone_gcode_disagreement_is_flagged(self):
        output = self.make_output()
        (output / "plate_1.gcode").write_bytes(b"old output")
        self.assertIn("standalone_gcode_mismatch", {x["kind"] for x in self.validate_output(output)["issues"]})

    def test_missing_duplicate_and_abnormal_metadata_are_not_clean(self):
        node = '<plate><metadata key="index" value="1"/><metadata key="printer_model_id" value="A1"/><metadata key="first_layer_time" value="10"/></plate>'
        for metadata in ("<config/>", "<config>" + node + node + "</config>",
                         '<config><plate><metadata key="index" value="1"/><metadata key="printer_model_id" value=""/><metadata key="first_layer_time" value="999999999999"/></plate></config>'):
            with self.subTest(metadata=metadata):
                self.assertTrue(self.validate_output(self.make_output(metadata=metadata))["issues"])

    def test_core_validation_error_becomes_output_finding(self):
        output = self.make_output()
        with patch.object(adapter, "inspect_project", side_effect=adapter.Bambu3MFError("unsupported output")):
            result = adapter.validate_slice(self.source, output, [1], adapter.SUPPORTED_VERSION)
        self.assertTrue(result["issues"])

    def test_nonfinite_result_is_reported_without_poisoning_json_output(self):
        output = self.make_output()
        for value in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(value=value):
                text = '{"return_code":0,"sliced_plates":[{"id":1,"total_predication":' + value + '}]}'
                (output / "result.json").write_text(text, encoding="utf-8")
                result = self.validate_output(output)
                self.assertTrue(result["issues"])
                # run_slice persists this value with strict JSON; failures must remain recordable.
                json.dumps(result, allow_nan=False)


    def test_same_run_inventory_avoids_duplicate_geometry_inspection(self):
        output = self.make_output()
        output_inventory = dict(self.inventory, sha256="output-digest")
        with patch.object(adapter, "inspect_project", return_value=output_inventory) as inspect, patch.object(
                adapter, "compare_project_inventories", return_value={"equal": True, "differences": []}) as compare:
            report = adapter.validate_slice(self.source, output, [1], adapter.SUPPORTED_VERSION,
                                            snapshot_inventory=self.inventory)
        self.assertEqual(report["issues"], [])
        inspect.assert_called_once_with(output / "sliced.3mf")
        compare.assert_called_once_with(self.inventory, output_inventory)

    def test_standalone_validation_inspects_each_archive_once(self):
        output = self.make_output()
        output_inventory = dict(self.inventory, sha256="output-digest")
        with patch.object(adapter, "inspect_project", side_effect=[self.inventory, output_inventory]) as inspect, patch.object(
                adapter, "compare_project_inventories", return_value={"equal": True, "differences": []}) as compare:
            report = adapter.validate_slice(self.source, output, [1], adapter.SUPPORTED_VERSION)
        self.assertEqual(report["issues"], [])
        self.assertEqual([call.args[0] for call in inspect.call_args_list], [self.source, output / "sliced.3mf"])
        compare.assert_called_once_with(self.inventory, output_inventory)

    def test_reused_inventory_requires_current_snapshot_hash(self):
        output = self.make_output()
        for mode in ("unrelated_inventory", "changed_snapshot"):
            with self.subTest(mode=mode):
                inventory = dict(self.inventory, sha256="0" * 64) if mode == "unrelated_inventory" else self.inventory
                if mode == "changed_snapshot":
                    self.source.write_bytes(b"snapshot changed after its first inspection")
                with patch.object(adapter, "inspect_project") as inspect, patch.object(
                        adapter, "compare_project_inventories") as compare:
                    report = adapter.validate_slice(self.source, output, [1], adapter.SUPPORTED_VERSION,
                                                    snapshot_inventory=inventory)
                self.assertIn("input_inventory_mismatch", {item["kind"] for item in report["issues"]})
                self.assertEqual(report["issues"][-1]["category"], "path_integrity_blocker")
                inspect.assert_not_called()
                compare.assert_not_called()

    def test_output_report_classifies_statistics_warning_and_send_gap_separately(self):
        metadata = '<config><plate><metadata key="index" value="1"/><metadata key="printer_model_id" value=""/><metadata key="first_layer_time" value="999"/></plate></config>'
        result = {"return_code": 0, "sliced_plates": [{"id": 1, "total_predication": 120,
                                                     "warning_message": "unrecognized slicer warning"}]}
        report = self.validate_output(self.make_output(metadata=metadata, result=result))
        by_kind = {item["kind"]: item for item in report["issues"]}
        self.assertEqual(by_kind["invalid_first_layer_time"]["category"], "auxiliary_statistic")
        self.assertEqual(by_kind["missing_printer_model_id"]["affected_stages"], ["print_send"])
        self.assertEqual(by_kind["slicer_warning"]["category"], "slicer_warning")
        self.assertIn("print_send", by_kind["slicer_warning"]["affected_stages"])
        self.assertEqual(report["verification_schema"], 2)
        self.assertFalse(report["review_summary"]["automatic_reslice"])


class DifferenceClassificationTests(AdapterCase):
    def classify(self, differences, *, inventory=None, expected=None):
        return adapter.classify_slice_differences(
            {"differences": differences}, inventory or self.inventory, expected or [1])

    def test_known_derived_additions_are_auditable_observations(self):
        differences = [{"category": "gcode", "path": "/gcode", "before": [], "after": [{"path": "Metadata/plate_1.gcode"}]}]
        for suffix in ("gcode", "gcode.md5", "json"):
            differences.append({"category": "member_bytes", "path": "/members/Metadata/plate_1." + suffix,
                                "before": None, "before_present": False, "after_present": True, "after": {"sha256": "new"}})
        for path in ("Metadata/slice_info.config", "Metadata/slice_info.config/size",
                     "Metadata/slice_info.config/sha256", "Metadata/project_settings.config/size",
                     "Metadata/project_settings.config/sha256"):
            differences.append({"category": "member_bytes", "path": "/members/" + path, "before": "old", "after": "new"})
        differences.append({"category": "plate", "path": "/plates/0/metadata/gcode_file",
                            "before_present": False, "after": "Metadata/plate_1.gcode"})
        issues, observations = self.classify(differences)
        self.assertEqual(issues, [])
        self.assertEqual([item["detail"] for item in observations], differences)

    def test_unknown_geometry_parameters_and_existing_path_changes_remain_issues(self):
        differences = [
            {"category": "global", "path": "/global_settings/filament_prime_volume", "before": [45, 30], "after": [45, 45]},
            {"category": "global", "path": "/global_settings/filament_map_2", "after": [2, 1]},
            {"category": "global", "path": "/global_settings/nozzle_temperature", "before": [200], "after": [220]},
            {"category": "object", "path": "/objects/part/metadata/sparse_infill_density", "before": "25%", "after": "30%"},
            {"category": "geometry_bytes", "path": "/three_d_sha256/3D/Objects/part.model", "before": "old", "after": "new"},
            {"category": "geometry", "path": "/objects/part/geometry", "before": "old", "after": "new"},
            {"category": "member_bytes", "path": "/members/Metadata/unknown.config/sha256", "before": "old", "after": "new"},
            {"category": "member_bytes", "path": "/members/Metadata/plate_2.gcode", "before_present": False, "after": "new"},
            {"category": "member_bytes", "path": "/members/Metadata/plate_1.gcode/sha256", "before": "old", "after": "new"},
            {"category": "member_bytes", "path": "/members/Metadata/project_settings.config", "before_present": True, "after_present": False},
            {"category": "gcode", "path": "/gcode/0/sha256", "before": "old", "after": "new"},
            {"category": "plate", "path": "/plates/0/metadata/gcode_file", "before_present": True,
             "before": "wrong", "after": "Metadata/plate_1.gcode"},
        ]
        issues, observations = self.classify(differences)
        self.assertEqual(observations, [])
        self.assertEqual([item["detail"] for item in issues], differences)

    def test_plate_path_classification_uses_actual_id_and_exact_target(self):
        inventory = dict(self.inventory, plates=[{"id": "7"}, {"id": "2"}])
        valid = {"category": "plate", "path": "/plates/0/metadata/gcode_file",
                 "before_present": False, "after": "Metadata/plate_7.gcode"}
        wrong_target = dict(valid, after="Metadata/plate_2.gcode")
        wrong_index = dict(valid, path="/plates/1/metadata/gcode_file")
        missing_index = dict(valid, path="/plates/99/metadata/gcode_file")
        issues, observations = self.classify([valid, wrong_target, wrong_index, missing_index], inventory=inventory, expected=[7])
        self.assertEqual([item["detail"] for item in observations], [valid])
        self.assertEqual([item["detail"] for item in issues], [wrong_target, wrong_index, missing_index])

    def test_derived_observation_never_suppresses_content_or_parameter_errors(self):
        output = self.make_output(md5_valid=False)
        differences = [
            {"category": "gcode", "path": "/gcode", "before": [], "after": [{"path": "Metadata/plate_1.gcode"}]},
            {"category": "member_bytes", "path": "/members/Metadata/project_settings.config/sha256", "before": "old", "after": "new"},
            {"category": "global", "path": "/global_settings/filament_prime_volume", "before": [45, 30], "after": [45, 45]},
        ]
        result = self.validate_output(output, differences=differences)
        kinds = {item["kind"] for item in result["issues"]}
        self.assertTrue({"gcode_md5", "output_difference"}.issubset(kinds))
        parameter_issues = [item for item in result["issues"] if item["kind"] == "output_difference"]
        self.assertEqual([item["detail"] for item in parameter_issues], [differences[2]])


class ReviewGuidanceTests(unittest.TestCase):
    def test_guidance_preserves_all_evidence_and_does_not_mutate_original(self):
        differences = [
            {"category": "global", "path": "/global_settings/nozzle_temperature", "before": [200], "after": [220]},
            {"category": "geometry", "path": "/objects/part/geometry", "before": "old", "after": "new"},
            {"category": "member_bytes", "path": "/members/unknown/sha256", "before": "old", "after": "new"},
        ]
        issues = [{"kind": "output_difference", "detail": item} for item in differences]
        issues += [{"kind": "slicer_warning", "message": "new unknown warning"}, {"kind": "future_unknown_issue"}]
        observation = {"kind": "derived_output_difference", "detail": {"category": "gcode", "path": "/gcode"}}
        original = {"issues": issues, "observations": [observation], "configuration_comparison": {"differences": differences}}
        before = json.dumps(original, sort_keys=True)
        report = adapter.with_review_guidance(original)
        self.assertEqual(json.dumps(original, sort_keys=True), before)
        self.assertEqual(report["configuration_comparison"], original["configuration_comparison"])
        self.assertEqual([item["category"] for item in report["issues"]],
                         ["configuration_blocker", "path_integrity_blocker", "unknown_difference", "slicer_warning", "unknown_issue"])
        for old, enriched in zip(issues + [observation], report["issues"] + report["observations"]):
            self.assertTrue(all(enriched[key] == value for key, value in old.items()))
            self.assertTrue(enriched["recommended_action"])
        self.assertEqual(report["observations"][0]["category"], "expected_derived_output")
        self.assertEqual(report["review_summary"]["counts_by_category"]["issues"]["slicer_warning"], 1)
        self.assertFalse(report["review_summary"]["automatic_reslice"])

    def test_rename_and_raw_geometry_bytes_are_not_declared_proven_geometry_damage(self):
        for category, path in (("geometry_bytes", "/three_d_sha256/3D/Objects/part.model"),
                               ("object", "/objects/part/metadata/name"),
                               ("plate", "/plates/0/metadata/name")):
            with self.subTest(category=category, path=path):
                item = adapter.review_guidance({"kind": "output_difference", "detail": {"category": category, "path": path}})
                self.assertEqual(item["category"], "unknown_difference")
                self.assertIn("print_send", item["affected_stages"])

    def test_auxiliary_estimates_and_handoff_fields_have_distinct_actions(self):
        for kind in ("invalid_first_layer_time", "invalid_total_estimate"):
            with self.subTest(kind=kind):
                item = adapter.review_guidance({"kind": kind})
                self.assertEqual(item["category"], "auxiliary_statistic")
                self.assertEqual(item["affected_stages"], ["estimate_reporting"])
                self.assertIn("Do not re-slice solely", item["recommended_action"])
        for kind in ("missing_printer_model_id", "missing_slice_metadata", "slice_metadata_coverage"):
            with self.subTest(kind=kind):
                item = adapter.review_guidance({"kind": kind})
                self.assertEqual(item["category"], "send_metadata_gap")
                self.assertEqual(item["affected_stages"], ["print_send"])


class OfflineCommandsTests(AdapterCase):
    def test_inspect_lists_actual_plates_and_geometry_uncertainty_without_inventory(self):
        inventory = dict(self.inventory, geometry_equivalence_unverified=True)
        with patch.object(adapter, "inspect_project", return_value=inventory):
            code, stdout, _ = self.invoke(["inspect", "--input", str(self.source)])
        brief = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(brief["plate_ids"], [1, 2])
        self.assertTrue(brief["geometry_equivalence_unverified"])
        self.assertNotIn("global_settings", brief)

    def test_slice_summary_exposes_every_issue_category_and_retains_details(self):
        verification = adapter.with_review_guidance({"issues": [
            {"kind": "slicer_warning", "message": "example warning", "plate": 2},
            {"kind": "future_issue"}, {"kind": "slicer_warning", "plate": 1}]})
        self.mocks(verification=verification)
        run = self.root / "run"
        code, stdout, _ = self.invoke(["slice", "--input", str(self.source), "--bambu", str(self.exe),
                                       "--accepted-sha256", self.inventory["sha256"], "--plates", "all",
                                       "--run-dir", str(run)])
        brief = json.loads(stdout)
        self.assertEqual((code, brief["selected_plates"], brief["issue_count"]), (3, [1, 2], 3))
        self.assertEqual(brief["counts_by_category"]["issues"], {"slicer_warning": 2, "unknown_issue": 1})
        self.assertEqual(brief["issue_index"]["issue_count"], 3)
        self.assertEqual([row["plate"] for row in brief["issue_index"]["groups"]], [2, None, 1])
        self.assertNotIn("example warning", stdout)
        saved = json.loads(Path(brief["verification"]).read_text(encoding="utf-8"))
        self.assertEqual(saved["issues"], verification["issues"])

    def test_grouped_review_retains_ids_old_reports_and_exact_values(self):
        issues = [
            {"kind": "output_difference", "detail": {"category": "global", "path": "/extruder",
             "before_present": False, "after_present": True, "before": None, "after": [30, 45]}},
            {"kind": "slicer_warning", "plate": 4, "message": "support?"},
            {"kind": "output_difference", "detail": {"category": "global", "path": "/large",
             "before": [0] * 1000, "after": [1] * 1000}},
            {"kind": "new_finding"}, {"kind": "slicer_warning", "plate": 4, "message": "different"},
        ]
        path = self.root / "v1.json"
        path.write_text(json.dumps({"issues": issues, "observations": []}), encoding="utf-8")
        argv = ["review", "--input", str(path)]
        code, stdout, _ = self.invoke(argv)
        self.assertEqual(code, 0)
        index = json.loads(stdout)
        self.assertEqual(index["issue_count"], 5)
        self.assertEqual([r["issue_ids"] for r in index["groups"]], ["1,3", "2,5", "4"])
        self.assertEqual(index["groups"][0]["field_family"], "global")
        self.assertIsNone(index["groups"][0]["plate"])
        changes = index["configuration_changes"]
        self.assertEqual(changes[0]["after"], [30, 45])
        self.assertFalse(changes[0]["before_present"])
        self.assertEqual(changes[1]["read_from_issue"], ["before", "after"])
        status, detail, _ = self.invoke([*argv, "--issue", "3"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(detail), {"id": 3, "issue": issues[2]})
        for invalid in ("0", "6"):
            self.assertEqual(self.invoke([*argv, "--issue", invalid])[0], 2)
        self.assertEqual(json.loads(path.read_text())["issues"], issues)

    def test_grouped_review_expands_truncated_ranges_groups_and_config_entries(self):
        issues = []
        for i in range(40):
            issues.append({"kind": "output_difference", "detail": {"category": "global", "path": f"/p{i}",
                          "before": i, "after": i + 1}})
            issues.append({"kind": "slicer_warning", "plate": i + 1})
        summary = adapter.issue_index(issues)
        self.assertEqual(len(summary["groups"]), 24)
        self.assertEqual(summary["omitted_groups"], 17)
        self.assertEqual(summary["groups"][0]["omitted_ranges"], 28)
        self.assertEqual(summary["omitted_configuration_changes"], 16)
        expanded = adapter.issue_index(issues, full=True)
        self.assertEqual(len(expanded["groups"]), 41)
        self.assertEqual(len(expanded["configuration_changes"]), 40)
        self.assertEqual(expanded["groups"][0]["issue_ids"], ",".join(str(i) for i in range(1, 81, 2)))

    def test_review_plate_diff_uses_stable_plate_id_not_array_index(self):
        before = {"plates": [{"id": "7"}, {"id": "2"}]}
        after = {"plates": [{"id": "7"}, {"id": "9"}]}
        diffs = [{"category": "plate", "path": f"/plates/{i}/instances"} for i in (0, 1)]
        issues, _ = adapter.classify_slice_differences({"differences": diffs}, after, [7], source_inventory=before)
        self.assertEqual(issues[0]["plate"], 7)
        self.assertNotIn("plate", issues[1])

    def test_compare_brief_preserves_unknown_category_and_uncertainty(self):
        report = self.root / "report.json"
        comparison = {"equal": False, "geometry_equivalence_verified": False, "geometry_equivalence_unverified": True,
                      "differences": [{"category": "new_category", "path": "/test", "after": "field detail"}]}
        with patch.object(adapter, "compare_projects", return_value=comparison):
            code, stdout, _ = self.invoke(["compare", "--before", str(self.source), "--after", str(self.source),
                                           "--report", str(report)])
        brief = json.loads(stdout)
        self.assertEqual((code, brief["difference_count"], brief["difference_counts_by_category"]),
                         (3, 1, {"new_category": 1}))
        self.assertTrue(brief["geometry_equivalence_unverified"])
        self.assertNotIn("field detail", stdout)
        self.assertEqual(json.loads(report.read_text(encoding="utf-8")), comparison)

    def test_prepare_does_not_launch_and_preserves_phase_status(self):
        changes = self.root / "changes.json"
        changes.write_text('[{"scope":"global","key":"x","from":"1","to":"2"}]', encoding="utf-8")
        output = self.root / "prepared.3mf"
        def prepare(source, destination, plan):
            destination.write_bytes(b"prepared")
            return {"changes": plan, "gui_validation": {"full_roundtrip_current_reasons": ["override_marker_created"]}}
        with patch.object(adapter, "prepare_project", side_effect=prepare), patch.object(adapter.subprocess, "Popen") as launch:
            code, stdout, _ = self.invoke(["prepare", "--input", str(self.source), "--output", str(output), "--changes", str(changes)])
        self.assertEqual(code, 0)
        data = json.loads(stdout)
        self.assertEqual(data["status"], "prepared_pending_gui_verification")
        self.assertEqual(data["full_roundtrip_current_reasons"], ["override_marker_created"])
        launch.assert_not_called()

    def test_existing_report_blocks_before_side_effect(self):
        report = self.root / "existing.json"
        report.write_text("keep", encoding="utf-8")
        with patch.object(adapter.subprocess, "Popen") as launch:
            code, _, _ = self.invoke(["open", "--input", str(self.source), "--bambu", str(self.exe), "--mode", "project", "--report", str(report)])
        self.assertEqual(code, 2)
        self.assertEqual(report.read_text(encoding="utf-8"), "keep")
        launch.assert_not_called()

    def test_skill_directory_output_rejected(self):
        with self.assertRaises(adapter.Bambu3MFError):
            adapter.writable_destination(adapter.PACKAGE / "generated.3mf")

    def test_shell_or_wrapper_cannot_be_used_as_bambu(self):
        wrapper = self.root / "wrapper.cmd"
        wrapper.write_text("must never execute", encoding="utf-8")
        with self.assertRaises(adapter.Bambu3MFError):
            adapter.resolve_executable(wrapper)

    def test_open_only_reports_launch_not_loaded_or_accepted(self):
        with patch.object(adapter, "inspect_project", return_value=self.inventory), patch.object(
                adapter.subprocess, "Popen", return_value=Mock(pid=1357)) as launch:
            code, stdout, _ = self.invoke(["open", "--input", str(self.source), "--bambu", str(self.exe), "--mode", "project"])
        result = json.loads(stdout)
        self.assertEqual(code, 0)
        self.assertEqual(result["loaded_or_previewed"], "not_verified")
        self.assertEqual(result["status"], "launch_requested")
        self.assertFalse(result["print_sent"])
        self.assertEqual(launch.call_args.args[0], [str(self.exe.resolve()), str(self.source.resolve())])

    def test_file_roles_gate_open_before_any_gui_launch(self):
        for role, valid_modes in (("sliced_toolpath", {"preview"}), ("preview_copy", {"preview"}),
                                  ("mixed_project", {"project"}), ("unverified", set())):
            for mode in ("project", "preview"):
                with self.subTest(role=role, mode=mode), patch.object(
                        adapter, "inspect_project", return_value=dict(self.inventory, file_role=role)), patch.object(
                            adapter.subprocess, "Popen", return_value=Mock(pid=1357)) as launch:
                    code, stdout, _ = self.invoke(["open", "--input", str(self.source), "--bambu", str(self.exe),
                                                  "--mode", mode])
                    if mode in valid_modes:
                        self.assertEqual(code, 0)
                        self.assertEqual(json.loads(stdout)["file_role"], role)
                        launch.assert_called_once()
                    else:
                        self.assertEqual(code, 2)
                        launch.assert_not_called()

    def test_mixed_project_cannot_be_opened_as_verified_preview(self):
        mixed = dict(self.inventory, gcode=["plate_1.gcode"], file_role="mixed_project")
        with patch.object(adapter, "inspect_project", return_value=mixed), patch.object(adapter.subprocess, "Popen") as launch:
            code, _, _ = self.invoke(["open", "--input", str(self.source), "--bambu", str(self.exe), "--mode", "preview"])
        self.assertEqual(code, 2)
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
