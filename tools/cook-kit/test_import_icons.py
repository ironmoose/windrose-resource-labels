"""Tests for import_icons.verify_texture_settings.

This is plain-Python/pytest -- no `unreal` needed and none available. See
the CRITICAL structural constraint documented at the top of import_icons.py:
`import unreal` only exists inside the UE editor, so import_icons.py (and
this test module) must import cleanly on a machine with no UE editor
installed.

Run with:
    python3 -m pytest tools/cook-kit/test_import_icons.py -q
or:
    python3 tools/cook-kit/test_import_icons.py
"""

import os
import shutil
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from import_icons import verify_texture_settings


class FakeTexture:
    """Duck-typed stand-in for a unreal.Texture2D: get_editor_property /
    set_editor_property backed by a plain dict, matching the real UE
    Python API's shape closely enough for verify_texture_settings, which
    only ever calls get_editor_property."""

    def __init__(self, **properties):
        self._properties = dict(properties)

    def get_editor_property(self, name):
        return self._properties[name]

    def set_editor_property(self, name, value):
        self._properties[name] = value


# Sentinel "intended" values standing in for the real unreal enum members
# (TEXTUREGROUP_UI, TC_EDITOR_ICON, TMGS_NO_MIPMAPS) that import_icons.py
# uses in the real UE editor. verify_texture_settings is generic over any
# comparable value, so plain strings/bools exercise it fully without unreal
# ever needing to be present.
CORRECT_INTENDED = {
    "lod_group": "TEXTUREGROUP_UI",
    "compression_settings": "TC_EDITOR_ICON",
    "srgb": True,
    "mip_gen_settings": "TMGS_NO_MIPMAPS",
}


class VerifyTextureSettingsTests(unittest.TestCase):
    def test_all_correct_settings_yield_no_mismatches(self):
        """Test A: a texture carrying the 4 correct values verifies clean."""
        tex = FakeTexture(**CORRECT_INTENDED)
        self.assertEqual(verify_texture_settings(tex, CORRECT_INTENDED), [])

    def test_wrong_compression_is_reported(self):
        """Test B: a wrong compression_settings (e.g. BC7 instead of the
        intended RGBA8/TC_EDITOR_ICON) is caught and named."""
        wrong = dict(CORRECT_INTENDED)
        wrong["compression_settings"] = "TC_DEFAULT_BC7"  # wrong sentinel
        tex = FakeTexture(**wrong)
        mismatches = verify_texture_settings(tex, CORRECT_INTENDED)
        self.assertTrue(mismatches, "expected at least one mismatch")
        self.assertTrue(
            any("compression_settings" in m for m in mismatches),
            f"expected a compression_settings mismatch, got: {mismatches}",
        )

    def test_wrong_lod_group_is_reported(self):
        """Test: a wrong lod_group value is caught and named."""
        wrong = dict(CORRECT_INTENDED)
        wrong["lod_group"] = "TEXTUREGROUP_WORLD"
        tex = FakeTexture(**wrong)
        mismatches = verify_texture_settings(tex, CORRECT_INTENDED)
        self.assertTrue(mismatches, "expected at least one mismatch")
        self.assertTrue(
            any("lod_group" in m for m in mismatches),
            f"expected a lod_group mismatch, got: {mismatches}",
        )

    def test_wrong_srgb_is_reported(self):
        """Test C: a wrong srgb value is caught and named."""
        wrong = dict(CORRECT_INTENDED)
        wrong["srgb"] = False
        tex = FakeTexture(**wrong)
        mismatches = verify_texture_settings(tex, CORRECT_INTENDED)
        self.assertTrue(mismatches, "expected at least one mismatch")
        self.assertTrue(
            any("srgb" in m for m in mismatches),
            f"expected a srgb mismatch, got: {mismatches}",
        )

    def test_multiple_wrong_settings_are_all_reported(self):
        """Both wrong properties should be individually named, not just the
        first one found."""
        wrong = dict(CORRECT_INTENDED)
        wrong["compression_settings"] = "TC_DEFAULT_BC7"
        wrong["mip_gen_settings"] = "TMGS_FROM_TEXTURE_GROUP"
        tex = FakeTexture(**wrong)
        mismatches = verify_texture_settings(tex, CORRECT_INTENDED)
        self.assertEqual(len(mismatches), 2)


