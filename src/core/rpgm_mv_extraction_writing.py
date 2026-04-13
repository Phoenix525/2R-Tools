#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-04 23:33:35
"""

import os
import pathlib
import shutil
import sys
from datetime import datetime

import main
from src.utils.global_data import GlobalData
from src.utils.utils import (
    del_key_from_dict,
    get_md5,
    match_lang,
    merge_dicts,
    print_info,
    print_warn,
    read_json,
    switch_change_mark,
    update_phoenix_mark,
    waiit_key_or_enter,
    write_json,
)

# 提取模式：从原游戏代码提取翻译文本
EXTRACT = "EXTRACT"
# 写入模式：将翻译文本写入游戏代码
WRITEIN = "WRITEIN"

# MV引擎默认文本库
RPGMV_DEFAULT_LIBRARY = "rpgmv_default_library.json"

TYPE_COMMONEVENTS = "CommonEvents"
TYPE_SYSTEM = "System"

# 要扫描的属性参数
KEY_NAME = "name"
KEY_DESCRIPTION = "description"
KEY_EVENTS = "events"
KEY_PAGES = "pages"
KEY_LIST = "list"
KEY_CODE = "code"
KEY_PARAMETERS = "parameters"
# -------- Actors.json --------
KEY_NICKNAME = "nickname"
KEY_PROFILE = "profile"
# -------- States.json --------
KEY_MESSAGE1 = "message1"
KEY_MESSAGE2 = "message2"
KEY_MESSAGE3 = "message3"
KEY_MESSAGE4 = "message4"
# -------- System.json --------
KEY_ARMORTYPES = "armorTypes"
KEY_WEAPONTYPES = "weaponTypes"
KEY_EQUIPTYPES = "equipTypes"
KEY_SKILLTYPES = "skillTypes"
KEY_CURRENCYUNIT = "currencyUnit"
KEY_ELEMENTS = "elements"
KEY_GAMETITLE = "gameTitle"
KEY_TERMS = "terms"
KEY_BASIC = "basic"
KEY_COMMANDS = "commands"
KEY_PARAMS = "params"
KEY_MESSAGES = "messages"
# -------- Mapxxx.json --------
KEY_DISPLAYNAME = "displayName"

# Wicked Rouge
TYPE_BATTLEHUD = "BattleHUD"
TYPE_MAPHUD = "MapHUD"
KEY_TYPE = "type"
KEY_VALUE = "Value"
KEY_TYPE_VALUE = "Text"

# pylint: disable=invalid-name
# 缓存文本
__game_txt_cache: dict[str, str] = None
# 默认文本
__game_txt_library: dict[str, str] = None
# 当前rpgm项目名称
__curr_rpgm_project_name: str = "Test_v0.1.json"
# 当前rpgm翻译文件的绝对路径
__curr_rpgm_project_path: str = os.path.join(
    GlobalData.RPGM_PROJECT_PARENT_FOLDER, __curr_rpgm_project_name
)


def start(project_name: str):
    """
    启动界面
    """

    global __curr_rpgm_project_name, __curr_rpgm_project_path

    __curr_rpgm_project_name = project_name
    __curr_rpgm_project_path = os.path.join(
        GlobalData.RPGM_PROJECT_PARENT_FOLDER, project_name
    )

    print("""
===========================================================================================
                               RPG Maker MV 文本提取写入工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
