"""Conservative Bambu Studio 3MF inspection and project-copy helpers.

Original code distributed under this package's MIT license. Python 3.10+.
Only the explicitly tested Bambu Studio version may be modified. No function
launches software, contacts a printer, modifies G-code, or overwrites an input.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from xml.parsers import expat
import zipfile
from pathlib import Path

SUPPORTED_VERSION = "02.09.01.70"
PREVIEW_MARKER = "Metadata/code_first_preview_only.json"
PROJECT = "Metadata/project_settings.config"
SETTINGS = "Metadata/model_settings.config"
MODEL = "3D/3dmodel.model"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PRODUCTION = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"
C = "{" + CORE + "}"
P = "{" + PRODUCTION + "}"
MAX_MEMBER_BYTES = 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024


# Deliberately scoped to ordinary settings verified against v02.09.01.70
# Preset::print_options / filament_options / printer_options in:
# https://github.com/bambulab/BambuStudio/blob/v02.09.01.70/src/libslic3r/Preset.cpp
# PresetBundle serializes dirty keys as [print, filament slots..., printer].
OVERRIDE_MARKER = "different_settings_to_system"
PROCESS_OVERRIDE_KEYS = frozenset("""
layer_height initial_layer_print_height wall_loops sparse_infill_density sparse_infill_pattern
bottom_shell_layers bottom_shell_thickness top_shell_layers top_shell_thickness
initial_layer_speed initial_layer_infill_speed outer_wall_speed inner_wall_speed
sparse_infill_speed internal_solid_infill_speed top_surface_speed gap_infill_speed
support_speed support_interface_speed travel_speed bridge_speed
initial_layer_acceleration default_acceleration outer_wall_acceleration inner_wall_acceleration
top_surface_acceleration travel_acceleration initial_layer_travel_acceleration
wall_generator line_width initial_layer_line_width outer_wall_line_width inner_wall_line_width
sparse_infill_line_width internal_solid_infill_line_width top_surface_line_width support_line_width
support_top_z_distance support_bottom_z_distance support_object_xy_distance
support_interface_top_layers support_interface_bottom_layers support_interface_spacing
support_interface_pattern enable_support support_type support_style support_on_build_plate_only
support_threshold_angle support_base_pattern_spacing support_expansion
brim_type brim_width brim_object_gap raft_layers raft_contact_distance
ironing_type print_sequence elefant_foot_compensation xy_hole_compensation xy_contour_compensation
resolution enable_arc_fitting enable_overhang_speed overhang_1_4_speed overhang_2_4_speed
overhang_3_4_speed overhang_4_4_speed small_perimeter_speed
""".split())
FILAMENT_OVERRIDE_KEYS = frozenset("""
nozzle_temperature nozzle_temperature_initial_layer eng_plate_temp eng_plate_temp_initial_layer
cool_plate_temp cool_plate_temp_initial_layer hot_plate_temp hot_plate_temp_initial_layer
textured_plate_temp textured_plate_temp_initial_layer supertack_plate_temp supertack_plate_temp_initial_layer
filament_type filament_flow_ratio filament_density filament_cost filament_max_volumetric_speed
filament_prime_volume filament_minimal_purge_on_wipe_tower
slow_down_layer_time slow_down_min_speed close_fan_the_first_x_layers
fan_min_speed fan_max_speed fan_cooling_layer_time full_fan_speed_layer
slow_down_for_layer_cooling no_slow_down_for_cooling_on_outwalls
enable_overhang_bridge_fan overhang_fan_speed additional_cooling_fan_speed
nozzle_temperature_range_low nozzle_temperature_range_high
""".split())
PRINTER_OVERRIDE_KEYS = frozenset("""
machine_max_acceleration_extruding machine_max_acceleration_retracting machine_max_acceleration_travel
machine_max_acceleration_x machine_max_acceleration_y machine_max_acceleration_z machine_max_acceleration_e
machine_max_speed_x machine_max_speed_y machine_max_speed_z machine_max_speed_e
machine_max_jerk_x machine_max_jerk_y machine_max_jerk_z machine_max_jerk_e
""".split())
# Project settings are stored separately from the system-preset dirty lists.
PROJECT_ONLY_KEYS = frozenset(("curr_bed_type", "filament_colour"))


class Bambu3MFError(ValueError):
    """Invalid, unsupported, ambiguous, or unsafe project operation."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise Bambu3MFError("Duplicate JSON key: " + key)
            out[key] = value
        return out

    def constant(value):
        raise Bambu3MFError("Non-finite JSON number: " + value)

    try:
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Bambu3MFError("Invalid UTF-8 JSON: " + str(exc)) from exc


def _xml(data, label="XML"):
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise Bambu3MFError(label + ": only UTF-8 XML is supported") from exc
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise Bambu3MFError(label + ": DTD and entity declarations are forbidden")
    declaration = re.match(r"\ufeff?\s*<\?xml\b([^?]*)\?>", text)
    if declaration:
        enc = re.search(r"""encoding\s*=\s*["']([^"']+)["']""",
                        declaration.group(1), re.I)
        if enc and enc.group(1).lower() != "utf-8":
            raise Bambu3MFError(label + ": XML encoding must be UTF-8")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise Bambu3MFError(label + ": " + str(exc)) from exc


def _path_safe(name):
    if (not name or "\x00" in name or "\\" in name or ":" in name
            or name.startswith("/") or any(s in ("", ".", "..")
                                          for s in name.rstrip("/").split("/"))):
        raise Bambu3MFError("Unsafe ZIP member path: " + repr(name))