def make_fake_texture(base_cls, stuck=(), **properties):
    """A get/set_editor_property texture double that IS-A the given fake
    unreal.Texture2D, so import_one's isinstance(texture, unreal.Texture2D)
    check passes.

    `stuck` names properties that silently refuse to change on
    set_editor_property (stay at their initial `properties` value forever).
    This simulates the real-world failure mode the read-back verification
    in import_one exists to catch: import_one calls set_editor_property
    with the correct values immediately before verifying, so to exercise
    the "it didn't actually take" path, at least one property has to
    reject that write, same as a real engine build occasionally ignoring a
    property set."""

    class _FakeTexture(base_cls):
        def __init__(self):
            self._properties = dict(properties)
            self._stuck = set(stuck)

        def get_editor_property(self, name):
            return self._properties[name]

        def set_editor_property(self, name, value):
            if name in self._stuck:
                return
            self._properties[name] = value

    return _FakeTexture()


def make_fake_unreal(log_sink):
    """Build a minimal fake `unreal` module: just enough surface
    (AssetImportTask, load_asset, the 3 enums, Texture2D, log/log_error/
    log_warning, EditorAssetLibrary, AssetToolsHelpers) to drive
    import_icons.import_one()/main()'s control flow with no real UE editor
    present. `log_sink` is a list that (level, message) tuples get
    appended to. Returns the fake module; the caller populates
    `fake.textures` (asset_name -> texture double) before use."""

    fake = types.ModuleType("unreal")
    textures = {}

    class Texture2D:
        pass

    class TextureGroup:
        TEXTUREGROUP_UI = "TEXTUREGROUP_UI"

    class TextureCompressionSettings:
        TC_EDITOR_ICON = "TC_EDITOR_ICON"

    class TextureMipGenSettings:
        TMGS_NO_MIPMAPS = "TMGS_NO_MIPMAPS"

    class AssetImportTask:
        def __init__(self):
            self.filename = None
            self.destination_path = None
            self.destination_name = None
            self.automated = None
            self.save = None
            self.replace_existing = None

    class AssetToolsHelpers:
        @staticmethod
        def get_asset_tools():
            return types.SimpleNamespace(import_asset_tasks=lambda tasks: None)

    class EditorAssetLibrary:
        @staticmethod
        def save_loaded_asset(tex):
            pass

    def load_asset(asset_path):
        return textures.get(asset_path.rsplit("/", 1)[-1])

    def log(msg):
        log_sink.append(("log", msg))

    def log_error(msg):
        log_sink.append(("error", msg))

    def log_warning(msg):
        log_sink.append(("warning", msg))

    fake.textures = textures
    fake.Texture2D = Texture2D
    fake.TextureGroup = TextureGroup
    fake.TextureCompressionSettings = TextureCompressionSettings
    fake.TextureMipGenSettings = TextureMipGenSettings
    fake.AssetImportTask = AssetImportTask
    fake.AssetToolsHelpers = AssetToolsHelpers
    fake.EditorAssetLibrary = EditorAssetLibrary
    fake.load_asset = load_asset
    fake.log = log
    fake.log_error = log_error
    fake.log_warning = log_warning
    return fake


