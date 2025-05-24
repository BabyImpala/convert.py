import os
import pathlib
import subprocess
import shutil
import json
import argparse
import re
import pprint
from datetime import datetime
from typing import Iterable

#Script Version: 0.9d v3 (to be used with SLSB v1.5.3+)
pp = pprint.PrettyPrinter(indent=4)
parser = argparse.ArgumentParser(
                    prog='Sexlab Catalytic Converter',
                    description='Converts SLAL anims to SLSB automagically')

parser.add_argument('slsb', help='path to your slsb executable')
parser.add_argument('working', help='path to your working directory; should be structured as {<working_dir>/<slal_pack>/SLAnims/json/}')
parser.add_argument('-a', '--author', help='name of the author of the pack', default='Unknown')
parser.add_argument('-c', '--clean', help='clean up temp dir after conversion', action='store_true')
parser.add_argument('-s', '--skyrim', help='path to your skyrim directory', default=None)
parser.add_argument('-slt', '--slate', help='path to the directory containig SLATE_ActionLog jsons', default=None)
parser.add_argument('-upd', '--update', help='if updating a public conversion, give path to the dir containig SLSB project jsons', default=None)
parser.add_argument('-ra', '--remove_anims', help='remove copied animations during fnis behaviour gen', action='store_true')
parser.add_argument('-nb', '--no_build', help='do not build the slsb project', action='store_true')
parser.add_argument('-pco', '--post-conversion-only', help='only reattempts the post-conversion part', action='store_true')
parser.add_argument('-sf', '--stricter_futa', help="only scenes with 'futa' tag (plus male_human x female_creature scenes) are futa compatible", action='store_true')
#parser.add_argument('-ff', '--flexible_futa', help='flags all positions with strap_on as futa compatible', action='store_true') #default

args = parser.parse_args()
slsb_path = args.slsb
skyrim_path = args.skyrim
slate_path = args.slate
slsb_json_path = args.update
fnis_path = skyrim_path + '/Data/tools/GenerateFNIS_for_Modders' if skyrim_path is not None else None
tmp_log_dir = fnis_path + '/temporary_logs' if skyrim_path is not None else None
remove_anims = args.remove_anims
stricter_futa = args.stricter_futa
parent_dir = args.working

unique_animlist_options = []
misplaced_slal_packs = []
xml_with_spaces = []
anim_cleanup_dirs = set()

timestamp = datetime.now().strftime('[%Y%m%d_%H%M%S]')

if args.post_conversion_only:
    print('\n\033[92m' + "=========> REATTEMPTING POST-CONVERSION" + '\033[0m')
else:
    if os.path.exists(parent_dir + "\\conversion"):
        conversion_subdir = os.path.join(parent_dir + "\\conversion", timestamp)
        os.makedirs(conversion_subdir, exist_ok=True)
        for item in os.listdir(parent_dir + "\\conversion"):
            item_path = os.path.join(parent_dir + "\\conversion", item)
            if not (item.startswith('[') and item.endswith(']')):
                dest_path = os.path.join(conversion_subdir, item)
                shutil.move(item_path, dest_path)

    if tmp_log_dir is not None:
        tmp_log_subdir = os.path.join(tmp_log_dir, timestamp)
        os.makedirs(tmp_log_subdir, exist_ok=True)
        
        for item in os.listdir(tmp_log_dir):
            item_path = os.path.join(tmp_log_dir, item)
            if os.path.isdir(item_path) and not (item.startswith('[') and item.endswith(']')):
                dir_path = os.path.join(tmp_log_dir, item)
                dest_dir = os.path.join(tmp_log_subdir, os.path.relpath(dir_path, tmp_log_dir))
                shutil.move(dir_path, dest_dir)
            
            if item.lower().endswith(('.xml', '.hkx')):
                file_path = os.path.join(tmp_log_dir, item)
                dest_file = os.path.join(tmp_log_subdir, os.path.relpath(file_path, tmp_log_dir))
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                shutil.move(file_path, dest_file)

################################################################
class Keywords:

    dominant: list[str] = ['rough', 'bound', 'dominant', 'domsub', 'femdom', 'femaledomination', 'maledom', 'lezdom', 'gaydom', 'bdsm']
    forced: list[str] = ['force', 'forced', 'rape', 'fbrape', 'defeated', 'conquering', 'humiliation', 'estrus']
    uses_only_agg_tag: list[str] = ['leito', 'kom', 'flufyfox', 'gs', 'cobalt', 'mastermike', 'nya', 'rydin', 'nibbles', 'anubs']
    unconscious: list[str] = ['necro', 'dead', 'unconscious']#, 'sleep', 'drunk']
    futa_kwds: list[str] = ['futa', 'futanari', 'futaxfemale']
    leadin_kwds: list[str] = ['kissing', 'hugging', 'holding', 'loving', 'foreplay', 'lying', 'kneeling', 'cuddle', 'sfw', 'romance']
    not_leadin: list[str] = ['vaginal', 'anal', 'oral', 'blowjob', 'cunnilingus', 'forced', 'sex', 'masturbation']
    fem_cre_body_only: list[str] = ['Chicken', 'Goat', 'Cow', 'Seeker', 'Wispmother', 'Hagraven', 'Spriggan', 'Flame Atronach']
    furniture: list[str] = [
        'alchemywb', 'bed', 'bench', 'cage', 'chair', 'coffin', 'counter', 'couch', 'desk',
        'doublebed', 'doublebeds', 'drawer', 'dwemerchair', 'enchantingwb', 'furn', 'furotub',
        'gallows', 'haybale', 'javtable', 'lowtable', 'necrochair', 'pillory', 'pillorylow',
        'pole', 'rpost', 'shack', 'sofa', 'spike', 'table', 'throne', 'torturerack', 'tub',
        'wall', 'wheel', 'woodenpony', 'workbench', 'xcross'
    ]
    allowed_furnitures: dict[str, list[str]] = {
        'beds': ['BedRoll', 'BedDouble', 'BedSingle'],
        'walls': ['Wall', 'Railing'],
        'crafting': ['CraftCookingPot', 'CraftAlchemy', 'CraftEnchanting', 'CraftSmithing', 'CraftAnvil', 'CraftWorkbench', 'CraftGrindstone'],
        'tables': ['Table', 'TableCounter'],
        'chairs': ['Chair', 'ChairCommon', 'ChairWood', 'ChairBar', 'ChairNoble', 'ChairMisc'],
        'benches': ['Bench', 'BenchNoble', 'BenchMisc'],
        'thrones': ['Throne', 'ThroneRiften', 'ThroneNordic'],
        'contraptions': ['XCross', 'Pillory']
    }

################################################################
class Tags:

    def if_any_found(tags:Iterable, _any:list[str]|str, *extra_any:Iterable) -> bool:
        if isinstance(_any, str):
            _any = [_any]
        if _any == [] or any(item in tags for item in _any) or any(item in extra_check for extra_check in extra_any for item in _any):
            return True
        return False

    def if_then_add(tags:list[str], scene_name:str, anim_dir_name:str, _any:list[str]|str, not_any:list[str]|str, add:str) -> None:
        if add not in tags and Tags.if_any_found(tags, _any, scene_name, anim_dir_name) and not Tags.if_any_found(tags, not_any):
            tags.append(add)

    def if_then_add_simple(tags:list[str], _any:list[str]|str, add:str) -> None:
        if add not in tags and Tags.if_any_found(tags, _any):
            tags.append(add)

    def if_in_then_add(tags:list[str], list:list[str], _any:list[str]|str, add:str) -> None:
        if add not in tags and Tags.if_any_found(list, _any):
            tags.append(add)

    def if_then_remove(tags:list[str], all_in_tags:list[str], any_not_in_tags:list[str], remove:str) -> None:
        if remove in tags and all(item in tags for item in all_in_tags) and not Tags.if_any_found(tags, any_not_in_tags):
            tags.remove(remove)

    def if_then_replace(tags: list[str], remove: str, add: str) -> None:
        if remove in tags:
            tags.remove(remove)
            if add not in tags:
                tags.append(add)

    def bulk_add(tags:list[str], add:list[str]|str) -> None:
        if isinstance(add, str):
            add = [add]
        for item in add:
            if item and item not in tags:
                tags.append(item)

    def bulk_remove(tags:list[str], remove:list[str]|str) -> None:
        if isinstance(remove, str):
            remove = [remove]
        for item in remove:
            if item in tags:
                tags.remove(item)

