# BDGS map vote thumbnails

Real map thumbnails in the BDGS end-of-match vote, for players running this IW4x client.
Players on the standard IW4x client keep the normal BDGS text vote.

**No fs_game mod is used**, so nobody's stats or custom classes are switched or reset.
(The original map vote mod ran as `mods\mapvote`; IW4x keeps separate stats inside a mod,
which is why classes looked reset there.)

## What's in this branch

| Part | File | What it does |
|---|---|---|
| Client | `src/Components/Modules/FastFiles.cpp` | Loads `zone\dlc\bdgs_vote.ff` (thumbnail materials) as a core zone if it exists, and sets `bdgs_thumbs 1` |
| Client | `FastFiles.cpp` (dvar `bdgs_thumbs`) | Userinfo flag that tells the server "this player can show thumbnails" |
| Server | `src/Components/Modules/GSC/UserInfo.cpp` | New GSC method `self GetUserInfo( key )` so scripts can read that flag |
| Assets | `bdgs/tools/build_bdgs_vote.py` | Builds the images + 6-tile menu (`main\z_bdgs_vote.iwd`) and the materials (`zone\dlc\bdgs_vote.ff`) |
| Server | `bdgs/server/scripts/bdgs_vote_menu.gsc` | Opens the thumbnail menu for flagged players and passes their votes to your vote script |

The same `iw4x.dll` is used on the server and by players.

## 1. Build the dll

Push to this repo and let GitHub Actions build it (same as your other fork), then download `iw4x.dll` from the run's artifacts.

## 2. Build the thumbnail files (on the server PC)

You need: Python 3, `zonebuilder.exe` in the MW2 folder, and `IW4x Post Map Vote Modified v2.zip`
(fella_guy's mod - the images and menu come from it and are not stored in this repo).

From the MW2 game root (a **test copy** first, see step 4):

```
python build_bdgs_vote.py build --mod-zip "D:\path\IW4x Post Map Vote Modified v2.zip"
zonebuilder.exe          -> type:  buildmod bdgs_vote   -> close it when done
python build_bdgs_vote.py install
```

Your usermaps (including the MW3 ports) get a thumbnail from their own loadscreen image;
maps without one show the "custom map" placeholder.

Results:
- `main\z_bdgs_vote.iwd` and `zone\dlc\bdgs_vote.ff` - the client files
- `bdgs_vote_out\bdgs_vote_client.zip` - those two, for players (unzip into the MW2 folder)
- `bdgs_vote_out\bdgs_thumbs_list.gsc` - goes in the server's `scripts\` folder next to `bdgs_vote_menu.gsc`

Run it again whenever you add maps, and hand out the new client zip.

## 3. Hook it into your vote script

`bdgs_vote_menu.gsc` does not run a vote on its own. Your existing vote keeps all the rules
(weekday/weekend mix, sizes by player count, FFA under 4, 9+ players originals only) and the tally;
it just opens the picture menu for players who have it. The comment at the top of the file
shows the 6 calls to add.

## 4. Test before it goes on BDGS

1. Second server on another port (not the live BDGS) with the new `iw4x.dll`, the two GSC files and your vote script.
2. One PC with the **standard** IW4x client, one with **this** client + the client zip.
3. Check: the standard client gets the text vote; this client gets thumbnails; votes from both count;
   the winning map loads; custom classes are the same before and after (both clients).
4. Only then copy to BDGS - at the 2 AM restart, not while people are playing.

Warning: `GetUserInfo` only exists in this dll. With `bdgs_vote_menu.gsc` on a server running the stock
`iw4x.dll`, the scripts fail to compile and the whole server's scripts stop.

## Credits

Vote menu, thumbnail images and material template: **IW4x Post Map Vote Modified** by fella_guy,
based on the **Map Vote Menu Mod** by |UzD|GaZa.
