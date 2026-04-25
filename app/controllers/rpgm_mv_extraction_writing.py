#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-04 23:33:35
"""

from datetime import datetime
from gc import collect
from pathlib import Path
from sys import exit

import main
from app.utils.global_data import GlobalData
from app.utils.utils import (
    copy_file,
    copy_tree,
    del_key_from_dict,
    get_md5,
    match_lang,
    merge_dicts,
    print_err,
    print_warn,
    read_json,
    switch_change_mark,
    update_phoenix_mark,
    write_json,
)

# 提取模式：从data文件提取翻译文本
EXTRACT: str = "EXTRACT"
# 写回模式：将翻译文本写入data文件
WRITEIN: str = "WRITEIN"

# MV引擎默认文本库
RPGMV_DEFAULT_LIBRARY: str = "rpgmv_default_library.json"

TYPE_COMMONEVENTS: str = "CommonEvents"
TYPE_SYSTEM: str = "System"

# -------- 通用属性参数 --------
KEY_NAME: str = "name"
KEY_DESCRIPTION: str = "description"
KEY_EVENTS: str = "events"
KEY_PAGES: str = "pages"
KEY_LIST: str = "list"
KEY_CODE: str = "code"
KEY_PARAMETERS: str = "parameters"
# -------- Actors.json --------
KEY_NICKNAME: str = "nickname"
KEY_PROFILE: str = "profile"
# -------- States.json --------
KEY_MESSAGE1: str = "message1"
KEY_MESSAGE2: str = "message2"
KEY_MESSAGE3: str = "message3"
KEY_MESSAGE4: str = "message4"
# -------- System.json --------
KEY_ARMORTYPES: str = "armorTypes"
KEY_WEAPONTYPES: str = "weaponTypes"
KEY_EQUIPTYPES: str = "equipTypes"
KEY_SKILLTYPES: str = "skillTypes"
KEY_CURRENCYUNIT: str = "currencyUnit"
KEY_ELEMENTS: str = "elements"
KEY_GAMETITLE: str = "gameTitle"
KEY_TERMS: str = "terms"
KEY_BASIC: str = "basic"
KEY_COMMANDS: str = "commands"
KEY_PARAMS: str = "params"
KEY_MESSAGES: str = "messages"
# -------- Mapxxx.json --------
KEY_DISPLAYNAME: str = "displayName"

# Wicked Rouge
# TYPE_BATTLEHUD: str = "BattleHUD"
# TYPE_MAPHUD: str = "MapHUD"
# KEY_TYPE: str = "type"
# KEY_VALUE: str = "Value"
# KEY_TYPE_VALUE: str = "Text"

# pylint: disable=invalid-name
__translated_cache: dict[str, str] = None
"""游戏译文库"""
__tmp_translated_cache: dict[str, str] = None
"""译文缓存库"""
__translated_library: dict[str, str] = None
"""初始译文库"""
__curr_trans_proj_name: str = ""
"""当前rpgm翻译项目名称"""
__curr_trans_proj_path: str | Path = ""
"""当前rpgm翻译文件的路径"""


def start(project_name: str):
    """
    启动界面

    :param project_name: rpgm翻译项目名称：名称_版本号.json
    """

    print("\n")

    global __curr_trans_proj_name, __curr_trans_proj_path

    __curr_trans_proj_name = project_name
    __curr_trans_proj_path = GlobalData.rpgm_trans_abspath / project_name

    no_skip = __choose_option()
    if not no_skip:
        #  初始化全局变量数据，避免数据干扰
        init_global_datas()
        main.start_main()
        return

    # 判断翻译文本是否有变动，没有则跳过
    if not __tmp_translated_cache or not __tmp_translated_cache.get(
        GlobalData.KEY_PHOENIX
    ):
        print(f"{__curr_trans_proj_name} 未发生更改，无需写入！\n")
    else:
        # 将更新标识的值重置为False
        update_phoenix_mark(__tmp_translated_cache)
        # 更新翻译项目
        write_json(__curr_trans_proj_path, __tmp_translated_cache)

    #  初始化全局变量数据，避免数据干扰
    init_global_datas()

    inp = input("按任意键返回主菜单或回车退出程序：").strip()
    if inp in ("", "\r", "\n"):
        exit()
    else:
        # 返回主菜单
        main.start_main()


def init_global_datas():
    """
    初始化全局变量数据
    """

    global \
        __translated_cache, \
        __tmp_translated_cache, \
        __translated_library, \
        __curr_trans_proj_name, \
        __curr_trans_proj_path

    __translated_cache = None
    __tmp_translated_cache = None
    __translated_library = None
    __curr_trans_proj_name = ""
    __curr_trans_proj_path = ""

    collect()


def __walk_file(deal_type: str):
    """
    遍历文件夹内所有内容

    :param deal_type: 读取/写回data模式
    """

    # 确保存放游戏data项目的路径存在
    GlobalData.rpgm_datas_abspath.mkdir(parents=True, exist_ok=True)
    # 先根据翻译项目名称查找相应名称的data文件
    datas_abspath = Path(GlobalData.rpgm_datas_abspath) / __curr_trans_proj_name
    if not datas_abspath.exists():
        # 如果不存在，再根据翻译项目名称查找相应名称的data文件夹
        datas_abspath = (
            Path(GlobalData.rpgm_datas_abspath) / __curr_trans_proj_name[:-5]
        )
        if not datas_abspath.exists():
            print_err(f"{datas_abspath.stem}项目不存在！")
            return

    if datas_abspath.is_file():
        if datas_abspath.suffix != ".json" or (
            datas_abspath.stem not in GlobalData.rpg_white_list
            and not GlobalData.pattern_map.match(datas_abspath.stem)
        ):
            print(f"{datas_abspath.name} 不在白名单内，已跳过！\n")
            return

        # 写回模式下，备份data文件
        if deal_type == WRITEIN:
            copy_file(datas_abspath)

        # 初始化缓存译文库和初始译文库
        if not __init_translated_cache_lib(deal_type):
            return

        __deal_with_data_file(datas_abspath, deal_type)

    else:
        # 写回模式下，备份data文件夹
        if deal_type == WRITEIN:
            copy_tree(datas_abspath)

        # 初始化缓存译文库和初始译文库
        if not __init_translated_cache_lib(deal_type):
            return

        # 遍历所有文件，筛选出需要的json文件进行处理
        for file in datas_abspath.rglob("*.json"):
            if not file.is_file():
                continue

            if (
                file.stem not in GlobalData.rpg_white_list
                and not GlobalData.pattern_map.match(file.stem)
            ):
                print(f"{file.name} 不在白名单内，已跳过！\n")
                continue

            __deal_with_data_file(file, deal_type)


def __deal_with_data_file(data_abspath: Path, deal_type: str):
    """
    处理游戏data文件，从data提取文本或将文本写回data

    :param data_abspath: data文件绝对路径
    :param deal_type: 读取/写回data模式
    """

    print(f"当前扫描文本：{data_abspath.name}")
    # 这里的json_datas不做拷贝，直接传入下面的函数
    json_datas = read_json(data_abspath)
    if not json_datas:
        print(f"{data_abspath.name} 无内容，已跳过！\n")
        return

    # 无后缀文件名
    filename = data_abspath.stem
    # 翻译文本中当前data文件的名称标识行
    file_mark = ""
    # 当前为提取模式时，在处理文本之前，将标识行写入文本缓存库
    if deal_type == EXTRACT:
        time = datetime.now().strftime("%Y_%m_%d %H:%M")
        file_mark = f"{GlobalData.TRANSLATED_FILE_MARK}{filename}_{time}"
        __write_to_translated_cache(file_mark, "", "", file_mark)

    # 标记文本是否有更改
    _change = False

    if filename in GlobalData.rpg_type_list_dict:
        _change = __sacnning_type_player(json_datas, deal_type, filename)
    elif filename == TYPE_COMMONEVENTS:
        _change = __sacnning_common_events(json_datas, deal_type)
    elif filename == TYPE_SYSTEM:
        _change = __scanning_system(json_datas, deal_type, filename)
    elif GlobalData.pattern_map.match(filename):
        _change = __scanning_type_maps(json_datas, deal_type, filename)

    # elif filename in (TYPE_BATTLEHUD, TYPE_MAPHUD):
    #     _change = scanning_wicked_rouge(json_datas, _type)

    # 提取模式
    if deal_type == EXTRACT:
        # 如果数据无变动，删除之前写入的标识行
        if not _change:
            global __tmp_translated_cache
            __tmp_translated_cache = del_key_from_dict(
                file_mark, __tmp_translated_cache
            )
        print(f"{data_abspath.name} 扫描完成！\n")

    # 当前为写回模式时，将翻译文本写回data文件
    elif deal_type == WRITEIN:
        write_json(data_abspath, json_datas, backup=False)


def __sacnning_type_player(
    json_datas: list[dict], deal_type: str, filename: str
) -> bool:
    """
    扫描各种武器护具敌人等数据文件。数据结构：list[dict]

    :param json_datas: data数据
    :param deal_type: 读取/写回data模式
    :param filename: data文件名称
    """

    if not json_datas or not isinstance(json_datas, list):
        return False

    # 记录文本更改
    _change = False

    for json_datas_idx, json_datas_item in enumerate(json_datas):
        if not json_datas_item or not isinstance(json_datas_item, dict):
            continue

        # 名称
        name = json_datas_item.get(KEY_NAME)
        if isinstance(name, str) and name.strip():
            # 人名基本不会出现歧义，可以去重
            if filename in GlobalData.rpg_duplicate_removal_list:
                if deal_type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_to_translated_cache(name)
                    )
                else:
                    json_datas_item[KEY_NAME] = __read_from_translated_cache(name)
            else:
                _loc = (
                    get_md5("_".join([filename, str(json_datas_idx), KEY_NAME]), True)
                    + "_"
                )
                if deal_type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_to_translated_cache(name, _loc)
                    )
                else:
                    json_datas_item[KEY_NAME] = __read_from_translated_cache(name, _loc)

        # 昵称
        nick_name = json_datas_item.get(KEY_NICKNAME)
        if isinstance(nick_name, str) and nick_name.strip():
            # 昵称应该不会出现歧义，此处去重
            # _loc = get_md5('_'.join([filename, str(i_json_datas), KEY_NICKNAME]), True) + "_"
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(nick_name)
                )
            else:
                json_datas_item[KEY_NICKNAME] = __read_from_translated_cache(nick_name)

        profile = json_datas_item.get(KEY_PROFILE)
        if isinstance(profile, str) and profile.strip():
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(profile)
                )
            else:
                json_datas_item[KEY_PROFILE] = __read_from_translated_cache(profile)

        # 描述
        description = json_datas_item.get(KEY_DESCRIPTION)
        if isinstance(description, str) and description.strip():
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(description)
                )
            else:
                json_datas_item[KEY_DESCRIPTION] = __read_from_translated_cache(
                    description
                )

        message_1 = json_datas_item.get(KEY_MESSAGE1)
        if isinstance(message_1, str) and message_1.strip():
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(message_1)
                )
            else:
                json_datas_item[KEY_MESSAGE1] = __read_from_translated_cache(message_1)

        message_2 = json_datas_item.get(KEY_MESSAGE2)
        if isinstance(message_2, str) and message_2.strip():
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(message_2)
                )
            else:
                json_datas_item[KEY_MESSAGE2] = __read_from_translated_cache(message_2)

        message_3 = json_datas_item.get(KEY_MESSAGE3)
        if isinstance(message_3, str) and message_3.strip():
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(message_3)
                )
            else:
                json_datas_item[KEY_MESSAGE3] = __read_from_translated_cache(message_3)

        message_4 = json_datas_item.get(KEY_MESSAGE4)
        if isinstance(message_4, str) and message_4.strip():
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(message_4)
                )
            else:
                json_datas_item[KEY_MESSAGE4] = __read_from_translated_cache(message_4)

        # pages是列表
        pages = json_datas_item.get(KEY_PAGES)
        if pages and isinstance(pages, list):
            for page in pages:
                if not page or not isinstance(page, dict):
                    continue

                # list是列表
                lists = page.get(KEY_LIST)
                if not lists or not isinstance(lists, list):
                    continue

                # 记录各元素的索引位置，用于删除无用的文本行
                lists_idx_record: list[int] = []
                for lists_idx, lists_item in enumerate(lists):
                    if not lists_item or not isinstance(lists_item, dict):
                        continue

                    # parameters是列表
                    parameters = lists_item.get(KEY_PARAMETERS)
                    if not parameters or not isinstance(parameters, list):
                        continue

                    code: int = lists_item.get(KEY_CODE, 0)
                    match code:
                        # 选择菜单
                        case 102:
                            chooses = parameters[0]
                            if chooses and isinstance(chooses, list):
                                for idx, choose in enumerate(chooses):
                                    if not choose or not choose.strip():
                                        continue

                                    if deal_type == EXTRACT:
                                        _change = switch_change_mark(
                                            _change, __write_to_translated_cache(choose)
                                        )
                                    else:
                                        lists_item[KEY_PARAMETERS][0][idx] = (
                                            __read_from_translated_cache(choose)
                                        )
                        # 变量操作
                        case 122:
                            variable = parameters[4]
                            if (
                                isinstance(variable, str)
                                and variable.strip()
                                and not any(s in variable for s in ("$", "."))
                            ):
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(variable)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][4] = (
                                        __read_from_translated_cache(variable)
                                    )
                        # 改名
                        case 320:
                            change_name = parameters[1]
                            if isinstance(change_name, str) and change_name.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change,
                                        __write_to_translated_cache(change_name),
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = (
                                        __read_from_translated_cache(change_name)
                                    )
                        # 脚本
                        case 355 | 655:
                            script = parameters[0]
                            if isinstance(script, str) and script.strip():
                                if '"' not in script:
                                    continue

                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change,
                                        __write_to_translated_cache(
                                            script, value=script
                                        ),
                                    )
                                else:
                                    txt = __read_from_translated_cache(script)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 对话
                        case 401:
                            dialog = parameters[0]
                            if isinstance(dialog, str) and dialog.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(dialog)
                                    )
                                else:
                                    txt = __read_from_translated_cache(dialog)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 选项
                        case 402:
                            choose = parameters[1]
                            if isinstance(choose, str) and choose.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(choose)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = (
                                        __read_from_translated_cache(choose)
                                    )
                        # 滚动文章
                        case 405:
                            text = parameters[0]
                            if isinstance(text, str) and text.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(text)
                                    )
                                else:
                                    txt = __read_from_translated_cache(text)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                if lists_idx_record:
                    # 反向列表中元素
                    lists_idx_record.reverse()
                    # 统一删除空文本行
                    for v in lists_idx_record:
                        lists.pop(v)
                page[KEY_LIST] = lists
            json_datas_item[KEY_PAGES] = pages

    return _change


def __sacnning_common_events(json_datas: list[dict], deal_type: str) -> bool:
    """
    扫描CommonEvents。数据结构：list[dict]

    :param json_datas: data数据
    :param deal_type: 读取/写回data模式
    """

    if not json_datas or not isinstance(json_datas, list):
        return False

    # 记录文本更改
    _change = False

    for json_datas_item in json_datas:
        if not json_datas_item or not isinstance(json_datas_item, dict):
            continue

        # list是列表
        lists = json_datas_item.get(KEY_LIST)
        if not lists or not isinstance(lists, list):
            continue

        # 记录各元素的索引位置，用于删除无用的文本行
        lists_idx_record: list[int] = []
        for lists_idx, lists_item in enumerate(lists):
            if not lists_item or not isinstance(lists_item, dict):
                continue

            # parameter是列表
            parameters = lists_item.get(KEY_PARAMETERS)
            if not parameters or not isinstance(parameters, list):
                continue

            code: int = lists_item.get(KEY_CODE, 0)
            match code:
                # 选择菜单
                case 102:
                    chooses = parameters[0]
                    if chooses and isinstance(chooses, list):
                        for idx, choose in enumerate(chooses):
                            if not choose or not choose.strip():
                                continue

                            if deal_type == EXTRACT:
                                _change = switch_change_mark(
                                    _change, __write_to_translated_cache(choose)
                                )
                            else:
                                lists_item[KEY_PARAMETERS][0][idx] = (
                                    __read_from_translated_cache(choose)
                                )
                # 变量操作
                case 122:
                    variable = parameters[4]
                    if (
                        isinstance(variable, str)
                        and variable.strip()
                        and not any(s in variable for s in ("$", "."))
                    ):
                        if deal_type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_to_translated_cache(variable)
                            )
                        else:
                            lists_item[KEY_PARAMETERS][4] = (
                                __read_from_translated_cache(variable)
                            )
                # 改名
                case 320:
                    change_name = parameters[1]
                    if isinstance(change_name, str) and change_name.strip():
                        if deal_type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_to_translated_cache(change_name)
                            )
                        else:
                            lists_item[KEY_PARAMETERS][1] = (
                                __read_from_translated_cache(change_name)
                            )
                # 脚本
                case 355 | 655:
                    script = parameters[0]
                    if isinstance(script, str) and script.strip():
                        if '"' not in script:
                            continue

                        if deal_type == EXTRACT:
                            _change = switch_change_mark(
                                _change,
                                __write_to_translated_cache(script, value=script),
                            )
                        else:
                            txt = __read_from_translated_cache(script)
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists_item[KEY_PARAMETERS][0] = txt
                # 对话
                case 401:
                    dialog = parameters[0]
                    if isinstance(dialog, str) and dialog.strip():
                        if deal_type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_to_translated_cache(dialog)
                            )
                        else:
                            txt = __read_from_translated_cache(dialog)
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists_item[KEY_PARAMETERS][0] = txt
                # 选项
                case 402:
                    choose = parameters[1]
                    if isinstance(choose, str) and choose.strip():
                        if deal_type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_to_translated_cache(choose)
                            )
                        else:
                            lists_item[KEY_PARAMETERS][1] = (
                                __read_from_translated_cache(choose)
                            )
                # 滚动文章
                case 405:
                    text = parameters[0]
                    if isinstance(text, str) and text.strip():
                        if deal_type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_to_translated_cache(text)
                            )
                        else:
                            txt = __read_from_translated_cache(text)
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists_item[KEY_PARAMETERS][0] = txt
        if lists_idx_record:
            # 反向列表中元素
            lists_idx_record.reverse()
            # 统一删除空文本行
            for v in lists_idx_record:
                lists.pop(v)
        json_datas_item[KEY_LIST] = lists

    return _change


def __scanning_system(json_datas: dict, deal_type: str, filename: str) -> bool:
    """
    扫描System.json

    :param json_datas: data数据
    :param deal_type: 读取/写回data模式
    :param filename: data文件名称
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, dict):
        return _change

    # armorTypes是列表
    armor_types = json_datas.get(KEY_ARMORTYPES)
    if armor_types and isinstance(armor_types, list):
        for idx, armortype in enumerate(armor_types):
            if not armortype or not armortype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_ARMORTYPES, str(idx)]), True) + "_"
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(armortype, _loc)
                )
            else:
                json_datas[KEY_ARMORTYPES][idx] = __read_from_translated_cache(
                    armortype, _loc
                )

    # currencyUnit是字串
    currency_unit = json_datas.get(KEY_CURRENCYUNIT)
    if isinstance(currency_unit, str) and currency_unit.strip():
        _loc = get_md5("_".join([filename, KEY_CURRENCYUNIT]), True) + "_"
        if deal_type == EXTRACT:
            _change = switch_change_mark(
                _change, __write_to_translated_cache(currency_unit, _loc)
            )
        else:
            json_datas[KEY_CURRENCYUNIT] = __read_from_translated_cache(
                currency_unit, _loc
            )

    # elements是列表
    elements = json_datas.get(KEY_ELEMENTS)
    if elements and isinstance(elements, list):
        for idx, element in enumerate(elements):
            if not element or not element.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_ELEMENTS, str(idx)]), True) + "_"
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(element, _loc)
                )
            else:
                json_datas[KEY_ELEMENTS][idx] = __read_from_translated_cache(
                    element, _loc
                )

    # equipTypes是列表
    equip_types = json_datas.get(KEY_EQUIPTYPES)
    if equip_types and isinstance(equip_types, list):
        for idx, equiptype in enumerate(equip_types):
            if not equiptype or not equiptype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_EQUIPTYPES, str(idx)]), True) + "_"
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(equiptype, _loc)
                )
            else:
                json_datas[KEY_EQUIPTYPES][idx] = __read_from_translated_cache(
                    equiptype, _loc
                )

    # 游戏标题是字串
    game_title = json_datas.get(KEY_GAMETITLE)
    if isinstance(game_title, str) and game_title.strip():
        _loc = get_md5("_".join([filename, KEY_GAMETITLE]), True) + "_"
        if deal_type == EXTRACT:
            _change = switch_change_mark(
                _change, __write_to_translated_cache(game_title, _loc)
            )
        else:
            json_datas[KEY_GAMETITLE] = __read_from_translated_cache(game_title, _loc)

    # skillTypes是列表
    skill_types = json_datas.get(KEY_SKILLTYPES)
    if skill_types and isinstance(skill_types, list):
        for idx, skilltype in enumerate(skill_types):
            if not skilltype or not skilltype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_SKILLTYPES, str(idx)]), True) + "_"
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(skilltype, _loc)
                )
            else:
                json_datas[KEY_SKILLTYPES][idx] = __read_from_translated_cache(
                    skilltype, _loc
                )

    # weaponTypes是列表
    weapon_types = json_datas.get(KEY_WEAPONTYPES)
    if weapon_types and isinstance(weapon_types, list):
        for idx, weapontype in enumerate(weapon_types):
            if not weapontype or not weapontype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_WEAPONTYPES, str(idx)]), True) + "_"
            if deal_type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_to_translated_cache(weapontype, _loc)
                )
            else:
                json_datas[KEY_WEAPONTYPES][idx] = __read_from_translated_cache(
                    weapontype, _loc
                )

    terms = json_datas.get(KEY_TERMS)
    if terms and isinstance(terms, dict):
        # basic是列表
        basics = terms.get(KEY_BASIC)
        if basics and isinstance(basics, list):
            for idx, basic in enumerate(basics):
                if not basic or not basic.strip():
                    continue

                _loc = (
                    get_md5("_".join([filename, KEY_TERMS, KEY_BASIC, str(idx)]), True)
                    + "_"
                )
                if deal_type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_to_translated_cache(basic, _loc)
                    )
                else:
                    json_datas[KEY_TERMS][KEY_BASIC][idx] = (
                        __read_from_translated_cache(basic, _loc)
                    )

        # commands是列表
        commands = terms.get(KEY_COMMANDS)
        if commands and isinstance(commands, list):
            for idx, command in enumerate(commands):
                if not command or not command.strip():
                    continue

                _loc = (
                    get_md5(
                        "_".join([filename, KEY_TERMS, KEY_COMMANDS, str(idx)]), True
                    )
                    + "_"
                )
                if deal_type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_to_translated_cache(command, _loc)
                    )
                else:
                    json_datas[KEY_TERMS][KEY_COMMANDS][idx] = (
                        __read_from_translated_cache(command, _loc)
                    )

        # params是列表
        params = terms.get(KEY_PARAMS)
        if params and isinstance(params, list):
            for idx, param in enumerate(params):
                if not param or not param.strip():
                    continue

                _loc = (
                    get_md5("_".join([filename, KEY_TERMS, KEY_PARAMS, str(idx)]), True)
                    + "_"
                )
                if deal_type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_to_translated_cache(param, _loc)
                    )
                else:
                    json_datas[KEY_TERMS][KEY_PARAMS][idx] = (
                        __read_from_translated_cache(param, _loc)
                    )

        # messages是字典
        messages = terms.get(KEY_MESSAGES)
        if messages and isinstance(messages, dict):
            for key, message in messages.items():
                if not message or not message.strip():
                    continue

                if deal_type == EXTRACT:
                    _change = switch_change_mark(
                        _change, __write_to_translated_cache(message)
                    )
                else:
                    json_datas[KEY_TERMS][KEY_MESSAGES][key] = (
                        __read_from_translated_cache(message)
                    )

    return _change


