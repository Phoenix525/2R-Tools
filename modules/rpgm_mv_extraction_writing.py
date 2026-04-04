#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-08-04 23:33:35
'''

import os
import shutil
import sys
from datetime import datetime

import main
from modules.utils import (BASE_ABSPATH, EXTRACT, GLOBAL_DATA, KEY_MARK1,
                           KEY_MARK2, KEY_PHOENIX, MARK_TODO, PATTERN_MAP,
                           RPGM_INPUT_ABSPATH, RPGM_OUTPUT_ABSPATH,
                           RPGM_PROJECT_PARENT_FOLDER, WRITEIN,
                           change_phoenix_mark, del_key_from_dict, get_md5,
                           matching_langs, merge_dicts, print_info, print_warn,
                           read_json, switch_change_mark, write_json)

# MV引擎默认文本库
RPGMV_DEFAULT_LIBRARY = 'rpgmv_default_library.json'

TYPE_COMMONEVENTS = 'CommonEvents'
TYPE_SYSTEM = 'System'

# 要扫描的属性参数
KEY_NAME = 'name'
KEY_DESCRIPTION = 'description'
KEY_EVENTS = 'events'
KEY_PAGES = 'pages'
KEY_LIST = 'list'
KEY_CODE = 'code'
KEY_PARAMETERS = 'parameters'
# -------- Actors.json --------
KEY_NICKNAME = 'nickname'
KEY_PROFILE = 'profile'
# -------- States.json --------
KEY_MESSAGE1 = 'message1'
KEY_MESSAGE2 = 'message2'
KEY_MESSAGE3 = 'message3'
KEY_MESSAGE4 = 'message4'
# -------- System.json --------
KEY_ARMORTYPES = 'armorTypes'
KEY_WEAPONTYPES = 'weaponTypes'
KEY_EQUIPTYPES = 'equipTypes'
KEY_SKILLTYPES = 'skillTypes'
KEY_CURRENCYUNIT = 'currencyUnit'
KEY_ELEMENTS = 'elements'
KEY_GAMETITLE = 'gameTitle'
KEY_TERMS = 'terms'
KEY_BASIC = 'basic'
KEY_COMMANDS = 'commands'
KEY_PARAMS = 'params'
KEY_MESSAGES = 'messages'
# -------- Mapxxx.json --------
KEY_DISPLAYNAME = 'displayName'

# Wicked Rouge
TYPE_BATTLEHUD = 'BattleHUD'
TYPE_MAPHUD = 'MapHUD'
KEY_TYPE = 'type'
KEY_VALUE = 'Value'
KEY_TYPE_VALUE = 'Text'

# pylint: disable=invalid-name
# 缓存文本
_game_txt_cache = {}
# 默认文本
_game_txt_library = {}
# 当前rpgm项目名称
curr_rpgm_project_name = 'Test_v0.1.json'
# 当前rpgm翻译文件的绝对路径
curr_rpgm_project_abspath = os.path.join(
    RPGM_PROJECT_PARENT_FOLDER, curr_rpgm_project_name
)


def walk_file(_type: str):
    '''
    遍历文件夹内所有内容
    '''

    if not os.path.exists(RPGM_INPUT_ABSPATH):
        os.makedirs(RPGM_INPUT_ABSPATH)
    if os.path.exists(RPGM_OUTPUT_ABSPATH):
        shutil.rmtree(RPGM_OUTPUT_ABSPATH)
    os.makedirs(RPGM_OUTPUT_ABSPATH)

    if not _read_game_txt(_type):
        return

    # 遍历所有文件，筛选出需要的json文件进行处理
    for root, dirs, files in os.walk(RPGM_INPUT_ABSPATH, topdown=False):

        # 新文件目录
        relative_path = os.path.relpath(root, RPGM_INPUT_ABSPATH)
        new_path = (
            RPGM_OUTPUT_ABSPATH
            if relative_path == '.'
            else os.path.join(RPGM_OUTPUT_ABSPATH, relative_path)
        )
        # 若新目录不存在，创建它
        if not os.path.exists(new_path):
            os.makedirs(new_path)

        for json_file in files:
            if not json_file.endswith('.json'):
                continue

            # 如果当前json文件不在白名单内，且不符合Map地图文件，则跳过它
            if json_file[:-5] not in GLOBAL_DATA[
                'rpg_white_list'
            ] and not PATTERN_MAP.match(json_file[:-5]):
                # 如果当前为写入模式，在新目录拷贝一份该文件
                if _type == WRITEIN:
                    shutil.copy(os.path.join(root, json_file), new_path)
                print(f'{json_file} 不在白名单内，已跳过！\n')
                continue

            deal_with_json_file(root, json_file, _type, new_path)


def deal_with_json_file(root: str, json_file: str, _type: str, new_path: str):
    '''
    处理JSON数据
    '''

    print(f'当前扫描文本：{json_file}')
    json_datas = read_json(os.path.join(root, json_file))
    if len(json_datas) < 1:
        print(f'{json_file} 无内容，已跳过！\n')
        return

    filename = json_file[:-5]
    # 翻译文本所在文件的标识
    file_mark = ''
    # 当前为提取模式时，在处理文本之前，将标识行写入缓存
    if _type == EXTRACT:
        time = datetime.now().strftime('%Y_%m_%d %H:%M')
        file_mark = f'{KEY_MARK1}{filename} {time}{KEY_MARK2}'
        write_in_cache(file_mark, '', '', file_mark)

    # 记录文本更改
    _change = False

    if filename in GLOBAL_DATA['rpg_type_array_object']:
        _change = sacnning_type_player(json_datas, _type, filename)
    elif filename == TYPE_COMMONEVENTS:
        _change = sacnning_common_events(json_datas, _type)
    elif filename == TYPE_SYSTEM:
        _change = scanning_system(json_datas, _type, filename)
    elif PATTERN_MAP.match(filename):
        _change = scanning_type_maps(json_datas, _type, filename)

    # elif filename in [TYPE_BATTLEHUD, TYPE_MAPHUD]:
    #     _change = scanning_wicked_rouge(json_datas, _type)

    # 提取模式
    if _type == EXTRACT:
        # 如果数据无变动，删除之前写入的标识行
        if not _change:
            _game_txt_cache = del_key_from_dict(file_mark, _game_txt_cache)
        print_info(f'{json_file} 扫描完成！\n')

    # 当前为写入模式时，写入json文本
    elif _type == WRITEIN:
        write_json(os.path.join(new_path, json_file), json_datas, backup=False)


def sacnning_type_player(json_datas: list, _type: str, filename: str) -> bool:
    '''
    扫描各种武器护具敌人等数据文件。数据结构：array[object]
    '''

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, list) or len(json_datas) < 1:
        return _change

    for idx_json_datas, item_json_datas in enumerate(json_datas):
        if not item_json_datas:
            continue

        if KEY_NAME in item_json_datas and isinstance(item_json_datas[KEY_NAME], str):
            # 人名基本不会出现歧义，可以去重
            if filename in GLOBAL_DATA['rpg_duplicate_removal_list']:
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, write_in_cache(item_json_datas[KEY_NAME])
                    )
                else:
                    json_datas[idx_json_datas][KEY_NAME] = read_from_cache(
                        item_json_datas[KEY_NAME]
                    )
            else:
                _loc = get_md5(
                    '_'.join([filename, str(idx_json_datas), KEY_NAME]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, write_in_cache(item_json_datas[KEY_NAME], _loc)
                    )
                else:
                    json_datas[idx_json_datas][KEY_NAME] = read_from_cache(
                        item_json_datas[KEY_NAME], _loc
                    )

        if KEY_NICKNAME in item_json_datas and isinstance(
            item_json_datas[KEY_NICKNAME], str
        ):
            # 昵称应该不会出现歧义，此处去重
            # _loc = get_md5('_'.join([filename, str(i_json_datas), KEY_NICKNAME]), True)
            _loc = ''
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_NICKNAME], _loc)
                )
            else:
                json_datas[idx_json_datas][KEY_NICKNAME] = read_from_cache(
                    item_json_datas[KEY_NICKNAME], _loc
                )

        if KEY_PROFILE in item_json_datas and isinstance(
            item_json_datas[KEY_PROFILE], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_PROFILE])
                )
            else:
                json_datas[idx_json_datas][KEY_PROFILE] = read_from_cache(
                    item_json_datas[KEY_PROFILE]
                )

        if KEY_DESCRIPTION in item_json_datas and isinstance(
            item_json_datas[KEY_DESCRIPTION], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_DESCRIPTION])
                )
            else:
                json_datas[idx_json_datas][KEY_DESCRIPTION] = read_from_cache(
                    item_json_datas[KEY_DESCRIPTION]
                )

        if KEY_MESSAGE1 in item_json_datas and isinstance(
            item_json_datas[KEY_MESSAGE1], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_MESSAGE1])
                )
            else:
                json_datas[idx_json_datas][KEY_MESSAGE1] = read_from_cache(
                    item_json_datas[KEY_MESSAGE1]
                )

        if KEY_MESSAGE2 in item_json_datas and isinstance(
            item_json_datas[KEY_MESSAGE2], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_MESSAGE2])
                )
            else:
                json_datas[idx_json_datas][KEY_MESSAGE2] = read_from_cache(
                    item_json_datas[KEY_MESSAGE2]
                )

        if KEY_MESSAGE3 in item_json_datas and isinstance(
            item_json_datas[KEY_MESSAGE3], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_MESSAGE3])
                )
            else:
                json_datas[idx_json_datas][KEY_MESSAGE3] = read_from_cache(
                    item_json_datas[KEY_MESSAGE3]
                )

        if KEY_MESSAGE4 in item_json_datas and isinstance(
            item_json_datas[KEY_MESSAGE4], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, write_in_cache(item_json_datas[KEY_MESSAGE4])
                )
            else:
                json_datas[idx_json_datas][KEY_MESSAGE4] = read_from_cache(
                    item_json_datas[KEY_MESSAGE4]
                )

        # pages是列表
        if (
            KEY_PAGES in item_json_datas
            and isinstance(item_json_datas[KEY_PAGES], list)
            and len(item_json_datas[KEY_PAGES]) > 0
        ):
            pages = item_json_datas[KEY_PAGES]
            for idx_pages, item_pages in enumerate(pages):
                # list是列表
                if (
                    not KEY_LIST in item_pages
                    or not isinstance(item_pages[KEY_LIST], list)
                    or len(item_pages[KEY_LIST]) < 1
                ):
                    continue

                lists = item_pages[KEY_LIST]
                # 记录各元素的索引位置，用于删除无用的文本行
                list_idx_record = []
                for idx_lists, item_lists in enumerate(lists):
                    if not item_lists:
                        continue

                    # parameters是列表
                    if (
                        KEY_PARAMETERS not in item_lists[KEY_PARAMETERS]
                        or not isinstance(item_lists[KEY_PARAMETERS], list)
                        or len(item_lists[KEY_PARAMETERS]) < 1
                    ):
                        continue

                    parameters = item_lists[KEY_PARAMETERS]
                    code = item_lists[KEY_CODE]
                    # 选择菜单
                    if (
                        code == 102
                        and isinstance(parameters[0], list)
                        and len(parameters[0]) > 0
                    ):
                        for idx, choose in enumerate(parameters[0]):
                            if _type == EXTRACT:
                                _change = switch_change_mark(
                                    _change, write_in_cache(choose)
                                )
                            else:
                                lists[idx_lists][KEY_PARAMETERS][0][idx] = (
                                    read_from_cache(choose)
                                )
                        continue

                    # 变量操作
                    if (
                        code == 122
                        and isinstance(parameters[4], str)
                        and not any(s in parameters[4] for s in ['$', '.'])
                    ):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, write_in_cache(parameters[4])
                            )
                        else:
                            lists[idx_lists][KEY_PARAMETERS][4] = read_from_cache(
                                parameters[4]
                            )
                        continue

                    # 改名
                    if code == 320 and isinstance(parameters[1], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, write_in_cache(parameters[1])
                            )
                        else:
                            lists[idx_lists][KEY_PARAMETERS][1] = read_from_cache(
                                parameters[1]
                            )
                        continue

                    # 脚本
                    if code in [355, 655] and isinstance(parameters[0], str):
                        if '"' not in parameters[0]:
                            continue
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change,
                                write_in_cache(parameters[0], value=parameters[0]),
                            )
                        else:
                            txt = read_from_cache(parameters[0])
                            if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                                list_idx_record.append(idx_lists)
                                txt = ''
                            lists[idx_lists][KEY_PARAMETERS][0] = txt

                    # 对话
                    if code == 401 and isinstance(parameters[0], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, write_in_cache(parameters[0])
                            )
                        else:
                            txt = read_from_cache(parameters[0])
                            if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                                list_idx_record.append(idx_lists)
                                txt = ''
                            lists[idx_lists][KEY_PARAMETERS][0] = txt
                        continue

                    # 选项
                    if code == 402 and isinstance(parameters[1], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, write_in_cache(parameters[1])
                            )
                        else:
                            lists[idx_lists][KEY_PARAMETERS][1] = read_from_cache(
                                parameters[1]
                            )
                        continue

                    # 滚动文章
                    if code == 405 and isinstance(parameters[0], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, write_in_cache(parameters[0])
                            )
                        else:
                            txt = read_from_cache(parameters[0])
                            if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                                list_idx_record.append(idx_lists)
                                txt = ''
                            lists[idx_lists][KEY_PARAMETERS][0] = txt
                        continue

                if len(list_idx_record) > 0:
                    # 反向列表中元素
                    list_idx_record.reverse()
                    # 统一删除空文本行
                    for v in list_idx_record:
                        lists.pop(v)
                pages[idx_pages][KEY_LIST] = lists
            json_datas[idx_json_datas][KEY_PAGES] = pages

    return _change


def sacnning_common_events(json_datas: list, _type: str) -> bool:
    '''
    扫描CommonEvents。数据结构：array[object]
    '''

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, list) or len(json_datas) < 1:
        return _change

    for idx_json_datas, item_json_datas in enumerate(json_datas):
        if not item_json_datas:
            continue

        # list是列表
        if (
            not KEY_LIST in item_json_datas
            or not isinstance(item_json_datas[KEY_LIST], list)
            or len(item_json_datas[KEY_LIST]) < 1
        ):
            continue

        lists = item_json_datas[KEY_LIST]
        # 记录各元素的索引位置，用于删除无用的文本行
        list_idx_record = []
        for idx_lists, item_lists in enumerate(lists):
            if not item_lists:
                continue

            # parameter是列表
            if (
                KEY_PARAMETERS not in item_lists
                or not isinstance(item_lists[KEY_PARAMETERS], list)
                or len(item_lists[KEY_PARAMETERS]) < 1
            ):
                continue

            parameters = item_lists[KEY_PARAMETERS]
            code = item_lists[KEY_CODE]
            # 选择菜单
            if (
                code == 102
                and isinstance(parameters[0], list)
                and len(parameters[0]) > 0
            ):
                for idx, choose in enumerate(parameters[0]):
                    if _type == EXTRACT:
                        _change = switch_change_mark(_change, write_in_cache(choose))
                    else:
                        lists[idx_lists][KEY_PARAMETERS][0][idx] = read_from_cache(
                            choose
                        )
                continue

            # 变量操作
            if (
                code == 122
                and isinstance(parameters[4], str)
                and not any(s in parameters[4] for s in ['$', '.'])
            ):
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(parameters[4]))
                else:
                    lists[idx_lists][KEY_PARAMETERS][4] = read_from_cache(parameters[4])
                continue

            # 改名
            if code == 320 and isinstance(parameters[1], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(parameters[1]))
                else:
                    lists[idx_lists][KEY_PARAMETERS][1] = read_from_cache(parameters[1])
                continue

            # 脚本
            if code == 355 and isinstance(parameters[0], str):
                if '"' not in parameters[0]:
                    continue
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, write_in_cache(parameters[0], value=parameters[0])
                    )
                else:
                    txt = read_from_cache(parameters[0])
                    if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                        list_idx_record.append(idx_lists)
                        txt = ''
                    lists[idx_lists][KEY_PARAMETERS][0] = txt

            # 对话
            if code == 401 and isinstance(parameters[0], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(parameters[0]))
                else:
                    txt = read_from_cache(parameters[0])
                    if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                        list_idx_record.append(idx_lists)
                        txt = ''
                    lists[idx_lists][KEY_PARAMETERS][0] = txt
                continue

            # 选项
            if code == 402 and isinstance(parameters[1], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(parameters[1]))
                else:
                    lists[idx_lists][KEY_PARAMETERS][1] = read_from_cache(parameters[1])
                continue

            # 滚动文章
            if code == 405 and isinstance(parameters[0], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(parameters[0]))
                else:
                    txt = read_from_cache(parameters[0])
                    if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                        list_idx_record.append(idx_lists)
                        txt = ''
                    lists[idx_lists][KEY_PARAMETERS][0] = txt
                continue

        if len(list_idx_record) > 0:
            # 反向列表中元素
            list_idx_record.reverse()
            # 统一删除空文本行
            for v in list_idx_record:
                lists.pop(v)
        json_datas[idx_json_datas][KEY_LIST] = lists

    return _change


def scanning_system(json_datas: dict, _type: str, filename: str) -> bool:
    '''
    扫描System.json
    '''

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, dict) or len(json_datas) < 1:
        return _change

    # armorTypes是列表
    if (
        KEY_ARMORTYPES in json_datas
        and isinstance(json_datas[KEY_ARMORTYPES], list)
        and len(json_datas[KEY_ARMORTYPES]) > 0
    ):
        for idx, armortype in enumerate(json_datas[KEY_ARMORTYPES]):
            _loc = get_md5('_'.join([filename, KEY_ARMORTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, write_in_cache(armortype, _loc))
            else:
                json_datas[KEY_ARMORTYPES][idx] = read_from_cache(armortype, _loc)

    # currencyUnit是字串
    if KEY_CURRENCYUNIT in json_datas and isinstance(json_datas[KEY_CURRENCYUNIT], str):
        _loc = get_md5('_'.join([filename, KEY_CURRENCYUNIT]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(
                _change, write_in_cache(json_datas[KEY_CURRENCYUNIT], _loc)
            )
        else:
            json_datas[KEY_CURRENCYUNIT] = read_from_cache(
                json_datas[KEY_CURRENCYUNIT], _loc
            )

    # elements是列表
    if (
        KEY_ELEMENTS in json_datas
        and isinstance(json_datas[KEY_ELEMENTS], list)
        and len(json_datas[KEY_ELEMENTS]) > 0
    ):
        for idx, element in enumerate(json_datas[KEY_ELEMENTS]):
            _loc = get_md5('_'.join([filename, KEY_ELEMENTS, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, write_in_cache(element, _loc))
            else:
                json_datas[KEY_ELEMENTS][idx] = read_from_cache(element, _loc)

    # equipTypes是列表
    if (
        KEY_EQUIPTYPES in json_datas
        and isinstance(json_datas[KEY_EQUIPTYPES], list)
        and len(json_datas[KEY_EQUIPTYPES]) > 0
    ):
        for idx, equiptype in enumerate(json_datas[KEY_EQUIPTYPES]):
            _loc = get_md5('_'.join([filename, KEY_EQUIPTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, write_in_cache(equiptype, _loc))
            else:
                json_datas[KEY_EQUIPTYPES][idx] = read_from_cache(equiptype, _loc)

    # 游戏标题是字串
    if KEY_GAMETITLE in json_datas and isinstance(json_datas[KEY_GAMETITLE], str):
        _loc = get_md5('_'.join([filename, KEY_GAMETITLE]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(
                _change, write_in_cache(json_datas[KEY_GAMETITLE], _loc)
            )
        else:
            json_datas[KEY_GAMETITLE] = read_from_cache(json_datas[KEY_GAMETITLE], _loc)

    # skillTypes是列表
    if (
        KEY_SKILLTYPES in json_datas
        and isinstance(json_datas[KEY_SKILLTYPES], list)
        and len(json_datas[KEY_SKILLTYPES]) > 0
    ):
        for idx, skilltype in enumerate(json_datas[KEY_SKILLTYPES]):
            _loc = get_md5('_'.join([filename, KEY_SKILLTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, write_in_cache(skilltype, _loc))
            else:
                json_datas[KEY_SKILLTYPES][idx] = read_from_cache(skilltype, _loc)

    # weaponTypes是列表
    if (
        KEY_WEAPONTYPES in json_datas
        and isinstance(json_datas[KEY_WEAPONTYPES], list)
        and len(json_datas[KEY_WEAPONTYPES]) > 0
    ):
        for idx, weapontype in enumerate(json_datas[KEY_WEAPONTYPES]):
            _loc = get_md5('_'.join([filename, KEY_WEAPONTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, write_in_cache(weapontype, _loc))
            else:
                json_datas[KEY_WEAPONTYPES][idx] = read_from_cache(weapontype, _loc)

    if KEY_TERMS in json_datas:
        _terms = json_datas[KEY_TERMS]
        # basic是列表
        if (
            KEY_BASIC in _terms
            and isinstance(_terms[KEY_BASIC], list)
            and len(_terms[KEY_BASIC]) > 0
        ):
            for idx, basic in enumerate(_terms[KEY_BASIC]):
                _loc = get_md5(
                    '_'.join([filename, KEY_TERMS, KEY_BASIC, str(idx)]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(basic, _loc))
                else:
                    json_datas[KEY_TERMS][KEY_BASIC][idx] = read_from_cache(basic, _loc)

        # commands是列表
        if (
            KEY_COMMANDS in _terms
            and isinstance(_terms[KEY_COMMANDS], list)
            and len(_terms[KEY_COMMANDS]) > 0
        ):
            for idx, command in enumerate(_terms[KEY_COMMANDS]):
                _loc = get_md5(
                    '_'.join([filename, KEY_TERMS, KEY_COMMANDS, str(idx)]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(command, _loc))
                else:
                    json_datas[KEY_TERMS][KEY_COMMANDS][idx] = read_from_cache(
                        command, _loc
                    )

        # params是列表
        if (
            KEY_PARAMS in _terms
            and isinstance(_terms[KEY_PARAMS], list)
            and len(_terms[KEY_PARAMS]) > 0
        ):
            for idx, param in enumerate(_terms[KEY_PARAMS]):
                _loc = get_md5(
                    '_'.join([filename, KEY_TERMS, KEY_PARAMS, str(idx)]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(param, _loc))
                else:
                    json_datas[KEY_TERMS][KEY_PARAMS][idx] = read_from_cache(
                        param, _loc
                    )

        # messages是字典
        if (
            KEY_MESSAGES in _terms
            and isinstance(_terms[KEY_MESSAGES], dict)
            and len(_terms[KEY_MESSAGES]) > 0
        ):
            for key, message in _terms[KEY_MESSAGES].items():
                if message.strip() == '':
                    continue
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, write_in_cache(message))
                else:
                    json_datas[KEY_TERMS][KEY_MESSAGES][key] = read_from_cache(message)

    return _change


def scanning_type_maps(json_datas: dict, _type: str, filename: str) -> bool:
    '''
    扫描各种Map
    '''

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, dict) or len(json_datas) < 1:
        return _change

    # displayName是字串
    if KEY_DISPLAYNAME in json_datas and isinstance(json_datas[KEY_DISPLAYNAME], str):
        _loc = get_md5('_'.join([filename, KEY_DISPLAYNAME]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(
                _change, write_in_cache(json_datas[KEY_DISPLAYNAME], _loc)
            )
        else:
            json_datas[KEY_DISPLAYNAME] = read_from_cache(
                json_datas[KEY_DISPLAYNAME], _loc
            )

    # events是列表
    if (
        KEY_EVENTS not in json_datas
        or not isinstance(json_datas[KEY_EVENTS], list)
        or len(json_datas[KEY_EVENTS]) < 1
    ):
        return _change

    for idx_events, item_events in enumerate(json_datas[KEY_EVENTS]):
        if not item_events:
            continue

        # pages是列表
        if (
            KEY_PAGES not in item_events
            or not isinstance(item_events[KEY_PAGES], list)
            or len(item_events[KEY_PAGES]) < 1
        ):
            continue

        pages = item_events[KEY_PAGES]
        for idx_pages, item_pages in enumerate(pages):
            # list是列表
            if (
                KEY_LIST not in item_pages
                or not isinstance(item_pages[KEY_LIST], list)
                or len(item_pages[KEY_LIST]) < 1
            ):
                continue

            lists = item_pages[KEY_LIST]
            # 记录各元素的索引位置，用于删除无用的文本行
            lists_idx_record = []
            for idx_lists, item_lists in enumerate(lists):
                if not item_lists:
                    continue

                # parameters是列表
                if (
                    KEY_PARAMETERS not in item_lists
                    or not isinstance(item_lists[KEY_PARAMETERS], list)
                    or len(item_lists[KEY_PARAMETERS]) < 1
                ):
                    continue

                parameters = item_lists[KEY_PARAMETERS]
                code = item_lists[KEY_CODE]
                # 选择菜单
                if (
                    code == 102
                    and isinstance(parameters[0], list)
                    and len(parameters[0]) > 0
                ):
                    for idx, choose in enumerate(parameters[0]):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, write_in_cache(choose)
                            )
                        else:
                            lists[idx_lists][KEY_PARAMETERS][0][idx] = read_from_cache(
                                choose
                            )
                    continue

                # 变量操作
                if (
                    code == 122
                    and isinstance(parameters[4], str)
                    and not any(s in parameters[4] for s in ['$', '.'])
                ):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, write_in_cache(parameters[4])
                        )
                    else:
                        lists[idx_lists][KEY_PARAMETERS][4] = read_from_cache(
                            parameters[4]
                        )
                    continue

                # 改名
                if code == 320 and isinstance(parameters[1], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, write_in_cache(parameters[1])
                        )
                    else:
                        lists[idx_lists][KEY_PARAMETERS][1] = read_from_cache(
                            parameters[1]
                        )
                    continue

                # 脚本
                if code in [355, 655] and isinstance(parameters[0], str):
                    if '"' not in parameters[0]:
                        continue
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, write_in_cache(parameters[0], value=parameters[0])
                        )
                    else:
                        txt = read_from_cache(parameters[0])
                        if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                            lists_idx_record.append(idx_lists)
                            txt = ''
                        lists[idx_lists][KEY_PARAMETERS][0] = txt

                # 对话
                if code == 401 and isinstance(parameters[0], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, write_in_cache(parameters[0])
                        )
                    else:
                        txt = read_from_cache(parameters[0])
                        if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                            lists_idx_record.append(idx_lists)
                            txt = ''
                        lists[idx_lists][KEY_PARAMETERS][0] = txt
                    continue

                # 选项
                if code == 402 and isinstance(parameters[1], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, write_in_cache(parameters[1])
                        )
                    else:
                        lists[idx_lists][KEY_PARAMETERS][1] = read_from_cache(
                            parameters[1]
                        )
                    continue

                # 滚动文章
                if code == 405 and isinstance(parameters[0], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, write_in_cache(parameters[0])
                        )
                    else:
                        txt = read_from_cache(parameters[0])
                        if txt.strip().upper() == GLOBAL_DATA['none_filter']:
                            lists_idx_record.append(idx_lists)
                            txt = ''
                        lists[idx_lists][KEY_PARAMETERS][0] = txt
                    continue

            if len(lists_idx_record) > 0:
                # 反向列表中元素
                lists_idx_record.reverse()
                # 统一删除空文本行
                for v in lists_idx_record:
                    lists.pop(v)
            pages[idx_pages][KEY_LIST] = lists
        json_datas[KEY_EVENTS][idx_events][KEY_PAGES] = pages

    return _change


# def scanning_wicked_rouge(json_datas: dict, _type: str) -> bool:
#     '''
#     扫描Wicked Rouge的BattleHUD.json和MapHUD.json
#     '''

