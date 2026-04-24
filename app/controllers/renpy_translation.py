#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-06-12 12:11:24
Ren'Py翻译文本机器翻译工具

以下形式的代码块为一个“待处理区块（Block Awaiting Processing，简称BAP）”，即“标识符行 + 原文注释 + 译文”。缓存数以一个BAP为基数
translate chinese xxx_xxx_xxxxxxxx:

    # pov "xxxxx" with dissolve
    pov "" with dissolve
"""

from gc import collect
from pathlib import Path
from sys import exit

import main
from app.controllers.interpreter import Interpreter
from app.utils.global_data import GlobalData
from app.utils.utils import (
    copy_file,
    copy_tree,
    get_file_encoding,
    print_err,
    print_info,
    validate_renpy_trans_file,
)

# 标准原译组结束标识符
END_SAY = "-*- END -*-"

# pylint: disable=invalid-name
__wait_translate_abspath: str | Path = GlobalData.rpy_trans_input_abspath

# 是否覆盖所有译文
__rewrite_all: bool = False

# 是否覆盖TODO译文
__rewrite_todo: bool = False

# 翻译器实例
__interpreter: Interpreter = None

# 当前renpy项目名称
__curr_renpy_project_name: str = ""
# 当前renpy项目的绝对路径
__curr_renpy_project_path = ""


def start():
    """
    Ren'Py 翻译文本翻译工具
    """

    print("\n")

    no_skip = __input_path()
    if not no_skip:
        main.start_main()
        return

    # 初始化翻译器
    global __interpreter, __rewrite_all
    __interpreter = Interpreter()

    # 是否开启覆盖所有译文
    __rewrite_all = __rewrite_all_text()
    # 如果不覆盖所有译文，再询问是否开启覆盖TODO译文
    if not __rewrite_all:
        global __rewrite_todo
        __rewrite_todo = __rewrite_todo_text()

    # 处理文本
    __walk_file()

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
        __wait_translate_abspath, \
        __bak_translate_abspath, \
        __rewrite_all, \
        __rewrite_todo, \
        __interpreter, \
        __curr_renpy_project_name, \
        __curr_renpy_project_path

    __wait_translate_abspath = GlobalData.rpy_trans_input_abspath
    __bak_translate_abspath = None
    __rewrite_all = False
    __rewrite_todo = False
    __interpreter = None
    __curr_renpy_project_name = ""
    __curr_renpy_project_path = ""

    collect()


def __walk_file():
    """
    遍历文件夹内所有内容
    """

    if __wait_translate_abspath.is_file():
        if not validate_renpy_trans_file(__wait_translate_abspath):
            print_err("没有可翻译的Ren'Py翻译文件！")
            return

        # 备份翻译文件
        copy_file(__wait_translate_abspath)
        print(f"当前更新文本：{__wait_translate_abspath.name}")
        __process_file(__wait_translate_abspath)

    else:
        # 备份翻译项目
        copy_tree(__wait_translate_abspath)
        for file in __wait_translate_abspath.rglob("*"):
            if not file.is_file():
                continue

            print(f"当前翻译文本：{file.name}")
            __process_file(file)
    print_info("翻译已全部完成，请前往原路径查看翻译文本！")


def __process_file(wait_trans_abspath: Path):
    """
    读取文本、翻译并写入
    """

    # todo 在遇到超大文件时会有内存占用问题。不过翻译文件一般不会超过20M，当天的逻辑基本不会有什么问题。
    # 临时文件内容
    tmp_lines = []
    # 待翻译文本字典，将文本提取出来统一翻译。键为源文本的行索引，值为文本
    translate_txts: dict[int, dict[str, str]] = {}

    encode = get_file_encoding(wait_trans_abspath)
    with open(wait_trans_abspath, "r", encoding=encode) as inp:
        # 原文
        _old_say = ""
        # 标识符
        _identifier = "strings"
        # 获取要翻译的文本列表
        for line_num, line in enumerate(inp, 1):
            tmp_lines.append(line)
            # 删除换行符
            temp_line = line.rstrip("\n")
            # 空行
            if GlobalData.pattern_empty_line.match(temp_line):
                continue

            # 标志符行
            identifier_match = GlobalData.pattern_identifier_line.match(temp_line)
            if identifier_match:
                _identifier = identifier_match.group(1)
                # 扫描到标志符行，说明进入了新的BAP，原文清空
                # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
                _old_say = ""
                continue

            # 原文行
            old_say_match = GlobalData.pattern_old_say_line.match(temp_line)
            if old_say_match and _identifier not in ("", "strings"):
                # 跳过cv语音行
                if old_say_match.group(1) != "voice":
                    _old_say = old_say_match.group(2)
                continue

            # 译文行
            new_say_match = GlobalData.pattern_new_say_line.match(temp_line)
            if new_say_match and _identifier not in ("", "strings"):
                _who = new_say_match.group(1)
                # 跳过cv语音行
                if _who == "voice":
                    continue

                # rpy翻译文件原文本质上是注释，有些rpy翻译文件因一些原因删除了原文注释，所以原文say为空，表明找不到原文注释，这种情况无法获取原文进行翻译，只能跳过
                if not _old_say.strip():
                    continue

                # 如果原文为END_SAY，说明当前BAP已结束，现在是多出来的译文行，跳过
                if _old_say == END_SAY:
                    continue

                # 存在字符串形式的who，先不作翻译
                # who_match = PATTERN_WHO.match(_who)
                # if who_match and who_match.group(1) != '':
                #     who = who_match.group(1)
                #     translate_txts[index]['who'] = who

                original_new_say = new_say_match.group(2)
                if (
                    original_new_say != ""  # 当译文不为空
                    and not __rewrite_all  # 当未启用覆盖所有译文
                    and original_new_say.upper()
                    != GlobalData.MARK_TODO  # 当译文不为TODO
                    and (
                        not __rewrite_todo  # 当未启用覆盖TODO译文
                        or not original_new_say.upper().startswith(
                            GlobalData.MARK_TODO
                        )  # 或当译文开头不为TODO
                    )
                ):
                    continue

                translate_txts[line_num] = {
                    "line": line,
                    "identifier": _identifier,
                    "src": _old_say,
                }
                _old_say = END_SAY
                continue

            # old行
            old_match = GlobalData.pattern_old_strings_line.match(temp_line)
            if old_match and _identifier == "strings":
                _old_say = old_match.group(1)
                continue

            # new行
            new_match = GlobalData.pattern_new_strings_line.match(temp_line)
            if new_match and _identifier == "strings":
                if not _old_say:
                    continue

                original_new = new_match.group(1)  # 译文
                if (
                    original_new != ""  # 当译文不为空
                    and not __rewrite_all  # 当未启用覆盖所有译文
                    and original_new.upper() != GlobalData.MARK_TODO  # 当译文不为TODO
                    and (
                        not __rewrite_todo  # 当未启用覆盖TODO译文
                        or not original_new.upper().startswith(
                            GlobalData.MARK_TODO
                        )  # 或当译文开头不为TODO
                    )
                ):
                    continue
                translate_txts[line_num] = {
                    "line": line,
                    "identifier": _identifier,
                    "src": _old_say,
                }
                _old_say = ""

    # 待翻文本字典为空，不需要翻译
    if not translate_txts:
        print(f"{wait_trans_abspath.name} 无需翻译！\n")
        return

    with open(wait_trans_abspath, "w", encoding=encode) as outp:
        tmp_translate_txts: dict[int, dict[str, str]] = {}
        txts_len = len(translate_txts)
        for idx, key in enumerate(translate_txts.keys()):
            # 待翻文本
            tmp_translate_txts[key] = value = translate_txts[key]
            # 翻译文本
            # 虽然翻译接口大多支持一次翻译多条文本，但存在翻译失败，个别文本丢失的情况，无法保证传入的文本和传回的结果对上号，所以这里还是一条文本发起一次请求
            translated = __interpreter.translate_txt(
                value["src"], activate_context="1", open_todo=GlobalData.open_todo
            )
            tmp_translate_txts[key]["dst"] = translated

            # 当为最后一个索引或缓存已达设定值，则写入文件，避免意外退出导致翻译结果完全丢失
            if (
                idx == txts_len - 1
                or len(tmp_translate_txts) == GlobalData.rpy_trans_bap_max_cache
            ):
                for tmp_key, tmp_value in tmp_translate_txts.items():
                    src = tmp_value["src"]
                    dst = tmp_value["dst"]
                    if dst in ("", src):
                        continue
                    reverse_line = tmp_value["line"][::-1]
                    reverse_dst = dst[::-1]
                    new_line = reverse_line.replace('""', f'"{reverse_dst}"')
                    reverse_line = new_line[::-1]
                    tmp_lines[tmp_key - 1] = reverse_line
                # 新逻辑会将未翻译文本也写回文件，避免意外退出导致文件中的翻译文本被截断
                outp.writelines(tmp_lines)
                outp.flush()
                tmp_translate_txts = {}

    print(f"{wait_trans_abspath.name} 翻译完成！\n")


def __input_path(first_select=True) -> bool:
    """
    输入待翻文件/文件夹的绝对路径

    :param first_select: 首次输入路径
    """

    global __wait_translate_abspath

    # 用户输入内容
    _inp = ""
    # 首次输入路径
    if first_select:
        if __wait_translate_abspath:
            print("正在验证默认翻译项目路径……")
            __wait_translate_abspath = Path(__wait_translate_abspath)
            # 若路径不存在，则重新手动输入
            if not __wait_translate_abspath.exists():
                __wait_translate_abspath = ""
                return __input_path(False)

            print("路径验证成功！\n")
            return True
        _inp = input("请输入翻译项目的绝对路径或回车返回主菜单：").strip()
    else:
        _inp = input("路径不存在，请重新输入正确的路径或回车返回主菜单：").strip()

    # 输入为空，返回主菜单
    if _inp in ("", "\r", "\n"):
        return False

    # 规范路径，不调整大小写
    _inp = Path(_inp)
    # 若路径不存在，重新输入
    if not _inp.exists():
        return __input_path(False)

    __wait_translate_abspath = _inp
    print("路径验证成功！\n")
    return True


def __rewrite_all_text() -> bool:
    """
    是否覆盖所有译文。如果提取翻译文本未勾选“为翻译生成空字串”，则务必选择覆盖写入
    """

    print("\n！！！！！以下选项谨慎操作！！！！！")
    rewrite_tmp = input(
        "是否覆盖所有译文？输入“y”覆盖，输入其他内容不覆盖。\n注意：如果生成翻译文本未勾选“为翻译生成空字串”，则必须选择覆盖："
    ).strip()

    if rewrite_tmp in ("Y", "y"):
        print("=====================当前选择为：覆盖写入=====================\n")
        return True

    print("====================当前选择为：不覆盖写入====================\n")
    return False


def __rewrite_todo_text() -> bool:
    """
    是否覆盖TODO译文
    """

    print("\n！！！！！以下选项谨慎操作！！！！！")
    rewrite_tmp = input("是否覆盖TODO译文？输入“y”覆盖，输入其他内容不覆盖：").strip()

    if rewrite_tmp in ("Y", "y"):
        print("=====================当前选择为：覆盖写入=====================\n")
        return True

    print("====================当前选择为：不覆盖写入====================\n")
    return False