def __scanning_type_maps(json_datas: dict, deal_type: str, filename: str) -> bool:
    """
    扫描各种Map

    :param json_datas: data数据
    :param deal_type: 读取/写回data模式
    :param filename: data文件名称
    """

    if not json_datas or not isinstance(json_datas, dict):
        return False

    # 记录文本更改
    _change = False

    # displayName是字串
    display_name = json_datas.get(KEY_DISPLAYNAME)
    if isinstance(display_name, str) and display_name.strip():
        _loc = get_md5("_".join([filename, KEY_DISPLAYNAME]), True) + "_"
        if deal_type == EXTRACT:
            _change = switch_change_mark(
                _change, __write_to_translated_cache(display_name, _loc)
            )
        else:
            json_datas[KEY_DISPLAYNAME] = __read_from_translated_cache(
                display_name, _loc
            )

    # events是列表
    events = json_datas.get(KEY_EVENTS)
    if events and isinstance(events, list):
        for events_item in events:
            if not events_item or not isinstance(events_item, dict):
                continue

            # pages是列表
            pages = events_item.get(KEY_PAGES)
            if not pages or not isinstance(pages, list):
                continue

            for page in pages:
                if not page or not isinstance(page, dict):
                    continue

                # list是列表
                lists = page.get(KEY_LIST)
                if not lists or not isinstance(lists, list):
                    continue

                # 记录各元素的索引位置，用于删除无用的文本行
                lists_idx_record: list[int] = []
                for lists_idx, lists_item in enumerate(lists):
                    if not lists_item or not isinstance(lists_item, dict):
                        continue

                    # parameters是列表
                    parameters = lists_item.get(KEY_PARAMETERS)
                    if not parameters or not isinstance(parameters, list):
                        continue

                    code: int = lists_item.get(KEY_CODE, 0)
                    match code:
                        # 选择菜单
                        case 102:
                            chooses = parameters[0]
                            if chooses and isinstance(chooses, list):
                                for idx, choose in enumerate(chooses):
                                    if not choose or not choose.strip():
                                        continue

                                    if deal_type == EXTRACT:
                                        _change = switch_change_mark(
                                            _change, __write_to_translated_cache(choose)
                                        )
                                    else:
                                        lists_item[KEY_PARAMETERS][0][idx] = (
                                            __read_from_translated_cache(choose)
                                        )
                        # 变量操作
                        case 122:
                            variable = parameters[4]
                            if (
                                isinstance(variable, str)
                                and variable.strip()
                                and not any(s in variable for s in ("$", "."))
                            ):
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(variable)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][4] = (
                                        __read_from_translated_cache(variable)
                                    )
                        # 改名
                        case 320:
                            change_name = parameters[1]
                            if isinstance(change_name, str) and change_name.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change,
                                        __write_to_translated_cache(change_name),
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = (
                                        __read_from_translated_cache(change_name)
                                    )
                        # 脚本
                        case 355 | 655:
                            script = parameters[0]
                            if isinstance(script, str) and script.strip():
                                if '"' not in script:
                                    continue

                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change,
                                        __write_to_translated_cache(
                                            script, value=script
                                        ),
                                    )
                                else:
                                    txt = __read_from_translated_cache(script)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 对话
                        case 401:
                            dialog = parameters[0]
                            if isinstance(dialog, str) and dialog.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(dialog)
                                    )
                                else:
                                    txt = __read_from_translated_cache(dialog)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 选项
                        case 402:
                            choose = parameters[1]
                            if isinstance(choose, str) and choose.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(choose)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = (
                                        __read_from_translated_cache(choose)
                                    )
                        # 滚动文章
                        case 405:
                            text = parameters[0]
                            if isinstance(text, str) and text.strip():
                                if deal_type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_to_translated_cache(text)
                                    )
                                else:
                                    txt = __read_from_translated_cache(text)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                if lists_idx_record:
                    # 反向列表中元素
                    lists_idx_record.reverse()
                    # 统一删除空文本行
                    for v in lists_idx_record:
                        lists.pop(v)
                page[KEY_LIST] = lists
            events_item[KEY_PAGES] = pages
        json_datas[KEY_EVENTS] = events
    return _change