################################################################
class TagsRepairer:

    def update_stage_tags(tags:list[str], scene_name:str, anim_dir_name:str) -> None:
        s = scene_name
        d = anim_dir_name
        # tags corrections
        Tags.if_then_add(tags,'','', ['laying'], ['eggs', 'egg'], 'lying')
        Tags.if_then_remove(tags, ['laying', 'lying'], ['eggs', 'egg'], 'laying')
        Tags.if_then_replace(tags, 'invfurn', 'invisfurn')
        Tags.if_then_replace(tags, 'invisible obj', 'invisfurn')
        Tags.if_then_replace(tags, 'cunnilingius', 'cunnilingus')
        Tags.if_then_replace(tags, 'agressive', 'aggressive')
        Tags.if_then_replace(tags, 'femodm', 'femdom')
        # furniutre tags
        Tags.if_then_add(tags,s,d, ['inv'], '', 'invisfurn')
        Tags.if_then_add(tags,s,d, Keywords.furniture, ['invisfurn'], 'furniture')
        Tags.if_then_remove(tags, ['invisfurn', 'furniture'], '', 'furniture')
        # unofficial standardization
        Tags.if_then_add(tags,s,d, ['femdom', 'amazon', 'cowgirl', 'femaledomination', 'female domination', 'leito xcross standing'], '', 'femdom')
        Tags.if_then_add(tags,s,d, ['basescale', 'base scale', 'setscale', 'set scale', 'bigguy'], '', 'scaling')
        Tags.if_then_add(tags,s,d, Keywords.futa_kwds, '', 'futa')
        # official standard tags
        Tags.if_then_add(tags,s,d, ['mage', 'staff', 'alteration', 'rune', 'magicdildo', 'magick'], '', 'magic')
        Tags.if_then_add(tags,s,d, ['dp', 'doublepen'], '', 'doublepenetration')
        Tags.if_then_add(tags,s,d, ['tp', 'triplepen'], '', 'triplepenetration')
        Tags.if_then_add(tags,s,d, ['guro', 'execution'], '', 'gore')
        Tags.if_then_add(tags,s,d, ['choke', 'choking'], '', 'asphyxiation')
        Tags.if_then_add(tags,s,d, ['titfuck', 'tittyfuck'], '', 'boobjob')
        Tags.if_then_add(tags,s,d, ['trib', 'tribbing'], '', 'tribadism')
        Tags.if_then_add(tags,s,d, ['doggystyle', 'doggy'], '', 'doggy')
        Tags.if_then_add(tags,s,d, ['facesit'], '', 'facesitting')
        Tags.if_then_add(tags,s,d, ['lotus'], '', 'lotusposition')
        Tags.if_then_add(tags,s,d, ['spank'], '', 'spanking')
        Tags.if_then_add(tags,s,d, ['rimjob'], '', 'rimming')
        Tags.if_then_add(tags,s,d, ['kiss'], '', 'kissing')
        Tags.if_then_add(tags,s,d, ['hold'], '', 'holding')
        Tags.if_then_add(tags,s,d, ['69'], '', 'sixtynine')
        if '' in tags:
            tags.remove('')

    def apply_submissive_flags(tags:list[str], scene_name:str, anim_dir_name:str) -> None:
        sub_tags: dict[str, bool] = {
            'unconscious': False,   # necro stuff
            'gore': False,          # something gets chopped off
            'amputee': False,       # missing one/more limbs
            'ryona': False,         # dilebrately hurting sub
            'humiliation': False,   # includes punishments too
            'forced': False,        # rape and general non-consensual
            'asphyxiation': False,  # involving choking sub
            'spanking': False,      # you guessed it
            'dominant': False       # consensual bdsm
        }
        s = scene_name
        d = anim_dir_name
        # disibuting submissive flags for scenes (not flags for actors)
        if Tags.if_any_found(tags, Keywords.unconscious, s,d):
            sub_tags['unconscious'] = True
        if Tags.if_any_found(tags, ['guro', 'gore'], s,d): 
            sub_tags['gore'] = True
        if Tags.if_any_found(tags, ['amputee'], s,d): 
            sub_tags['amputee'] = True
        if Tags.if_any_found(tags, ['nya', 'molag', 'psycheslavepunishment'], s,d): 
            sub_tags['ryona'] = True
        if Tags.if_any_found(tags, ['humiliation', 'punishment'], s,d): 
            sub_tags['humiliation'] = True
        if Tags.if_any_found(tags, ['asphyxiation'], s,d): 
            sub_tags['asphyxiation'] = True
        if Tags.if_any_found(tags, ['spanking'], s,d): 
            sub_tags['spanking'] = True
        if Tags.if_any_found(tags, Keywords.dominant, s,d):
            sub_tags['dominant'] = True
        # extensive treatment of forced scenes
        if Tags.if_any_found(tags, Keywords.forced, s,d):
            sub_tags['forced'] = True
        if 'aggressive' in tags:
            if Tags.if_any_found(tags, Keywords.uses_only_agg_tag, s,d):
                sub_tags['forced'] = True
        # adjust stage tags based on sub_flags
        subtags_found:list[str] = []
        for sub_tag, flag_value in sub_tags.items():
            if flag_value:
                subtags_found.append(sub_tag)
                if sub_tag not in tags:
                    tags.append(sub_tag)
            elif not flag_value and sub_tag in tags:
                tags.remove(sub_tag)
        return subtags_found

