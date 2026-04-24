#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-04 23:33:35
"""

from gc import collect
from sys import exit

import main
from app.controllers.interpreter import Interpreter
from app.utils.global_data import GlobalData
from app.utils.utils import (
    match_lang,
    print_info,
    print_warn,
    read_json,
    update_phoenix_mark,
    write_json,
)

# pylint: disable=invalid-name
# 待翻译文本
__game_txt_cache: dict[str, str] = None
# 翻译器实例
__interpreter: Interpreter = None
# 当前rpgm项目名称
__curr_rpgm_project_name: str = ""
# 当前rpgm翻译文件的绝对路径
__curr_rpgm_project_path = ""


def start(project_name: str):
    """
    启动界面
    """

    print("\n")

    global __curr_rpgm_project_name, __curr_rpgm_project_path

    __curr_rpgm_project_name = project_name
    __curr_rpgm_project_path = GlobalData.rpgm_trans_abspath / project_name

    no_skip = __choose_option()

    #  初始化全局变量数据，避免数据干扰
    init_global_datas()

    if not no_skip:
        main.start_main()
        return

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
        __interpreter, \
        __curr_rpgm_project_name, \
        __curr_rpgm_project_path

    __game_txt_cache = None
    __interpreter = None
    __curr_rpgm_project_name = ""
    __curr_rpgm_project_path = ""

    collect()


def __initialize():
    """
    初始化翻译器
    """

    # 实例化翻译引擎
    global __interpreter
    __interpreter = Interpreter()
    # 开始翻译
    __translate()


def __translate(filter_lang: str = ""):
    """
    扫描缓存，逐条翻译并覆写

    :param filter_lang: 过滤语种
    """

    print_info("正在翻译……")
    # 读取指定项目的翻译文件，未找到时返回
    if not __read_game_txt():
        print_warn("未找到需要翻译的项目，翻译结束！")
        return

    _count = 0
    _bak = True
    for k, v in __game_txt_cache.items():
        # 键或值非字串的跳过
        if not isinstance(k, str) or not isinstance(v, str):
            continue

        v = v.strip()
        v_upper = v.upper()
        # 无需显示的行，不翻译
        if v_upper == GlobalData.none_filter:
            continue
        # 不翻译文本
        if v_upper in GlobalData.pass_filter:
            continue
        # 已经有翻译但不确定的不翻译
        if GlobalData.MARK_TODO in v_upper and v_upper != GlobalData.MARK_TODO:
            continue
        # 已翻译的
        if v and v_upper != GlobalData.MARK_TODO:
            continue

        # 将字段按连字符切割成两份。为以防万一，只从左往右切割1次，前面的是md5值，后面是文本
        txt = k.split("_", maxsplit=1)[-1]

        # 过滤指定语种文本
        if not match_lang(txt, filter_lang):
            continue

        __game_txt_cache[k] = __interpreter.translate_txt(txt)
        update_phoenix_mark(__game_txt_cache, True)
        _count += 1
        if _count >= GlobalData.json_max_cache:
            __wirte_in_file(_bak)
            # 已备份过，无需再备份
            _bak = False
            # 缓存数归零
            _count = 0
    if _count > 0:
        __wirte_in_file(_bak)
    print_info("翻译完成！\n")


def __add_todo(filter_lang: str = ""):
    """
    查找漏翻字段，添加TODO
    """

    print("正在扫描……")
    if not __read_game_txt():
        print_warn("未找到需要扫描的项目，扫描结束！")
        return

    # 漏翻字段数量
    _count = 0
    for k, v in __game_txt_cache.items():
        if not isinstance(k, str) or not isinstance(v, str):  # 键或值非字串的跳过
            continue
        # 这里只考虑值是否不为空，不考虑键的情况。
        # 因为某些情况下有可能会有翻译的值和键不对应的情况。比如键不为空，但值为空或只有换行符。
        if v != "":  # 如果已有值则pass
            continue

        # 若传入_filter，则只处理指定的语种
        if not match_lang(k.split("_")[-1], filter_lang):
            continue

        _count += 1
        __game_txt_cache[k] = GlobalData.MARK_TODO

    if _count > 0:
        update_phoenix_mark(__game_txt_cache, True)
    print_info(f"空值字段扫描结果为：{_count}\n")

    __wirte_in_file()


def __add_pass(filter_lang: str = "ru"):
    """
    查找指定语种，添加PASS
    """

    if not filter_lang.strip():
        _inp = input("请输入指定语种缩写，直接回车默认为ru（俄语）：").strip()
        if _inp != "":
            filter_lang = _inp
        else:
            filter_lang = "ru"

    print(f"当前指定语种为{filter_lang}\n")

    print("正在扫描……")
    if not __read_game_txt():
        print_warn("未找到需要扫描的项目，扫描结束！")
        return

    # 漏翻字段数量
    _count = 0
    for k, v in __game_txt_cache.items():
        if not isinstance(k, str) or not isinstance(v, str):  # 键或值非字串的跳过
            continue
        # 如果已有值则pass
        if v != "":
            continue
        # 处理指定语种
        if not match_lang(k.split("_")[-1], filter_lang):
            continue

        _count += 1
        __game_txt_cache[k] = GlobalData.MARK_TODO + "_" + GlobalData.pass_filter[0]

    if _count > 0:
        update_phoenix_mark(__game_txt_cache, True)
    print_info(f"指定字段扫描结果为：{_count}\n")

    __wirte_in_file()


def __read_game_txt() -> bool:
    """
    读取指定项目的JSON翻译文件
    """

    # 读取待翻译文本
    cache = read_json(__curr_rpgm_project_path)

    if not cache:
        return False

    global __game_txt_cache
    __game_txt_cache = cache

    # 将更新标记设置为False
    update_phoenix_mark(__game_txt_cache)

    return True


def __wirte_in_file(bak: bool = True):
    """
    将结果写入文件

    :param bak: 启用备份
    """

    if not __game_txt_cache.get(GlobalData.KEY_PHOENIX, False):
        print(f"{__curr_rpgm_project_name} 未发生更改，无需写入！\n")
        return

    update_phoenix_mark(__game_txt_cache)
    write_json(__curr_rpgm_project_path, __game_txt_cache, backup=bak)


def __choose_option(first_select: bool = True) -> bool:
    """
    输入序号选择对应的操作

    :param first_select: 首次进入选项
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        print(f"""1) 翻译JSON翻译文本
2) 检索值为空的字段，并添加{GlobalData.MARK_TODO}
3) 检索指定语种字段，并添加{GlobalData.pass_filter[0]}
""")
        _inp = input("请输入要操作的序号或回车返回主菜单：")
    else:
        _inp = input("列表中不存在该序号，请重新输入正确序号或回车返回主菜单：")

    match _inp:
        case "" | "\r" | "\n":
            return False
        case "1":
            __initialize()
            return True
        case "2":
            __add_todo()
            return True
        case "3":
            __add_pass()
            return True
        case _:
            return __choose_option(False)

    return False
