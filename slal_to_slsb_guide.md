# Guide for Converting SLAL Packs to SLSB Format Using `convert.py`

This guide provides **step-by-step instructions** for converting **SLAL (SexLab Animation Loader)** packs to **SLSB (SexLab Scene Builder)** format using the `convert.py` script.

## **Hard Requirements**
1. **Python 3.9 or greater**: Ensure Python is installed and accessible via the command line.
2. **SexLab Scene Builder (SLSB)**: [Discord link](https://discord.com/channels/906462751101177886/1063514401375780874/1335314789194534992) (updates in `sexlab-wip-releases` channel on Scrab’s Discord)
3. **convert.py Script**: [GitHub link](https://github.com/BabyImpala/convert.py/blob/main/convert.py) (this repository)
4. **FNIS + Creature Addon**: [Nexus Mods](https://www.nexusmods.com/skyrimspecialedition/mods/3038)
5. **Command Line FNIS**: [Nexus Mods](https://www.nexusmods.com/skyrim/mods/81882)


## **Soft Requirements**
1. **hkxconv**: [Nexus Mods](https://www.nexusmods.com/skyrimspecialedition/mods/81744) (marginally expediates the conversion for some packs)
2. **SLATE_Creature Patch**: [LoversLab](https://www.loverslab.com/files/file/10316-osmelmc-mod-tweaks/)
3. **SexLab AnimStageLabels**: [LoversLab](https://www.loverslab.com/files/file/27407-sexlab-anim-stage-labels/)
4. **Hentairim tags**: [LoversLab](https://www.loverslab.com/files/file/41502-hentairim/)
5. **Hentairim Sound Effects**: [LoversLab](https://www.loverslab.com/files/file/41502-hentairim/)

## **Setting Up the Workspace**
1. Place the following files in a single directory:
   - `slsb.exe`
   - `convert.py`
   - `hkxconv.exe` (get the one with .net runtime if you gonna add it)
2. Create a subdirectory named `basegame_replica` in the same directory. Inside it, create another subdirectory named `Data`.
3. Install the following into the `Data` directory:
   - `FNIS` + `Creature Addon`
   - `Command Line FNIS`
4. Extract your SLAL pack(s) and place them in a directory titled `SLALPacks`. Ensure the path is structured like this ==> D:/SLSB/SLALPacks/BillyyCreatures/SLAnims/slal (this allows bulk conversions).
5. Open a terminal in the directory where `convert.py` is located (**Right-Click > Open in Terminal**) and type the necessary commands.

## **Useful Accepted Arguments**
| Argument | Description |
|---------|-------------|
| `-c`     | Cleans temporary files. **Always include this.** |
| `-ra`    | Removes animation files copied during behavior generation. Always use this to avoid duplicate animation HKX files (unless making a standalone SLSB conversion, in which case `-ra` can be omitted). |
| `-pco`   | Reattempts post-conversion for modules/paths with spaces. Use this if converting Anubs's or Baka's packs and post-conversion gives an error. |
| `-s "PATH"` | Specifies the Skyrim installation path (where FNIS is located). This generates the required behaviors for SLSB conversions. Almost always **required**. |
| `-slt "PATH"` | Incorporates SLATE action logs from the provided `<PATH>`. |
| `-upd "PATH"` | Incorporates hashes from SLSB JSONs located in `<PATH>`. Useful for updating public releases. |

## **If Publicly Releasing**
For public releases, ensure your SLSB conversions include the following features:

### **(a) Maintain Hashes**
SLSB and SLPP rely on hashes to identify scenes or stages. These hashes are randomly generated upon export, which can cause users to lose animation toggles (enable/disable) upon updates as well as custom allignment adjustments and inserted annotations. To avoid this:
1. Extract the latest `AutomatedSLSBConversions.7z`.
2. Search for `json` in the extracted directory.
3. Copy all JSON files to a separate folder named `SLSB_JSONS`.

### **(b) Incorporate Tag Updates**
Although SLATE is redundant with SLSB and SLPP, its ActionLogs can be incorporated by the script. These logs are significant for features like SLPP's internal enjoyment system, which detects interaction types (e.g., oral) in real-time and also makes the SLSB conversions ready for mods like HentaiRim and IVDT Hentai Edition. To include these:
1. Download and extract the archives:
   - SLATE_Creature Patch(2023_12_30).7z
   - SLAnimStageLabels.7z
   - Hentairim tags.7z
   - Hentairim Sound Effects.7z
2. Extract all JSONs from `SKSE/Plugins/SLATE/` of these extracted archives and place them in a folder titled `SLATE`.

## **Example Commands**

### **For Testing the Script**
This will not generate behaviors; only for testing the convert.py script upon changes (e.g. for priting debug info) without wasting time in generating behaviors. Can add -slt{path} and -upd{path} arguments, but don't add the -s{path}.
```bash
python3 convert.py "D:/SkyrimAE/SLSB/Tools/slsb.exe" "D:/SkyrimAE/SLSB/SLALPacks/"
```
### **Barebones SLSB Conversion**
```bash
python3 convert.py "D:/SkyrimAE/SLSB/Tools/slsb.exe" "D:\SkyrimAE\SLSB\SLALPacks" -s "D:\SkyrimAE\SLSB\Tools\base_game_replica" -c -ra
```
### **For Public Releases**
```bash
python3 convert.py "D:/SkyrimAE/SLSB/Tools/slsb.exe" "D:\SkyrimAE\SLSB\SLALPacks" -s "D:\SkyrimAE\SLSB\Tools\base_game_replica" -slt "D:/SkyrimAE/SLSB/Tools/SLATE" -upd "D:/SkyrimAE/SLSB/Tools/SLSB_JSONS" -c -ra
```
### **Reattempting Post-Conversion**
```bash
python3 convert.py "D:/SkyrimAE/SLSB/Tools/slsb.exe" "D:\SkyrimAE\SLSB\SLALPacks" -s "D:\SkyrimAE\SLSB\Tools\base_game_replica" -slt "D:/SkyrimAE/SLSB/Tools/SLATE" -upd "D:/SkyrimAE/SLSB/Tools/SLSB_JSONS" -c -ra -pco
```
