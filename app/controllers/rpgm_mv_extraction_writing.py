#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-04 23:33:35
"""

from datetime import datetime
from gc import collect
from pathlib import Path
from shutil import copy, rmtree
from sys import exit

import main
from app.utils.global_data import GlobalData
from app.utils.utils import (
    del_key_from_dict,
    get_md5,
    iter_files,
    match_lang,
    merge_dicts,
    print_err,
    print_info,
    print_warn,
    read_json,
    switch_change_mark,
    update_phoenix_mark,
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
__curr_rpgm_project_name: str = ""
# 当前rpgm翻译文件的绝对路径
__curr_rpgm_project_path = ""


def start(project_name: str):
    """
    启动界面
    """

    global __curr_rpgm_project_name, __curr_rpgm_project_path

    __curr_rpgm_project_name = project_name
    __curr_rpgm_project_path = GlobalData.rpgm_project_folder_abspath / project_name

    print("""
===========================================================================================
                               RPG Maker MV 文本提取写入工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
""")

    no_skip = __choose_option()
    if not no_skip:
        #  初始化全局变量数据，避免数据干扰
        init_global_datas()
        main.start_main()
        return

    # 判断翻译文本是否有变动，没有则跳过
    if not __game_txt_cache.get(GlobalData.KEY_PHOENIX):
        print(f"{__curr_rpgm_project_name} 未发生更改，无需写入！\n")
    else:
        # 将更新标识的值重置为False
        update_phoenix_mark(__game_txt_cache)
        # 更新翻译项目
        write_json(__curr_rpgm_project_path, __game_txt_cache)

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
        __game_txt_cache, \
        __game_txt_library, \
        __curr_rpgm_project_name, \
        __curr_rpgm_project_path

    __game_txt_cache = None
    __game_txt_library = None
    __curr_rpgm_project_name = ""
    __curr_rpgm_project_path = ""

    collect()


def __walk_file(_type: str):
    """
    遍历文件夹内所有内容
    """

    if not GlobalData.rpgm_input_abspath.exists():
        GlobalData.rpgm_input_abspath.mkdir(parents=True)
        print_err("RPGM Data Input目录无文件！")
        return

    if _type == WRITEIN:
        if GlobalData.rpgm_output_abspath.exists():
            rmtree(GlobalData.rpgm_output_abspath)
        GlobalData.rpgm_output_abspath.mkdir(parents=True, exist_ok=True)

    # 读取文本库
    if not __read_game_txt(_type):
        return

    # 遍历所有文件，筛选出需要的json文件进行处理
    for file, target_path in iter_files(
        GlobalData.rpgm_input_abspath,
        create_dir=_type == WRITEIN,
        target_abspath=GlobalData.rpgm_output_abspath,
    ):
        if file.suffix != ".json" or (
            file.stem not in GlobalData.rpg_white_list
            and not GlobalData.pattern_map.match(file.stem)
        ):
            # 如果当前为写入模式，在新目录拷贝一份该文件
            if _type == WRITEIN:
                copy(str(file), str(target_path))
            print(f"{file.name} 不在白名单内，已跳过！\n")
            continue

        __deal_with_json_file(file, target_path, _type)


def __deal_with_json_file(source_file: Path, target_path: Path, _type: str):
    """
    处理JSON数据
    """

    print(f"当前扫描文本：{source_file.name}")
    # 这里的json_datas不做拷贝，直接传入下面的函数
    json_datas = read_json(source_file)
    if not json_datas:
        print(f"{source_file.name} 无内容，已跳过！\n")
        return

    # 无后缀文件名
    filename = source_file.stem
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
    elif GlobalData.pattern_map.match(filename):
        _change = __scanning_type_maps(json_datas, _type, filename)

    # elif filename in (TYPE_BATTLEHUD, TYPE_MAPHUD):
    #     _change = scanning_wicked_rouge(json_datas, _type)

    # 提取模式
    if _type == EXTRACT:
        # 如果数据无变动，删除之前写入的标识行
        if not _change:
            global __game_txt_cache
            __game_txt_cache = del_key_from_dict(file_mark, __game_txt_cache)
        print_info(f"{source_file.name} 扫描完成！\n")

    # 当前为写入模式时，写入json文本
    elif _type == WRITEIN:
        write_json(target_path / source_file.name, json_datas, backup=False)


def __sacnning_type_player(json_datas: list, _type: str, filename: str) -> bool:
    """
    扫描各种武器护具敌人等数据文件。数据结构：array[object]
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, list):
        return _change

    for json_datas_idx, json_datas_item in enumerate(json_datas):
        if not json_datas_item or not isinstance(json_datas_item, dict):
            continue

        # 名称
        name = json_datas_item.get(KEY_NAME)
        if isinstance(name, str) and name.strip():
            # 人名基本不会出现歧义，可以去重
            if filename in GlobalData.rpg_duplicate_removal_list:
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, __write_in_cache(name))
                else:
                    json_datas_item[KEY_NAME] = __read_from_cache(name)
            else:
                _loc = get_md5(
                    "_".join([filename, str(json_datas_idx), KEY_NAME]), True
                )
                if _type == EXTRACT:
                    _change = switch_change_mark(_change, __write_in_cache(name, _loc))
                else:
                    json_datas_item[KEY_NAME] = __read_from_cache(name, _loc)

        # 昵称
        nick_name = json_datas_item.get(KEY_NICKNAME)
        if isinstance(nick_name, str) and nick_name.strip():
            # 昵称应该不会出现歧义，此处去重
            # _loc = get_md5('_'.join([filename, str(i_json_datas), KEY_NICKNAME]), True)
            _loc = ""
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(nick_name, _loc))
            else:
                json_datas_item[KEY_NICKNAME] = __read_from_cache(nick_name, _loc)

        profile = json_datas_item.get(KEY_PROFILE)
        if isinstance(profile, str) and profile.strip():
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(profile))
            else:
                json_datas_item[KEY_PROFILE] = __read_from_cache(profile)

        # 描述
        description = json_datas_item.get(KEY_DESCRIPTION)
        if isinstance(description, str) and description.strip():
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(description))
            else:
                json_datas_item[KEY_DESCRIPTION] = __read_from_cache(description)

        message_1 = json_datas_item.get(KEY_MESSAGE1)
        if isinstance(message_1, str) and message_1.strip():
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(message_1))
            else:
                json_datas_item[KEY_MESSAGE1] = __read_from_cache(message_1)

        message_2 = json_datas_item.get(KEY_MESSAGE2)
        if isinstance(message_2, str) and message_2.strip():
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(message_2))
            else:
                json_datas_item[KEY_MESSAGE2] = __read_from_cache(message_2)

        message_3 = json_datas_item.get(KEY_MESSAGE3)
        if isinstance(message_3, str) and message_3.strip():
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(message_3))
            else:
                json_datas_item[KEY_MESSAGE3] = __read_from_cache(message_3)

        message_4 = json_datas_item.get(KEY_MESSAGE4)
        if isinstance(message_4, str) and message_4.strip():
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(message_4))
            else:
                json_datas_item[KEY_MESSAGE4] = __read_from_cache(message_4)

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

                                    if _type == EXTRACT:
                                        _change = switch_change_mark(
                                            _change, __write_in_cache(choose)
                                        )
                                    else:
                                        lists_item[KEY_PARAMETERS][0][idx] = (
                                            __read_from_cache(choose)
                                        )
                        # 变量操作
                        case 122:
                            variable = parameters[4]
                            if (
                                isinstance(variable, str)
                                and variable.strip()
                                and not any(s in variable for s in ("$", "."))
                            ):
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(variable)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][4] = __read_from_cache(
                                        variable
                                    )
                        # 改名
                        case 320:
                            change_name = parameters[1]
                            if isinstance(change_name, str) and change_name.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(change_name)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = __read_from_cache(
                                        change_name
                                    )
                        # 脚本
                        case 355 | 655:
                            script = parameters[0]
                            if isinstance(script, str) and script.strip():
                                if '"' not in script:
                                    continue

                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(script, value=script)
                                    )
                                else:
                                    txt = __read_from_cache(script)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 对话
                        case 401:
                            dialog = parameters[0]
                            if isinstance(dialog, str) and dialog.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(dialog)
                                    )
                                else:
                                    txt = __read_from_cache(dialog)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 选项
                        case 402:
                            choose = parameters[1]
                            if isinstance(choose, str) and choose.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(choose)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = __read_from_cache(
                                        choose
                                    )
                        # 滚动文章
                        case 405:
                            text = parameters[0]
                            if isinstance(text, str) and text.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(text)
                                    )
                                else:
                                    txt = __read_from_cache(text)
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


