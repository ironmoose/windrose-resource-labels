"""import_icons.py -- OPTIONAL, PHASE 2. Not needed for the single-icon
cook kit proof (see docs/cook-kit-win11.md). Keep for when we scale past
Iron to importing many resource icons in one pass.

Batch-imports every PNG in a source folder as a UTexture2D under
/Game/UI/HUD/Building/Icons/BuildingBits/, naming each new asset after its
source filename (minus the .png extension), and applies the same import
settings the cook-kit guide has you set by hand in Step 2 of
docs/cook-kit-win11.md:

    Texture Group        = UI
    Compression Settings  = UserInterface2D (RGBA8) uncompressed -- matches
                             the proven Iron cook (PF_B8G8R8A8)
                             (Python: TC_EDITOR_ICON)
    sRGB                  = ON
    Mip Gen Settings      = NoMipmaps

After applying those settings, this script reads each one back and fails
loud (raises, does not just log) if any imported icon doesn't match, so a
batch run of many icons can't silently succeed with wrong settings on some
of them. See verify_texture_settings() below.

Run this from inside the Unreal Editor: open the project, then use
Tools > Execute Python Script (or the Output Log's Python console) and
point it at this file. It can also be run non-interactively via the
editor's command line, for example:

    UnrealEditor-Cmd.exe "C:\\WindroseIcons\\WindroseIcons.uproject" -run=pythonscript -script="import_icons.py"

or with the newer -ExecutePythonScript flag on some engine versions:

    UnrealEditor-Cmd.exe "C:\\WindroseIcons\\WindroseIcons.uproject" -ExecutePythonScript="import_icons.py"

NOTE on TC_EDITOR_ICON: this is the Python enum member for the Texture
Editor's "UserInterface2D (RGBA8)" compression dropdown entry, per Unreal's
TextureCompressionSettings enum (the "Editor Icon" internal name predates
the current on-screen label). It stores the texture uncompressed as RGBA8
-- this is what reproduces the proven Iron cook's PF_B8G8R8A8 format. BC7
is a separate, block-compressed dropdown entry and is NOT what we want
here (BC7 would cook to a much smaller, lossy-compressed .uexp, roughly
64 KB at 256x256 versus the ~262 KB RGBA8 the proven Iron cook produced).
If this looks wrong once you can see it running (for example the dropdown
value it lands on doesn't match "UserInterface2D (RGBA8)" in the Texture
Editor), fall back to setting that one property by hand per icon, same as
Step 2 of docs/cook-kit-win11.md.

STRUCTURAL NOTE: `import unreal` only works inside a running UE editor
Python environment; it cannot be imported on a plain machine (this repo is
public and developed partly on Fedora, with no editor installed). So this
module does NOT import unreal at module scope -- only the functions that
actually need it (import_one, get_intended_settings, main) import it
locally, on demand. verify_texture_settings() below has zero unreal
dependency at all, which is what makes it unit-testable off of a Windows
UE box; see test_import_icons.py.
"""

import os

# --- Configuration: edit these two paths before running --------------------

# Folder on disk containing one or more source PNGs, one per resource icon.
SOURCE_FOLDER = r"C:\WindroseIcons\SourceIcons"

# Destination folder inside the project's Content Browser. Matches the
# game's own icon path (see docs/HOW-IT-WORKS.md).
DEST_PATH = "/Game/UI/HUD/Building/Icons/BuildingBits"


def verify_texture_settings(tex, intended):
    """Pure verifier: read back tex's editor properties and compare each
    one against `intended`. Returns a list of human-readable mismatch
    strings, one per property that doesn't match; an empty list means
    everything matches.

    `tex` only needs to duck-type get_editor_property(name) (this is true
    of a real unreal.Texture2D, and of any test double). `intended` is a
    mapping of property-name -> expected value, compared with `==`.

    This function never imports or otherwise requires `unreal` -- callers
    (e.g. import_one, below) are responsible for building `intended` out of
    real unreal enum values when running for real. That split is what
    keeps this function importable and testable on a machine with no UE
    editor installed.
    """
    mismatches = []
    for name, expected in intended.items():
        actual = tex.get_editor_property(name)
        if actual != expected:
            mismatches.append(f"{name}: expected {expected!r}, got {actual!r}")
    return mismatches