def _load(path):
    path = Path(path).resolve()
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            names = [i.filename for i in infos]
            if len(names) != len(set(names)):
                raise Bambu3MFError("Duplicate ZIP member names")
            if sum(i.file_size for i in infos) > MAX_TOTAL_BYTES:
                raise Bambu3MFError("ZIP expanded size exceeds safety limit")
            for info in infos:
                _path_safe(info.orig_filename)
                _path_safe(info.filename)
                if info.flag_bits & 1:
                    raise Bambu3MFError("Encrypted ZIP members are unsupported")
                if info.file_size > MAX_MEMBER_BYTES:
                    raise Bambu3MFError("ZIP member exceeds safety limit")
            blobs = {i.filename: z.read(i) for i in infos}
    except (OSError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        raise Bambu3MFError("Cannot read project ZIP: " + str(exc)) from exc
    for name, data in blobs.items():
        if name.lower().endswith((".xml", ".rels", ".model")):
            _xml(data, name)
        elif name.lower().endswith(".config") and data.lstrip().startswith(b"<"):
            _xml(data, name)
    if MODEL not in blobs:
        raise Bambu3MFError("Required Bambu 3MF model member missing: " + MODEL)
    for name in (PROJECT, SETTINGS):
        if name not in blobs:
            raise Bambu3MFError("Missing Bambu project metadata: " + name +
                                ". For a model-only 3MF, import the geometry and save a Bambu Studio project.")
    config = _json(blobs[PROJECT])
    if not isinstance(config, dict):
        raise Bambu3MFError("Project settings must be a JSON object")
    return path, infos, blobs, config


def _metadata(element):
    result = {}
    for child in element.findall("metadata"):
        key = child.get("key")
        if key is None:
            continue
        if key in result:
            raise Bambu3MFError("Duplicate XML metadata key: " + key)
        result[key] = child.get("value")
    return result


def _floats(text, expected=None):
    try:
        values = tuple(float(v) for v in (text or "").split())
    except ValueError as exc:
        raise Bambu3MFError("Invalid numeric transform") from exc
    if any(not math.isfinite(v) for v in values):
        raise Bambu3MFError("Non-finite transform")
    if expected is not None and len(values) != expected:
        raise Bambu3MFError("Unexpected transform length")
    return list(values)


def _mesh_signature(mesh):
    if any(child.tag not in (C + "vertices", C + "triangles") for child in mesh):
        raise Bambu3MFError("Unknown mesh structure")
    vertices = mesh.find(C + "vertices")
    triangles = mesh.find(C + "triangles")
    if vertices is None or triangles is None:
        raise Bambu3MFError("Mesh lacks vertices or triangles")
    vh, th = hashlib.sha256(), hashlib.sha256()
    for vertex in vertices:
        if vertex.tag != C + "vertex":
            raise Bambu3MFError("Unknown vertices child")
        try:
            xyz = [float(vertex.attrib[k]) for k in ("x", "y", "z")]
        except (KeyError, ValueError) as exc:
            raise Bambu3MFError("Invalid vertex") from exc
        if not all(math.isfinite(v) for v in xyz):
            raise Bambu3MFError("Non-finite vertex")
        extra = {k: v for k, v in vertex.attrib.items() if k not in ("x", "y", "z")}
        vh.update(json.dumps([xyz, extra], sort_keys=True).encode("utf-8") + b"\n")
    seams = supports = 0
    for triangle in triangles:
        if triangle.tag != C + "triangle":
            raise Bambu3MFError("Unknown triangles child")
        attrs = dict(triangle.attrib)
        for key in ("v1", "v2", "v3"):
            try:
                index = int(attrs[key])
            except (KeyError, ValueError) as exc:
                raise Bambu3MFError("Invalid triangle index") from exc
            if index < 0 or index >= len(vertices):
                raise Bambu3MFError("Triangle index outside vertex range")
            attrs[key] = index
        seams += "paint_seam" in attrs
        supports += "paint_supports" in attrs
        th.update(json.dumps(attrs, sort_keys=True).encode("utf-8") + b"\n")
    return {"vertices": len(vertices), "triangles": len(triangles),
            "vertices_sha256": vh.hexdigest(), "triangles_sha256": th.hexdigest(),
            "paint_seam_count": seams, "paint_supports_count": supports}


def _file_role(objects, plates, gcode, config, unknown_geometry, marked_preview):
    """Classify supported Bambu package contents independently of the filename."""
    placed = {oid for plate in plates for oid in plate["object_ids"]}
    if not objects:
        readable_paths = bool(gcode) and all(
            entry["size"] > 0 and (not entry["md5_present"] or entry["md5_valid"]) for entry in gcode)
        if not readable_paths or unknown_geometry or not plates or placed:
            return "unverified"
        paths = {entry["path"] for entry in gcode}
        linked_paths = set()
        for plate in plates:
            reference = plate["metadata"].get("gcode_file")
            if reference:
                linked_paths.add(reference)
            else:
                stem = "Metadata/plate_" + plate["id"]
                linked_paths.update(paths.intersection((stem + ".gcode", stem + ".bgcode")))
        if linked_paths != paths:
            return "unverified"
        return "preview_copy" if marked_preview else "sliced_toolpath"

    if marked_preview or unknown_geometry:
        return "unverified"
    built = {obj["id"] for obj in objects if obj["instances"]}
    if not placed or not placed.issubset(built):
        return "unverified"
    if not any(config.get(key) for key in (
            "print_settings_id", "printer_settings_id", "filament_settings_id", "filament_type", "layer_height")):
        return "unverified"
    for obj in objects:
        if obj["geometry_equivalence_unverified"] or not obj["geometry"]:
            return "unverified"
        if not all(part["mesh"]["vertices"] and part["mesh"]["triangles"] for part in obj["geometry"]):
            return "unverified"
    return "mixed_project" if gcode else "editable_project"


def _inventory(path, blobs, config):
    settings = _xml(blobs[SETTINGS], SETTINGS)
    model = _xml(blobs[MODEL], MODEL)
    if settings.tag != "config" or model.tag != C + "model":
        raise Bambu3MFError("Unsupported metadata roots")
    objects, seen_ids = [], set()
    resources = model.find(C + "resources")
    model_objects = {}
    if resources is not None:
        for obj in resources.findall(C + "object"):
            oid = obj.get("id")
            if oid in model_objects:
                raise Bambu3MFError("Duplicate core model object ID")
            model_objects[oid] = obj
    build = model.find(C + "build")
    build_items = list(build) if build is not None else []
    for obj in settings.findall("object"):
        oid = obj.get("id")
        if not oid or oid in seen_ids:
            raise Bambu3MFError("Missing/duplicate object ID")
        seen_ids.add(oid)
        metadata = _metadata(obj)
        item = {"id": oid, "name": metadata.get("name"), "metadata": metadata,
                "parts": [{"attributes": dict(part.attrib), "metadata": _metadata(part),
                           "xml": ET.tostring(part, encoding="unicode")}
                          for part in obj.findall("part")],
                "instances": [], "geometry": [],
                "geometry_equivalence_unverified": False,
                "model_unit": model.get("unit", "millimeter")}
        for instance in build_items:
            if instance.get("objectid") == oid:
                item["instances"].append({
                    "transform": _floats(instance.get("transform", "1 0 0 0 1 0 0 0 1 0 0 0"), 12),
                    "printable": instance.get("printable", "1"),
                    "attributes": dict(instance.attrib)})
        try:
            core_obj = model_objects[oid]
            direct = core_obj.find(C + "mesh")
            if direct is not None:
                item["geometry"].append({"mesh": _mesh_signature(direct), "transform": None,
                                         "unit": model.get("unit", "millimeter")})
            components = core_obj.find(C + "components")
            if components is not None:
                for component in components:
                    if component.tag != C + "component":
                        raise Bambu3MFError("Unknown component")
                    ref = component.get(P + "path")
                    if not ref:
                        raise Bambu3MFError("Only external mesh components are supported")
                    ref = ref.lstrip("/")
                    _path_safe(ref)
                    target = _xml(blobs[ref], ref)
                    matches = [o for o in target.findall(C + "resources/" + C + "object")
                               if o.get("id") == component.get("objectid")]
                    if len(matches) != 1 or matches[0].find(C + "mesh") is None:
                        raise Bambu3MFError("Missing/ambiguous component mesh")
                    item["geometry"].append({
                        "mesh": _mesh_signature(matches[0].find(C + "mesh")),
                        "unit": target.get("unit", "millimeter"),
                        "transform": _floats(component.get("transform",
                                               "1 0 0 0 1 0 0 0 1 0 0 0"), 12)})
            if not item["geometry"]:
                raise Bambu3MFError("No supported geometry")
        except (KeyError, Bambu3MFError) as exc:
            item["geometry_equivalence_unverified"] = True
            item["geometry_error"] = str(exc)
        objects.append(item)
    plates, plate_ids = [], set()
    for plate in settings.findall("plate"):
        metadata = _metadata(plate)
        pid = metadata.get("plater_id")
        if not pid or pid in plate_ids:
            raise Bambu3MFError("Missing/duplicate plate ID")
        plate_ids.add(pid)
        instances = [_metadata(instance) for instance in plate.findall("model_instance")]
        plates.append({"id": pid, "name": metadata.get("plater_name"),
                       "metadata": metadata, "object_ids": [i.get("object_id") for i in instances],
                       "instances": instances})
    gcode = []
    for name, data in blobs.items():
        if name.lower().endswith((".gcode", ".bgcode")):
            md5 = hashlib.md5(data).hexdigest()
            stored = blobs.get(name + ".md5")
            valid = False
            if stored is not None:
                try:
                    valid = stored.decode("ascii").strip().lower() == md5
                except UnicodeError:
                    pass
            gcode.append({"path": name, "sha256": _sha(data), "hash": _sha(data),
                          "size": len(data), "md5": md5,
                          "md5_present": stored is not None, "md5_valid": valid})
    unknown_geometry = (set(model_objects) != seen_ids or
                        any(i.tag != C + "item" or i.get("objectid") not in seen_ids for i in build_items) or
                        (resources is not None and any(o.tag != C + "object" for o in resources)))
    application = [m.text or "" for m in model.findall(C + "metadata")
                   if m.get("name") == "Application"]
    marked = PREVIEW_MARKER in blobs
    marker = _json(blobs[PREVIEW_MARKER]) if marked else None
    role = _file_role(objects, plates, gcode, config, unknown_geometry, marked)
    return {"path": str(path), "sha256": _sha(path.read_bytes()), "zip_crc_valid": True,
            "version": config.get("version"), "application": application,
            "supported_for_mutation": (role == "editable_project" and config.get("version") == SUPPORTED_VERSION
                                       and application == ["BambuStudio-" + SUPPORTED_VERSION]),
            "preview_only": role in ("sliced_toolpath", "preview_copy"), "preview_marker": marker,
            "file_role": role,
            "global_settings": config, "objects": objects, "plates": plates, "gcode": gcode,
            "geometry_equivalence_unverified": unknown_geometry or any(o["geometry_equivalence_unverified"] for o in objects),
            "transforms": [{"object_id": i.get("objectid"), "attributes": dict(i.attrib)} for i in build_items],
            "three_d_sha256": {n: _sha(b) for n, b in blobs.items() if n.startswith("3D/")},
            "members": {n: {"sha256": _sha(b), "size": len(b)} for n, b in blobs.items()}}


def inspect_project(path):
    """Read-only inventory. Unknown application versions are allowed."""
    source, _, blobs, config = _load(path)
    return _inventory(source, blobs, config)


def is_preview_only(path):
    """Identify a viewing-only input, including a native toolpath without an adapter marker."""
    return inspect_project(path)["preview_only"]


def _require_version(blobs, config):
    model = _xml(blobs[MODEL], MODEL)
    apps = [m.text or "" for m in model.findall(C + "metadata") if m.get("name") == "Application"]
    if config.get("version") != SUPPORTED_VERSION or apps != ["BambuStudio-" + SUPPORTED_VERSION]:
        raise Bambu3MFError("Modification is only validated for BambuStudio " + SUPPORTED_VERSION)


def _write_copy(source, output, infos, original, replacement, removed=()):
    output = Path(output).resolve()
    if output == source or output.exists():
        raise Bambu3MFError("Output must be a new path distinct from the source")
    if not output.parent.is_dir():
        raise Bambu3MFError("Output parent directory does not exist")
    removed = set(removed)
    created = False
    try:
        with output.open("xb") as stream:
            created = True
            with zipfile.ZipFile(stream, "w") as z:
                for info in infos:
                    if info.filename not in removed:
                        z.writestr(copy.copy(info), replacement.get(info.filename, original[info.filename]))
                for name, data in replacement.items():
                    if name not in original and name not in removed:
                        z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(output) as z:
            expected = (set(original) | set(replacement)) - removed
            if set(z.namelist()) != expected:
                raise Bambu3MFError("Written ZIP member mismatch")
            for name in expected:
                if z.read(name) != replacement.get(name, original.get(name)):
                    raise Bambu3MFError("Written ZIP content mismatch: " + name)
    except Exception:
        if created and output.exists():
            output.unlink()
        raise
    return output


def _same_type(old, new):
    if type(old) is not type(new):
        return False
    if isinstance(old, list):
        return len(old) == len(new) and all(_same_type(a, b) for a, b in zip(old, new))
    if isinstance(old, dict) or old is None:
        return False
    return isinstance(old, (str, bool, int, float)) and (
        not isinstance(new, float) or math.isfinite(new))


def _json_member_spans(text):
    decoder = json.JSONDecoder()

    def ws(i):
        while i < len(text) and text[i].isspace():
            i += 1
        return i

    pos = ws(0)
    if pos >= len(text) or text[pos] != "{":
        raise Bambu3MFError("Expected JSON object")
    pos += 1
    spans = {}
    while True:
        pos = ws(pos)
        if text[pos] == "}":
            break
        key, end = decoder.raw_decode(text, pos)
        pos = ws(end)
        if not isinstance(key, str) or text[pos] != ":":
            raise Bambu3MFError("Unsupported JSON member")
        pos = ws(pos + 1)
        start = pos
        _, end = decoder.raw_decode(text, pos)
        spans[key] = (start, end)
        pos = ws(end)
        if text[pos] == "}":
            break
        if text[pos] != ",":
            raise Bambu3MFError("Unsupported JSON separator")
        pos += 1
    return spans


def _json_value_patch(token, old, new):
    if isinstance(old, list):
        decoder, pos, patches = json.JSONDecoder(), 1, []
        for a, b in zip(old, new):
            while token[pos].isspace() or token[pos] == ",":
                pos += 1
            _, end = decoder.raw_decode(token, pos)
            patches.append((pos, end, _json_value_patch(token[pos:end], a, b)))
            pos = end
        for start, end, value in reversed(patches):
            token = token[:start] + value + token[end:]
        return token
    if old == new:
        return token
    return json.dumps(new, ensure_ascii="\\u" in token, allow_nan=False)


def _xml_tokens(data):
    """Return element byte ranges with parsed attributes and ancestry."""
    parser, stack, tokens = expat.ParserCreate(), [], []

    def start(name, attrs):
        offset = parser.CurrentByteIndex
        quote = None
        end = offset
        while end < len(data):
            ch = data[end]
            if quote:
                if ch == quote:
                    quote = None
            elif ch in (34, 39):
                quote = ch
            elif ch == 62:
                break
            end += 1
        item = {"name": name, "attrs": attrs, "start": offset, "start_end": end + 1,
                "ancestors": tuple(t["name"] for t in stack),
                "parent": stack[-1] if stack else None,
                "self_closing": data[offset:end].rstrip().endswith(b"/")}
        stack.append(item)
        tokens.append(item)

    def finish(name):
        item = stack.pop()
        if item["self_closing"]:
            item["end"] = item["start_end"]
        else:
            offset = parser.CurrentByteIndex
            item["end"] = data.index(b">", offset) + 1

    parser.StartElementHandler, parser.EndElementHandler = start, finish
    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        raise Bambu3MFError("XML tokenization failed: " + str(exc)) from exc
    return tokens


def _attribute_patch(data, token, key, new_value):
    head = data[token["start"]:token["start_end"]]
    pattern = re.compile(rb"(?<![\w:.-])" + key.encode("ascii") + rb"""\s*=\s*(["'])(.*?)\1""", re.S)
    matches = list(pattern.finditer(head))
    if len(matches) != 1:
        raise Bambu3MFError("Missing/ambiguous XML attribute: " + key)
    match = matches[0]
    quote = match.group(1)
    value = new_value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace('"', "&quot;") if quote == b'"' else value.replace("'", "&apos;")
    value = value.replace("\t", "&#9;").replace("\n", "&#10;").replace("\r", "&#13;")
    return (token["start"] + match.start(2), token["start"] + match.end(2), value.encode("utf-8"))


def _replace_ranges(data, replacements):
    last = len(data) + 1
    for start, end, value in sorted(replacements, reverse=True):
        if start < 0 or end > last or end < start:
            raise Bambu3MFError("Overlapping or invalid text replacements")
        data = data[:start] + value + data[end:]
        last = start
    return data


def _override_groups(value, count):
    if not isinstance(value, list) or len(value) != count + 2:
        raise Bambu3MFError("Unsupported preset override layout; use native GUI preparation")
    groups = []
    for entry in value:
        if not isinstance(entry, str):
            raise Bambu3MFError("Preset override entries must be strings")
        keys = entry.split(";") if entry else []
        # Known option names need no C-style escaping. Do not guess other encodings.
        if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) for key in keys):
            raise Bambu3MFError("Unsupported escaped/malformed preset override keys")
        groups.append(set(keys))
    return groups


