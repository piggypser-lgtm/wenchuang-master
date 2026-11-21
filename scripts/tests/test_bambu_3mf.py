"""Synthetic-package behavioral tests; no real projects or private paths."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import warnings
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bambu_3mf as api

MODEL = "3D/3dmodel.model"
CONFIG = "Metadata/project_settings.config"
SETTINGS = "Metadata/model_settings.config"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PROD = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"


def fixture(sliced=False, version="02.09.01.70"):
    config = ('{\r\n    "version": "' + version + '",\r\n'
              '    "filament_settings_id": ["Material A", "Material B"],\r\n'
              '    "different_settings_to_system": ["outer_wall_speed", "", "", ""],\r\n'
              '    "outer_wall_speed": [\r\n        "45",\r\n        "50"\r\n    ],\r\n'
              '    "filament_prime_volume": ["45", "30"],\r\n'
              '    "filament_type": ["PLA", "PETG"],\r\n'
              '    "eng_plate_temp": ["55", "70"],\r\n'
              '    "mystery": "中文\\\\路径",\r\n'
              '    "count": 2\r\n}\r\n')
    objects = []
    plates = []
    for i, name in [(2, "左套筒"), (4, "右套筒")]:
        objects.append(
            f'<object id="{i}">\n'
            f'  <metadata key="name" value="{name}"/>\n'
            '  <metadata key="sparse_infill_density" value="25%"/>\n'
            '  <metadata key="extruder" value="1"/>\n'
            '  <metadata key="unrecognized_setting" value="保留 &amp; 原样"/>\n'
            f'  <part id="{i-1}" subtype="normal_part">\n'
            '    <metadata key="sparse_infill_density" value="25%"/>\n'
            '    <mesh_stat face_count="1"/>\n'
            '  </part>\n</object>')
        plate_id = i // 2
        gref = f'<metadata key="gcode_file" value="Metadata/plate_{plate_id}.gcode"/>' if sliced else ""
        plates.append(
            f'<plate><metadata key="plater_id" value="{plate_id}"/>'
            f'<metadata key="plater_name" value="第{plate_id}盘"/>'
            f'{gref}<model_instance><metadata key="object_id" value="{i}"/>'
            '<metadata key="instance_id" value="0"/></model_instance></plate>')
    settings = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<config><!-- untouched comment 中文 -->\n'
                + "\n".join(objects + plates)
                + '<assemble><assemble_item object_id="2" instance_id="0" transform="'
                + IDENTITY + '"/></assemble></config>')
    components = "".join(
        f'<object id="{i}" type="model"><components>'
        f'<component p:path="/3D/Objects/object_{i-1}.model" objectid="{i-1}" transform="{IDENTITY}"/>'
        '</components></object>' for i in (2, 4))
    build = "".join(f'<item objectid="{i}" transform="{IDENTITY}" printable="1"/>' for i in (2, 4))
    main = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<model xmlns="{CORE}" xmlns:p="{PROD}" unit="millimeter">'
            f'<metadata name="Application">BambuStudio-{version}</metadata>'
            f'<resources>{components}</resources><build>{build}</build></model>')
    members = {
        CONFIG: config.encode("utf-8"), SETTINGS: settings.encode("utf-8"), MODEL: main.encode("utf-8"),
        "3D/_rels/3dmodel.model.rels": b'<Relationships/>',
        "[Content_Types].xml": b'<Types/>',
        "_rels/.rels": b'<Relationships/>',
        "Metadata/unknown.bin": b"\x01KEEP\x00\xff",
    }
    for i in (1, 3):
        mesh = (f'<model xmlns="{CORE}"><resources><object id="{i}"><mesh>'
                '<vertices><vertex x="0" y="0" z="0"/><vertex x="1" y="0" z="0"/>'
                '<vertex x="0" y="1" z="0"/></vertices>'
                '<triangles><triangle v1="0" v2="1" v3="2" paint_seam="1"/></triangles>'
                '</mesh></object></resources></model>')
        members[f"3D/Objects/object_{i}.model"] = mesh.encode("utf-8")
    if sliced:
        members["Metadata/slice_info.config"] = (
            '<config><header/><plate><metadata key="index" value="1"/>'
            '<metadata key="first_layer_time" value="0.000000"/></plate>'
            '<plate><metadata key="index" value="2"/>'
            '<metadata key="first_layer_time" value="36893488147419103232.000000"/>'
            '</plate></config>').encode("utf-8")
        for i in (1, 2):
            code = f"; BambuStudio {version}\n; plate {i}\nG1 X{i} Y10 E0.1\n".encode("ascii")
            members[f"Metadata/plate_{i}.gcode"] = code
            members[f"Metadata/plate_{i}.gcode.md5"] = hashlib.md5(code).hexdigest().upper().encode("ascii")
    return members


class ThreeMFTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="bambu-core-test-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, members, filename="input.3mf"):
        path = self.root / filename
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
            for name, data in members.items():
                z.writestr(name, data)
        return path

    def test_file_roles_follow_archive_contents(self):
        # Misleading extensions or the absence of our optional preview marker do not decide the role.
        editable = self.write(fixture(), "source.gcode.3mf")
        mixed = self.write(fixture(sliced=True), "mixed.3mf")
        self.assertEqual(api.inspect_project(editable)["file_role"], "editable_project")
        self.assertTrue(api.inspect_project(editable)["supported_for_mutation"])
        self.assertEqual(api.inspect_project(mixed)["file_role"], "mixed_project")
        self.assertFalse(api.inspect_project(mixed)["supported_for_mutation"])
        viewer = self.root / "viewer.3mf"
        api.make_preview(mixed, viewer)
        self.assertEqual(api.inspect_project(viewer)["file_role"], "preview_copy")
        with zipfile.ZipFile(viewer) as archive:
            native = {n: archive.read(n) for n in archive.namelist() if n != api.PREVIEW_MARKER}
        native_info = api.inspect_project(self.write(native))
        self.assertEqual(native_info["file_role"], "sliced_toolpath")
        self.assertTrue(native_info["preview_only"])
        self.assertFalse(native_info["supported_for_mutation"])
        self.assertIsNone(native_info["preview_marker"])
        self.assertTrue(api.is_preview_only(self.write(native)))
        mismatched = dict(native)
        mismatched[SETTINGS] = native[SETTINGS].replace(b"Metadata/plate_1.gcode", b"Metadata/missing.gcode")
        self.assertEqual(api.inspect_project(self.write(mismatched))["file_role"], "unverified")
        native["Metadata/plate_1.gcode.md5"] = b"wrong"
        self.assertEqual(api.inspect_project(self.write(native))["file_role"], "unverified")

    def test_editable_role_requires_mesh_build_plate_and_project_settings(self):
        cases = {"missing_mesh": lambda m: m.pop("3D/Objects/object_1.model"),
                 "empty_triangles": lambda m: m.update({"3D/Objects/object_1.model":
                     m["3D/Objects/object_1.model"].replace(
                         b'<triangle v1="0" v2="1" v3="2" paint_seam="1"/>', b"")}),
                 "dangling_plate": lambda m: m.update({SETTINGS: m[SETTINGS].replace(
                     b'key="object_id" value="2"', b'key="object_id" value="99"')}),
                 "no_build_instances": lambda m: m.update({MODEL: m[MODEL].replace(b"<item ", b"<unused ")}),
                 "empty_settings": lambda m: m.update({CONFIG: b"{}"}),
                 "incorrect_preview_mark": lambda m: m.update({api.PREVIEW_MARKER: b'{"preview_only":true}'})}
        for name, update in cases.items():
            with self.subTest(name=name):
                members = fixture()
                update(members)
                source = self.write(members)
                inventory = api.inspect_project(source)
                self.assertEqual(inventory["file_role"], "unverified")
                self.assertFalse(inventory["supported_for_mutation"])
                output = self.root / "unexpected.3mf"
                with self.assertRaises(api.Bambu3MFError):
                    api.prepare_project(source, output, [self.global_change()])
                self.assertFalse(output.exists())
        members = fixture()
        del members[CONFIG]
        del members[SETTINGS]
        with self.assertRaisesRegex(api.Bambu3MFError, "import the geometry"):
            api.inspect_project(self.write(members))

    def global_change(self):
        return {"scope": "global", "key": "outer_wall_speed", "from": ["45", "50"], "to": ["42", "50"]}

    def object_change(self):
        return {"scope": "object", "name": "左套筒", "key": "sparse_infill_density", "from": "25%", "to": "30%"}

    def test_inventory_and_exact_targeted_patch_preserve_whitespace_nested_metadata(self):
        members = fixture()
        source = self.write(members)
        before = source.read_bytes()
        output = self.root / "prepared.3mf"
        report = api.prepare_project(source, output, [self.global_change(), self.object_change()])
        self.assertTrue(report["unchanged_members_byte_identical"])
        self.assertEqual(source.read_bytes(), before)
        with zipfile.ZipFile(output) as z:
            self.assertEqual(set(z.namelist()), set(members))
            self.assertEqual(z.read(CONFIG), members[CONFIG].replace(b'        "45"', b'        "42"', 1))
            expected = members[SETTINGS].replace(
                b'<metadata key="sparse_infill_density" value="25%"/>',
                b'<metadata key="sparse_infill_density" value="30%"/>', 1)
            self.assertEqual(z.read(SETTINGS), expected)
            for name in members:
                if name not in (CONFIG, SETTINGS):
                    self.assertEqual(z.read(name), members[name], name)
        inv = api.inspect_project(output)
        self.assertEqual([o["name"] for o in inv["objects"]], ["左套筒", "右套筒"])
        self.assertEqual(inv["objects"][0]["parts"][0]["metadata"]["sparse_infill_density"], "25%")
        self.assertEqual([p["object_ids"] for p in inv["plates"]], [["2"], ["4"]])
        self.assertEqual(inv["objects"][0]["geometry"][0]["mesh"]["paint_seam_count"], 1)
        self.assertFalse(inv["geometry_equivalence_unverified"])

    def configured_fixture(self, config_updates=None, remove=()):
        members = fixture()
        config = json.loads(members[CONFIG])
        config.update(config_updates or {})
        for key in remove:
            config.pop(key, None)
        members[CONFIG] = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
        return members

    def read_config(self, output):
        with zipfile.ZipFile(output) as z:
            return json.loads(z.read(CONFIG))

    def test_process_and_material_overrides_survive_preset_reconstruction(self):
        members = self.configured_fixture({
            "initial_layer_speed": "50", "slow_down_layer_time": ["4", "8"],
            "inherits_group": ["Print parent", "Material A parent", "Material B parent", "Printer parent"],
            "different_settings_to_system": ["outer_wall_speed;custom_existing", "fan_max_speed", "", "machine_max_speed_x"]})
        changes = [
            {"scope": "global", "key": "initial_layer_speed", "from": "50", "to": "15"},
            {"scope": "global", "key": "slow_down_layer_time", "from": ["4", "8"], "to": ["4", "12"]},
            {"scope": "global", "key": "eng_plate_temp", "from": ["55", "70"], "to": ["60", "70"]}]
        source = self.write(members)
        output = self.root / "retained.3mf"
        report = api.prepare_project(source, output, changes)
        cfg = self.read_config(output)
        self.assertEqual(cfg["different_settings_to_system"], [
            "outer_wall_speed;custom_existing;initial_layer_speed", "fan_max_speed;eng_plate_temp",
            "slow_down_layer_time", "machine_max_speed_x"])
        # Simulate the relevant native import contract: load preset defaults, then
        # retain only registered overrides for each group. This catches the actual
        # regression (written values being discarded), beyond testing string shape.
        native_values = {"initial_layer_speed": "50", "slow_down_layer_time": ["4", "8"], "eng_plate_temp": ["55", "70"]}
        groups = [set(x.split(";")) for x in cfg["different_settings_to_system"]]
        if "initial_layer_speed" in groups[0]: native_values["initial_layer_speed"] = cfg["initial_layer_speed"]
        for slot in range(2):
            for key in ("slow_down_layer_time", "eng_plate_temp"):
                if key in groups[slot + 1]: native_values[key][slot] = cfg[key][slot]
        self.assertEqual(native_values, {"initial_layer_speed": "15", "slow_down_layer_time": ["4", "12"], "eng_plate_temp": ["60", "70"]})
        self.assertEqual(cfg["inherits_group"], json.loads(members[CONFIG])["inherits_group"])
        self.assertTrue(report["gui_validation"]["actual_load_required"])
        self.assertFalse(report["gui_validation"]["completed"])
        self.assertEqual(report["gui_validation"]["full_roundtrip_current_reasons"], [])
        with zipfile.ZipFile(output) as z:
            for name, original in members.items():
                if name != CONFIG: self.assertEqual(z.read(name), original)

    def test_printer_override_uses_last_group_and_noops_do_not_duplicate_keys(self):
        source = self.write(self.configured_fixture({"machine_max_acceleration_x": ["10000"]}))
        output = self.root / "machine.3mf"
        report = api.prepare_project(source, output, [self.global_change(),
            {"scope": "global", "key": "machine_max_acceleration_x", "from": ["10000"], "to": ["8000"]}])
        self.assertEqual(self.read_config(output)["different_settings_to_system"],
                         ["outer_wall_speed", "", "", "machine_max_acceleration_x"])
        self.assertEqual(len(report["preset_override_retention"]["automatic_additions"]), 1)
        unchanged = self.root / "noop.3mf"
        noop = dict(self.global_change(), to=["45", "50"])
        report = api.prepare_project(source, unchanged, [noop])
        self.assertFalse(report["preset_override_retention"]["automatic_additions"])
        with zipfile.ZipFile(source) as a, zipfile.ZipFile(unchanged) as b:
            self.assertEqual(a.read(CONFIG), b.read(CONFIG))

    def test_missing_override_marker_is_added_only_with_known_slot_layout(self):
        source = self.write(self.configured_fixture(remove=("different_settings_to_system",)))
        output = self.root / "new-marker.3mf"
        report = api.prepare_project(source, output, [self.global_change()])
        self.assertEqual(self.read_config(output)["different_settings_to_system"], ["outer_wall_speed", "", "", ""])
        self.assertTrue(report["preset_override_retention"]["marker_created"])
        self.assertIn("override_marker_created", report["gui_validation"]["full_roundtrip_current_reasons"])
        bad = self.write(self.configured_fixture(remove=("different_settings_to_system", "filament_settings_id")), "no-slots.3mf")
        with self.assertRaises(api.Bambu3MFError):
            api.prepare_project(bad, self.root / "bad.3mf", [self.global_change()])
        self.assertFalse((self.root / "bad.3mf").exists())

    def test_unknown_global_groups_and_malformed_layout_are_refused_without_output(self):
        variants = [
            {"different_settings_to_system": ["", "", ""]},
            {"different_settings_to_system": ["", 2, "", ""]},
            {"different_settings_to_system": ["outer_wall_speed;;layer_height", "", "", ""]},
            {"different_settings_to_system": ['"outer_wall_speed"', "", "", ""]},
            {"inherits_group": ["parent"]},
            {"filament_settings_id": [""]},
        ]
        for i, updates in enumerate(variants):
            with self.subTest(i=i), self.assertRaises(api.Bambu3MFError):
                api.prepare_project(self.write(self.configured_fixture(updates), f"malformed{i}.3mf"),
                                    self.root / f"bad{i}.3mf", [self.global_change()])
            self.assertFalse((self.root / f"bad{i}.3mf").exists())
        source = self.write(self.configured_fixture({"unclassified_speed": "10"}), "unknown.3mf")
        with self.assertRaisesRegex(api.Bambu3MFError, "group is not verified"):
            api.prepare_project(source, self.root / "unknown-out.3mf", [
                {"scope": "global", "key": "unclassified_speed", "from": "10", "to": "20"}])
        self.assertFalse((self.root / "unknown-out.3mf").exists())

    def test_filament_variant_layout_and_marker_removal_are_refused(self):
        source = self.write(self.configured_fixture({"slow_down_layer_time": ["4", "5", "6", "7"]}))
        with self.assertRaisesRegex(api.Bambu3MFError, "variant layout"):
            api.prepare_project(source, self.root / "variant.3mf", [
                {"scope": "global", "key": "slow_down_layer_time", "from": ["4", "5", "6", "7"], "to": ["8", "5", "6", "7"]}])
        with self.assertRaisesRegex(api.Bambu3MFError, "keys must be preserved"):
            api.prepare_project(source, self.root / "remove.3mf", [
                {"scope": "global", "key": "different_settings_to_system",
                 "from": ["outer_wall_speed", "", "", ""], "to": ["", "", "", ""]}])
        self.assertFalse((self.root / "variant.3mf").exists())
        self.assertFalse((self.root / "remove.3mf").exists())

    def test_project_only_metadata_does_not_change_preset_markers(self):
        members = self.configured_fixture({"curr_bed_type": "Engineering Plate", "filament_colour": ["#FFFFFF", "#000000"]})
        source = self.write(members)
        output = self.root / "project-only.3mf"
        report = api.prepare_project(source, output, [
            {"scope": "global", "key": "curr_bed_type", "from": "Engineering Plate", "to": "Textured PEI Plate"},
            {"scope": "global", "key": "filament_colour", "from": ["#FFFFFF", "#000000"], "to": ["#FF0000", "#000000"]}])
        self.assertEqual(self.read_config(output)["different_settings_to_system"], json.loads(members[CONFIG])["different_settings_to_system"])
        self.assertEqual(report["preset_override_retention"]["automatic_additions"], [])

    def test_explicit_marker_addition_and_automatic_updates_are_merged_once(self):
        members = self.configured_fixture({"layer_height": "0.2"})
        source = self.write(members)
        output = self.root / "merged.3mf"
        api.prepare_project(source, output, [
            {"scope": "global", "key": "different_settings_to_system", "from": ["outer_wall_speed", "", "", ""],
             "to": ["outer_wall_speed;layer_height", "", "", ""]},
            {"scope": "global", "key": "layer_height", "from": "0.2", "to": "0.12"}])
        self.assertEqual(self.read_config(output)["different_settings_to_system"], ["outer_wall_speed;layer_height", "", "", ""])

    def test_explicit_marker_cannot_misclassify_or_add_unknown_keys(self):
        source = self.write(fixture())
        for i, target in enumerate((
                ["outer_wall_speed;eng_plate_temp", "", "", ""],
                ["outer_wall_speed", "layer_height", "", ""],
                ["outer_wall_speed;unknown_key", "", "", ""])):
            with self.subTest(i=i), self.assertRaisesRegex(api.Bambu3MFError, "unverified group/key"):
                api.prepare_project(source, self.root / f"wrong-group{i}.3mf", [
                    {"scope": "global", "key": "different_settings_to_system",
                     "from": ["outer_wall_speed", "", "", ""], "to": target}])
            self.assertFalse((self.root / f"wrong-group{i}.3mf").exists())

    def test_preinspected_comparison_matches_file_comparison(self):
        source = self.write(fixture())
        output = self.root / "comparison.3mf"
        api.prepare_project(source, output, [self.global_change()])
        left, right = api.inspect_project(source), api.inspect_project(output)
        left_before, right_before = json.dumps(left, sort_keys=True), json.dumps(right, sort_keys=True)
        self.assertEqual(api.compare_project_inventories(left, right), api.compare_projects(source, output))
        self.assertEqual(json.dumps(left, sort_keys=True), left_before)
        self.assertEqual(json.dumps(right, sort_keys=True), right_before)

    def test_source_and_existing_output_never_overwritten(self):
        source = self.write(fixture())
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        for target in (source, self.root / "existing.3mf"):
            if target != source:
                target.write_bytes(b"keep")
            old = target.read_bytes()
            with self.assertRaises(api.Bambu3MFError):
                api.prepare_project(source, target, [self.global_change()])
            self.assertEqual(target.read_bytes(), old)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), digest)

    def test_old_gcode_and_unknown_version_refused_for_mutation(self):
        for index, members in enumerate((fixture(True), fixture(False, "99.0.0"))):
            source = self.write(members, f"case{index}.3mf")
            self.assertIsInstance(api.inspect_project(source), dict)
            with self.assertRaises(api.Bambu3MFError):
                api.prepare_project(source, self.root / "out.3mf", [self.global_change()])
        unknown_sliced = self.write(fixture(True, "99.0.0"), "unknown.3mf")
        with self.assertRaises(api.Bambu3MFError):
            api.make_preview(unknown_sliced, self.root / "unknown-preview.3mf")

    def test_stale_from_missing_keys_type_and_list_length_rejected(self):
        source = self.write(fixture())
        cases = [
            {"scope": "global", "key": "outer_wall_speed", "from": ["99", "50"], "to": ["42", "50"]},
            {"scope": "global", "key": "outer_wall_speed", "from": ["45", "50"], "to": ["42"]},
            {"scope": "global", "key": "outer_wall_speed", "from": ["45", "50"], "to": [42, "50"]},
            {"scope": "global", "key": "count", "from": 2, "to": True},
            {"scope": "global", "key": "not_here", "from": "1", "to": "2"},
            {"scope": "object", "name": "左套筒", "key": "not_here", "from": "1", "to": "2"},
        ]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(api.Bambu3MFError):
                api.prepare_project(source, self.root / "bad.3mf", [change])
            self.assertFalse((self.root / "bad.3mf").exists())

    def test_ambiguous_object_requires_matching_id_duplicate_edits_refused(self):
        members = fixture()
        members[SETTINGS] = members[SETTINGS].replace("右套筒".encode(), "左套筒".encode())
        source = self.write(members)
        with self.assertRaises(api.Bambu3MFError):
            api.prepare_project(source, self.root / "ambiguous.3mf", [self.object_change()])
        change = dict(self.object_change(), id="2")
        api.prepare_project(source, self.root / "selected.3mf", [change])
        with self.assertRaises(api.Bambu3MFError):
            api.prepare_project(source, self.root / "duplicate.3mf", [change, change])

    def test_xml_escaping_and_nonstandard_encoding(self):
        source = self.write(fixture())
        change = {"scope": "object", "name": "左套筒", "key": "unrecognized_setting",
                  "from": "保留 & 原样", "to": '测试 < > & " \n'}
        output = self.root / "escaped.3mf"
        api.prepare_project(source, output, [change])
        self.assertEqual(api.inspect_project(output)["objects"][0]["metadata"]["unrecognized_setting"], change["to"])
        members = fixture()
        members[SETTINGS] = members[SETTINGS].replace(b'encoding="UTF-8"', b'encoding="utf8"')
        with self.assertRaises(api.Bambu3MFError):
            api.inspect_project(self.write(members, "bad-encoding.3mf"))

    def test_duplicate_json_duplicate_zip_dangerous_paths_and_dtd_refused(self):
        members = fixture()
        members[CONFIG] = members[CONFIG].replace(b'"count": 2', b'"count": 2, "count": 3')
        with self.assertRaises(api.Bambu3MFError):
            api.inspect_project(self.write(members, "duplicate-json.3mf"))
        dup = self.write(fixture(), "duplicate-zip.3mf")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(dup, "a") as z:
                z.writestr(CONFIG, b"{}")
        with self.assertRaises(api.Bambu3MFError):
            api.inspect_project(dup)
        for i, path in enumerate(("../bad", "/root", "C" + ":/" + "bad", r"Metadata\bad", "a/../bad")):
            members = fixture()
            members[path] = b"x"
            path_zip = self.write(members, f"path{i}.3mf")
            if "\\" in path:
                # ZipInfo normalizes Windows backslashes on creation; inject one
                # into both raw ZIP headers to exercise the untrusted-reader path.
                path_zip.write_bytes(path_zip.read_bytes().replace(path.replace("\\", "/").encode(), path.encode()))
            with self.assertRaises(api.Bambu3MFError):
                api.inspect_project(path_zip)
        members = fixture()
        members[SETTINGS] = b'<!DOCTYPE config [<!ENTITY x "boom">]><config/>'
        with self.assertRaises(api.Bambu3MFError):
            api.inspect_project(self.write(members, "dtd.3mf"))

    def test_bad_crc_refused(self):
        source = self.write(fixture())
        with zipfile.ZipFile(source) as z:
            info = z.getinfo("Metadata/unknown.bin")
            offset = info.header_offset
        data = bytearray(source.read_bytes())
        name_len, extra_len = struct.unpack_from("<HH", data, offset + 26)
        data[offset + 30 + name_len + extra_len] ^= 1
        source.write_bytes(data)
        with self.assertRaises(api.Bambu3MFError):
            api.inspect_project(source)

    def test_compare_reports_material_prime_volume_unknown_metadata_and_geometry(self):
        a = fixture()
        b = fixture()
        b[CONFIG] = b[CONFIG].replace(b'["45", "30"]', b'["45", "45"]')
        b["Metadata/unknown.bin"] = b"changed"
        source, other = self.write(a, "before.3mf"), self.write(b, "after.3mf")
        report = api.compare_projects(source, other)
        self.assertFalse(report["equal"])
        self.assertTrue(report["geometry_equivalence_verified"])
        self.assertTrue(any(d["path"] == "/global_settings/filament_prime_volume/1" and
                            d["before"] == "30" and d["after"] == "45" for d in report["differences"]))
        self.assertTrue(any("unknown.bin" in d["path"] for d in report["differences"]))
        b["3D/Objects/object_1.model"] = b["3D/Objects/object_1.model"].replace(b'x="1"', b'x="2"')
        changed = self.write(b, "geometry.3mf")
        self.assertFalse(api.compare_projects(source, changed)["geometry_equivalence_verified"])

    def test_geometry_format_and_object_id_reordering_are_not_damage(self):
        a, b = fixture(), fixture()
        for key in (MODEL, SETTINGS):
            b[key] = b[key].replace(b'id="2"', b'id="20"').replace(b'objectid="2"', b'objectid="20"')
            b[key] = b[key].replace(b'key="object_id" value="2"', b'key="object_id" value="20"')
            b[key] = b[key].replace(b'object_id="2"', b'object_id="20"')
        b["3D/Objects/object_1.model"] = b["3D/Objects/object_1.model"].replace(b'x="1"', b'x="1.000"')
        report = api.compare_projects(self.write(a, "a.3mf"), self.write(b, "b.3mf"))
        self.assertTrue(report["geometry_equivalence_verified"])
        self.assertTrue(report["needs_review"])


    def test_geometry_unit_changes_are_not_equivalent(self):
        a, b = fixture(), fixture()
        b[MODEL] = b[MODEL].replace(b'unit="millimeter"', b'unit="inch"')
        report = api.compare_projects(self.write(a, "unit-a.3mf"), self.write(b, "unit-b.3mf"))
        self.assertFalse(report["geometry_equivalence_verified"])
        b = fixture()
        key = "3D/Objects/object_1.model"
        b[key] = b[key].replace(b"<model ", b'<model unit="inch" ')
        report = api.compare_projects(self.root / "unit-a.3mf", self.write(b, "external-unit.3mf"))
        self.assertFalse(report["geometry_equivalence_verified"])

    def test_preview_retains_gcode_checksum_stats_and_plate_references(self):
        members = fixture(True)
        source = self.write(members)
        output = self.root / "preview.gcode.3mf"
        report = api.make_preview(source, output)
        self.assertTrue(report["gcode_byte_identical"])
        self.assertTrue(api.is_preview_only(output))
        inventory = api.inspect_project(output)
        self.assertEqual(inventory["objects"], [])
        self.assertEqual(len(inventory["plates"]), 2)
        self.assertTrue(all(g["md5_valid"] for g in inventory["gcode"]))
        with zipfile.ZipFile(output) as z:
            for name in members:
                if ".gcode" in name or name == "Metadata/slice_info.config":
                    self.assertEqual(z.read(name), members[name])
            self.assertEqual(z.read("Metadata/unknown.bin"), members["Metadata/unknown.bin"])
            root = ET.fromstring(z.read(MODEL))
            self.assertEqual(len(root.find("{" + CORE + "}resources")), 0)
            self.assertEqual(len(root.find("{" + CORE + "}build")), 0)
            settings = ET.fromstring(z.read(SETTINGS))
            self.assertEqual(settings.findall("object"), [])
            self.assertEqual(settings.findall("assemble"), [])
            self.assertEqual(settings.findall("plate/model_instance"), [])
        for plate in inventory["plates"]:
            self.assertEqual(plate["metadata"]["gcode_file"], f"Metadata/plate_{plate['id']}.gcode")
        with self.assertRaises(api.Bambu3MFError):
            api.prepare_project(output, self.root / "reslice.3mf", [self.global_change()])

    def test_preview_rejects_bad_checksum_missing_plate_and_unknown_references(self):
        cases = []
        b = fixture(True)
        b["Metadata/plate_1.gcode.md5"] = b"0" * 32
        cases.append(b)
        b = fixture(True)
        del b["Metadata/plate_2.gcode"]
        cases.append(b)
        b = fixture(True)
        b[SETTINGS] = b[SETTINGS].replace(b"</config>", b"<unknown_ref/></config>")
        cases.append(b)
        b = fixture(True)
        b["Metadata/custom.xml"] = b'<custom path="../3D/Objects/object_1.model"/>'
        cases.append(b)
        b = fixture(True)
        b["3D/Objects/unreferenced.model"] = b'<model/>'
        cases.append(b)
        b = fixture(True)
        b["3D/_rels/3dmodel.model.rels"] = (
            '<Relationships><Relationship Target="/Metadata/unknown.bin" Id="unexpected" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>'
        ).encode()
        cases.append(b)
        b = fixture(True)
        b["Metadata/custom.json"] = b'{"mesh":"/3D/Objects/object_1.model"}'
        cases.append(b)
        for i, members in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(api.Bambu3MFError):
                api.make_preview(self.write(members, f"bad{i}.3mf"), self.root / f"out{i}.3mf")
            self.assertFalse((self.root / f"out{i}.3mf").exists())


if __name__ == "__main__":
    unittest.main()