def get_intended_settings():
    """The 4 import settings from docs/cook-kit-win11.md Step 2, as an
    editor-property-name -> value mapping, using the real unreal enum
    values. Requires `unreal` (imported locally) -- not callable on a
    machine with no UE editor installed.
    """
    import unreal

    return {
        "lod_group": unreal.TextureGroup.TEXTUREGROUP_UI,
        "compression_settings": unreal.TextureCompressionSettings.TC_EDITOR_ICON,
        "srgb": True,
        "mip_gen_settings": unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS,
    }


def import_one(asset_tools, png_path, asset_name):
    """Import a single PNG as a texture asset named asset_name, then apply
    the cook-kit's standard icon import settings. Reads the settings back
    afterward and fails (returns False, logs an error per mismatched
    property) if any of them didn't take."""

    import unreal

    task = unreal.AssetImportTask()
    task.filename = png_path
    task.destination_path = DEST_PATH
    task.destination_name = asset_name
    task.automated = True
    task.save = True
    task.replace_existing = True

    asset_tools.import_asset_tasks([task])

    asset_path = f"{DEST_PATH}/{asset_name}"
    texture = unreal.load_asset(asset_path)

    if texture is None:
        unreal.log_error(f"import_icons: failed to load imported asset {asset_path}")
        return False

    if not isinstance(texture, unreal.Texture2D):
        unreal.log_warning(
            f"import_icons: {asset_path} did not import as a Texture2D, "
            "skipping settings"
        )
        return False

    texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property(
        "compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON
    )
    texture.set_editor_property("srgb", True)
    texture.set_editor_property(
        "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS
    )

    # Read the 4 properties back and fail loud (per-property) if any of
    # them didn't actually take. This is what makes a batch run safe with
    # zero per-icon manual settings: a silently-wrong icon can't sneak
    # through as a "success".
    mismatches = verify_texture_settings(texture, get_intended_settings())
    if mismatches:
        for mismatch in mismatches:
            unreal.log_error(
                f"import_icons: {asset_path} import setting mismatch: {mismatch}"
            )
        return False

    # Non-fatal: warn (never fail) if we can determine the imported texture
    # isn't square. The exact size accessor can differ across engine
    # builds, so this best-effort read never raises.
    try:
        width = texture.get_size_x()
        height = texture.get_size_y()
    except Exception:
        width = height = None
    if width and height and width != height:
        unreal.log_warning(
            f"import_icons: {asset_path} is not square ({width}x{height})"
        )

    unreal.EditorAssetLibrary.save_loaded_asset(texture)
    unreal.log(f"import_icons: imported and configured {asset_path}")
    return True


def main():
    import unreal

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    if not os.path.isdir(SOURCE_FOLDER):
        unreal.log_error(f"import_icons: SOURCE_FOLDER not found: {SOURCE_FOLDER}")
        return

    pngs = sorted(f for f in os.listdir(SOURCE_FOLDER) if f.lower().endswith(".png"))
    if not pngs:
        unreal.log_warning(f"import_icons: no PNGs found in {SOURCE_FOLDER}")
        return

    imported = 0
    failed = []
    for filename in pngs:
        asset_name = os.path.splitext(filename)[0]
        png_path = os.path.join(SOURCE_FOLDER, filename)
        try:
            ok = import_one(asset_tools, png_path, asset_name)
        except Exception as e:
            unreal.log_error(
                f"import_icons: unexpected exception importing {filename}: {e}"
            )
            failed.append(filename)
            continue
        if ok:
            imported += 1
        else:
            failed.append(filename)

    if failed:
        unreal.log_error(
            "import_icons: FAILED - {0}/{1} icon(s) had import or "
            "settings-verification problems: {2}".format(
                len(failed), len(pngs), ", ".join(failed)
            )
        )
        raise RuntimeError(
            f"import_icons: {len(failed)} of {len(pngs)} icon(s) failed "
            f"import or settings verification: {', '.join(failed)}"
        )

    unreal.log(f"import_icons: done, {imported}/{len(pngs)} icon(s) imported")


if __name__ == "__main__":
    main()