def _retain_preset_overrides(config, expected, changes):
    actual = [c for c in changes if c["scope"] == "global" and c["from"] != c["to"]]
    if not actual:
        return None, [], False
    needing_markers = [c for c in actual if c["key"] not in PROJECT_ONLY_KEYS]
    if not needing_markers:
        return None, [], False
    ids = config.get("filament_settings_id")
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) and x for x in ids):
        raise Bambu3MFError("Cannot determine filament slots for preset overrides; use native GUI preparation")
    count = len(ids)
    inherits = config.get("inherits_group")
    if inherits is not None and (not isinstance(inherits, list) or len(inherits) != count + 2
                                 or not all(isinstance(x, str) for x in inherits)):
        raise Bambu3MFError("Ambiguous preset inheritance layout")
    created = OVERRIDE_MARKER not in config
    old_values = config.get(OVERRIDE_MARKER, [""] * (count + 2))
    old_groups = _override_groups(old_values, count)
    values = copy.deepcopy(expected.get(OVERRIDE_MARKER, old_values))
    groups = _override_groups(values, count)
    if any(not old <= new for old, new in zip(old_groups, groups)):
        raise Bambu3MFError("Existing preset override keys must be preserved")
    for index, (old, new) in enumerate(zip(old_groups, groups)):
        verified_keys = (PROCESS_OVERRIDE_KEYS if index == 0 else
                         PRINTER_OVERRIDE_KEYS if index == count + 1 else FILAMENT_OVERRIDE_KEYS)
        if not (new - old) <= verified_keys:
            raise Bambu3MFError("Explicit preset override additions use an unverified group/key")
    additions = []
    for change in needing_markers:
        key, old, new = change["key"], change["from"], change["to"]
        if key == OVERRIDE_MARKER:
            continue
        if key in PROCESS_OVERRIDE_KEYS:
            indexes = [0]
        elif key in PRINTER_OVERRIDE_KEYS:
            indexes = [count + 1]
        elif key in FILAMENT_OVERRIDE_KEYS:
            if not isinstance(old, list) or len(old) != count or any(isinstance(x, (list, dict)) for x in old + new):
                raise Bambu3MFError("Unsupported filament value/variant layout: " + key)
            indexes = [i + 1 for i, (a, b) in enumerate(zip(old, new)) if a != b]
        else:
            raise Bambu3MFError("Preset group is not verified for global key: " + key + "; use native GUI preparation")
        for index in indexes:
            if key not in groups[index]:
                # Append without reordering or deleting the native dirty-key string.
                values[index] += (";" if values[index] else "") + key
                groups[index].add(key)
                additions.append({"key": key, "group_index": index,
                                  "group": "process" if index == 0 else "printer" if index == count + 1 else "filament",
                                  **({"filament_slot": index - 1} if 1 <= index <= count else {})})
    return values, additions, created


