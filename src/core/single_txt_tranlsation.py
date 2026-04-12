#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-06-12 12:11:24
机器翻译工具
"""

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
                                      版权归作者所有""")

    # 实例化翻译引擎
    global __interpreter
    __interpreter = Interpreter()
    # 开始翻译
    if not __translate():
        main.start_main()


def __translate(first_trans=True):
    """
    开始翻译

    :param first_trans: 首次调用翻译
    """

    if first_trans:
        tmp = input("\n原文：").strip()
        if tmp in ("", "\r", "\n"):
            return __translate(False)

        __interpreter.translate_txt(tmp)
        return __translate()

    tmp = input("未输入文本或输入文本无意义，请重新输入或回车返回主菜单：")
    if tmp in ("", "\r", "\n"):
        return False

    __interpreter.translate_txt(tmp)
    return __translate()