#     # 记录文本更改
#     _change = False

#     if not json_datas or not isinstance(json_datas, dict) or len(json_datas) < 1:
#         return _change

#     for i_json_datas, item_json_datas in json_datas.items():
#         if (
#             not item_json_datas
#             or not isinstance(item_json_datas, list)
#             or len(item_json_datas) < 1
#         ):
#             continue

#         for i, item in enumerate(item_json_datas):
#             if not item or not isinstance(item, dict):
#                 continue
#             if KEY_TYPE not in item or not item[KEY_TYPE] == KEY_TYPE_VALUE:
#                 continue
#             if KEY_VALUE not in item or item[KEY_VALUE].strip() == '':
#                 continue

#             if _type == EXTRACT:
#                 _change = switch_change_mark(_change, write_in_cache(item[KEY_VALUE]))
#             else:
#                 json_datas[i_json_datas][i][KEY_VALUE] = read_from_cache(
#                     item[KEY_VALUE]
#                 )

#     return _change


def _read_game_txt(_type: str) -> bool:
    '''
    读取gameText.json和文本库
    '''

    # 读取待翻译文本
    global _game_txt_cache
    _game_txt_cache = read_json(curr_rpgm_project_abspath)

    # 将更新标识的值重置为False
    change_phoenix_mark(_game_txt_cache)

    # 当处于写入模式时，如果缓存数据为空，则返回False
    if _type == WRITEIN and len(_game_txt_cache) < 2:
        print_warn(f'{curr_rpgm_project_name} 不存在或无内容！')
        return False

    # 读取引擎默认文本库
    default_libraries = read_json(
        os.path.join(BASE_ABSPATH, 'libraries', RPGMV_DEFAULT_LIBRARY)
    )
    # 读取游戏已有译文
    translated_libraries = read_json(
        os.path.join(BASE_ABSPATH, 'libraries', GLOBAL_DATA['rpg_game_default_txt'])
    )
    # 初始化译文库缓存
    global _game_txt_library
    _game_txt_library = merge_dicts([default_libraries, translated_libraries])

    return True