def __sacnning_common_events(json_datas: list, _type: str) -> bool:
    """
    扫描CommonEvents。数据结构：array[object]
    """

    # 记录文本更改
    _change = False

    if not json_datas or not isinstance(json_datas, list):
        return _change

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

                            if _type == EXTRACT:
                                _change = switch_change_mark(
                                    _change, __write_in_cache(choose)
                                )
                            else:
                                lists_item[KEY_PARAMETERS][0][idx] = __read_from_cache(
                                    choose
                                )
                # 变量操作
                case 122:
                    variable = parameters[4]
                    if (
                        isinstance(variable, str)
                        and variable.strip()
                        and not any(s in variable for s in ("$", "."))
                    ):
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(variable)
                            )
                        else:
                            lists_item[KEY_PARAMETERS][4] = __read_from_cache(variable)
                # 改名
                case 320:
                    change_name = parameters[1]
                    if isinstance(change_name, str) and change_name.strip():
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(change_name)
                            )
                        else:
                            lists_item[KEY_PARAMETERS][1] = __read_from_cache(
                                change_name
                            )
                # 脚本
                case 355 | 655:
                    script = parameters[0]
                    if isinstance(script, str) and script.strip():
                        if '"' not in script:
                            continue

                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(script, value=script)
                            )
                        else:
                            txt = __read_from_cache(script)
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists_item[KEY_PARAMETERS][0] = txt
                # 对话
                case 401:
                    dialog = parameters[0]
                    if isinstance(dialog, str) and dialog.strip():
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(dialog)
                            )
                        else:
                            txt = __read_from_cache(dialog)
                            if txt.strip().upper() == GlobalData.none_filter:
                                lists_idx_record.append(lists_idx)
                                txt = ""
                            lists_item[KEY_PARAMETERS][0] = txt
                # 选项
                case 402:
                    choose = parameters[1]
                    if isinstance(choose, str) and choose.strip():
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(choose)
                            )
                        else:
                            lists_item[KEY_PARAMETERS][1] = __read_from_cache(choose)
                # 滚动文章
                case 405:
                    text = parameters[0]
                    if isinstance(text, str) and text.strip():
                        if _type == EXTRACT:
                            _change = switch_change_mark(
                                _change, __write_in_cache(text)
                            )
                        else:
                            txt = __read_from_cache(text)
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