class ImportOneAndMainFailLoudControlFlowTests(unittest.TestCase):
    """Exercises import_one()/main()'s control flow -- mismatch detected ->
    per-property log_error -> import_one returns False -> main() collects
    the failing filename -> main() raises RuntimeError -- against a fake
    `unreal` module injected into sys.modules.

    This validates the Python-level control flow only. It does NOT
    validate the real unreal API's names/semantics (the real
    AssetImportTask, the real Texture2D class, or whether TC_EDITOR_ICON
    really round-trips through get_editor_property the same way on a real
    UE5.6 engine build). Only a real editor run can prove that part; see
    the implementer report's UNVALIDATED section."""

    def setUp(self):
        self._saved_unreal = sys.modules.get("unreal")
        self._tmpdir = tempfile.mkdtemp()
        for name in ("good", "bad"):
            open(os.path.join(self._tmpdir, f"{name}.png"), "wb").close()

        import import_icons

        self._import_icons = import_icons
        self._saved_source_folder = import_icons.SOURCE_FOLDER

    def tearDown(self):
        if self._saved_unreal is None:
            sys.modules.pop("unreal", None)
        else:
            sys.modules["unreal"] = self._saved_unreal
        self._import_icons.SOURCE_FOLDER = self._saved_source_folder
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_import_one_fails_and_logs_on_settings_mismatch(self):
        log_sink = []
        fake_unreal = make_fake_unreal(log_sink)
        sys.modules["unreal"] = fake_unreal

        good_tex = make_fake_texture(fake_unreal.Texture2D, **CORRECT_INTENDED)
        wrong = dict(CORRECT_INTENDED)
        wrong["compression_settings"] = "TC_DEFAULT_BC7"
        # "stuck": simulates set_editor_property silently not taking for
        # this property, same as a real engine build occasionally would --
        # otherwise import_one's own set_editor_property call would just
        # overwrite our seeded "wrong" value before verification ever runs.
        bad_tex = make_fake_texture(
            fake_unreal.Texture2D, stuck={"compression_settings"}, **wrong
        )
        fake_unreal.textures["good"] = good_tex
        fake_unreal.textures["bad"] = bad_tex

        fake_asset_tools = fake_unreal.AssetToolsHelpers.get_asset_tools()
        ok_good = self._import_icons.import_one(fake_asset_tools, "good.png", "good")
        ok_bad = self._import_icons.import_one(fake_asset_tools, "bad.png", "bad")

        self.assertTrue(ok_good)
        self.assertFalse(ok_bad)
        self.assertTrue(
            any(
                level == "error" and "compression_settings" in msg
                for level, msg in log_sink
            ),
            f"expected a compression_settings log_error, got: {log_sink}",
        )

    def test_main_raises_when_any_icon_fails_verification(self):
        log_sink = []
        fake_unreal = make_fake_unreal(log_sink)
        sys.modules["unreal"] = fake_unreal

        good_tex = make_fake_texture(fake_unreal.Texture2D, **CORRECT_INTENDED)
        wrong = dict(CORRECT_INTENDED)
        wrong["srgb"] = False
        bad_tex = make_fake_texture(fake_unreal.Texture2D, stuck={"srgb"}, **wrong)
        fake_unreal.textures["good"] = good_tex
        fake_unreal.textures["bad"] = bad_tex

        self._import_icons.SOURCE_FOLDER = self._tmpdir

        with self.assertRaises(RuntimeError) as ctx:
            self._import_icons.main()
        self.assertIn("bad.png", str(ctx.exception))

    def test_main_succeeds_when_all_icons_verify_clean(self):
        log_sink = []
        fake_unreal = make_fake_unreal(log_sink)
        sys.modules["unreal"] = fake_unreal

        fake_unreal.textures["good"] = make_fake_texture(
            fake_unreal.Texture2D, **CORRECT_INTENDED
        )
        fake_unreal.textures["bad"] = make_fake_texture(
            fake_unreal.Texture2D, **CORRECT_INTENDED
        )

        self._import_icons.SOURCE_FOLDER = self._tmpdir

        self._import_icons.main()  # must not raise

        self.assertTrue(
            any(level == "log" and "2/2" in msg for level, msg in log_sink),
            f"expected a '2/2 imported' success log, got: {log_sink}",
        )


if __name__ == "__main__":
    unittest.main()