def prepare_project(source, output, changes):
    """Apply explicit from/to edits, preserving all unrelated member bytes."""
    source, infos, blobs, config = _load(source)
    _require_version(blobs, config)
    if PREVIEW_MARKER in blobs or any(n.lower().endswith((".gcode", ".bgcode", ".gcode.md5")) for n in blobs):
        raise Bambu3MFError("Prepare requires an unsliced editable project")
    if not isinstance(changes, list) or not changes:
        raise Bambu3MFError("Changes must be a nonempty JSON list")
    settings = _xml(blobs[SETTINGS], SETTINGS)
    if settings.tag != "config":
        raise Bambu3MFError("Unsupported model settings root")
    if settings.attrib or any(c.tag not in ("object", "plate", "assemble") for c in settings):
        raise Bambu3MFError("Unsupported model settings structure")
    inventory = _inventory(source, blobs, config)
    if not inventory["objects"] or inventory["geometry_equivalence_unverified"]:
        raise Bambu3MFError("Prepare requires supported editable geometry")
    object_ids_known = {o["id"] for o in inventory["objects"]}
    if any(oid not in object_ids_known for p in inventory["plates"] for oid in p["object_ids"]):
        raise Bambu3MFError("Plate refers to an unknown object")
    objects = settings.findall("object")
    # Reject duplicated identifiers before matching object names.
    object_ids = [o.get("id") for o in objects]
    if None in object_ids or len(set(object_ids)) != len(object_ids):
        raise Bambu3MFError("Missing/duplicate object ID")
    if not inventory["supported_for_mutation"]:
        raise Bambu3MFError("Prepare requires a verified, unsliced editable project")
    tokens = _xml_tokens(blobs[SETTINGS])
    expected_config = copy.deepcopy(config)
    expected_settings = copy.deepcopy(settings)
    json_text = blobs[PROJECT].decode("utf-8")
    spans = _json_member_spans(json_text)
    json_edits, xml_edits, used = [], [], set()
    for change in changes:
        if not isinstance(change, dict):
            raise Bambu3MFError("Each change must be an object")
        scope, key = change.get("scope"), change.get("key")
        if scope not in ("global", "object") or not isinstance(key, str) or not key:
            raise Bambu3MFError("A change needs a supported scope and nonempty string key")
        allowed = {"scope", "key", "from", "to"} | ({"name", "id"} if scope == "object" else set())
        if set(change) - allowed or not {"scope", "key", "from", "to"} <= set(change):
            raise Bambu3MFError("Unexpected/missing change fields")
        old, new = change["from"], change["to"]
        if not _same_type(old, new):
            raise Bambu3MFError("Change must preserve value type and list lengths")
        if scope == "global":
            if key not in config or not _same_type(config[key], old) or config[key] != old:
                raise Bambu3MFError("Global from value does not match: " + str(key))
            identity = ("global", key)
            start, end = spans[key]
            value = _json_value_patch(json_text[start:end], old, new)
            if key != OVERRIDE_MARKER:
                json_edits.append((start, end, value))
            expected_config[key] = new
        elif scope == "object":
            if not isinstance(old, str) or not isinstance(new, str) or not isinstance(change.get("name"), str):
                raise Bambu3MFError("Object changes require a name and string from/to values")
            matches = [o for o in objects if _metadata(o).get("name") == change["name"]
                       and ("id" not in change or o.get("id") == str(change["id"]))]
            if len(matches) != 1:
                raise Bambu3MFError("Object selection is missing or ambiguous")
            obj = matches[0]
            oid = obj.get("id")
            metadata = _metadata(obj)
            if key not in metadata or metadata[key] != old:
                raise Bambu3MFError("Object from value does not match: " + str(key))
            identity = ("object", oid, key)
            matches = [t for t in tokens if t["ancestors"] == ("config", "object")
                       and t["name"] == "metadata" and t["attrs"].get("key") == key
                       and t["parent"]["attrs"].get("id") == oid]
            if len(matches) != 1:
                raise Bambu3MFError("Object metadata token is ambiguous")
            xml_edits.append(_attribute_patch(blobs[SETTINGS], matches[0], "value", new))
            expected_obj = next(o for o in expected_settings.findall("object") if o.get("id") == oid)
            next(m for m in expected_obj.findall("metadata") if m.get("key") == key).set("value", new)
        else:
            raise Bambu3MFError("Only global and object changes are supported")
        if identity in used:
            raise Bambu3MFError("Duplicate edits to the same setting")
        used.add(identity)
    marker_values, marker_additions, marker_created = _retain_preset_overrides(config, expected_config, changes)
    if marker_values is not None:
        expected_config[OVERRIDE_MARKER] = marker_values
        if OVERRIDE_MARKER in spans:
            start, end = spans[OVERRIDE_MARKER]
            json_edits.append((start, end, _json_value_patch(
                json_text[start:end], config[OVERRIDE_MARKER], marker_values)))
        else:
            # This one known metadata key may be added; arbitrary new settings remain forbidden.
            end = json_text.rfind("}")
            addition = ", " + json.dumps(OVERRIDE_MARKER) + ": " + json.dumps(marker_values)
            json_edits.append((end, end, addition))
    for start, end, value in sorted(json_edits, reverse=True):
        json_text = json_text[:start] + value + json_text[end:]
    replacements = {}
    if json_edits:
        replacements[PROJECT] = json_text.encode("utf-8")
    if xml_edits:
        replacements[SETTINGS] = _replace_ranges(blobs[SETTINGS], xml_edits)
    new_config = _json(replacements.get(PROJECT, blobs[PROJECT]))
    new_settings = _xml(replacements.get(SETTINGS, blobs[SETTINGS]), SETTINGS)
    if new_config != expected_config or ET.tostring(new_settings) != ET.tostring(expected_settings):
        raise Bambu3MFError("Semantic validation found an unplanned change")
    result = _write_copy(source, output, infos, blobs, replacements)
    return {"source": str(source), "output": str(result), "source_sha256": _sha(source.read_bytes()),
            "output_sha256": _sha(result.read_bytes()), "version": SUPPORTED_VERSION,
            "changes": copy.deepcopy(changes), "unchanged_members_byte_identical": True,
            "preset_override_retention": {"marker_created": marker_created,
                                          "automatic_additions": marker_additions,
                                          "existing_keys_preserved": True},
            "gui_validation": {"actual_load_required": True, "completed": False,
                "full_roundtrip_current_reasons": ["override_marker_created"] if marker_created else [],
                "full_roundtrip_required_if": ["first_use_of_version_fields_or_structure",
                                                "unexplained_parameter_difference",
                                                "software_ignores_or_resets_settings"],
                "reuse_scope": {"version": SUPPORTED_VERSION,
                    "global_keys": sorted({c["key"] for c in changes if c["scope"] == "global"}),
                    "object_keys": sorted({c["key"] for c in changes if c["scope"] == "object"})}}}