""")

    no_skip = __choose_option()
    if not no_skip:
        main.start_main()
        return

    # 判断翻译文本是否有变动，没有则跳过
    if (
        GlobalData.KEY_PHOENIX in __game_txt_cache
        and not __game_txt_cache[GlobalData.KEY_PHOENIX]
    ):
        print(f"{__curr_rpgm_project_name} 未发生更改，无需写入！\n")
    else:
        # 将更新标识的值重置为False
        update_phoenix_mark(__game_txt_cache)
        # 更新翻译项目
        write_json(__curr_rpgm_project_path, __game_txt_cache)

    inp = waiit_key_or_enter("按任意键返回主菜单或回车退出程序：")
    if inp:
        sys.exit()
    else:
        # 返回主菜单
        main.start_main()


def __walk_file(_type: str):
    """
    遍历文件夹内所有内容
    """

    pathlib.Path(GlobalData.RPGM_INPUT_ABSPATH).mkdir(parents=True, exist_ok=True)
    if os.path.exists(GlobalData.RPGM_OUTPUT_ABSPATH):
        shutil.rmtree(GlobalData.RPGM_OUTPUT_ABSPATH)
    os.makedirs(GlobalData.RPGM_OUTPUT_ABSPATH)

    # 读取文本库
    if not __read_game_txt(_type):
        return

    # 遍历所有文件，筛选出需要的json文件进行处理
    for root, dirs, files in os.walk(GlobalData.RPGM_INPUT_ABSPATH, topdown=False):
        # 新文件目录
        relative_path = os.path.relpath(root, GlobalData.RPGM_INPUT_ABSPATH)
        new_path = (
            GlobalData.RPGM_OUTPUT_ABSPATH
            if relative_path == "."
            else os.path.join(GlobalData.RPGM_OUTPUT_ABSPATH, relative_path)
        )
        # 自动创建新目录
        os.makedirs(new_path, exist_ok=True)

        for json_file in files:
            # 只处理扩展名为json的文件，非json扩展名的文件即便内容是标准json，也不处理
            if not json_file.endswith(".json"):
                continue
            # 如果当前json文件不在白名单内，且不符合Map地图文件，则跳过它
            if json_file[
                :-5
            ] not in GlobalData.rpg_white_list and not GlobalData.PATTERN_MAP.match(
                json_file[:-5]
            ):
                # 如果当前为写入模式，在新目录拷贝一份该文件
                if _type == WRITEIN:
                    shutil.copy(os.path.join(root, json_file), new_path)
                print(f"{json_file} 不在白名单内，已跳过！\n")
                continue

            __deal_with_json_file(root, json_file, _type, new_path)


def __deal_with_json_file(root: str, json_file: str, _type: str, new_path: str):
    """
    处理JSON数据
    """

    print(f"当前扫描文本：{json_file}")
    # 这里的json_datas不做拷贝，直接传入下面的函数
    json_datas = read_json(os.path.join(root, json_file))
    if not json_datas:
        print(f"{json_file} 无内容，已跳过！\n")
        return

    filename = json_file[:-5]
    # 翻译文本所在文件的标识
    file_mark = ""
    # 当前为提取模式时，在处理文本之前，将标识行写入缓存
    if _type == EXTRACT:
        time = datetime.now().strftime("%Y_%m_%d %H:%M")
        file_mark = f"{GlobalData.TRANSLATED_FILE_MARK}{filename}_{time}"
        __write_in_cache(file_mark, "", "", file_mark)

    # 记录文本更改
    _change = False

    if filename in GlobalData.rpg_type_array_object:
        _change = __sacnning_type_player(json_datas, _type, filename)
    elif filename == TYPE_COMMONEVENTS:
        _change = __sacnning_common_events(json_datas, _type)
    elif filename == TYPE_SYSTEM:
        _change = __scanning_system(json_datas, _type, filename)
    elif GlobalData.PATTERN_MAP.match(filename):
        _change = __scanning_type_maps(json_datas, _type, filename)

    # elif filename in (TYPE_BATTLEHUD, TYPE_MAPHUD):
    #     _change = scanning_wicked_rouge(json_datas, _type)

    # 提取模式
    if _type == EXTRACT:
        # 如果数据无变动，删除之前写入的标识行
        if not _change:
            global __game_txt_cache
            __game_txt_cache = del_key_from_dict(file_mark, __game_txt_cache)
        print_info(f"{json_file} 扫描完成！\n")

    # 当前为写入模式时，写入json文本
    elif _type == WRITEIN:
        write_json(os.path.join(new_path, json_file), json_datas, backup=False)


def __sacnning_type_player(json_datas: list, _type: str, filename: str) -> bool:
    """
    扫描各种武器护具敌人等数据文件。数据结构：array[object]
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, list):
        return _change

    for json_datas_idx, json_datas_item in enumerate(json_datas):
        if not json_datas_item:
            continue

        if KEY_NAME in json_datas_item and isinstance(json_datas_item[KEY_NAME], str):
            # 人名基本不会出现歧义，可以去重
            if filename in GlobalData.rpg_duplicate_removal_list:
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(json_datas_item[KEY_NAME])
                    )
                else:
                    json_datas[json_datas_idx][KEY_NAME] = __read_from_cache(
                        json_datas_item[KEY_NAME]
                    )
            else:
                _loc = get_md5(
                    "_".join([filename, str(json_datas_idx), KEY_NAME]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(json_datas_item[KEY_NAME], _loc)
                    )
                else:
                    json_datas[json_datas_idx][KEY_NAME] = __read_from_cache(
                        json_datas_item[KEY_NAME], _loc
                    )

        if KEY_NICKNAME in json_datas_item and isinstance(
            json_datas_item[KEY_NICKNAME], str
        ):
            # 昵称应该不会出现歧义，此处去重
            # _loc = get_md5('_'.join([filename, str(i_json_datas), KEY_NICKNAME]), True)
            _loc = ""
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_NICKNAME], _loc)
                )
            else:
                json_datas[json_datas_idx][KEY_NICKNAME] = __read_from_cache(
                    json_datas_item[KEY_NICKNAME], _loc
                )

        if KEY_PROFILE in json_datas_item and isinstance(
            json_datas_item[KEY_PROFILE], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_PROFILE])
                )
            else:
                json_datas[json_datas_idx][KEY_PROFILE] = __read_from_cache(
                    json_datas_item[KEY_PROFILE]
                )

        if KEY_DESCRIPTION in json_datas_item and isinstance(
            json_datas_item[KEY_DESCRIPTION], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_DESCRIPTION])
                )
            else:
                json_datas[json_datas_idx][KEY_DESCRIPTION] = __read_from_cache(
                    json_datas_item[KEY_DESCRIPTION]
                )

        if KEY_MESSAGE1 in json_datas_item and isinstance(
            json_datas_item[KEY_MESSAGE1], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_MESSAGE1])
                )
            else:
                json_datas[json_datas_idx][KEY_MESSAGE1] = __read_from_cache(
                    json_datas_item[KEY_MESSAGE1]
                )

        if KEY_MESSAGE2 in json_datas_item and isinstance(
            json_datas_item[KEY_MESSAGE2], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_MESSAGE2])
                )
            else:
                json_datas[json_datas_idx][KEY_MESSAGE2] = __read_from_cache(
                    json_datas_item[KEY_MESSAGE2]
                )

        if KEY_MESSAGE3 in json_datas_item and isinstance(
            json_datas_item[KEY_MESSAGE3], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_MESSAGE3])
                )
            else:
                json_datas[json_datas_idx][KEY_MESSAGE3] = __read_from_cache(
                    json_datas_item[KEY_MESSAGE3]
                )

        if KEY_MESSAGE4 in json_datas_item and isinstance(
            json_datas_item[KEY_MESSAGE4], str
        ):
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(json_datas_item[KEY_MESSAGE4])
                )
            else:
                json_datas[json_datas_idx][KEY_MESSAGE4] = __read_from_cache(
                    json_datas_item[KEY_MESSAGE4]
                )

        # pages是列表
        if (
            KEY_PAGES in json_datas_item
            and json_datas_item[KEY_PAGES]
            and isinstance(json_datas_item[KEY_PAGES], list)
        ):
            pages = json_datas_item[KEY_PAGES]
            for pages_idx, pages_item in enumerate(pages):
                # list是列表
                if (
                    KEY_LIST not in pages_item
                    or not pages_item[KEY_LIST]
                    or not isinstance(pages_item[KEY_LIST], list)
                ):
                    continue

                lists = pages_item[KEY_LIST]
                # 记录各元素的索引位置，用于删除无用的文本行
                lists_idx_record: list[int] = []
                for lists_idx, lists_item in enumerate(lists):
                    if not lists_item:
                        continue

                    # parameters是列表
                    if (
                        KEY_PARAMETERS not in lists_item[KEY_PARAMETERS]
                        or not lists_item[KEY_PARAMETERS]
                        or not isinstance(lists_item[KEY_PARAMETERS], list)
                    ):
                        continue

                    parameters = lists_item[KEY_PARAMETERS]
                    code = lists_item[KEY_CODE]
                    # 选择菜单
                    if (
                        code == 102
                        and parameters[0]
                        and isinstance(parameters[0], list)
                    ):
                        for idx, choose in enumerate(parameters[0]):
                            if _type == EXTRACT:
                                _change = switch_change_mark(
                                    _change, __write_in_cache(choose)
                                )
                            else:
                                lists[lists_idx][KEY_PARAMETERS][0][idx] = (
                                    __read_from_cache(choose)
                                )
                        continue

                    # 变量操作
                    if (
                        code == 122
                        and isinstance(parameters[4], str)
                        and not any(s in parameters[4] for s in ("$", "."))
                    ):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(parameters[4])
                            )
                        else:
                            lists[lists_idx][KEY_PARAMETERS][4] = __read_from_cache(
                                parameters[4]
                            )
                        continue

                    # 改名
                    if code == 320 and isinstance(parameters[1], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(parameters[1])
                            )
                        else:
                            lists[lists_idx][KEY_PARAMETERS][1] = __read_from_cache(
                                parameters[1]
                            )
                        continue

                    # 脚本
                    if code in (355, 655) and isinstance(parameters[0], str):
                        if '"' not in parameters[0]:
                            continue
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change,
                                __write_in_cache(parameters[0], value=parameters[0]),
                            )
                        else:
                            txt = __read_from_cache(parameters[0])
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists[lists_idx][KEY_PARAMETERS][0] = txt

                    # 对话
                    if code == 401 and isinstance(parameters[0], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(parameters[0])
                            )
                        else:
                            txt = __read_from_cache(parameters[0])
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists[lists_idx][KEY_PARAMETERS][0] = txt
                        continue

                    # 选项
                    if code == 402 and isinstance(parameters[1], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(parameters[1])
                            )
                        else:
                            lists[lists_idx][KEY_PARAMETERS][1] = __read_from_cache(
                                parameters[1]
                            )
                        continue

                    # 滚动文章
                    if code == 405 and isinstance(parameters[0], str):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(parameters[0])
                            )
                        else:
                            txt = __read_from_cache(parameters[0])
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists[lists_idx][KEY_PARAMETERS][0] = txt
                        continue

                if lists_idx_record:
                    # 反向列表中元素
                    lists_idx_record.reverse()
                    # 统一删除空文本行
                    for v in lists_idx_record:
                        lists.pop(v)
                pages[pages_idx][KEY_LIST] = lists
            json_datas[json_datas_idx][KEY_PAGES] = pages

    return _change


