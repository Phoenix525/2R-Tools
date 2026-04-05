#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-06-12 12:11:24
Ren'Py翻译文本机器翻译工具
'''

import sys

import main
from modules.interpreter import Interpreter

# pylint: disable=invalid-name
_interpreter = None  # 翻译器实例


def _translate(reselect='0'):
    '''
    开始翻译
    '''

    if reselect == '0':
        tmp = input('\n原文：').strip()
        if tmp == '':
            _translate('1')
            return

        _interpreter.translate_txt(tmp)
        _translate()
        return

    tmp = input('未输入文本或输入文本无意义，请重新输入或回车退出程序：').strip()
    if tmp == '':
        sys.exit(0)

    _interpreter.translate_txt(tmp)
    _translate()


def _select_serial_num(reselect=False, serial_num=''):
    '''
    输入序号选择对应的操作
    '''

    if not reselect:
        print(
            '''1) 翻译文本
0) 返回上一级
'''
        )

        _inp = input('请输入要操作的序号：').strip()
        if _inp == '1':
            return
        if _inp == '0':
            main.start_main()
        else:
            _select_serial_num(True, _inp)
        return

    _tmp = input(
        f'列表中不存在序号 {serial_num}，请重新输入正确序号或回车退出程序：'
    ).strip()
    if _tmp == '':
        sys.exit(0)

    if _tmp == '1':
        return
    if _tmp == '0':
        main.start_main()
    else:
        _select_serial_num(True, _tmp)


def start():
    '''
    翻译单条语句模式
    '''

    print(
        '''
===========================================================================================
                                       机器翻译工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
'''
    )

    _select_serial_num()

    # 实例化翻译引擎
    global _interpreter
    _interpreter = Interpreter()
    # 开始翻译
    _translate()