def __scanning_system(json_datas: dict, _type: str, filename: str) -> bool:
    """
    扫描System.json
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

            _loc = get_md5("_".join([filename, KEY_ARMORTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(armortype, _loc))
            else:
                json_datas[KEY_ARMORTYPES][idx] = __read_from_cache(armortype, _loc)

    # currencyUnit是字串
    currency_unit = json_datas.get(KEY_CURRENCYUNIT)
    if isinstance(currency_unit, str) and currency_unit.strip():
        _loc = get_md5("_".join([filename, KEY_CURRENCYUNIT]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(_change, __write_in_cache(currency_unit, _loc))
        else:
            json_datas[KEY_CURRENCYUNIT] = __read_from_cache(currency_unit, _loc)

    # elements是列表
    elements = json_datas.get(KEY_ELEMENTS)
    if elements and isinstance(elements, list):
        for idx, element in enumerate(elements):
            if not element or not element.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_ELEMENTS, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(element, _loc))
            else:
                json_datas[KEY_ELEMENTS][idx] = __read_from_cache(element, _loc)

    # equipTypes是列表
    equip_types = json_datas.get(KEY_EQUIPTYPES)
    if equip_types and isinstance(equip_types, list):
        for idx, equiptype in enumerate(equip_types):
            if not equiptype or not equiptype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_EQUIPTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(equiptype, _loc))
            else:
                json_datas[KEY_EQUIPTYPES][idx] = __read_from_cache(equiptype, _loc)

    # 游戏标题是字串
    game_title = json_datas.get(KEY_GAMETITLE)
    if isinstance(game_title, str) and game_title.strip():
        _loc = get_md5("_".join([filename, KEY_GAMETITLE]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(_change, __write_in_cache(game_title, _loc))
        else:
            json_datas[KEY_GAMETITLE] = __read_from_cache(game_title, _loc)

    # skillTypes是列表
    skill_types = json_datas.get(KEY_SKILLTYPES)
    if skill_types and isinstance(skill_types, list):
        for idx, skilltype in enumerate(skill_types):
            if not skilltype or not skilltype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_SKILLTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(_change, __write_in_cache(skilltype, _loc))
            else:
                json_datas[KEY_SKILLTYPES][idx] = __read_from_cache(skilltype, _loc)

    # weaponTypes是列表
    weapon_types = json_datas.get(KEY_WEAPONTYPES)
    if weapon_types and isinstance(weapon_types, list):
        for idx, weapontype in enumerate(weapon_types):
            if not weapontype or not weapontype.strip():
                continue

            _loc = get_md5("_".join([filename, KEY_WEAPONTYPES, str(idx)]), True)
            if _type == EXTRACT:
                _change = switch_change_mark(
                    _change, __write_in_cache(weapontype, _loc)
                )
            else:
                json_datas[KEY_WEAPONTYPES][idx] = __read_from_cache(weapontype, _loc)

    terms = json_datas.get(KEY_TERMS)
    if terms and isinstance(terms, dict):
        # basic是列表
        basics = terms.get(KEY_BASIC)
        if basics and isinstance(basics, list):
            for idx, basic in enumerate(basics):
                if not basic or not basic.strip():
                    continue

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
        commands = terms.get(KEY_COMMANDS)
        if commands and isinstance(commands, list):
            for idx, command in enumerate(commands):
                if not command or not command.strip():
                    continue

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
        params = terms.get(KEY_PARAMS)
        if params and isinstance(params, list):
            for idx, param in enumerate(params):
                if not param or not param.strip():
                    continue

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
        messages = terms.get(KEY_MESSAGES)
        if messages and isinstance(messages, dict):
            for key, message in messages.items():
                if not message or not message.strip():
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
    display_name = json_datas.get(KEY_DISPLAYNAME)
    if isinstance(display_name, str) and display_name.strip():
        _loc = get_md5("_".join([filename, KEY_DISPLAYNAME]), True)
        if _type == EXTRACT:
            _change = switch_change_mark(_change, __write_in_cache(display_name, _loc))
        else:
            json_datas[KEY_DISPLAYNAME] = __read_from_cache(display_name, _loc)

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

                                    if _type == EXTRACT:
                                        _change = switch_change_mark(
                                            _change, __write_in_cache(choose)
                                        )
                                    else:
                                        lists_item[KEY_PARAMETERS][0][idx] = (
                                            __read_from_cache(choose)
                                        )
                        # 变量操作
                        case 122:
                            variable = parameters[4]
                            if (
                                isinstance(variable, str)
                                and variable.strip()
                                and not any(s in variable for s in ("$", "."))
                            ):
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(variable)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][4] = __read_from_cache(
                                        variable
                                    )
                        # 改名
                        case 320:
                            change_name = parameters[1]
                            if isinstance(change_name, str) and change_name.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(change_name)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = __read_from_cache(
                                        change_name
                                    )
                        # 脚本
                        case 355 | 655:
                            script = parameters[0]
                            if isinstance(script, str) and script.strip():
                                if '"' not in script:
                                    continue

                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(script, value=script)
                                    )
                                else:
                                    txt = __read_from_cache(script)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 对话
                        case 401:
                            dialog = parameters[0]
                            if isinstance(dialog, str) and dialog.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(dialog)
                                    )
                                else:
                                    txt = __read_from_cache(dialog)
                                    if txt.strip().upper() == GlobalData.none_filter:
                                        lists_idx_record.append(lists_idx)
                                        txt = ""
                                    lists_item[KEY_PARAMETERS][0] = txt
                        # 选项
                        case 402:
                            choose = parameters[1]
                            if isinstance(choose, str) and choose.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(choose)
                                    )
                                else:
                                    lists_item[KEY_PARAMETERS][1] = __read_from_cache(
                                        choose
                                    )
                        # 滚动文章
                        case 405:
                            text = parameters[0]
                            if isinstance(text, str) and text.strip():
                                if _type == EXTRACT:
                                    _change = switch_change_mark(
                                        _change, __write_in_cache(text)
                                    )
                                else:
                                    txt = __read_from_cache(text)
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
    if not txt_cache:
        __game_txt_cache = {}
    else:
        __game_txt_cache = txt_cache

    # 将更新标识的值重置为False
    update_phoenix_mark(__game_txt_cache)

    # 当处于写入模式时，如果游戏翻译项目缓存数据为空，则返回False
    if _type == WRITEIN and len(__game_txt_cache) < 2:
        print_warn(f"{__curr_rpgm_project_name} 不存在或无内容！")
        return False

    # 读取引擎默认文本库
    default_libraries = read_json(
        GlobalData.translated_libraries_abspath / RPGMV_DEFAULT_LIBRARY
    )
    # 读取游戏已有译文
    translated_libraries = read_json(
        GlobalData.translated_libraries_abspath / GlobalData.RPGM_GAME_DEFAULT_TXT
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
    val = __game_txt_cache.get(_key, "")
    val_strip = val.strip().upper()
    if val_strip and val_strip != GlobalData.MARK_TODO:
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

    # default_strings中有该条文本且不为空字串，赋值
    val = __game_txt_library.get(_key, "")
    val_strip = val.strip().upper()
    if val_strip and val_strip != GlobalData.MARK_TODO:
        __game_txt_cache[_key] = val
        update_phoenix_mark(__game_txt_cache, True)
        return True

    # 如果参数中直接传入了文本值value且不为空字符串时，直接赋值
    if value:
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

    val = __game_txt_cache.get(_key, "")
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
