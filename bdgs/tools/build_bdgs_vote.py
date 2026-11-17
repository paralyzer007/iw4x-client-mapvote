#!/usr/bin/env python3
"""
BDGS map vote thumbnails - asset builder.

Builds the files that players running the BDGS IW4x client need to see map
thumbnails in the end-of-match vote, WITHOUT an fs_game mod (so player stats
and custom classes are never switched or reset).

Run from your MW2 game root (the folder with iw4x.exe / zonebuilder.exe):

  Step 1:  python build_bdgs_vote.py build --mod-zip "C:\\path\\IW4x Post Map Vote Modified v2.zip"
  Step 2:  zonebuilder.exe   then type:  buildmod bdgs_vote   (close it when done)
  Step 3:  python build_bdgs_vote.py install

Outputs:
  main\\z_bdgs_vote.iwd             thumbnail images + ui_mp\\scriptmenus\\bdgs_vote.menu
  zone\\dlc\\bdgs_vote.ff            the thumbnail materials (after step 2 + 3)
  bdgs_vote_out\\bdgs_thumbs_list.gsc  list of maps that have a thumbnail (server)
  bdgs_vote_out\\bdgs_vote_client.zip  the two client files, ready to hand out

Thumbnail images, the material template and the vote menu come from
"IW4x Post Map Vote Modified" by fella_guy (original Map Vote Menu Mod by
|UzD|GaZa). They are read from your copy of the zip, not shipped in this repo.
"""
import argparse
import os
import re
import shutil
import sys
import zipfile

ROOT = os.getcwd()
MOD_NAME = "bdgs_vote"
MOD_DIR = os.path.join(ROOT, "mods", MOD_NAME)
CSV_PATH = os.path.join(ROOT, "zone_source", MOD_NAME + ".csv")
IWD_PATH = os.path.join(ROOT, "main", "z_bdgs_vote.iwd")
ZONE_DST = os.path.join(ROOT, "zone", "dlc", MOD_NAME + ".ff")
OUT_DIR = os.path.join(ROOT, "bdgs_vote_out")
USERMAPS = os.path.join(ROOT, "usermaps")

SRC_PREFIX = "IW4x Post Map Vote Modified/"
# Shader/techset files the "2d" preview material needs (from the mod's f8 folder)
TECH_DIRS = ("techsets/", "techniques/", "ps/", "vs/", "decl/")
TILE_COUNT = 6  # BDGS vote shows 6 maps


