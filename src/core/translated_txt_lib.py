#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-10 23:33:35
"""

import copy
import os

import main
from src.utils.global_data import GlobalData
from src.utils.utils import (
    get_file_encoding,
    merge_dicts,
    print_info,
    read_json,
    validate_renpy_trans_file,
    write_json,
)

__txt_library_cache: dict[str, str] = None


def start():

    print(r"""
===========================================================================================
                                  rpy/json 写入译文库工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
""")

    if not __choose_option():
        main.start_main()


def __walk_file():
    """
    遍历文件夹内所有文件
    """

    # 如果文件夹不存在，新建一个
    if not os.path.exists(GlobalData.WAITING_FOR_ENTRY):
        print("无待录入文本，译文库无需更新！")
        os.makedirs(GlobalData.WAITING_FOR_ENTRY)
        return

    print("正在更新译文库……\n")
    global __txt_library_cache
    for root, dirs, files in os.walk(GlobalData.WAITING_FOR_ENTRY, topdown=False):
        # 遍历所有文件
        for _file in files:
            _file_path = os.path.join(root, _file)
            # 扫描renpy翻译文件
            if validate_renpy_trans_file(_file_path):
                print(f"当前扫描文本：{_file}")
                __scanning_rpy_file(root, _file, __txt_library_cache, True)
                print(f"{_file} 扫描完成！\n")
                continue

            # 扫描json文件，这里即便是扩展名非json的文件，只要内容符合标准json格式也进行处理
            json_datas = read_json(_file_path)
            if json_datas is not None:
                print(f"当前扫描文本：{_file}")
                __txt_library_cache = merge_dicts(__txt_library_cache, json_datas)
                print(f"{_file} 扫描完成！\n")

    if not __txt_library_cache or len(__txt_library_cache) < 2:
        print_info("待录入文本为空，译文库无需更新！")
        return

    __write_translib()
    print_info("译文库已完成更新！")


def __scanning_rpy_file(
    file_path: str, filename: str, txt_libraries=None, rewrite=False
):
    """
    扫描原翻译文本，将需要的数据存入缓存器

    :param file_path: 文件路径
    :param filename: 文件名称
    :param txt_libraries: 文本字典
    :param rewrite: 是否覆盖文本字典内已有的值。默认不覆盖
    """

    if txt_libraries is None:
        txt_libraries = {}

    with open(
        os.path.join(file_path, filename),
        "r",
        encoding=get_file_encoding(os.path.join(file_path, filename)),
    ) as inp:
        # todo 读出所有行，文件较大时可能会报错，需优化
        light_sen = inp.readlines()

    _old_say = ""  # 原文
    _identifier = "strings"  # 标识符
    for line in light_sen:
        # 空行
        if GlobalData.PATTERN_EMPTY_LINE.match(line) is not None:
            continue

        # 标志符行
        identifier_match = GlobalData.PATTERN_IDENTIFIER.match(line)
        if identifier_match is not None:
            _identifier = identifier_match.group(1)
            # 扫描到标志符行，说明进入了新的原译组，则初始化原文
            # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
            _old_say = ""
            continue

        # 原文本行
        old_say_match = GlobalData.PATTERN_OLD_SAY.match(line)
        if (
            old_say_match is not None
            and old_say_match.group(1) != "voice"
            and _identifier not in ("", "strings")
        ):
            _old_say = old_say_match.group(2)
            continue

        # 译文行
        new_say_match = GlobalData.PATTERN_NEW_SAY.match(line)
        if (
            new_say_match is not None
            and new_say_match.group(1) != "voice"
            and _identifier not in ("", "strings")
        ):
            if _old_say.strip() == "":
                continue
            new_say = new_say_match.group(2)  # 译文
            if new_say == "":
                continue
            if _old_say not in txt_libraries or rewrite:
                txt_libraries[_old_say] = new_say
            # 如果单条语句中有多行译文，只扫描第一行的译文
            _old_say = ""
            continue

        # old行
        old_match = GlobalData.PATTERN_OLD.match(line)
        if old_match is not None and _identifier == "strings":
            _old_say = old_match.group(1)
            continue

        # new 行
        new_match = GlobalData.PATTERN_NEW.match(line)
        if new_match is not None and _identifier == "strings":
            if _old_say.strip() == "":
                continue
            new_say = new_match.group(1)  # 译文
            if new_say == "":
                continue
            if _old_say not in txt_libraries or rewrite:
                txt_libraries[_old_say] = new_say
            _old_say = ""


def __write_translib():
    """
    写入译文库
    """
    translated_txt_lib = copy.deepcopy(GlobalData.translated_lib_library)
    for k, v in __txt_library_cache.items():
        # 如果缓存库查询到的键或值不是字串，为错误数据，跳过以屏蔽
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        # 译文库中已有该文本，跳过
        if k in translated_txt_lib:
            continue
        if v.strip() == "":
            continue

        translated_txt_lib[k] = v

    write_json(
        GlobalData.TRANSLATED_LIB_ABSPATH,
        translated_txt_lib,
        backup=False,
    )


def __update_json_trans(pre_trans_path: str, new_trans_path: str):
    print("正在扫描JSON文件……")
    _dict1 = read_json(pre_trans_path)
    _dict2 = read_json(new_trans_path)
    trans_datas = merge_dicts([_dict1, _dict2])
    write_json(new_trans_path, trans_datas)
    print("JSON文本已完成更新！")


def __choose_option(first_select=True) -> bool:
    """
    输入序号选择对应的操作

    :param first_select: 首次进入选项
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        print("""1) 更新译文库（待录入文本务必是标准rpy或json翻译文件，以免污染译文库）
2) 更新JSON文本（试验功能，仅可输入合法文本路径，暂不支持路径验证及输入目录）
""")
        _inp = input("请输入要操作的序号或回车返回主菜单：").strip()
    else:
        _inp = input("列表中不存在该序号，请重新输入正确序号或回车返回主菜单：").strip()

    match _inp:
        case "" | "\r" | "\n":
            return False
        case "1":
            __walk_file()
            return True
        case "2":
            _file1 = input("\n请输入原文本库路径：").strip()
            _file2 = input("\n请输入新文本库路径：").strip()
            # todo 此处需要增加验证路径和文件是否合法的逻辑
            __update_json_trans(_file1, _file2)
            return True
        case _:
            return __choose_option(False)

    return False