def _diff(a, b, path, category, out):
    if type(a) is not type(b):
        out.append({"category": category, "path": path, "before": a, "after": b})
    elif isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                out.append({"category": category, "path": path + "/" + str(key),
                            "before": a.get(key), "after": b.get(key),
                            "before_present": key in a, "after_present": key in b})
            else:
                _diff(a[key], b[key], path + "/" + str(key), category, out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append({"category": category, "path": path, "before": a, "after": b})
        else:
            for i, (left, right) in enumerate(zip(a, b)):
                _diff(left, right, path + "/" + str(i), category, out)
    elif a != b:
        out.append({"category": category, "path": path, "before": a, "after": b})


def compare_projects(before, after):
    """List all changes; no global parameters (including prime volume) are ignored."""
    return compare_project_inventories(inspect_project(before), inspect_project(after))


def compare_project_inventories(left, right):
    """Compare already inspected snapshots; callers bind inventories to those bytes.

    This is a pure comparison, not a disk freshness check or a persistent cache.
    """
    differences = []
    _diff(left["global_settings"], right["global_settings"], "/global_settings", "global", differences)
    unique = all(len({o["name"] for o in inv["objects"]}) == len(inv["objects"])
                 and all(o["name"] for o in inv["objects"]) for inv in (left, right))
    objects_a = {o["name"] if unique else o["id"]: o for o in left["objects"]}
    objects_b = {o["name"] if unique else o["id"]: o for o in right["objects"]}
    for key in sorted(set(objects_a) | set(objects_b)):
        a, b = objects_a.get(key), objects_b.get(key)
        if a is None or b is None:
            differences.append({"category": "object", "path": "/objects/" + str(key), "before": a, "after": b})
            continue
        for field in ("metadata", "parts", "instances", "geometry", "model_unit", "id", "geometry_equivalence_unverified"):
            _diff(a[field], b[field], "/objects/" + str(key) + "/" + field,
                  "geometry" if field == "geometry" else "object", differences)
    _diff(left["plates"], right["plates"], "/plates", "plate", differences)
    _diff(left["three_d_sha256"], right["three_d_sha256"], "/three_d_sha256", "geometry_bytes", differences)
    _diff(left["gcode"], right["gcode"], "/gcode", "gcode", differences)
    _diff(left["members"], right["members"], "/members", "member_bytes", differences)
    _diff(left["preview_only"], right["preview_only"], "/preview_only", "role", differences)
    geometry_unknown = left["geometry_equivalence_unverified"] or right["geometry_equivalence_unverified"]
    geometry_equal = bool(objects_a) and unique and set(objects_a) == set(objects_b) and not geometry_unknown and all(
        objects_a[k]["geometry"] == objects_b[k]["geometry"] and
        objects_a[k]["model_unit"] == objects_b[k]["model_unit"] and
        [{f: i[f] for f in ("transform", "printable")} for i in objects_a[k]["instances"]] ==
        [{f: i[f] for f in ("transform", "printable")} for i in objects_b[k]["instances"]]
        for k in objects_a)
    return {"equal": not differences, "needs_review": bool(differences),
            "geometry_equivalence_verified": geometry_equal,
            "geometry_equivalence_unverified": geometry_unknown or not unique or not objects_a,
            "differences": differences,
            "before": {"path": left["path"], "sha256": left["sha256"], "version": left["version"]},
            "after": {"path": right["path"], "sha256": right["sha256"], "version": right["version"]}}


def make_preview(source, output):
    """Create a marked viewing copy; preserve every G-code byte and its checksum."""
    source, infos, blobs, config = _load(source)
    _require_version(blobs, config)
    if PREVIEW_MARKER in blobs:
        raise Bambu3MFError("Input is already a preview-only copy")
    inv = _inventory(source, blobs, config)
    if not inv["gcode"] or not inv["objects"]:
        raise Bambu3MFError("Preview conversion needs a sliced editable project")
    if inv["geometry_equivalence_unverified"]:
        raise Bambu3MFError("Preview conversion requires supported verified geometry")
    if any(not g["md5_valid"] or not g["size"] for g in inv["gcode"]):
        raise Bambu3MFError("All G-code entries need valid MD5 checksums")
    model, settings = _xml(blobs[MODEL]), _xml(blobs[SETTINGS])
    if any(child.tag not in (C + "metadata", C + "resources", C + "build") for child in model):
        raise Bambu3MFError("Unknown core model structure")
    if len(model.findall(C + "resources")) != 1 or len(model.findall(C + "build")) != 1:
        raise Bambu3MFError("Expected exactly one resources and build element")
    resources, build = model.find(C + "resources"), model.find(C + "build")
    if any(o.tag != C + "object" for o in resources) or any(i.tag != C + "item" for i in build):
        raise Bambu3MFError("Unknown model resource/build structure")
    references = set()
    for obj in resources:
        if len(obj) != 1 or obj[0].tag != C + "components":
            raise Bambu3MFError("Only external component geometry is supported for preview")
        for component in obj[0]:
            if component.tag != C + "component":
                raise Bambu3MFError("Unknown component structure")
            path = component.get(P + "path", "").lstrip("/")
            if not re.fullmatch(r"3D/Objects/[^/]+\.model", path):
                raise Bambu3MFError("Unexpected component path")
            references.add(path)
    expected_removed = references | {"3D/_rels/3dmodel.model.rels"}
    three_d = {n for n in blobs if n.startswith("3D/")}
    if three_d - {MODEL} != expected_removed or not references:
        raise Bambu3MFError("Unknown or unreferenced 3D content; conversion refused")
    relationships = _xml(blobs["3D/_rels/3dmodel.model.rels"])
    if relationships.tag.split("}")[-1] != "Relationships":
        raise Bambu3MFError("Unknown 3D relationships root")
    for relationship in relationships:
        target = relationship.get("Target", "")
        resolved = target.lstrip("/") if target.startswith("/") else "3D/" + target
        if (relationship.tag.split("}")[-1] != "Relationship" or len(relationship)
                or set(relationship.attrib) - {"Target", "Id", "Type"}
                or relationship.get("Type") != "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"
                or resolved not in references):
            raise Bambu3MFError("Unknown relationship would be removed with model geometry")
    if settings.attrib or any(c.tag not in ("object", "plate", "assemble") for c in settings):
        raise Bambu3MFError("Unknown model-settings structure")
    for obj in settings.findall("object"):
        if any(c.tag not in ("metadata", "part") for c in obj):
            raise Bambu3MFError("Unknown object settings structure")
        for part in obj.findall("part"):
            if any(c.tag not in ("metadata", "mesh_stat") for c in part):
                raise Bambu3MFError("Unknown part settings structure")
    for assembly in settings.findall("assemble"):
        if any(c.tag != "assemble_item" for c in assembly):
            raise Bambu3MFError("Unknown assembly structure")
    gcode_paths = {g["path"] for g in inv["gcode"]}
    plate_gcodes = []
    for plate in settings.findall("plate"):
        if any(c.tag not in ("metadata", "model_instance") for c in plate):
            raise Bambu3MFError("Unknown plate structure")
        for instance in plate.findall("model_instance"):
            if any(c.tag != "metadata" for c in instance):
                raise Bambu3MFError("Unknown plate instance structure")
        metadata = _metadata(plate)
        pid = metadata["plater_id"]
        expected = "Metadata/plate_" + pid + ".gcode"
        if metadata.get("gcode_file") != expected:
            raise Bambu3MFError("Plate G-code reference mismatch")
        plate_gcodes.append(expected)
    if len(plate_gcodes) != len(set(plate_gcodes)) or set(plate_gcodes) != gcode_paths:
        raise Bambu3MFError("Plate/G-code coverage mismatch")
    if "Metadata/slice_info.config" not in blobs:
        raise Bambu3MFError("Slice metadata is required")
    slice_root = _xml(blobs["Metadata/slice_info.config"])
    slice_ids = [_metadata(p).get("index") for p in slice_root.findall("plate")]
    if len(slice_ids) != len(set(slice_ids)) or set(slice_ids) != {p["id"] for p in inv["plates"]}:
        raise Bambu3MFError("Slice metadata plate coverage mismatch")
    model_edits = []
    for token in _xml_tokens(blobs[MODEL]):
        if len(token["ancestors"]) == 1 and token["name"].split(":")[-1] in ("resources", "build"):
            model_edits.append((token["start"], token["end"], ("<" + token["name"] + "/>").encode("utf-8")))
    setting_edits = []
    for token in _xml_tokens(blobs[SETTINGS]):
        if ((token["ancestors"] == ("config",) and token["name"] in ("object", "assemble"))
                or (token["ancestors"] == ("config", "plate") and token["name"] == "model_instance")):
            setting_edits.append((token["start"], token["end"], b""))
    replacements = {
        MODEL: _replace_ranges(blobs[MODEL], model_edits),
        SETTINGS: _replace_ranges(blobs[SETTINGS], setting_edits),
        PREVIEW_MARKER: json.dumps({
            "schema": 1, "preview_only": True, "source_sha256": inv["sha256"],
            "version": SUPPORTED_VERSION,
            "purpose": "G-code viewing copy; never use as an editable model or slicing input.",
            "gcode_byte_identical": True
        }, indent=2).encode("utf-8"),
    }
    # Unknown surviving references are refused, never silently rewritten.
    for name, data in blobs.items():
        if name in expected_removed:
            continue
        data = replacements.get(name, data)
        if name.lower().endswith((".json", ".config")) and data.lstrip().startswith((b"{", b"[")):
            decoded = _json(data)
            pending = [decoded]
            while pending:
                value = pending.pop()
                if isinstance(value, dict):
                    pending.extend(value.values())
                elif isinstance(value, list):
                    pending.extend(value)
                elif isinstance(value, str):
                    normalized = value.replace("\\\\", "/")
                    if any(ref in normalized or ref.removeprefix("3D/") in normalized for ref in references):
                        raise Bambu3MFError("Surviving JSON reference to removed geometry in " + name)
        if name.lower().endswith((".xml", ".rels", ".model", ".config")) and data.lstrip().startswith(b"<"):
            root = _xml(data, name)
            for element in root.iter():
                values = list(element.attrib.values()) + ([element.text] if element.text else [])
                for value in values:
                    normalized = value.replace("\\", "/")
                    if any(ref in normalized or ref.removeprefix("3D/") in normalized for ref in references):
                        raise Bambu3MFError("Surviving reference to removed geometry in " + name)
    output_path = _write_copy(source, output, infos, blobs, replacements, expected_removed)
    final = inspect_project(output_path)
    if final["objects"] or final["file_role"] != "preview_copy" or final["gcode"] != inv["gcode"]:
        output_path.unlink()
        raise Bambu3MFError("Preview validation failed")
    return {"source": str(source), "output": str(output_path), "version": SUPPORTED_VERSION,
            "preview_only": True, "source_sha256": inv["sha256"],
            "output_sha256": final["sha256"], "gcode": final["gcode"],
            "gcode_byte_identical": True, "requires_gui_preview": True,
            "slice_statistics_unchanged": True}