def die(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def read_mod_zip(path):
    if not os.path.isfile(path):
        die("mod zip not found: " + path)
    z = zipfile.ZipFile(path)
    names = z.namelist()

    def find(suffix):
        for n in names:
            if n.replace("\\", "/").endswith(suffix):
                return n
        die("not found in mod zip: " + suffix)

    template = z.read(find("mods/previewName.iw4x.json")).decode("utf-8")
    inner = z.read(find("mods/mapvote/z_mapvote.iwd"))

    tech = {}
    for n in names:
        rel = n.replace("\\", "/")
        if "/mods/f8/" in rel and not rel.endswith("/"):
            sub = rel.split("/mods/f8/", 1)[1]
            if sub.startswith(TECH_DIRS):
                tech[sub] = z.read(n)
    if not tech:
        die("no techset/shader files found in the mod zip (mods/f8)")

    import io
    iz = zipfile.ZipFile(io.BytesIO(inner))
    images, menu = {}, None
    for n in iz.namelist():
        low = n.lower()
        if low.startswith("images/preview_") and low.endswith(".iwi"):
            images[os.path.basename(n)[:-4].lower()] = iz.read(n)
        elif low.endswith("scriptmenus/vote.menu"):
            menu = iz.read(n).decode("latin-1")
    if not menu:
        die("vote.menu not found inside z_mapvote.iwd")
    return template, tech, images, menu


def find_loadscreen(iwd_path, mapname):
    """Pick the loadscreen image out of a usermap's .iwd."""
    try:
        with zipfile.ZipFile(iwd_path) as iwd:
            imgs = [f for f in iwd.namelist()
                    if f.lower().startswith("images/") and f.lower().endswith(".iwi")]
            key = mapname.lower()
            for test in (lambda f: "loadscreen" in f and key in f,
                         lambda f: "loadscreen" in f,
                         lambda f: "screen" in f and "mp_" in f):
                hits = [f for f in imgs if test(f.lower())]
                if hits:
                    return iwd.read(hits[0])
    except zipfile.BadZipFile:
        print("  bad iwd, skipped: " + iwd_path)
    return None


def usermap_images():
    found = {}
    if not os.path.isdir(USERMAPS):
        return found
    for m in sorted(os.listdir(USERMAPS)):
        iwd = os.path.join(USERMAPS, m, m + ".iwd")
        if not os.path.isfile(iwd):
            continue
        data = find_loadscreen(iwd, m)
        if data:
            found["preview_" + m.lower()] = data
        else:
            print("  no loadscreen image in usermap " + m + " (will show placeholder)")
    return found


def block_end(s, start):
    i = s.index("{", start)
    depth = 0
    while True:
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1


def make_menu(menu):
    """vote.menu (9 tiles) -> bdgs_vote.menu (6 tiles, own name)."""
    out, pos = [], 0
    removed = 0
    while True:
        j = menu.find("itemDef", pos)
        if j < 0:
            out.append(menu[pos:])
            break
        e = block_end(menu, j)
        block = menu[j:e]
        m = re.search(r"\bname\s+map(\d+)", block)
        if m and int(m.group(1)) > TILE_COUNT:
            # drop the block (and the whitespace before it)
            out.append(menu[pos:j].rstrip(" \t"))
            removed += 1
        else:
            out.append(menu[pos:e])
        pos = e
    s = "".join(out)
    s, n = re.subn(r"(\bname\s+)vote\b", r"\1bdgs_vote", s, count=1)
    if n != 1 or removed == 0:
        die("vote.menu layout not recognised (removed %d tiles)" % removed)
    header = ("// BDGS map vote menu (6 tiles). Based on the Map Vote Menu Mod by |UzD|GaZa,\n"
              "// modified by fella_guy. Trimmed and renamed for BDGS by build_bdgs_vote.py.\n")
    return header + s


def build(args):
    template, tech, images, menu = read_mod_zip(args.mod_zip)
    print("Mod zip: %d thumbnails, %d shader files" % (len(images), len(tech)))

    um = usermap_images()
    print("Usermaps: %d thumbnails" % len(um))
    for k, v in um.items():
        images.setdefault(k, v)  # official images win over usermap ones

    if "preview_custom_map" not in images:
        die("placeholder image preview_custom_map missing from mod zip")

    # 1) client iwd: images + menu
    os.makedirs(os.path.dirname(IWD_PATH), exist_ok=True)
    tmp = IWD_PATH + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as iwd:
        for name in sorted(images):
            iwd.writestr("images/%s.iwi" % name, images[name])
        iwd.writestr("ui_mp/scriptmenus/bdgs_vote.menu", make_menu(menu).encode("latin-1"))
    os.replace(tmp, IWD_PATH)
    print("Wrote " + IWD_PATH)

    # 2) ZoneBuilder sources: materials + techset, csv
    if os.path.isdir(MOD_DIR):
        shutil.rmtree(MOD_DIR)
    for rel, data in tech.items():
        p = os.path.join(MOD_DIR, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
    mat_dir = os.path.join(MOD_DIR, "materials")
    img_dir = os.path.join(MOD_DIR, "images")
    os.makedirs(mat_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)
    for name in sorted(images):
        with open(os.path.join(mat_dir, name + ".iw4x.json"), "w", encoding="utf-8") as f:
            f.write(template.replace("previewName", name))
        with open(os.path.join(img_dir, name + ".iwi"), "wb") as f:
            f.write(images[name])
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8") as f:
        f.write("# BDGS map vote thumbnails - generated by build_bdgs_vote.py\n")
        for name in sorted(images):
            f.write("material,%s\n" % name)
    print("Wrote %s and %s" % (MOD_DIR, CSV_PATH))

    # 3) server list of maps with thumbnails
    os.makedirs(OUT_DIR, exist_ok=True)
    maps = sorted(n[len("preview_"):] for n in images if n != "preview_custom_map")
    lines = ["// Generated by build_bdgs_vote.py - maps that have a vote thumbnail.",
             "// Rebuild and redeploy together with zone\\dlc\\bdgs_vote.ff.",
             "", "get()", "{", "\tlist = [];"]
    lines += ['\tlist["%s"] = true;' % m for m in maps]
    lines += ["\treturn list;", "}", ""]
    with open(os.path.join(OUT_DIR, "bdgs_thumbs_list.gsc"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote %d map names to bdgs_vote_out\\bdgs_thumbs_list.gsc" % len(maps))

    print("\nNext: open zonebuilder.exe, type  buildmod %s  and close it when done,"
          "\nthen run:  python build_bdgs_vote.py install" % MOD_NAME)


def install(args):
    src = os.path.join(MOD_DIR, "mod.ff")
    if not os.path.isfile(src):
        die("mods\\%s\\mod.ff not found - run ZoneBuilder 'buildmod %s' first" % (MOD_NAME, MOD_NAME))
    if not os.path.isfile(IWD_PATH):
        die("main\\z_bdgs_vote.iwd missing - run the build step first")
    os.makedirs(os.path.dirname(ZONE_DST), exist_ok=True)
    shutil.copyfile(src, ZONE_DST)
    os.remove(src)  # never leave a loadable mod.ff behind in mods\
    print("Installed " + ZONE_DST)

    os.makedirs(OUT_DIR, exist_ok=True)
    pkg = os.path.join(OUT_DIR, "bdgs_vote_client.zip")
    with zipfile.ZipFile(pkg, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(IWD_PATH, "main/z_bdgs_vote.iwd")
        z.write(ZONE_DST, "zone/dlc/bdgs_vote.ff")
    print("Client package: " + pkg + "  (unzip into the MW2 folder of players using the BDGS client)")


def main():
    ap = argparse.ArgumentParser(description="Build BDGS map vote thumbnails")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="step 1: prepare images, menu and ZoneBuilder sources")
    b.add_argument("--mod-zip", required=True, help='path to "IW4x Post Map Vote Modified v2.zip"')
    sub.add_parser("install", help="step 3: after 'buildmod bdgs_vote' in ZoneBuilder")
    args = ap.parse_args()
    if not os.path.isfile(os.path.join(ROOT, "iw4x.exe")) and not os.path.isdir(os.path.join(ROOT, "main")):
        die("run this from your MW2 game root (the folder with iw4x.exe and main\\)")
    build(args) if args.cmd == "build" else install(args)


if __name__ == "__main__":
    main()