# def __scanning_wicked_rouge(json_datas: dict, _type: str) -> bool:
#     '''
#     扫描Wicked Rouge的BattleHUD.json和MapHUD.json
#     '''

#     if not json_datas or not isinstance(json_datas, dict):
#         return False

#     # 记录文本更改
#     _change = False

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


def __init_translated_cache_lib(deal_type: str) -> bool:
    """
    读取翻译项目、默认文本库及可选的gameText.json，分别写入游戏译文库和初始译文库

    :param deal_type: 读取/写回data模式
    """

    # 读取游戏翻译项目
    txt_cache = read_json(__curr_trans_proj_path)
    global __translated_cache, __tmp_translated_cache
    __tmp_translated_cache = {}
    if not txt_cache:
        __translated_cache = {}
    else:
        __translated_cache = txt_cache

    # 将更新标识的值重置为False
    update_phoenix_mark(__tmp_translated_cache)

    # 当处于写回模式时，如果游戏译文库为空，则返回False
    if deal_type == WRITEIN and len(__translated_cache) < 2:
        print_warn(f"{__curr_trans_proj_name} 不存在或无内容！")
        return False

    # 读取引擎默认文本库
    default_libraries = read_json(GlobalData.trans_libs_abspath / RPGMV_DEFAULT_LIBRARY)
    # 读取游戏已有译文
    translated_libraries = read_json(
        GlobalData.trans_libs_abspath / GlobalData.RPGM_GAME_DEFAULT_TXT
    )

    global __translated_library
    # 合并两个译文为一个译文库，若有相同键，游戏译文覆盖默认译文
    __translated_library = merge_dicts([default_libraries, translated_libraries])
    return True


