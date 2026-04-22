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

from datetime import datetime
from gc import collect
from pathlib import Path
from sys import exit

import main
from app.controllers.interpreter import Interpreter
from app.utils.global_data import GlobalData
from app.utils.utils import (
    copy_directory,
    get_file_encoding,
    iter_files,
    print_err,
    print_info,
    replace_complex_stem,
    validate_renpy_trans_file,
)

# 标准原译组结束标识符
END_SAY = "-*- END -*-"

# pylint: disable=invalid-name
__input_abspath: str | Path = GlobalData.rpy_trans_input_abspath
__output_abspath: Path = None

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

    print(r"""
===========================================================================================
                                Ren'Py 翻译文本机翻工具
                                    作者：Phoenix
                                    版权归作者所有
                            PS： 所有操作均不会影响原文件！
===========================================================================================
""")

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
        __input_abspath, \
        __output_abspath, \
        __rewrite_all, \
        __rewrite_todo, \
        __interpreter, \
        __curr_renpy_project_name, \
        __curr_renpy_project_path

    __input_abspath = GlobalData.rpy_trans_input_abspath
    __output_abspath = None
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

    if __input_abspath.is_file():
        if not validate_renpy_trans_file(__input_abspath):
            print_err("没有可翻译的Ren'Py翻译文件！")
            return
        print(f"当前更新文本：{__input_abspath.name}")
        __process_file(__input_abspath, __output_abspath)
    else:
        for file, target_abspath in iter_files(
            __input_abspath, create_dir=True, target_abspath=__output_abspath
        ):
            # 非renPy翻译文本直接拷贝至新目录
            if not validate_renpy_trans_file(file):
                copy_directory(file, target_abspath)
                continue

            print(f"当前翻译文本：{file.name}")
            __process_file(file, target_abspath / file.name)
    print_info("翻译已全部完成，请前往原路径查看翻译文本！")


def __process_file(old_trans_abspath: Path, new_trans_abspath: Path):
    """
    读取文本、翻译并写入
    """

    # 待翻译文本字典，将文本提取出来统一翻译。键为源文本的行索引，值为文本
    translate_txts: dict[int, dict[str, str]] = {}
    # 原文
    _old_say = ""
    # 标识符
    _identifier = "strings"

    lightSen = []

    with open(
        old_trans_abspath, "r", encoding=get_file_encoding(old_trans_abspath)
    ) as inp:
        # 获取要翻译的文本列表
        for line_num, line in enumerate(inp, 1):
            lightSen.append(line)
            # 删除换行符
            temp_line = line.rstrip("\n")
            # 空行
            if GlobalData.pattern_empty_line.match(temp_line) is not None:
                continue

            # 标志符行
            identifier_match = GlobalData.pattern_identifier.match(temp_line)
            if identifier_match is not None:
                _identifier = identifier_match.group(1)
                # 扫描到标志符行，说明进入了新的BAP，原文清空
                # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
                _old_say = ""
                continue

            # 原文行
            old_say_match = GlobalData.pattern_old_say.match(temp_line)
            if old_say_match is not None and _identifier not in ("", "strings"):
                # 跳过cv语音行
                if old_say_match.group(1) != "voice":
                    _old_say = old_say_match.group(2)
                continue

            # 译文行
            new_say_match = GlobalData.pattern_new_say.match(temp_line)
            if new_say_match is not None and _identifier not in ("", "strings"):
                _who = new_say_match.group(1)
                # 跳过cv语音行
                if _who == "voice":
                    continue

                # rpy翻译文件原文本质上是注释，有些rpy翻译文件因一些原因删除了原文注释，所以原文say为空，表明找不到原文注释，这种情况无法获取原文进行翻译，只能跳过
                if _old_say.strip() == "":
                    continue

                # 如果原文为END_SAY，说明当前BAP已结束，现在是多出来的译文行，跳过
                if _old_say == END_SAY:
                    continue

                # 存在字符串形式的who，先不作翻译
                # who_match = PATTERN_WHO.match(_who)
                # if who_match is not None and who_match.group(1) != '':
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
            old_match = GlobalData.pattern_old.match(temp_line)
            if old_match is not None and _identifier == "strings":
                _old_say = old_match.group(1)
                continue

            # new行
            new_match = GlobalData.pattern_new.match(temp_line)
            if new_match is not None and _identifier == "strings":
                if _old_say == "":
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
        print_info(f"{old_trans_abspath.name} 无需翻译！\n")
        return

    with open(
        new_trans_abspath, "w", encoding=get_file_encoding(new_trans_abspath)
    ) as outp:
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
                    lightSen[tmp_key - 1] = reverse_line
                # 新逻辑会将未翻译文本也写回文件，避免意外退出导致文件中的翻译文本被截断
                outp.writelines(lightSen)
                outp.flush()
                tmp_translate_txts = {}

    print_info(f"{old_trans_abspath.name} 翻译完成！")


def __input_path(first_select=True) -> bool:
    """
    输入待翻文件/文件夹的绝对路径

    :param first_select: 首次输入路径
    """

    global __input_abspath, __output_abspath

    # 用户输入内容
    _inp = ""
    # 首次输入路径
    if first_select:
        if __input_abspath:
            print_info("正在验证默认路径……")
            # 若路径不存在，则重新手动输入
            if not Path(__input_abspath).exists():
                __input_abspath = ""
                return __input_path(False)

            __input_abspath, __output_abspath = __create_new_trans_project_path(
                __input_abspath
            )
            print_info("路径验证成功！\n")
            return True
        _inp = input("请输入翻译项目的绝对路径或回车返回主菜单：").strip()
    else:
        _inp = input("路径错误，请重新输入正确的路径或回车返回主菜单：").strip()

    # 输入为空，返回主菜单
    if _inp in ("", "\r", "\n"):
        return False

    # 规范路径，不调整大小写
    _inp = Path(_inp)
    # 若路径不存在，重新输入
    if not _inp.exists():
        return __input_path(False)

    __input_abspath, __output_abspath = __create_new_trans_project_path(_inp)
    print_info("路径验证成功！\n")
    return True


def __create_new_trans_project_path(input_abspath: str | Path) -> tuple[Path]:
    """
    创建新翻译项目路径

    :param input_abspath: 原路径
    """

    input_abspath = Path(input_abspath)
    output_abspath: Path = None
    # 如果输入路径是文件夹
    if input_abspath.is_dir():
        # 输出路径也生成文件夹
        output_abspath = input_abspath.with_name(f"{input_abspath.name}-new")
        # 如果输出文件夹已存在，先将其更名，再新建空文件夹
        if output_abspath.exists():
            time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            bak_output_abspath = output_abspath.with_name(
                f"{output_abspath.name}_{time}"
            )
            output_abspath.rename(bak_output_abspath)
        output_abspath.mkdir(parents=True, exist_ok=True)

    # 如果输入路径是文件
    elif input_abspath.is_file():
        # 如果输出文件已存在，将其更名备份
        output_abspath = replace_complex_stem(input_abspath, "-new")
        if output_abspath.exists():
            time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            bak_output_abspath = replace_complex_stem(output_abspath, f"_{time}")
            output_abspath.rename(bak_output_abspath)

    return input_abspath, output_abspath


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
