#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-06-12 12:11:24
机器翻译工具
"""

import sys

import main
from src.core.interpreter import Interpreter

# pylint: disable=invalid-name
__interpreter = None  # 翻译器实例


def start():
    """
    翻译单条语句模式
    """

    print("""
===========================================================================================
                                       机器翻译工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
""")
    __choose_option()

    # 实例化翻译引擎
    global __interpreter
    __interpreter = Interpreter()
    # 开始翻译
    __translate()


def __translate(first_trans=True):
    """
    开始翻译

    :param first_trans: 首次调用翻译
    """

    if first_trans:
        tmp = input("\n原文：").strip()
        if tmp == "":
            __translate("1")
            return

        __interpreter.translate_txt(tmp)
        __translate()
        return

    tmp = input("未输入文本或输入文本无意义，请重新输入或回车退出程序：").strip()
    if tmp == "":
        sys.exit()

    __interpreter.translate_txt(tmp)
    __translate()


def __choose_option(first_select=True):
    """
    输入序号选择对应的操作

    :param first_select: 首次进入选项
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        print("""1) 开始翻译
0) 返回上一级
""")
        _inp = input("请输入要操作的序号或回车退出程序：").strip()
    else:
        _inp = input("列表中不存在该序号，请重新输入正确序号或回车退出程序：").strip()

    match _inp:
        case "":
            sys.exit()
        case "0":
            main.start_main()
        case "1":
            return
        case _:
            __choose_option(False)