def __sacnning_common_events(json_datas: list, _type: str) -> bool:
    """
    扫描CommonEvents。数据结构：array[object]
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, list):
        return _change

    for json_datas_idx, json_datas_item in enumerate(json_datas):
        if not json_datas_item:
            continue

        # list是列表
        if (
            KEY_LIST not in json_datas_item
            or not json_datas_item[KEY_LIST]
            or not isinstance(json_datas_item[KEY_LIST], list)
        ):
            continue

        lists = json_datas_item[KEY_LIST]
        # 记录各元素的索引位置，用于删除无用的文本行
        lists_idx_record: list[int] = []
        for lists_idx, lists_item in enumerate(lists):
            if not lists_item:
                continue

            # parameter是列表
            if (
                KEY_PARAMETERS not in lists_item
                or not lists_item[KEY_PARAMETERS]
                or not isinstance(lists_item[KEY_PARAMETERS], list)
            ):
                continue

            parameters = lists_item[KEY_PARAMETERS]
            code = lists_item[KEY_CODE]
            # 选择菜单
            if code == 102 and parameters[0] and isinstance(parameters[0], list):
                for idx, choose in enumerate(parameters[0]):
                    if _type == EXTRACT:
                        _change = switch_change_mark(_change, __write_in_cache(choose))
                    else:
                        lists[lists_idx][KEY_PARAMETERS][0][idx] = __read_from_cache(
                            choose
                        )
                continue

            # 变量操作
            if (
                code == 122
                and isinstance(parameters[4], str)
                and not any(s in parameters[4] for s in ("$", "."))
            ):
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(parameters[4])
                    )
                else:
                    lists[lists_idx][KEY_PARAMETERS][4] = __read_from_cache(
                        parameters[4]
                    )
                continue

            # 改名
            if code == 320 and isinstance(parameters[1], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(parameters[1])
                    )
                else:
                    lists[lists_idx][KEY_PARAMETERS][1] = __read_from_cache(
                        parameters[1]
                    )
                continue

            # 脚本
            if code in (355, 655) and isinstance(parameters[0], str):
                if '"' not in parameters[0]:
                    continue
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(parameters[0], value=parameters[0])
                    )
                else:
                    txt = __read_from_cache(parameters[0])
                    if txt.strip().upper() == GlobalData.none_filter:
                        lists_idx_record.append(lists_idx)
                        txt = ""
                    lists[lists_idx][KEY_PARAMETERS][0] = txt

            # 对话
            if code == 401 and isinstance(parameters[0], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(parameters[0])
                    )
                else:
                    txt = __read_from_cache(parameters[0])
                    if txt.strip().upper() == GlobalData.none_filter:
                        lists_idx_record.append(lists_idx)
                        txt = ""
                    lists[lists_idx][KEY_PARAMETERS][0] = txt
                continue

            # 选项
            if code == 402 and isinstance(parameters[1], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(parameters[1])
                    )
                else:
                    lists[lists_idx][KEY_PARAMETERS][1] = __read_from_cache(
                        parameters[1]
                    )
                continue

            # 滚动文章
            if code == 405 and isinstance(parameters[0], str):
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(parameters[0])
                    )
                else:
                    txt = __read_from_cache(parameters[0])
                    if txt.strip().upper() == GlobalData.none_filter:
                        lists_idx_record.append(lists_idx)
                        txt = ""
                    lists[lists_idx][KEY_PARAMETERS][0] = txt
                continue

        if lists_idx_record:
            # 反向列表中元素
            lists_idx_record.reverse()
            # 统一删除空文本行
            for v in lists_idx_record:
                lists.pop(v)
        json_datas[json_datas_idx][KEY_LIST] = lists

    return _change


def __scanning_system(json_datas: dict, _type: str, filename: str) -> bool:
    """
    扫描System.json
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, dict):
        return _change

    # armorTypes是列表
    if (
        KEY_ARMORTYPES in json_datas
        and json_datas[KEY_ARMORTYPES]
        and isinstance(json_datas[KEY_ARMORTYPES], list)
    ):
        for idx, armortype in enumerate(json_datas[KEY_ARMORTYPES]):
            _loc = get_md5("_".join([filename, KEY_ARMORTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(armortype, _loc))
            else:
                json_datas[KEY_ARMORTYPES][idx] = __read_from_cache(armortype, _loc)

    # currencyUnit是字串
    if KEY_CURRENCYUNIT in json_datas and isinstance(json_datas[KEY_CURRENCYUNIT], str):
        _loc = get_md5("_".join([filename, KEY_CURRENCYUNIT]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(
                _change, __write_in_cache(json_datas[KEY_CURRENCYUNIT], _loc)
            )
        else:
            json_datas[KEY_CURRENCYUNIT] = __read_from_cache(
                json_datas[KEY_CURRENCYUNIT], _loc
            )

    # elements是列表
    if (
        KEY_ELEMENTS in json_datas
        and json_datas[KEY_ELEMENTS]
        and isinstance(json_datas[KEY_ELEMENTS], list)
    ):
        for idx, element in enumerate(json_datas[KEY_ELEMENTS]):
            _loc = get_md5("_".join([filename, KEY_ELEMENTS, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(element, _loc))
            else:
                json_datas[KEY_ELEMENTS][idx] = __read_from_cache(element, _loc)

    # equipTypes是列表
    if (
        KEY_EQUIPTYPES in json_datas
        and json_datas[KEY_EQUIPTYPES]
        and isinstance(json_datas[KEY_EQUIPTYPES], list)
    ):
        for idx, equiptype in enumerate(json_datas[KEY_EQUIPTYPES]):
            _loc = get_md5("_".join([filename, KEY_EQUIPTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(equiptype, _loc))
            else:
                json_datas[KEY_EQUIPTYPES][idx] = __read_from_cache(equiptype, _loc)

    # 游戏标题是字串
    if KEY_GAMETITLE in json_datas and isinstance(json_datas[KEY_GAMETITLE], str):
        _loc = get_md5("_".join([filename, KEY_GAMETITLE]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(
                _change, __write_in_cache(json_datas[KEY_GAMETITLE], _loc)
            )
        else:
            json_datas[KEY_GAMETITLE] = __read_from_cache(
                json_datas[KEY_GAMETITLE], _loc
            )

    # skillTypes是列表
    if (
        KEY_SKILLTYPES in json_datas
        and json_datas[KEY_SKILLTYPES]
        and isinstance(json_datas[KEY_SKILLTYPES], list)
    ):
        for idx, skilltype in enumerate(json_datas[KEY_SKILLTYPES]):
            _loc = get_md5("_".join([filename, KEY_SKILLTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(skilltype, _loc))
            else:
                json_datas[KEY_SKILLTYPES][idx] = __read_from_cache(skilltype, _loc)

    # weaponTypes是列表
    if (
        KEY_WEAPONTYPES in json_datas
        and json_datas[KEY_WEAPONTYPES]
        and isinstance(json_datas[KEY_WEAPONTYPES], list)
    ):
        for idx, weapontype in enumerate(json_datas[KEY_WEAPONTYPES]):
            _loc = get_md5("_".join([filename, KEY_WEAPONTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(weapontype, _loc)
                )
            else:
                json_datas[KEY_WEAPONTYPES][idx] = __read_from_cache(weapontype, _loc)

    if KEY_TERMS in json_datas:
        _terms = json_datas[KEY_TERMS]
        # basic是列表
        if (
            KEY_BASIC in _terms
            and _terms[KEY_BASIC]
            and isinstance(_terms[KEY_BASIC], list)
        ):
            for idx, basic in enumerate(_terms[KEY_BASIC]):
                _loc = get_md5(
                    "_".join([filename, KEY_TERMS, KEY_BASIC, str(idx)]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, __write_in_cache(basic, _loc))
                else:
                    json_datas[KEY_TERMS][KEY_BASIC][idx] = __read_from_cache(
                        basic, _loc
                    )

        # commands是列表
        if (
            KEY_COMMANDS in _terms
            and _terms[KEY_COMMANDS]
            and isinstance(_terms[KEY_COMMANDS], list)
        ):
            for idx, command in enumerate(_terms[KEY_COMMANDS]):
                _loc = get_md5(
                    "_".join([filename, KEY_TERMS, KEY_COMMANDS, str(idx)]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_in_cache(command, _loc)
                    )
                else:
                    json_datas[KEY_TERMS][KEY_COMMANDS][idx] = __read_from_cache(
                        command, _loc
                    )

        # params是列表
        if (
            KEY_PARAMS in _terms
            and _terms[KEY_PARAMS]
            and isinstance(_terms[KEY_PARAMS], list)
        ):
            for idx, param in enumerate(_terms[KEY_PARAMS]):
                _loc = get_md5(
                    "_".join([filename, KEY_TERMS, KEY_PARAMS, str(idx)]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, __write_in_cache(param, _loc))
                else:
                    json_datas[KEY_TERMS][KEY_PARAMS][idx] = __read_from_cache(
                        param, _loc
                    )

        # messages是字典
        if (
            KEY_MESSAGES in _terms
            and _terms[KEY_MESSAGES]
            and isinstance(_terms[KEY_MESSAGES], dict)
        ):
            for key, message in _terms[KEY_MESSAGES].items():
                if message.strip() == "":
                    continue
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, __write_in_cache(message))
                else:
                    json_datas[KEY_TERMS][KEY_MESSAGES][key] = __read_from_cache(
                        message
                    )

    return _change


def __scanning_type_maps(json_datas: dict, _type: str, filename: str) -> bool:
    """
    扫描各种Map
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, dict):
        return _change

    # displayName是字串
    if KEY_DISPLAYNAME in json_datas and isinstance(json_datas[KEY_DISPLAYNAME], str):
        _loc = get_md5("_".join([filename, KEY_DISPLAYNAME]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(
                _change, __write_in_cache(json_datas[KEY_DISPLAYNAME], _loc)
            )
        else:
            json_datas[KEY_DISPLAYNAME] = __read_from_cache(
                json_datas[KEY_DISPLAYNAME], _loc
            )

    # events是列表
    if (
        KEY_EVENTS not in json_datas
        or not json_datas[KEY_EVENTS]
        or not isinstance(json_datas[KEY_EVENTS], list)
    ):
        return _change

    for events_idx, events_item in enumerate(json_datas[KEY_EVENTS]):
        if not events_item:
            continue

        # pages是列表
        if (
            KEY_PAGES not in events_item
            or not events_item[KEY_PAGES]
            or not isinstance(events_item[KEY_PAGES], list)
        ):
            continue

        pages = events_item[KEY_PAGES]
        for pages_idx, pages_item in enumerate(pages):
            # list是列表
            if (
                KEY_LIST not in pages_item
                or not pages_item[KEY_LIST]
                or not isinstance(pages_item[KEY_LIST], list)
            ):
                continue

            lists = pages_item[KEY_LIST]
            # 记录各元素的索引位置，用于删除无用的文本行
            lists_idx_record: list[int] = []
            for lists_idx, lists_item in enumerate(lists):
                if not lists_item:
                    continue

                # parameters是列表
                if (
                    KEY_PARAMETERS not in lists_item
                    or not lists_item[KEY_PARAMETERS]
                    or not isinstance(lists_item[KEY_PARAMETERS], list)
                ):
                    continue

                parameters = lists_item[KEY_PARAMETERS]
                code = lists_item[KEY_CODE]
                # 选择菜单
                if code == 102 and parameters[0] and isinstance(parameters[0], list):
                    for idx, choose in enumerate(parameters[0]):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(choose)
                            )
                        else:
                            lists[lists_idx][KEY_PARAMETERS][0][idx] = (
                                __read_from_cache(choose)
                            )
                    continue

                # 变量操作
                if (
                    code == 122
                    and isinstance(parameters[4], str)
                    and not any(s in parameters[4] for s in ("$", "."))
                ):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, __write_in_cache(parameters[4])
                        )
                    else:
                        lists[lists_idx][KEY_PARAMETERS][4] = __read_from_cache(
                            parameters[4]
                        )
                    continue

                # 改名
                if code == 320 and isinstance(parameters[1], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, __write_in_cache(parameters[1])
                        )
                    else:
                        lists[lists_idx][KEY_PARAMETERS][1] = __read_from_cache(
                            parameters[1]
                        )
                    continue

                # 脚本
                if code in (355, 655) and isinstance(parameters[0], str):
                    if '"' not in parameters[0]:
                        continue
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change,
                            __write_in_cache(parameters[0], value=parameters[0]),
                        )
                    else:
                        txt = __read_from_cache(parameters[0])
                        if txt.strip().upper() == GlobalData.none_filter:
                            lists_idx_record.append(lists_idx)
                            txt = ""
                        lists[lists_idx][KEY_PARAMETERS][0] = txt

                # 对话
                if code == 401 and isinstance(parameters[0], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, __write_in_cache(parameters[0])
                        )
                    else:
                        txt = __read_from_cache(parameters[0])
                        if txt.strip().upper() == GlobalData.none_filter:
                            lists_idx_record.append(lists_idx)
                            txt = ""
                        lists[lists_idx][KEY_PARAMETERS][0] = txt
                    continue

                # 选项
                if code == 402 and isinstance(parameters[1], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, __write_in_cache(parameters[1])
                        )
                    else:
                        lists[lists_idx][KEY_PARAMETERS][1] = __read_from_cache(
                            parameters[1]
                        )
                    continue

                # 滚动文章
                if code == 405 and isinstance(parameters[0], str):
                    if _type == EXTRACT:
                        _change = switch_change_mark(
                            _change, __write_in_cache(parameters[0])
                        )
                    else:
                        txt = __read_from_cache(parameters[0])
                        if txt.strip().upper() == GlobalData.none_filter:
                            lists_idx_record.append(lists_idx)
                            txt = ""
                        lists[lists_idx][KEY_PARAMETERS][0] = txt
                    continue

            if lists_idx_record:
                # 反向列表中元素
                lists_idx_record.reverse()
                # 统一删除空文本行
                for v in lists_idx_record:
                    lists.pop(v)
            pages[pages_idx][KEY_LIST] = lists
        json_datas[KEY_EVENTS][events_idx][KEY_PAGES] = pages

    return _change


# def __scanning_wicked_rouge(json_datas: dict, _type: str) -> bool:
#     '''
#     扫描Wicked Rouge的BattleHUD.json和MapHUD.json
#     '''

#     # 记录文本更改
#     _change = False

#     if not json_datas or not isinstance(json_datas, dict):
#         return _change

#     for i_json_datas, json_datas_item in json_datas.items():
#         if (
#             not json_datas_item
#             or not json_datas_item
#             or not isinstance(json_datas_item, list)
#         ):
#             continue

#         for i, item in enumerate(json_datas_item):
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


def __read_game_txt(_type: str) -> bool:
    """
    读取默认文本库和gameText.json
    """

    # 读取游戏翻译项目
    txt_cache = read_json(__curr_rpgm_project_path)
    global __game_txt_cache
    if txt_cache is not None:
        __game_txt_cache = txt_cache
    else:
        __game_txt_cache = {}

    # 将更新标识的值重置为False
    update_phoenix_mark(__game_txt_cache)

    # 当处于写入模式时，如果游戏翻译项目缓存数据为空，则返回False
    if _type == WRITEIN and len(__game_txt_cache) < 2:
        print_warn(f"{__curr_rpgm_project_name} 不存在或无内容！")
        return False

    # 读取引擎默认文本库
    default_libraries = read_json(
        os.path.join(GlobalData.TRANSLATED_LIBRARIES_ABSPATH, RPGMV_DEFAULT_LIBRARY)
    )
    # 读取游戏已有译文
    translated_libraries = read_json(
        os.path.join(
            GlobalData.TRANSLATED_LIBRARIES_ABSPATH, GlobalData.rpg_game_default_txt
        )
    )
    # 合并两个译文为一个译文库，若有相同键，游戏译文覆盖默认译文
    libraries = merge_dicts([default_libraries, translated_libraries])
    # 初始化译文库缓存
    global __game_txt_library
    __game_txt_library = libraries
    return True


def __write_in_cache(key: str, _loc="", filter_lang="", value="") -> bool:
    """
    将数据存入缓存
    """

    if key.strip() == "":
        return False

    _key = _loc + "_" + key if _loc != "" else key

    # 不匹配指定语种的文本不存入缓存
    if not match_lang(key, filter_lang):
        return False

    # 缓存中已有该字段，且值不为空字串或TODO时，直接返回
    if (
        _key in __game_txt_cache
        and __game_txt_cache[_key] != ""
        and __game_txt_cache[_key].strip().upper() != GlobalData.MARK_TODO
    ):
        return False

    # Threads of Destiny
    # if '{' in key and '}' in key:
    #     key1 = key[key.find('{') + 1:key.find('}')]
    #     _key2 = _loc + '_' + key1 if _loc != '' else key1
    #     if _key2 in _translation_library and _translation_library[_key2] != '' and _translation_library[_key2] != TODO_FILTER:
    #         temp_game_txt_cache[_key] = key[:key.find('{')] + _translation_library[_key2] + key[key.find('}') + 1:]
    #         update_phoenix_mark(_game_txt_cache, True)
    #         return True

    # default_strings中有该条文本且不为空字串，赋值
    if (
        _key in __game_txt_library
        and __game_txt_library[_key] != ""
        and __game_txt_library[_key].strip().upper() != GlobalData.MARK_TODO
    ):
        __game_txt_cache[_key] = __game_txt_library[_key]
        update_phoenix_mark(__game_txt_cache, True)
        return True

    # 如果参数中直接传入了文本值value且不为空字符串时，直接赋值
    if value != "":
        __game_txt_cache[_key] = value
        if _key.startswith(GlobalData.TRANSLATED_FILE_MARK):
            return True
        update_phoenix_mark(__game_txt_cache, True)
        return True

    # 既然前面可赋值的情况都pass了，若缓存中有该字段，直接返回
    if _key in __game_txt_cache:
        return False

    __game_txt_cache[_key] = ""
    update_phoenix_mark(__game_txt_cache, True)
    return True


def __read_from_cache(key: str, _loc="") -> str:
    """
    从缓存获取数据，若找不到则返回原值
    """

    if key is None or key.strip() == "":
        return key

    _key = _loc + "_" + key if _loc != "" else key

    if _key not in __game_txt_cache or __game_txt_cache[_key] == "":
        return key
    # if TODO_FILTER in _game_txt_cache[_key].upper():    # 标记。待复核文本
    #     return key
    if (
        __game_txt_cache[_key].strip().upper() == GlobalData.MARK_TODO
    ):  # 标记。待翻译文本
        return key
    if __game_txt_cache[_key].upper() in GlobalData.pass_filter:  # 标记。不翻译文本
        return key

    return __game_txt_cache[_key]


def __choose_option(first_select=True) -> bool:
    """
    输入序号选择对应的操作

    :param first_select: 首次进入选项
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        print("""1) 从data提取JSON翻译文本
2) 将JSON翻译文本写回data
""")
        _inp = input("请输入要操作的序号或回车返回主菜单：").strip()
    else:
        _inp = input("列表中不存在该序号，请重新输入正确序号或回车返回主菜单：").strip()

    match _inp:
        case "" | "\r" | "\n":
            return False
        case "1":
            __walk_file(EXTRACT)
            return True
        case "2":
            __walk_file(WRITEIN)
            return True
        case _:
            return __choose_option(False)

    return False
