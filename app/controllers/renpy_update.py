#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-07-20 23:33:35

以下形式的代码块为一个“待处理区块（Block Awaiting Processing，简称BAP）”，即“标识符行 + 原文注释 + 译文”。缓存数以一个BAP为基数
translate chinese xxx_xxx_xxxxxxxx:

    # pov "xxxxx" with dissolve
    pov "" with dissolve
"""

from copy import deepcopy
from gc import collect
from pathlib import Path
from sys import exit

import main
from app.utils.global_data import GlobalData
from app.utils.utils import (
    copy_file,
    copy_tree,
    del_key_from_dict,
    get_file_encoding,
    print_err,
    print_info,
    validate_renpy_trans_file,
)

PRE_PROJECT = "PRE_PROJECT"
WAIT_PROJECT = "WAIT_PROJECT"

# 标准原译组结束标识符
END_SAY = "-*- END -*-"

# pylint: disable=invalid-name
# 旧版本翻译项目路径
__pre_trans_project_abspath: str | Path = GlobalData.rpy_update_old_abspath
# 待更新的翻译项目路径
__wait_upd_project_abspath: str | Path = GlobalData.rpy_update_wait_abspath

__translation_cache: dict[str, dict[str, list[str]]] = {}
"""译文缓存库。key为原文，可储存who和strings。格式：{old_say:{identifier:[str,str]}}"""
__identifier_cache: dict[str, list[str]] = {}
"""标识符译文缓存库。key为标识符作，不可储存who和strings。格式：{identifier:[str,str]}"""

# 当前翻译项目名称
__curr_renpy_project_name: str = ""
# 当前翻译项目的绝对路径
__curr_renpy_project_path = ""


def start():
    """
    Ren'Py 翻译文本更新工具
    """

    print("\n")

    no_skip = __input_path(PRE_PROJECT)
    if not no_skip:
        main.start_main()
        return
    no_skip = __input_path(WAIT_PROJECT)
    if not no_skip:
        main.start_main()
        return

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
        __pre_trans_project_abspath, \
        __wait_upd_project_abspath, \
        __translation_cache, \
        __identifier_cache, \
        __curr_renpy_project_name, \
        __curr_renpy_project_path

    __pre_trans_project_abspath = GlobalData.rpy_update_old_abspath
    __wait_upd_project_abspath = GlobalData.rpy_update_wait_abspath
    __translation_cache.clear()
    __identifier_cache.clear()
    __curr_renpy_project_name = ""
    __curr_renpy_project_path = ""

    collect()


def __walk_file():
    """
    遍历文件夹内所有内容
    """

    # 扫描旧版本翻译项目，将符合要求的译文存入缓存库
    pre_trans_project_abspath = Path(__pre_trans_project_abspath)
    if pre_trans_project_abspath.is_file():
        if not validate_renpy_trans_file(pre_trans_project_abspath):
            print_err("没有旧版的已翻Ren'Py翻译文件！")
            return

        print(f"当前扫描文本：{pre_trans_project_abspath.name}")
        __scanning_file(pre_trans_project_abspath)

    else:
        for file in pre_trans_project_abspath.rglob("*"):
            if not file.is_file():
                continue

            # 跳过非renPy翻译文本
            if not validate_renpy_trans_file(file):
                continue

            print(f"当前扫描文本：{file.name}")
            __scanning_file(file)

    # 将缓存的译文写入到待更新翻译文本中
    wait_upd_project_abspath = Path(__wait_upd_project_abspath)
    if wait_upd_project_abspath.is_file():
        if not validate_renpy_trans_file(wait_upd_project_abspath):
            print_err("没有可更新的Ren'Py翻译文件！")
            return

        # 备份待翻译文件
        copy_file(wait_upd_project_abspath)
        print(f"当前更新文本：{wait_upd_project_abspath.name}")
        __process_file(wait_upd_project_abspath)

    else:
        # 备份待翻译项目
        copy_tree(wait_upd_project_abspath)
        for file in wait_upd_project_abspath.rglob("*"):
            if not file.is_file():
                continue

            print(f"当前更新文本：{file.name}")
            __process_file(file)

    print_info("翻译文本已完成更新！")


def __scanning_file(file_abspath: Path):
    """
    扫描旧版本翻译文本，将需要的数据存入缓存器
    """

    # _old_who = ''  # 字符串形式的who
    _old_say = ""  # 原文say
    _identifier = "strings"  # strings标识符，用来区分who_say和old_new
    _curr_bap_processed = ""  # 标志当前BAP处理结束

    with open(file_abspath, "r", encoding=get_file_encoding(file_abspath)) as inp:
        for line in inp:
            # 删除换行符
            line = line.rstrip("\n")

            # 空行
            if GlobalData.pattern_empty_line.match(line):
                continue

            # 标志符行
            identifier_match = GlobalData.pattern_identifier_line.match(line)
            if identifier_match:
                _identifier = identifier_match.group(1)
                # 扫描到标志符行，说明进入了新的BAP，清空原文
                # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
                # _old_who = ''
                _old_say = ""
                # 重置BAP结束标志
                _curr_bap_processed = False
                continue

            # 原文本行
            old_say_match = GlobalData.pattern_old_say_line.match(line)
            if old_say_match and _identifier not in ("", "strings"):
                old_say_list = old_say_match.groups()
                _who = old_say_list[0]
                # 跳过cv语音行
                if _who == "voice":
                    continue

                # 存在字符串形式的who，在存入缓存库之前，不能修改_old_who
                # who_match = PATTERN_WHO.match(_who)
                # if who_match and who_match.group(1) != '':
                #     _old_who = who_match.group(1)

                # 获取原文
                _old_say = old_say_list[1]
                continue

            # old行
            old_match = GlobalData.pattern_old_strings_line.match(line)
            if old_match and _identifier == "strings":
                # 获取原文，在存入缓存库之前，不能修改_old_say
                _old_say = old_match.group(1)
                _curr_bap_processed = False
                continue

            # 如果当前BAP已处理结束，则不论原译文下面还有多少行，直接进入新的BAP。
            if _curr_bap_processed:
                continue

            # 译文行
            new_say_match = GlobalData.pattern_new_say_line.match(line)
            if new_say_match and _identifier not in ("", "strings"):
                new_say_list = new_say_match.groups()
                _who = new_say_list[0]
                # 跳过cv语音行
                if _who == "voice":
                    continue

                # 写入标识符缓存库
                new_say = new_say_list[1]
                __write_to_the_identifier_cache(_identifier, new_say)

                # 原文say为空时，表示找不到该条原文注释，无法通过原文来找译文，故只存入标识符缓存库，不存入文本缓存库
                if not _old_say:
                    continue

                # 字符串形式的who
                # who_match = PATTERN_WHO.match(_who)
                # if who_match and who_match.group(1) != '':
                #     write_in_txt_library_cache(_old_who, who_match.group(1), 'who')

                # 写入文本缓存库，并返回当前BAP处理标志
                _curr_bap_processed = __write_to_translation_cache(
                    _old_say, new_say, _identifier
                )
                continue

            # new 行
            new_match = GlobalData.pattern_new_strings_line.match(line)
            if new_match and _identifier == "strings":
                # 写入文本缓存库
                __write_to_translation_cache(_old_say, new_match.group(1), _identifier)
                # 当前BAP处理结束
                _curr_bap_processed = True

    print(f"{file_abspath.name} 扫描完成！\n")


def __process_file(wait_trans_abspath: Path):
    """
    将缓存区中原文相匹配的译文写入到新翻译文本中
    """
    encode = get_file_encoding(wait_trans_abspath)
    with open(wait_trans_abspath, "r", encoding=encode) as file:
        # todo 读出所有行，文件较大时可能会报错，需优化
        lightSen = file.readlines()

    # 删除文件
    wait_trans_abspath.unlink()

    with open(wait_trans_abspath, "w", encoding=encode) as outp:
        # 临时文本列表，写入文件用
        _tmp_lightSen = deepcopy(lightSen)

        # 原文say
        _old_say = ""
        # 标识符
        _identifier = "strings"
        # BAP当前缓存量
        _bap_count = 0

        _tmp_idx = -1

        for line in lightSen:
            _tmp_idx += 1
            # 空行
            if GlobalData.pattern_empty_line.match(line):
                continue

            # 标志符行
            identifier_match = GlobalData.pattern_identifier_line.match(line)
            if identifier_match:
                _identifier = identifier_match.group(1)
                # 进入新的BAP，缓存量+1
                _bap_count += 1
                # 扫描到标志符行，说明进入了新的BAP，原文清空
                # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
                _old_say = ""
                continue

            # 原文本行
            old_say_match = GlobalData.pattern_old_say_line.match(line)
            if old_say_match and _identifier not in ("", "strings"):
                _old_say_list = old_say_match.groups()
                # 跳过cv语音行
                if _old_say_list[0] == "voice":
                    continue
                _old_say = _old_say_list[1]
                continue

            # 译文行
            new_say_match = GlobalData.pattern_new_say_line.match(line)
            if new_say_match and _identifier not in ("", "strings"):
                _new_say_list = new_say_match.groups()
                _who = _new_say_list[0]
                # 跳过cv语音行
                if _who == "voice":
                    continue

                # 原文say为空时，表明无原文注释，这时可以尝试通过标识符来找译文
                if not _old_say:
                    if not _new_say_list[1].strip():
                        translated_list = __read_from_identifier_cache(_identifier)
                        if translated_list:
                            for list_idx, list_item in enumerate(translated_list):
                                reverse_list_item = list_item[::-1]
                                reverse_line = line[::-1]
                                new_line = reverse_line.replace(
                                    '""', f'"{reverse_list_item}"', 1
                                )
                                reverse_line = new_line[::-1]
                                if list_idx == 0:
                                    _tmp_lightSen[_tmp_idx] = reverse_line
                                    continue
                                _tmp_idx += 1
                                _tmp_lightSen.insert(_tmp_idx, reverse_line)

                    if _bap_count >= GlobalData.rpy_update_bap_max_cache:
                        outp.writelines(_tmp_lightSen)
                        outp.flush()
                        # 清空BAP缓存
                        _bap_count = 0
                    # 当前BAP处理结束，若当前BAP的译文是多行翻译，除第一行外均删除
                    _old_say = END_SAY
                    continue

                # 以原翻译文本译文为准，新翻译文本中当前BAP其他行的译文均舍弃
                if _old_say == END_SAY:
                    continue

                # who
                # who_match = PATTERN_WHO.match(_who)
                # if who_match and who_match.group(1) != '':
                #     original_new_who = who_match.group(1)
                #     _list = read_from_translation_cache(original_new_who, 'who')
                #     if _list:
                #         _who = sub(
                #             escape(repr(original_new_who))[1:-1], _list[0], _who, 1
                #         )

                # 以下为原文say不为空时的处理逻辑
                if not _new_say_list[1].strip():  # 当译文行为空时，尝试获取已有译文
                    translated_list = __read_from_identifier_cache(_identifier)
                    # 如果从identifier_cache未匹配到，可以通过标识符在translation_cache中再匹配一次
                    if not translated_list:
                        translated_list = __read_from_translation_cache(
                            _old_say, _identifier
                        )

                    if translated_list:
                        for list_idx, list_item in enumerate(translated_list):
                            reverse_list_item = list_item[::-1]
                            reverse_line = line[::-1]
                            new_line = reverse_line.replace(
                                '""', f'"{reverse_list_item}"', 1
                            )
                            reverse_line = new_line[::-1]
                            if list_idx == 0:
                                _tmp_lightSen[_tmp_idx] = reverse_line
                                continue
                            _tmp_idx += 1
                            _tmp_lightSen.insert(_tmp_idx, reverse_line)

                if _bap_count >= GlobalData.rpy_update_bap_max_cache:
                    outp.writelines(_tmp_lightSen)
                    outp.flush()
                    # 清空BAP缓存
                    _bap_count = 0
                # 当前BAP处理结束，若当前BAP的译文是多行翻译，除第一行外均删除
                _old_say = END_SAY
                continue

            # old行
            old_match = GlobalData.pattern_old_strings_line.match(line)
            if old_match and _identifier == "strings":
                _old_say = old_match.group(1)
                continue

            # new 行
            new_match = GlobalData.pattern_new_strings_line.match(line)
            if new_match and _identifier == "strings":
                if not _old_say:
                    if _bap_count >= GlobalData.rpy_update_bap_max_cache:
                        outp.writelines(_tmp_lightSen)
                        outp.flush()
                        # 清空BAP缓存
                        _bap_count = 0
                    continue

                original_new_say = new_match.group(1)  # 译文
                # 当译文不为空时，如果覆盖写入，则发出请求
                if not original_new_say:
                    translated_list = __read_from_translation_cache(
                        _old_say, _identifier
                    )
                    if translated_list:
                        # strings只可能有一行，所以直接取首位索引值即可
                        _tmp_lightSen[_tmp_idx] = (
                            '    new "' + translated_list[0] + '"\n'
                        )

                if _bap_count >= GlobalData.rpy_update_bap_max_cache:
                    outp.writelines(_tmp_lightSen)
                    outp.flush()
                    # 清空BAP缓存
                    _bap_count = 0
                _old_say = ""

        if _bap_count > 0:
            outp.writelines(_tmp_lightSen)
            outp.flush()

    print_info(f"{wait_trans_abspath.name} 更新完成！")


def __write_to_the_identifier_cache(identifier: str = "", translated_txt: str = ""):
    """
    写入标识符缓存库
    """

    # 如果标识符为空或who或strings，不写入缓存库
    identifier = identifier.strip()
    if identifier in ("", "who", "strings"):
        return

    global __identifier_cache
    # 如果译文为空，或译文中含有TODO，不写入缓存库，已写入缓存库的也删除
    if not translated_txt.strip() or GlobalData.MARK_TODO in translated_txt:
        if identifier in __identifier_cache:
            __identifier_cache = del_key_from_dict(identifier, __identifier_cache)
        return

    if identifier not in __identifier_cache:
        __identifier_cache[identifier] = [translated_txt]
    else:
        __identifier_cache[identifier].append(translated_txt)


def __write_to_translation_cache(
    source_txt: str = "", translated_txt: str = "", identifier: str = "strings"
) -> bool:
    """
    写入文本缓存库
    """

    # 如果原文为空，直接返回
    if not source_txt.strip():
        return True

    # 如果标识符为空，表明数据非法，直接返回
    identifier = identifier.strip()
    if not identifier:
        return True

    # 去除首尾空行，who和strings的空行往往都是有意而为，故不剔除
    if identifier not in ("who", "strings"):
        source_txt = source_txt.strip()

    # 将文本全部转为大写，方便大小写不同的语句的统一查询
    source_txt = source_txt.upper()

    # 如果译文为空，或译文中含有TODO，不写入缓存库，已写入缓存库的也删除
    if not translated_txt.strip() or GlobalData.MARK_TODO in translated_txt:
        if identifier not in ("who", "strings"):
            if (
                source_txt in __translation_cache
                and identifier in __translation_cache[source_txt]
            ):
                __translation_cache[source_txt] = del_key_from_dict(
                    identifier, __translation_cache[source_txt]
                )
        return True

    if source_txt not in __translation_cache:
        __translation_cache[source_txt] = {}
    # 相同文本有可能存在不同标识符，也表示有可能存在不同的翻译，所以要通过标识符进行分别储存
    if identifier not in __translation_cache[source_txt]:
        # 译文行存在一条原文对应多条译文的情况，所以这里应该用列表来储存译文
        __translation_cache[source_txt][identifier] = [translated_txt]
    else:
        if identifier not in ("who", "strings"):
            __translation_cache[source_txt][identifier].append(translated_txt)

    return False


def __read_from_identifier_cache(identifier: str) -> list[str]:
    """
    从标识符缓存库读取
    """

    identifier = identifier.strip()
    if identifier in ("", "who", "strings"):
        return []

    if not __identifier_cache:
        return []

    # 如果缓存库中有该标识符键，直接返回相应的译文列表
    # 无需判断译文是否有TODO，在写入缓存库中时，有TODO的译文已经被屏蔽了
    if identifier in __identifier_cache:
        return __identifier_cache[identifier]

    # 当标识符不匹配时，可能是标识符增量不符，截取实际8位标识符再查询一次
    ident = __get_8bit_identifier(identifier)
    if ident == "wrong":
        return []

    for key, value in __identifier_cache.items():
        cache_ident = __get_8bit_identifier(key)
        if cache_ident == "wrong":
            continue
        if ident == cache_ident:
            return value

    return []


def __read_from_translation_cache(source_txt: str, identifier: str) -> list[str]:
    """
    从文本缓存库读取

    1. 直接匹配文本。匹配成功，则根据标识符获取译文；若为找到相应标识符，则选择首位索引下的译文
    2. 将文本所有字母转为大写再进行匹配
    """

    if not source_txt.strip():
        return []

    if not __translation_cache:
        return []

    # 去除首尾空行，strings下的空行往往都是有意而为，故不剔除
    if identifier != "strings":
        source_txt = source_txt.strip()

    # 将文本全部转为大写
    source_txt = source_txt.upper()

    if source_txt not in __translation_cache:
        return []

    translated_txts = __translation_cache[source_txt]
    if not translated_txts:
        return []

    # 如果标识符在缓存库中，直接返回结果。这里包含了“who”和“strings”的
    if identifier in translated_txts:
        return translated_txts[identifier]
    else:
        # 注意，这里获取的译文只是某个非指定的相同文本的译文，不一定符合当前语境。原文本越短，语义差异的可能性越大。
        return next(iter(translated_txts.values()))


def __get_8bit_identifier(ident: str) -> str:
    """
    获取除“who”和“strings”外的8位标识符，标识符由大小写字母“A-Za-z”、数字“0-9”和连字符“_”组成。

    将标识符字符串通过“_”分割成多个字符后，一般最后一位便是8位标识符。但由于可能也存在多个相同文本在同一label语句中的情况，Ren'Py会在标识符行末尾添加一个递增数字来加以区分，此时倒数第二位才是8位标识符。
    """

    # 先将标识符反转，方便获取真正的8位标识符，避免与前缀里可能出现的8位字串混淆
    ident = ident[::-1]
    ident_match = GlobalData.pattern_identifier.match(ident)
    if not ident_match:
        return ""
    ident_8bit = ident_match.group(1)
    return ident_8bit[::-1]


def __input_path(project: str = WAIT_PROJECT, first_select: bool = True) -> bool:
    """
    输入旧版本翻译项目和待翻项目的绝对路径

    :param project: 翻译项目
    :param first_select: 首次输入路径
    """

    global __pre_trans_project_abspath, __wait_upd_project_abspath
    # 用户输入内容
    _inp = ""
    # 首次进入
    if first_select:
        if project == PRE_PROJECT:
            # 若存在默认路径
            if __pre_trans_project_abspath:
                print("正在验证默认路径……")
                # 若路径不存在，重新手动输入
                if not Path(__pre_trans_project_abspath).exists():
                    __pre_trans_project_abspath = ""
                    return __input_path(project, False)

                print("路径验证成功！\n")
                return True
            _inp = input("请输入旧翻译文本的绝对路径或回车返回主菜单：").strip()
        else:
            # 若存在默认路径
            if __wait_upd_project_abspath:
                print("正在验证默认路径……")
                # 若路径不存在，则重新手动输入
                if not Path(__wait_upd_project_abspath).exists():
                    __wait_upd_project_abspath = ""
                    return __input_path(project, False)

                print("路径验证成功！\n")
                return True
            _inp = input("请输入新翻译文本的绝对路径或回车返回主菜单：").strip()
    else:
        _inp = input("路径错误，请重新输入正确的路径或回车返回主菜单：").strip()

    # 输入为空，返回主菜单
    if _inp in ("", "\r", "\n"):
        return False

    # 规范路径，不调整大小写
    _inp = Path(_inp)
    # 若路径不存在，重新输入
    if not _inp.exists():
        return __input_path(project, False)

    if project == PRE_PROJECT:
        __pre_trans_project_abspath = _inp
    else:
        __wait_upd_project_abspath = _inp
    print("路径验证成功！\n")
    return True