def write_in_cache(key: str, _loc='', _filter='', value='') -> bool:
    '''
    将数据存入缓存
    '''

    if key.strip() == '':
        return False

    _key = _loc + '_' + key if _loc != '' else key

    # 不匹配指定语种的文本不存入缓存
    if not matching_langs(key, _filter):
        return False

    # 缓存中已有该字段，且值不为空字串或TODO时，直接返回
    if (
        _key in _game_txt_cache
        and _game_txt_cache[_key] != ''
        and _game_txt_cache[_key].strip().upper() != MARK_TODO
    ):
        return False

    # Threads of Destiny
    # if '{' in key and '}' in key:
    #     key1 = key[key.find('{') + 1:key.find('}')]
    #     _key2 = _loc + '_' + key1 if _loc != '' else key1
    #     if _key2 in _translation_library and _translation_library[_key2] != '' and _translation_library[_key2] != TODO_FILTER:
    #         temp_game_txt_cache[_key] = key[:key.find('{')] + _translation_library[_key2] + key[key.find('}') + 1:]
    #         change_phoenix_mark(_game_txt_cache, True)
    #         return True

    # default_strings中有该条文本且不为空字串，赋值
    if (
        _key in _game_txt_library
        and _game_txt_library[_key] != ''
        and _game_txt_library[_key].strip().upper() != MARK_TODO
    ):
        _game_txt_cache[_key] = _game_txt_library[_key]
        change_phoenix_mark(_game_txt_cache, True)
        return True

    # 如果参数中直接传入了文本值value且不为空字符串时，直接赋值
    if value != '':
        _game_txt_cache[_key] = value
        if _key.startswith(KEY_MARK1) and _key.endswith(KEY_MARK2):
            return True
        change_phoenix_mark(_game_txt_cache, True)
        return True

    # 既然前面可赋值的情况都pass了，若缓存中有该字段，直接返回
    if _key in _game_txt_cache:
        return False

    _game_txt_cache[_key] = ''
    change_phoenix_mark(_game_txt_cache, True)
    return True