################################################################
class SLATE_ActionLogs:

    def check_hentairim_tags(tags:list[str], stage_num:int, pos_ind:str) -> None:
        rimtags = {
            # Stimulation Labels (actor getting cunnilingus/licking/fingering/etc)
            'sst': '{stage}{pos}sst',  # soft/slow
            'fst': '{stage}{pos}fst',  # intense/fast
            'bst': '{stage}{pos}bst',  # huge/fisting/big_non-pp_insertions
            # Penetration Labels (actor getting penile penetration)
            'svp': '{stage}{pos}svp',  # slow_vaginal
            'fvp': '{stage}{pos}fvp',  # fast_vaginal
            'sap': '{stage}{pos}sap',  # slow_anal
            'fap': '{stage}{pos}fap',  # fast_anal
            'scg': '{stage}{pos}scg',  # slow_vaginal_cowgirl
            'fcg': '{stage}{pos}fcg',  # fast_vaginal_cowgirl
            'sac': '{stage}{pos}sac',  # slow_anal_cowgirl
            'fac': '{stage}{pos}fac',  # fast_anal_cowgirl
            'sdp': '{stage}{pos}sdp',  # slow_double_pen
            'fdp': '{stage}{pos}fdp',  # fast_double_pen
            # Penis Action Labels (what actor's penis is doing)
            'sdv': '{stage}{pos}sdv',  # slow_giving_vaginal
            'fdv': '{stage}{pos}fdv',  # fast_giving_vaginal
            'sda': '{stage}{pos}sda',  # slow_giving_anal
            'fda': '{stage}{pos}fda',  # fast_giving_anal
            'shj': '{stage}{pos}shj',  # slow_getting_handjob
            'fhj': '{stage}{pos}fhj',  # fast_getting_handjob
            'stf': '{stage}{pos}stf',  # slow_getting_titfuck
            'ftf': '{stage}{pos}ftf',  # fast_getting_titfuck
            'smf': '{stage}{pos}smf',  # slow_getting_blowjob
            'fmf': '{stage}{pos}fmf',  # fast_getting_blowjob
            'sfj': '{stage}{pos}sfj',  # slow_getting_footjob
            'ffj': '{stage}{pos}ffj',  # fast_getting_footjob
            # Oral Labels (what actor's mouth is doing)
            'kis': '{stage}{pos}kis',  # kissing
            'cun': '{stage}{pos}cun',  # cunnilingus
            'sbj': '{stage}{pos}sbj',  # slow_giving_blowjob
            'fbj': '{stage}{pos}fbj',  # fast_giving_blowjob
        }
        tags_set = set(tags)
        rimtags_found:list[str] = []
        non_stage_tags = set()
        for entry, dynamic_tag in rimtags.items():
            static_tag = dynamic_tag.format(stage=stage_num, pos=pos_ind)
            if static_tag in tags_set:
                rimtags_found.append(entry)
            # ensure stage-specifiicity for rim-tags
            for tag in tags:
                if tag.endswith(pos_ind+entry):
                    prefix = tag[:-len(pos_ind+entry)]
                    if prefix.isdigit() and int(prefix) != stage_num:
                        non_stage_tags.add(tag)
        if non_stage_tags:
            tags[:] = [tag for tag in tags if tag not in non_stage_tags]
        return rimtags_found

    def implement_hentairim_tags(tags: list[str], rimtags: list[str]) -> None:
        Tags.bulk_add(tags, ['rimtagged'])
        # removes all stage tags that would be added by HentaiRim
        if 'rimtagged' in tags and 'rim_ind' not in tags:
            Tags.bulk_remove(tags, ['grinding','kissing','handjob','footjob','boobjob','blowjob','cunnilingus','oral','cowgirl','vaginal','anal','doublepenetration']) #'triplepenetration'
            Tags.bulk_add(tags, ['rim_ind'])
        # each stage tagged differently based on HentaiRim interactions
        Tags.if_in_then_add(tags, rimtags, ['sst', 'fst'], 'grinding')
        Tags.if_in_then_add(tags, rimtags, ['bst'], 'penetration')
        Tags.if_in_then_add(tags, rimtags, ['kis'], 'kissing')
        Tags.if_in_then_add(tags, rimtags, ['shj', 'fhj'], 'handjob')
        Tags.if_in_then_add(tags, rimtags, ['sfj', 'ffj'], 'footjob')
        Tags.if_in_then_add(tags, rimtags, ['stf', 'ftf'], 'boobjob')
        Tags.if_in_then_add(tags, rimtags, ['sbj', 'fbj', 'smf', 'fmf'], 'blowjob')
        Tags.if_in_then_add(tags, rimtags, ['cun'], 'cunnilingus')
        Tags.if_in_then_add(tags, rimtags, ['sbj', 'fbj', 'smf', 'fmf', 'cun'], 'oral')
        Tags.if_in_then_add(tags, rimtags, ['scg', 'fcg', 'sac', 'fac'], 'cowgirl')
        Tags.if_in_then_add(tags, rimtags, ['svp', 'fvp', 'sdv', 'fdv', 'scg', 'fcg'], 'vaginal')
        Tags.if_in_then_add(tags, rimtags, ['sap', 'fap', 'sda', 'fda', 'sac', 'fac'], 'anal')
        if 'sdp' in rimtags or 'fdp' in rimtags:
            Tags.bulk_add(tags, ['doublepenetration', 'vaginal', 'anal'])
        Tags.if_in_then_add(tags, rimtags, ['fst','bst','fvp','fap','fcg','fac','fdp','fdv','fda','fhj','ftf','fmf','ffj','fbj'], 'aslfast')
        Tags.if_in_then_add(tags, rimtags, ['sst','svp','sap','scg','sac','sdp','sdv','sda','shj','stf','smf','sfj','kis','cun','sbj'], 'aslslow')

    def check_asl_tags(tags:list[str], stage_num:int) -> None:
        if f'{stage_num}en' in tags:
            stage_num = stage_num - 1
        asltags = {
            'en': '{stage}en',  # end_stage
            'li': '{stage}li',  # lead_in
            'sb': '{stage}sb',  # slow_oral
            'fb': '{stage}fb',  # fast_oral
            'sv': '{stage}sv',  # slow_vaginal
            'fv': '{stage}fv',  # fast_vaginal
            'sa': '{stage}sa',  # slow_anal
            'fa': '{stage}fa',  # fast_anal
            'sr': '{stage}sr',  # spit_roast
            'dp': '{stage}dp',  # double_pen
            'tp': '{stage}tp',  # triple_pen
        }
        tags_set = set(tags)
        asltags_found:list[str] = []
        non_stage_tags = set()
        for entry, dynamic_tag in asltags.items():
            static_tag = dynamic_tag.format(stage=stage_num)
            if static_tag in tags_set:
                asltags_found.append(entry)
            # ensure stage-specifiicity for asl-tags
            for tag in tags:
                if tag.endswith(entry):
                    prefix = tag[:-len(entry)]
                    if prefix.isdigit() and int(prefix) != stage_num:
                        non_stage_tags.add(tag)
        if non_stage_tags:
            tags[:] = [tag for tag in tags if tag not in non_stage_tags]
        return asltags_found

    def implement_asl_tags(tags: list[str], asltags: list[str]) -> None:
        Tags.bulk_add(tags, ['asltagged'])
        if 'rimtagged' in tags:
            Tags.bulk_remove(tags, 'rim_ind')
            return
        # stores info on vaginal/anal tag presence (for spitroast)
        Tags.if_then_add(tags,'','', 'anal', 'vaginal', 'sranaltmp')
        Tags.if_then_add(tags,'','', 'vaginal', 'anal', 'srvagtmp')
        # removes all scene tags that would be added by ASL
        Tags.bulk_remove(tags, ['leadin', 'oral', 'vaginal', 'anal', 'spitroast', 'doublepenetration', 'triplepenetration'])
        # each stage tagged differently based on ASL interactions
        Tags.if_in_then_add(tags, asltags, ['li'], 'leadin')
        Tags.if_in_then_add(tags, asltags, ['sb', 'fb'], 'oral')
        Tags.if_in_then_add(tags, asltags, ['sv', 'fv'], 'vaginal')
        Tags.if_in_then_add(tags, asltags, ['sa', 'fa'], 'anal')
        if 'sr' in asltags:
            Tags.bulk_add(tags, ['spitroast', 'oral'])
            Tags.if_then_add_simple(tags, ['sranaltmp'], 'anal')
            Tags.if_then_add_simple(tags, ['srvagtmp'], 'vaginal')
        if 'dp' in asltags:
            Tags.bulk_add(tags, ['doublepenetration', 'vaginal', 'anal'])
        if 'tp' in asltags:
            Tags.bulk_add(tags, ['triplepenetration', 'oral', 'vaginal', 'anal'])
        Tags.if_in_then_add(tags, asltags, ['sb','sv','sa'], 'aslslow')
        Tags.if_in_then_add(tags, asltags, ['fb','fv','fa'], 'aslfast')
        Tags.bulk_remove(tags, ['sranaltmp', 'srvagtmp'])

    def correct_aslsfx_tags(tags:list[str], stage_num:int) -> None:
        aslsfx_tags = {
            'na': '{stage}na',  # no_sound?
            'ss': '{stage}ss',  # slow_slushing
            'ms': '{stage}ms',  # medium_slushing
            'fs': '{stage}fs',  # fast_slushing
            'rs': '{stage}rs',  # rapid_slushing
            'sc': '{stage}sc',  # slow_clapping (1/0.60s)
            'mc': '{stage}mc',  # medium_clapping (1/0.45s)
            'fc': '{stage}fc',  # fast_clapping (1/0.30s)
        }
        non_stage_tags = set()
        for entry, e in aslsfx_tags.items():
            for tag in tags:
                if tag.endswith(entry):
                    prefix = tag[:-len(entry)]
                    if prefix.isdigit() and int(prefix) != stage_num:
                        non_stage_tags.add(tag)
        if non_stage_tags:
            tags[:] = [tag for tag in tags if tag not in non_stage_tags]

################################################################

