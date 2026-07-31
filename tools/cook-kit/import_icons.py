"""import_icons.py -- OPTIONAL, PHASE 2. Not needed for the single-icon
cook kit proof (see docs/cook-kit-win11.md). Keep for when we scale past
Iron to importing many resource icons in one pass.

Batch-imports every PNG in a source folder as a UTexture2D under
/Game/UI/HUD/Building/Icons/BuildingBits/, naming each new asset after its
source filename (minus the .png extension), and applies the same import
settings the cook-kit guide has you set by hand in Step 2 of
docs/cook-kit-win11.md:

    Texture Group        = UI
    Compression Settings  = UserInterface2D (BC7)   (Python: TC_EDITOR_ICON)
    sRGB                  = ON
    Mip Gen Settings      = NoMipmaps

Run this from inside the Unreal Editor: open the project, then use
Tools > Execute Python Script (or the Output Log's Python console) and
point it at this file. It can also be run non-interactively via the
editor's command line, for example:

    UnrealEditor-Cmd.exe "C:\\WindroseIcons\\WindroseIcons.uproject" -run=pythonscript -script="import_icons.py"

or with the newer -ExecutePythonScript flag on some engine versions:

    UnrealEditor-Cmd.exe "C:\\WindroseIcons\\WindroseIcons.uproject" -ExecutePythonScript="import_icons.py"

NOTE on TC_EDITOR_ICON: this is the Python enum member for the Texture
Editor's "UserInterface2D (BC7)" compression dropdown entry, per Unreal's
TextureCompressionSettings enum (the "Editor Icon" internal name predates
the current on-screen label). If this looks wrong once you can see it
running (for example the dropdown value it lands on doesn't match
"UserInterface2D (BC7)" in the Texture Editor), fall back to setting that
one property by hand per icon, same as Step 2 of docs/cook-kit-win11.md.
"""

import os

import unreal

# --- Configuration: edit these two paths before running --------------------

# Folder on disk containing one or more source PNGs, one per resource icon.
SOURCE_FOLDER = r"C:\WindroseIcons\SourceIcons"

# Destination folder inside the project's Content Browser. Matches the
# game's own icon path (see docs/HOW-IT-WORKS.md).
DEST_PATH = "/Game/UI/HUD/Building/Icons/BuildingBits"


def import_one(asset_tools, png_path, asset_name):
    """Import a single PNG as a texture asset named asset_name, then apply
    the cook-kit's standard icon import settings."""

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

    unreal.EditorAssetLibrary.save_loaded_asset(texture)
    unreal.log(f"import_icons: imported and configured {asset_path}")
    return True


def main():
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    if not os.path.isdir(SOURCE_FOLDER):
        unreal.log_error(f"import_icons: SOURCE_FOLDER not found: {SOURCE_FOLDER}")
        return

    pngs = sorted(f for f in os.listdir(SOURCE_FOLDER) if f.lower().endswith(".png"))
    if not pngs:
        unreal.log_warning(f"import_icons: no PNGs found in {SOURCE_FOLDER}")
        return

    imported = 0
    for filename in pngs:
        asset_name = os.path.splitext(filename)[0]
        png_path = os.path.join(SOURCE_FOLDER, filename)
        if import_one(asset_tools, png_path, asset_name):
            imported += 1

    unreal.log(f"import_icons: done, {imported}/{len(pngs)} icon(s) imported")


if __name__ == "__main__":
    main()