def __write_to_translated_cache(
    key: str = "", _loc: str = "", filter_lang: str = "", value: str = ""
) -> bool:
    """
    将数据存入游戏译文库

    :param key: 原文本
    :param _loc: 16位md5值标识符，用于分别存储译文不同但原文相同的文本
    :param filter_lang: 过滤语种
    :param value: 传入译文值。默认空，不为空时直接将该值写入缓存库
    """

    if not key.strip():
        return False

    _key = (_loc + key).upper()

    # 不匹配指定语种的文本不存入缓存
    if not match_lang(key, filter_lang):
        return False

    # 游戏译文库中已有该字段，且值不为空字串或TODO时，直接返回
    val = __translated_cache.get(_key, "")
    val_strip = val.strip().upper()
    if val_strip and val_strip != GlobalData.MARK_TODO:
        # 将其写入临时游戏译文库
        if _key not in __tmp_translated_cache:
            __tmp_translated_cache[_key] = val
            update_phoenix_mark(__tmp_translated_cache, True)
            return True
        return False

    # Threads of Destiny
    # if "{" in key and "}" in key:
    #     key1 = key[key.find("{") + 1 : key.find("}")]
    #     _key2 = _loc + "_" + key1 if _loc != "" else key1
    #     val = __game_txt_library.get(_key2, "")
    #     val_strip = val.strip().upper()
    #     if val_strip and val_strip != GlobalData.MARK_TODO:
    #         __game_txt_cache[_key] = (
    #             key[: key.find("{")] + val + key[key.find("}") + 1 :]
    #         )
    #         update_phoenix_mark(__game_txt_cache, True)
    #         return True

    # 初始译文库中有该条文本且不为空字串，赋值
    val = __translated_library.get(_key, "")
    val_strip = val.strip().upper()
    if val_strip and val_strip != GlobalData.MARK_TODO:
        __tmp_translated_cache[_key] = val
        update_phoenix_mark(__tmp_translated_cache, True)
        return True

    # 如果参数中直接传入了文本值value时，直接赋值
    if value.strip():
        __tmp_translated_cache[_key] = value
        if _key.startswith(GlobalData.TRANSLATED_FILE_MARK):
            return True
        update_phoenix_mark(__tmp_translated_cache, True)
        return True

    # 既然前面可赋值的情况都pass了，若游戏译文库中有该字段，直接返回
    if _key in __tmp_translated_cache:
        return False

    __tmp_translated_cache[_key] = ""
    update_phoenix_mark(__tmp_translated_cache, True)
    return True


def __read_from_translated_cache(key: str = "", _loc: str = "") -> str:
    """
    从游戏译文库获取数据，若找不到则返回原值

    :param key: 原文本
    :param _loc: 16位md5值标识符，用于分别读取译文不同但原文相同的文本
    """

    if not key.strip():
        return key

    _key = (_loc + key).upper()
    val = __tmp_translated_cache.get(_key, "")
    val_strip = val.strip().upper()
    if not val_strip:
        return key
    # if TODO_FILTER in val_strip:    # 标记。待复核文本
    #     return key
    if val_strip == GlobalData.MARK_TODO:  # 标记。待翻译文本
        return key
    if val_strip in GlobalData.pass_filter:  # 标记。不翻译文本
        return key

    return val


def __choose_option(first_select: bool = True) -> bool:
    """
    输入序号选择对应的操作

    :param first_select: 首次进入选项
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        print("""1) 从data提取翻译文本
2) 将翻译文本写回data
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