def read_from_cache(key: str, _loc='') -> str:
    '''
    从缓存获取数据
    '''

    if key.strip() == '':
        return key

    _key = _loc + '_' + key if _loc != '' else key

    if _key not in _game_txt_cache or _game_txt_cache[_key] == '':
        return key
    # if TODO_FILTER in _game_txt_cache[_key].upper():    # 标记。待复核文本
    #     return key
    if _game_txt_cache[_key].strip().upper() == MARK_TODO:  # 标记。待翻译文本
        return key
    if _game_txt_cache[_key].upper() in GLOBAL_DATA['pass_filter']:  # 标记。不翻译文本
        return key

    return _game_txt_cache[_key]


def _select_serial_num(reselect=False, serial_num=''):
    '''
    输入序号选择对应的操作
    '''

    if not reselect:
        print(
            '''1) 提取翻译文本
2) 写入翻译文本
0) 返回上一级
'''
        )

        _inp = input('请输入要操作的序号：').strip()
        if _inp == '1':
            walk_file(EXTRACT)
        elif _inp == '2':
            walk_file(WRITEIN)
        elif _inp == '0':
            main.start_main()
        else:
            _select_serial_num(True, _inp)
        return

    _tmp = input(
        f'列表中不存在序号 {serial_num}，请重新输入正确序号或回车退出程序：'
    ).strip()
    if _tmp == '':
        sys.exit(0)

    if _tmp == '1':
        walk_file(EXTRACT)
    elif _tmp == '2':
        walk_file(WRITEIN)
    elif _tmp == '0':
        main.start_main()
    else:
        _select_serial_num(True, _tmp)


def start(project_name: str):
    '''
    启动界面
    '''

    global curr_rpgm_project_name, curr_rpgm_project_abspath

    curr_rpgm_project_name = project_name
    curr_rpgm_project_abspath = os.path.join(RPGM_PROJECT_PARENT_FOLDER, project_name)

    print(
        '''
===========================================================================================
                               RPG Maker MV 文本提取写入工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
'''
    )

    _select_serial_num()

    # 判断翻译文本是否有变动，没有则跳过
    if KEY_PHOENIX in _game_txt_cache and not _game_txt_cache[KEY_PHOENIX]:
        print(f'{curr_rpgm_project_name} 未发生更改，无需写入！\n')
        sys.exit(0)

    # 将更新标识的值重置为False
    change_phoenix_mark(_game_txt_cache)
    # 更新gameText.json
    write_json(curr_rpgm_project_abspath, _game_txt_cache)

    sys.exit(0)