def convert(parent_dir, dir):
    working_dir = os.path.join(parent_dir, dir)
    
    slal_dir = working_dir + "\\SLAnims\\json"
    anim_source_dir = working_dir + "\\SLAnims\\source"
    out_dir = parent_dir + "\\conversion\\" + dir
    tmp_dir = './tmp'

    if not os.path.exists(slal_dir):
        return

    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)

    os.makedirs(tmp_dir + '/edited')
    os.makedirs(out_dir + '/SKSE/Sexlab/Registry/Source')

    animations = dict()
    anim_data = dict()
    source_file_data = []
    slal_json_data = {}
    slsb_json_data = {}
    parsed_slate_data = []
    source_metadata = {
        "anim_name_prefix": None,
    }
    anim_dir_name = None
    ActionLogFound = False

    #=================================== PARSER (1/5): SLAL JSON ===================================# 
    def parse_slal_json(file):
        json_array = json.load(file)
        for json_object in json_array:

            for scene_data in json_array["animations"]:
                scene_info = {
                    "scene_name": scene_data["name"],
                    "scene_id": scene_data["id"],
                    "scene_tags": scene_data["tags"].split(","),
                    "scene_sound": scene_data["sound"],
                    "actors": {},
                    "stage_params": {}
                }
                
                for key, actor_data in enumerate(scene_data["actors"], 1):
                    actor_key = f"a{key}"
                    
                    actor_info = {
                        "actor_key": actor_key,
                        "gender": actor_data["type"],
                        "add_cum": actor_data.get("add_cum", 0),
                        f"{actor_key}_stage_params": {}
                    }
                    
                    for idx, actor_stage_data in enumerate(actor_data["stages"], 1):
                        actor_stage_params_key = f"Stage {idx}"
                       
                        actor_stage_params_info = {
                            "actor_stage_params_key": actor_stage_params_key,
                            "stage_id": actor_stage_data["id"],
                            "open_mouth": actor_stage_data.get("open_mouth", "False"),
                            "strap_on": actor_stage_data.get("strap_on", "False"),
                            "silent": actor_stage_data.get("silent", "False"),
                            "sos": actor_stage_data.get("sos", 0),
                            "up": actor_stage_data.get("up", 0),
                            "side": actor_stage_data.get("side", 0),
                            "rotate": actor_stage_data.get("rotate", 0),
                            "forward": actor_stage_data.get("forward", 0)
                        }
                        
                        actor_info[f"{actor_key}_stage_params"][actor_stage_params_key] = actor_stage_params_info
                    
                    scene_info["actors"][actor_key] = actor_info
                
                for scene_stage_data in scene_data.get("stages", []):
                    stage_params_key = f"Stage {scene_stage_data.get('number', 'None')}"
                    
                    scene_stage_params_info = {
                        "stage_params_key": stage_params_key,
                        "sound": scene_stage_data.get("sound", "None"),
                        "timer": scene_stage_data.get("timer", 0)
                    }
                    scene_info["stage_params"][stage_params_key] = scene_stage_params_info
                
                slal_json_data[scene_info["scene_name"]] = scene_info
                
        return slal_json_data

    #=================================== PARSER (2/5): SOURCE TXT ===================================# 
    def parse_source_type(file):
        def reset_source_animation():
            return {
                "id": None,
                "name": None,
                "actors": {},
            }
        current_animation = None
        inside_animation = False
        for line in file:
            line = line.strip()
            
            if re.match(r'^\s*anim_name_prefix\("([^"]*)"\)', line):
                source_metadata["anim_name_prefix"] = re.search(r'anim_name_prefix\("([^"]*)"\)', line).group(1)
            if re.match(r'^\s*Animation\(', line):
                if current_animation:
                    animations[source_metadata["anim_name_prefix"] + current_animation["name"]] = current_animation
                    
                current_animation = reset_source_animation()
                inside_animation = True
                current_actor_number = None
                
            elif inside_animation and re.match(r'^\s*\)', line):
                inside_animation = False
                
            elif inside_animation:
                if re.match(r'^\s*id=', line):
                    current_animation["id"] = re.search(r'id="([^"]*)"', line).group(1)
                elif re.match(r'^\s*name=', line):
                    current_animation["name"] = re.search(r'name="([^"]*)"', line).group(1)
                    
                elif actor_match := re.search(r'actor\s*(\d+)\s*=\s*([^()]+)\(([^)]*)\)', line):
                    current_actor_number = actor_match.group(1)
                    current_actor_gender = actor_match.group(2)
                    
                    if current_actor_gender:
                        source_file_data.append({
                            "scene_name": current_animation['name'],
                            "actor_number": current_actor_number,
                            "gender_type": current_actor_gender
                        })
                        
        if current_animation:
            if source_metadata["anim_name_prefix"] in animations:
                animations[source_metadata["anim_name_prefix"] + current_animation["name"]] = current_animation
            else:
                current_animation["name"] = current_animation
        
        return source_file_data

    #=================================== PARSER (3/5): SLSB JSON ===================================# 
    def parse_slsb_json(file):
        parsed_json = json.load(file)
        pack_info = {
            'pack_name': parsed_json['pack_name'],
            'pack_hash': parsed_json['prefix_hash'],
            'pack_author': parsed_json['pack_author'],
            'scenes': {}
        }

        for scene in parsed_json['scenes']:
            scene_data = parsed_json['scenes'][scene]
            scene_info = {
                'scene_hash': scene_data['id'],
                'scene_name': scene_data['name'],
                'scene_stages': {},
                'scene_root': scene_data['root'],
                'scene_graph': scene_data["graph"]
            }

            for i in range(len(scene_data['stages'])):
                stage_data = scene_data['stages'][i]
                stage_info = {
                    'stage_hash': stage_data['id'],
                    'stage_name': stage_data['name'],
                    'navigation_text': stage_data['extra']['nav_text']
                }

                scene_info['scene_stages'][i] = stage_info

            pack_info['scenes'][scene] = scene_info
            slsb_json_data[pack_info['pack_name']] = pack_info
            
        return slsb_json_data

    #=================================== PARSER (4/5): SLATE ACTIONLOG ===================================#  
    def parse_slate_actionlogs(file):
        info = json.load(file)
        string_list = info["stringList"]["slate.actionlog"]
        
        for item in string_list:
            action, anim, tag = item.split(',', 2)
            action = action.lower()
            anim = anim.strip()
            tag = tag.strip()
            
            parsed_slate_data.append({
                "action": action,
                "anim": anim,
                "tag": tag
            })

        return parsed_slate_data

    #=================================== ITERATOR: FNIS LIST ===================================#
    def iter_fnis_lists(dir, func):
        anim_dir = os.path.join(dir, 'animations')
        if os.path.exists(anim_dir) and os.path.exists(os.path.join(dir, 'animations')):
            for filename in os.listdir(anim_dir):
                path = os.path.join(anim_dir, filename)
                if os.path.isdir(path):
                    for filename in os.listdir(path):
                        if filename.startswith('FNIS_') and filename.endswith('_List.txt'):
                            func(path, filename)
        elif os.path.isdir(dir):
            for filename in os.listdir(dir):
                path = os.path.join(dir, filename)
                iter_fnis_lists(path, func)

    #=================================== PARSER (5/5): SLAL FNIS LIST ===================================#
    def parse_fnis_list(parent_dir, file):
        path = os.path.join(parent_dir, file)
        with open(path) as topo_file:
            last_seq = None
            for line in topo_file:
                line = line.strip()
                if len(line) > 0 and line[0] != "'":
                    splits = line.split()
                    if (len(splits)) == 0 or splits[0].lower() == 'version' or splits[0].lower() == 'ï»¿version':
                        continue

                    anim_file_name = None
                    anim_event_name = None
                    options = []
                    anim_objects = []

                    for i in range(len(splits)):
                        split = splits[i]
                        if anim_event_name is not None:
                            anim_objects.append(split)
                        if '.hkx' in split.lower():
                            anim_file_name = splits[i]
                            anim_event_name = splits[i - 1]
                        if split.startswith("-"):
                            options_list = split[1:].split(",")
                            for item in options_list:
                                if item.lower() != "avbhumanoidfootikdisable" and item.lower() != "tn" and item != "o" and item != "a" and item not in options:
                                    options.append(item)

                    if options:
                        unique_animlist_options.append(anim_file_name)
                        unique_animlist_options.append(options)
                            
                    anim_event_name = anim_event_name.lower()
                    if '-a,' in line or '-a ' in line or '-o,a,' in line or '-o,a ' in line:
                        last_seq = anim_event_name
                    
                    anim_path = os.path.join(parent_dir, anim_file_name)
                    out_path = os.path.normpath(anim_path)
                    out_path = out_path.split(os.sep)

                    for i in range(len(out_path) - 1, -1, -1):
                        if (out_path[i].lower() == 'meshes'):
                            out_path = out_path[i:]
                            break
                
                    out_path = os.path.join('', *out_path)
                    
                    data = {
                        'anim_file_name': anim_file_name,
                        'sequence': [],
                        'options': options,
                        'anim_obj': anim_objects,
                        'path': anim_path,
                        'out_path': out_path
                    }

                    if last_seq is None:
                        anim_data[anim_event_name] = data
                    else:
                        try:
                            anim_data[last_seq]['sequence'].append(data)    #don't know what this is supposed to do; the ['sequence'] is empty so always KeyError
                        except KeyError:
                            anim_data[last_seq] = data
                        last_seq = None

    #=================================== EDTIOR: SLSB FNIS LISTS ==================================#
    def edit_output_fnis(file_path, filename):
        full_path = os.path.join(file_path, filename)
        modified_lines = []

        with open(full_path, 'r') as file:
            for line in file:
                splits = line.split()
                for i in range(len(splits)):
                    
                    if splits[i] in unique_animlist_options:
                        idx = unique_animlist_options.index(splits[i])
                        options = ",".join(unique_animlist_options[idx + 1])
                        if splits[i-2] == "b":
                            splits[i-2] = f"b -{options}"
                        if splits[i-2] == "-o":
                            splits[i-2] = f"-o,{options}"
                        if splits[i-2] == "-a,tn":
                            splits[i-2] = f"-a,tn,{options}"
                        if splits[i-2] == "-o,a,tn":
                            splits[i-2] = f"-o,a,tn,{options}"
                        line = " ".join(splits) + "\n"

                modified_lines.append(line)
        with open(full_path, 'w') as file:
            file.writelines(modified_lines)

    #=================================== GENERATOR: FNIS BEHAVIOR ==================================#
    def build_behaviour(parent_dir, list_name):
        list_path = os.path.join(parent_dir, list_name)

        if '_canine' in list_name.lower():
            return

        behavior_file_name = list_name.lower().replace('fnis_', '')
        behavior_file_name = behavior_file_name.lower().replace('_list.txt', '')
        behavior_file_name = 'FNIS_' + behavior_file_name + '_Behavior.hkx'

        print('generating', behavior_file_name)

        cwd = os.getcwd()
        os.chdir(fnis_path)
        output = subprocess.Popen(f"./commandlinefnisformodders.exe \"{list_path}\"", stdout=subprocess.PIPE).stdout.read()
        os.chdir(cwd)

        out_path = os.path.normpath(list_path)
        out_path = out_path.split(os.sep)

        start_index = -1
        end_index = -1

        for i in range(len(out_path) - 1, -1, -1):
            split = out_path[i].lower()

            if split == 'meshes':
                start_index = i
            elif split == 'animations':
                end_index = i

        behaviour_folder = 'behaviors' if '_wolf' not in list_name.lower() else 'behaviors wolf'
        behaviour_path = os.path.join(skyrim_path, 'data', *out_path[start_index:end_index], behaviour_folder, behavior_file_name)

        if os.path.exists(behaviour_path):
            out_behavior_dir = os.path.join(out_dir, *out_path[start_index:end_index], behaviour_folder)
            out_behaviour_path = os.path.join(out_behavior_dir, behavior_file_name)
            os.makedirs(out_behavior_dir, exist_ok=True)
            shutil.copyfile(behaviour_path, out_behaviour_path)

        if remove_anims:
            anim_cleanup_dirs.add(parent_dir)

    #=================================== CLEANUP: REMOVE ANIMS ==================================#
    def do_remove_anims(parent_dir):
        for filename in os.listdir(parent_dir):
            if os.path.splitext(filename)[1].lower() == '.hkx':
                os.remove(os.path.join(parent_dir, filename))
        if parent_dir.endswith("EstrusSLSB"):
            base_dir = os.path.dirname(parent_dir)
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                if item == "EstrusSLSB":
                    continue
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

    #===============================================================================================#
    #=================================== FUNCTION: PROCESS STAGE ===================================# 
    #===============================================================================================#
    def process_stage(scene, stage, stage_num):
        #--------------------------------------------
        ######################## Initiating Variables
        #--------------------------------------------
        name = scene['name']
        tags = [tag.lower().strip() for tag in stage['tags']]

        positions = stage['positions']
        furniture = scene['furniture']

        sub = False
        futa = False
        #leadin = False

        #----------------------------------------------------------------
        ######################## Incorporating Tags from SLATE ActionLogs
        #----------------------------------------------------------------
        if ActionLogFound:
            TagToAdd = ''
            TagToRemove = ''
            for entry in parsed_slate_data:
                if name.lower() in entry['anim'].lower():
                    if entry['action'].lower() == 'addtag':
                        TagToAdd = entry['tag'].lower()
                        if TagToAdd not in tags:
                            tags.append(TagToAdd)
                    elif entry['action'].lower() == 'removetag':
                        TagToRemove = entry['tag'].lower()
                        if TagToRemove in tags:
                            tags.remove(TagToRemove)

        #-----------------------------------------------------
        ######################## Standardizing SLSB Tags (1/2)
        #-----------------------------------------------------
        TagsRepairer.update_stage_tags(tags,name.lower(),anim_dir_name.lower())
        sub_tags:list[str] = TagsRepairer.apply_submissive_flags(tags, name.lower(),anim_dir_name.lower())
        if sub_tags:
            sub = True

        #----------------------------------------------------
        ######################## Inserting HentaiRim Tags
        #----------------------------------------------------
        if ActionLogFound:

            rimtags:list[str] = []
            rim_pos_tags:list[str] = []
            for i in range(len(positions)):
                pos = positions[i]
                pos_ind:str = ''
                for pos in positions:
                    if i == 0:
                        pos_ind = 'a'
                    elif i == 1:
                        pos_ind = 'b'
                    elif i == 2:
                        pos_ind = 'c'
                    elif i == 3:
                        pos_ind = 'd'
                    elif i == 4:
                        pos_ind = 'e'
                    rimtags_found:list[str] = SLATE_ActionLogs.check_hentairim_tags(tags, stage_num, pos_ind)
                    rim_pos_tags = rimtags_found # TODO: rely upon this to introduce position tags #
                    Tags.bulk_add(rimtags, rimtags_found) # adding all pos_tags for stage_tags
            if rimtags:
                SLATE_ActionLogs.implement_hentairim_tags(tags, rimtags)
            SLATE_ActionLogs.correct_aslsfx_tags(tags, stage_num)
            asltags:list[str] = SLATE_ActionLogs.check_asl_tags(tags, stage_num)
            if asltags:
               SLATE_ActionLogs.implement_asl_tags(tags, asltags)        

        #-----------------------------------------------------
        ######################## Standardizing SLSB Tags (2/2)
        #-----------------------------------------------------
        # flagging futa scenes (not actors)
        if 'futa' in tags:
            futa = True

        # standardizing 'leadin' tag
        if 'asltagged' not in tags:
            Tags.bulk_remove(tags, ['leadin'])
            if any(kwd in tags for kwd in Keywords.leadin_kwds) and all(kwd not in tags for kwd in Keywords.not_leadin):
                tags.append('leadin')

        #---------------------------------------------------
        ######################## Assessing Initial Positions
        #---------------------------------------------------
        male_count = 0
        female_count = 0
        human_male_count = 0
        cre_male_count = 0
        human_female_count = 0
        cre_female_count = 0
        cre_count = 0

        for pos in positions:
            if pos['sex']['male']:
                male_count += 1
                if pos['race'] == 'Human':
                    human_male_count += 1
                else:
                    cre_male_count += 1
            if pos['sex']['female']:
                female_count += 1
                if pos['race'] == 'Human':
                    human_female_count += 1
                else:
                    cre_female_count += 1
                    
        straight = male_count > 0 and female_count > 0
        gay = male_count > 0 and female_count == 0
        lesbian = female_count > 0 and male_count == 0
        cre_count = cre_male_count + cre_female_count

        for i in range(len(positions)):
            pos = positions[i]

            #----------------------------------------------------------------------
            ######################## Circumventing SLSB's Gender Restrictions (1/2)
            #----------------------------------------------------------------------
            if pos['race'] in Keywords.fem_cre_body_only:
                pos['sex']['female'] = True
                pos['sex']['male'] = True

            if human_male_count and cre_female_count and (cre_male_count+human_female_count==0):
                if pos['sex']['male']:
                    pos['sex']['futa'] = True

            #--------------------------------------------------
            ######################## Flagging FUTA Actors (1/3)
            #--------------------------------------------------
            if futa: # initial preparations
                if 'kom_futaduo' in pos['event'][0].lower():
                    pos['sex']['female'] = False
                    pos['sex']['male'] = True
                if 'futafurniture01(bed)' in pos['event'][0].lower():
                    if i==0:
                        pos['sex']['female'] = False
                        pos['sex']['futa'] = True
                    if i==1:
                        pos['sex']['male'] = False
                        pos['sex']['female'] = True
                if 'gs' in tags and 'mf' in tags:
                    if not pos['sex']['male'] and len(positions)==2:
                        if i==1:
                            pos['sex']['female'] = False
                            pos['sex']['futa'] = True
                if 'billyy' in tags and 'cf' in tags and pos['extra']['submissive']:
                    pos['extra']['submissive'] = False

            #-------------------------------------------------
            ######################## Incorporating AnimObjects 
            #-------------------------------------------------
            if pos['event'] and len(pos['event']) > 0:
                event = pos['event'][0].lower()
                if event in anim_data.keys():
                    data = anim_data[event]
                    pos['event'][0] = os.path.splitext(data['anim_file_name'])[0]
                    os.makedirs(os.path.dirname(os.path.join(out_dir, data['out_path'])), exist_ok=True)
                    if skyrim_path is not None:
                        shutil.copyfile(data['path'], os.path.join(out_dir, data['out_path']))
                    if 'anim_obj' in data and data['anim_obj'] is not None:
                        pos['anim_obj'] = ','.join(data['anim_obj'])

            # standardizing "Toys" tag
            anim_obj_found = any(pos['anim_obj'] != "" and "cum" not in pos['anim_obj'].lower() for pos in stage['positions'])
            if not anim_obj_found and 'toys' in tags:
                tags.remove('toys')
            if anim_obj_found and 'toys' not in tags:
                tags.append('toys')

            #--------------------------------------------------               
            ######################## Flagging SUBMISSIVE Actors
            #--------------------------------------------------
            # IMP: Deal with sub/dead flags before futa flags
            if sub:
                if straight and female_count == 1 and 'femdom' not in tags and pos['sex']['female']:
                    pos['extra']['submissive'] = True
                if straight and female_count == 2 and 'femdom' not in tags: #needs_testing
                    if pos['sex']['female']:
                        pos['extra']['submissive'] = True
                if straight and ('femdom' in tags or 'ffffm' in tags) and pos['sex']['male']:
                    pos['extra']['submissive'] = True
                if gay and ((male_count == 2 and i == 0) or ('hcos' in tags and (pos['race'] == 'Rabbit' or pos['race'] == 'Skeever' or pos['race'] == 'Horse'))): # needs_testing
                    pos['extra']['submissive'] = True
                if lesbian and i == 0: # needs_testing
                    pos['extra']['submissive'] = True

                if Tags.if_any_found(sub_tags, ['unconscious', 'gore', 'amputee']) and pos['extra']['submissive']:
                    pos['extra']['submissive'] = False
                    pos['extra']['dead'] = True

            #-------------------------------------------------------------
            ######################## Incorporating Parsed ActorStageParams
            #-------------------------------------------------------------
            has_strap_on = ''
            has_sos_value = ''
            has_schlong = ''
            has_add_cum = ''
            has_forward = ''
            has_side = ''
            has_up = ''
            has_rotate = ''

            if name in slal_json_data:
                source_anim_data = slal_json_data[name]
                actor_map = source_anim_data['actors']
                for i, actor_dict in enumerate(actor_map):
                    for key, value in actor_map.items():
                        actor_key = key
                        if actor_key.startswith('a'):
                            source_actor_data = actor_map[actor_key]

                            if 'add_cum' in source_actor_data and source_actor_data['add_cum'] != 0:
                                if has_add_cum and actor_key[1:] not in has_add_cum:
                                    has_add_cum += f",{actor_key[1:]}"
                                else:
                                    has_add_cum = actor_key[1:]

                            actor_stage_params_map = source_actor_data[f'{actor_key}_stage_params']
                            for key, value in actor_stage_params_map.items():
                                actor_stage_params_key = key
                                event_key = f"{actor_key}" + f"_s{actor_stage_params_key[6:]}"
                                if actor_stage_params_key.startswith('Stage'):
                                    source_actor_stage_params = actor_stage_params_map[actor_stage_params_key]

                                    if 'strap_on' in source_actor_stage_params and source_actor_stage_params['strap_on'] != "False":
                                        if has_strap_on and actor_key[1:] not in has_strap_on:
                                            has_strap_on += f",{actor_key[1:]}"
                                        else:
                                            has_strap_on = actor_key[1:]
                                    if 'sos' in source_actor_stage_params and source_actor_stage_params['sos'] != 0:
                                        has_sos_value = event_key
                                        if event_key in has_sos_value and int(event_key[4:]) == stage_num:
                                            pos_num = int(actor_key[1:]) - 1
                                            for pos in [positions[pos_num]]:
                                                pos['schlong'] = source_actor_stage_params['sos']
                                        # for futa
                                        if has_schlong and actor_key[1:] not in has_schlong:
                                            has_schlong += f",{actor_key[1:]}"
                                        else:
                                            has_schlong = actor_key[1:]

                                    if 'forward' in source_actor_stage_params and source_actor_stage_params['forward'] != 0:
                                        has_forward = event_key
                                        if event_key in has_forward and int(event_key[4:]) == stage_num:
                                            pos_num = int(actor_key[1:]) - 1
                                            for pos in [positions[pos_num]]:
                                                pos['offset']['y'] = source_actor_stage_params['forward']
                                    if 'side' in source_actor_stage_params and source_actor_stage_params['side'] != 0:
                                        has_side = event_key
                                        if event_key in has_side and int(event_key[4:]) == stage_num:
                                            pos_num = int(actor_key[1:]) - 1
                                            for pos in [positions[pos_num]]:
                                                pos['offset']['x'] = source_actor_stage_params['side']
                                    if 'up' in source_actor_stage_params and source_actor_stage_params['up'] != 0:
                                        has_up = event_key
                                        if event_key in has_up and int(event_key[4:]) == stage_num:
                                            pos_num = int(actor_key[1:]) - 1
                                            for pos in [positions[pos_num]]:
                                                pos['offset']['z'] = source_actor_stage_params['up']
                                    if 'rotate' in source_actor_stage_params and source_actor_stage_params['rotate'] != 0:
                                        has_rotate = event_key
                                        if event_key in has_rotate and int(event_key[4:]) == stage_num:
                                            pos_num = int(actor_key[1:]) - 1
                                            for pos in [positions[pos_num]]:
                                                pos['offset']['r'] = source_actor_stage_params['rotate']

                            ####### actor-specific fine tuning #######
                            #--------------------------------------------------
                            ######################## Flagging FUTA Actors (2/3)
                            #--------------------------------------------------
                            if futa:
                                if 'anubs' in tags and ('ff' in tags or 'fff' in tags):
                                    if actor_key[1:] in has_schlong:
                                        pos_num = int(actor_key[1:]) - 1
                                        for pos in [positions[pos_num]]:
                                            pos['sex']['female'] = False
                                            pos['sex']['futa'] = True
                                if 'flufyfox' in tags or 'milky' in tags:
                                    if actor_key[1:] in has_strap_on:
                                        pos_num = int(actor_key[1:]) - 1
                                        for pos in [positions[pos_num]]:
                                            pos['sex']['female'] = False
                                            pos['sex']['futa'] = True

                            # Circumventing SLSB's Gender Restrictions (2/2)
                            if not stricter_futa:
                                if actor_key[1:] in has_strap_on:
                                    pos_num = int(actor_key[1:]) - 1
                                    for pos in [positions[pos_num]]:
                                        if pos['race'] == 'Human':
                                            pos['sex']['futa'] = True

                        #--------------------------------------------------------
                        ######################## Incorporating Parsed StageParams
                        #--------------------------------------------------------
                        stage_params_map = source_anim_data['stage_params']
                        for key, value in stage_params_map.items():
                            stage_params_key = key
                            if stage_params_key.startswith('Stage'):
                                source_stage_params = stage_params_map[stage_params_key]

                                if 'timer' in source_stage_params and source_stage_params['timer'] != 0:
                                    if int(stage_params_key[6:]) == stage_num:
                                        #stage['extra']['fixed_len'] = round(float(source_stage_params['timer']), 2)
                                        stage['extra']['fixed_len'] = round(float(source_stage_params['timer']) * 1000) # timers in miliseconds


            #-----------------------------------------------
            ######################## Flagging VAMPIRE Actors
            #-----------------------------------------------
            if 'vamp' in pos['event'][0].lower() and 'vampirelord' not in tags:
                human_vampire_anim = all(pos['race'] != "Vampire Lord" for pos in stage['positions'])
                if human_vampire_anim:
                    if 'vampire' not in tags:
                        tags.append('vampire')
                    if 'vampirefemale' in tags or 'vampirelesbian' in tags or 'femdom' in tags or 'cowgirl' in tags or 'vampfeedf' in pos['event'][0].lower():
                        if pos['sex']['female']:
                            pos['extra']['vampire'] = True
                    else:
                        if pos['sex']['male']:
                            pos['extra']['vampire'] = True

            #--------------------------------------------------
            ######################## Flagging FUTA Actors (3/3)
            #--------------------------------------------------
            if futa:
                if 'solo' in tags or 'futaall' in tags or ('anubs' in tags and 'mf' in tags) or ('ff' in tags and ('frotting' in tags or 'milking' in tags)):
                    for pos in stage['positions']:
                        if pos['sex']['female']:
                            pos['sex']['female'] = False
                            pos['sex']['futa'] = True
                elif 'billyy' in tags and '2futa' in tags and len(positions) == 3:
                    for pos in [positions[0], positions[1]]:
                        pos['sex']['female'] = False
                        pos['sex']['futa'] = True
                elif 'ff' in tags and pos['sex']['male']:
                    pos['sex']['male'] = False
                    pos['sex']['futa'] = True

            #-----------------------------------------------
            ######################## Flagging SCALING Actors
            #-----------------------------------------------
            if 'bigguy' in tags or 'scaling' in tags:
                if bigguy_value := re.search(r'(base\s?scale)\s?(\d+\.\d+)', name.lower()):
                    for pos in positions:
                        if pos['sex']['male']:
                            pos['scale'] = round(float(bigguy_value.group(2)), 2)
                if scaling_value := re.search(r'(set\s?scale)\s?(\d+(?:\.\d+)?)?', name.lower()):
                    value = round(float(scaling_value.group(2)), 2)
                    if 'gs orc' in name.lower() and pos['sex']['male']:
                        pos['scale'] = value
                    if 'gs giantess' in name.lower() and pos['sex']['female']:
                        pos['scale'] = value
                    if 'hcos small' in name.lower() and pos['race'] == 'Dragon':
                        pos['scale'] = value

            #----------------------------------------------
            ######################## SLSB Furniture Support
            #----------------------------------------------
            if 'lying' in tags and not 'invisfurn' in tags and not anim_obj_found and cre_count == 0 and len(positions) < 3:
                furniture['allow_bed'] = True
                if 'allowbed' not in tags:
                    tags.append('allowbed')

            if 'invisfurn' in tags:
                if 'bed' in name.lower():
                    furniture['furni_types'] = Keywords.allowed_furnitures['beds']
                if 'chair' in name.lower():
                    furniture['furni_types'] = Keywords.allowed_furnitures['chairs'] + Keywords.allowed_furnitures['thrones']
                if 'wall' in name.lower():
                    furniture['furni_types'] = Keywords.allowed_furnitures['walls']
                if 'table' in name.lower():
                    furniture['furni_types'] = [Keywords.allowed_furnitures['tables'][0]]
                if 'counter' in name.lower():
                    furniture['furni_types'] = [Keywords.allowed_furnitures['tables'][1]]
        
        #---------------------------------------------------
        ######################## Finalizing Stage Processing
        #---------------------------------------------------
            #if leadin:
            #    for pos in stage['positions']:
            #        pos['strip_data']['default'] = False
            #        pos['strip_data']['helmet'] = True
            #        pos['strip_data']['gloves'] = True

        stage['tags'] = tags

    #===================================================================================================#
    #=================================== EXECUTION: CONVERT FUNCTION ===================================# 
    #===================================================================================================#
    print("---------> PARSING SLAL SOURCE TXTs")
    if os.path.exists(anim_source_dir):
        for filename in os.listdir(anim_source_dir):
            path = os.path.join(anim_source_dir, filename)
            ext = pathlib.Path(filename).suffix
            if os.path.isfile(path) and ext == ".txt":
                with open(path, "r") as file:
                    parse_source_type(file)

    print("---------> PARSING SLAL FNIS LISTS")
    anim_dir = working_dir + '\\meshes\\actors'
    if os.path.exists(anim_dir):
        for filename in os.listdir(anim_dir):
            path = os.path.join(anim_dir, filename)
            if os.path.isdir(path):
                iter_fnis_lists(path, parse_fnis_list)

    if slsb_json_path is not None:
        print("---------> PARSING SLSB JSON PROJECTS")
        for filename in os.listdir(slsb_json_path):
            path = os.path.join(slsb_json_path, filename)
            if os.path.isfile(path) and filename.lower().endswith(".slsb.json"):
                with open(path, "r") as file:
                    parse_slsb_json(file)

    if slate_path is not None:
        print("---------> PARSING SLATE ACTION_LOGS")
        for filename in os.listdir(slate_path):
            path = os.path.join(slate_path, filename)
            if os.path.isfile(path) and (filename.startswith('SLATE_ActionLog') or filename.startswith('Hentairim')) and filename.endswith('.json'):
                ActionLogFound = True
                with open(path, "r") as file:
                    parse_slate_actionlogs(file)

    print("---------> FIXING SLAL JSONs")
    json_files = [json_file for json_file in os.listdir(slal_dir) if json_file.lower().endswith(".json")]
    json_count = len(json_files)
    for filename in os.listdir(slal_dir):
        path = os.path.join(slal_dir, filename)
        if os.path.isfile(path) and filename.lower().endswith(".json"):
            json_base_name = pathlib.Path(filename).stem
            matching_source_path = None
            if os.path.exists(anim_source_dir):
                for source_file in os.listdir(anim_source_dir):
                    if source_file.lower().endswith(".txt") and pathlib.Path(source_file).stem.lower() == json_base_name.lower():
                        matching_source_path = os.path.join(anim_source_dir, source_file)
                        break
                if matching_source_path is not None:
                    with open(matching_source_path, 'r') as txt_file:
                        for line in txt_file:
                            if match := re.match(r'anim_dir\("([^"]*)"\)', line):
                                anim_dir_name = match.group(1)
                                break
            else:
                anim_dir_path = working_dir + "\\meshes\\actors\\character\\animations"
                if os.path.exists(anim_dir_path):
                    for dir_name in os.listdir(anim_dir_path):
                        if json_count == 1:
                            anim_dir_name = dir_name
                        else:
                            anim_dir_name = json_base_name
            
            changes_made = False
            if anim_dir_name is not None:
                with open(path, 'r+') as json_file:
                    #fixes directory names
                    json_data = json.load(json_file)
                    if "name" in json_data and json_data["name"].lower() != anim_dir_name.lower():
                        json_data["name"] = anim_dir_name
                        changes_made = True
                    #fixes type-type gender
                    if "animations" in json_data:
                        for scene_data in json_data["animations"]:
                            for key, actor_data in enumerate(scene_data["actors"], 1):
                                actor_key = f"a{key}"
                                if actor_data["type"].lower() == "type" and os.path.exists(anim_source_dir):
                                    slal_type_scene = scene_data["name"]
                                    slal_actor_key = actor_key
                                    for info in source_file_data:
                                        if source_metadata['anim_name_prefix'] and source_metadata['anim_name_prefix'] is not None:
                                            source_scene_name = source_metadata['anim_name_prefix'] + info['scene_name']
                                        else:
                                            source_scene_name = info['scene_name']
                                        source_actor_key = f"a{info['actor_number']}"
                                        if (slal_type_scene in source_scene_name) and (slal_actor_key in source_actor_key):
                                            actor_data["type"] = info['gender_type']
                                            changes_made = True
                    if changes_made:
                        json_file.seek(0)
                        json.dump(json_data, json_file, indent=2)
                        json_file.truncate()

            print("---------> CONVERTING SLAL TO SLSB PROJECTS")
            with open(path, "r") as file:
                parse_slal_json(file)

            print('converting', filename)
            output = subprocess.Popen(f"{slsb_path} convert --in \"{path}\" --out \"{tmp_dir}\"", stdout=subprocess.PIPE).stdout.read()


    print("---------> EDITING AND BUILDING SLSB PROJECTS")
    for filename in os.listdir(tmp_dir):
        path = os.path.join(tmp_dir, filename)
        if os.path.isdir(path):
            continue

        print('editing slsb', filename)
        data = None
        with open(path, 'r') as f:
            data = json.load(f)
            data['pack_author'] = args.author
            
            pack_data_old = {}
            scenes_old = {}
            if data['pack_name'] in slsb_json_data:
                pack_data_old = slsb_json_data[data['pack_name']]
                scenes_old = pack_data_old['scenes']
                data['prefix_hash'] = pack_data_old['pack_hash']
                if data['pack_author'] == 'Unknown':
                    data['pack_author'] = pack_data_old['pack_author']

            new_scenes = {}
            scenes = data['scenes']
            for id in scenes:
                scene = scenes[id]
                
                scene_old = {}
                stages_old = {}
                for item in scenes_old:
                    if scene['name'] == scenes_old[item]['scene_name']:
                        scene_old = scenes_old[item]
                        scene['id'] = scene_old['scene_hash']
                        scene['root'] = scene_old['scene_root']
                        scene['graph'] = scene_old['scene_graph']
                        stages_old = scene_old['scene_stages']
                new_scenes[scene['id']] = scene

                stages = scene['stages']
                for i in range(len(stages)):
                    stage = stages[i]
                    stage_num = i + 1
                    process_stage(scene, stage, stage_num)

                    if stages_old != {}:
                        #print(scene['name'])       #for debugging on error
                        stage_old = stages_old[i]
                        stage['id'] = stage_old['stage_hash']

                # marks scenes as private (for manual conversions)
                if anim_dir_name == 'ZaZAnimsSLSB' or anim_dir_name == 'DDSL': #or anim_dir_name == 'EstrusSLSB'
                    scene['private'] = True

            data['scenes'] = new_scenes

        edited_path = tmp_dir + '/edited/' + filename
        with open(edited_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        if not args.no_build:
            output = subprocess.Popen(f"{slsb_path} build --in \"{edited_path}\" --out \"{out_dir}\"", stdout=subprocess.PIPE).stdout.read()
            shutil.copyfile(edited_path, out_dir + '/SKSE/Sexlab/Registry/Source/' + filename)


    slsb_fnis_list_dir = out_dir + '\\meshes\\actors'
    iter_fnis_lists(slsb_fnis_list_dir, edit_output_fnis)
    if fnis_path is not None:
        print("---------> BUILDING FNIS BEHAVIOUR")
        iter_fnis_lists(slsb_fnis_list_dir, build_behaviour)

    if remove_anims:
        #print("---------> REMOVING ANIMATION FILES FROM OUTPUT")
        for d in anim_cleanup_dirs:
            do_remove_anims(d)

    if args.clean:
        shutil.rmtree(tmp_dir)

#========================================================================================#
#=================================== SCRIPT EXECUTION ===================================#
#========================================================================================#
if not args.post_conversion_only:
    slal_dir_outside = os.path.join(parent_dir, 'SLAnims')
    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        if os.path.isdir(item_path):
            slal_dir_default = os.path.join(item_path, 'SLAnims')            
            if os.path.exists(slal_dir_default):
                print('\n\033[92m' + "============== PROCESSING " + item + " ==============" + '\033[0m')
                convert(parent_dir, item)

#=======================================================================================#
#=================================== POST-CONVERSION ===================================# 
#=======================================================================================#

#============================ FUNCTION: REPLICATE STRUCTURE ============================#
def replicate_structure(source_dir, required_structure):
    for root, _, files in os.walk(source_dir):
        for file in files:
            source_path = os.path.join(root, file)

            req_paths = []
            for dest_root, dirs, dest_files in os.walk(required_structure):
                dirs[:] = [d for d in dirs if d.lower() != "conversion"]
                if file in dest_files:
                    req_paths.append(os.path.join(dest_root, file))

            if len(req_paths) > 1:
                print(f"\033[93m---> {len(req_paths)} instances found for {file}:\033[0m")
                print(req_paths)
                print("\033[93mScript is handling this, but it's undesirable. Make sure the directory with SLAL packs is not polluted. It can also hint at packaging issues by animators.\033[0m")

            while req_paths:
                req_path = req_paths.pop(0)
                req_subdir = os.path.relpath(req_path, required_structure)
                source_structure = os.path.join(source_dir, req_subdir)

                os.makedirs(os.path.dirname(source_structure), exist_ok=True)
                if req_paths:
                    shutil.copy2(source_path, source_structure)
                else:
                    shutil.move(source_path, source_structure)

#============================ FUNCTION: MOVE WITH REPLACE ============================#
def move_with_replace(source_dir, target_dir):
    if os.path.isdir(target_dir):
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            target_item = os.path.join(target_dir, item)

            if os.path.isfile(source_item):
                if os.path.isfile(target_item):
                    os.remove(target_item)
                shutil.move(source_item, target_item)
                
            elif os.path.isdir(source_item):
                if not os.path.isdir(target_item):
                    os.makedirs(target_item)
                move_with_replace(source_item, target_item)

        if not os.listdir(source_dir):
            os.rmdir(source_dir)

#============================ EXECUTION: HANDLING XMLs WITH SPACES ============================# 
if tmp_log_dir is not None:
    for f in os.listdir(tmp_log_dir):
        if f.lower().endswith(".xml") and " " in f:
            xml_with_spaces.append(f)

    if not xml_with_spaces == []:
        print("\n======== PROCESSING XMLs_WITH_SPACES ========")
        rely_on_hkxcmd:bool = False

        tmp_xml_subdir = os.path.join(tmp_log_dir, "xml")
        tmp_hkx_subdir = os.path.join(tmp_log_dir, "hkx")
        if args.post_conversion_only and os.path.exists(tmp_hkx_subdir):
            shutil.rmtree(tmp_hkx_subdir)
        os.makedirs(tmp_xml_subdir, exist_ok=True)
        os.makedirs(tmp_hkx_subdir, exist_ok=True)

        print("---------> segregating XMLs with spaces in names")
        for filename in os.listdir(tmp_log_dir):
            path = os.path.join(tmp_log_dir, filename)
            if os.path.isfile(path) and filename.lower().endswith(".xml") and " " in filename:
                print(filename)
                new_path = os.path.join(tmp_xml_subdir, filename)
                shutil.move(path, new_path)

        print("---------> converting XMLs to HKXs")
        if not any(f.lower() == "hkxconv.exe" for f in os.listdir()):
            rely_on_hkxcmd = True
        else:
            command = ["hkxconv.exe", "convert", "-v hkx", tmp_xml_subdir, tmp_hkx_subdir]
            try:
                subprocess.run(command, check=True)
            except:
                rely_on_hkxcmd = True

        if rely_on_hkxcmd:
            print('\033[93m' + '[INFO]: hkxconv.exe not found alongside convert.py or gave error(s). relying upon HKXCMD instead.' + '\033[0m')
            for xml_file in os.listdir(tmp_xml_subdir):
                if xml_file.lower().endswith(".xml"):
                    hkxcmd_path = os.path.join(fnis_path, "hkxcmd.exe")
                    input_path = os.path.join(tmp_xml_subdir, xml_file)
                    output_file = os.path.splitext(xml_file)[0] + ".hkx"
                    output_path = os.path.join(tmp_hkx_subdir, output_file)
                    command = [hkxcmd_path, "convert", "-v:amd64", os.path.normpath(input_path), os.path.normpath(output_path)]
                    try:
                        subprocess.run(command, check=True)
                    except:
                        print(f"Failed to convert: {xml_file}")

        print("---------> replicating source structure; stay patient...")
        replicate_structure(tmp_hkx_subdir, parent_dir)

        print("---------> incorporating converted HKXs")
        conversions_dir = os.path.join(parent_dir, "conversion")
        move_with_replace(tmp_hkx_subdir, conversions_dir)

print('\n<<<<<<<<<<<<<<< ALL PROCESSES COMPLETED SUCCESSFULLY >>>>>>>>>>>>>>>')

#============================ WARNINGS: PROBLEMATIC DIRECTORY STRUCTURE ============================# 
if not args.post_conversion_only:
    slal_dir_outside = os.path.join(parent_dir, 'SLAnims')
    if os.path.exists(slal_dir_outside):
        print('\033[91m' + "ERROR: Found 'SLAnims' folder directly inside the provided path. No packs outside a sub-directory will be processed for conversion." + '\033[0m')
        print('\033[92m' + "SOLUTION: Each SLAL pack has to be in its own sub-directory, even when converting a single pack." + '\033[0m')    

    for item in os.listdir(parent_dir):
        item_path = os.path.join(parent_dir, item)
        if os.path.isdir(item_path):
            slal_dir_default = os.path.join(item_path, 'SLAnims')            
            if not os.path.exists(slal_dir_default):
                for sub_item in os.listdir(item_path):
                    sub_item_path = os.path.join(item_path, sub_item)
                    if os.path.isdir(sub_item_path):
                        slal_dir_inside = os.path.join(sub_item_path, 'SLAnims')
                        if os.path.exists(slal_dir_inside):
                            misplaced_slal_packs.append(sub_item_path)
    if misplaced_slal_packs:
        print('\n\033[93m' + "WARNING: Found at least one sub-directory having a standalone SLAL pack inside a sub-directory in the provided path. The pack in this sub-sub-directory will not be processed for conversion." + '\033[0m')
        for entry in misplaced_slal_packs:
            print(f"- {entry}")
        print('\033[92m' + "SOLUTION: If you want these packs to also be processed for conversion, make sure they appear as direct sub-directories inside the provided path." + '\033[0m')
