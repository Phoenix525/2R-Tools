#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-08-04 23:33:35
'''

import os
import sys

import main
from modules.interpreter import Interpreter
from modules.utils import (GLOBAL_DATA, KEY_PHOENIX, MARK_TODO,
                           RPGM_PROJECT_PARENT_FOLDER, matching_langs,
                           print_info, print_warn, read_json, write_json)

# pylint: disable=invalid-name
# 待翻译文本
__game_txt_cache = None
# 翻译器实例
__interpreter = None
# 当前rpgm项目名称
__curr_rpgm_project_name = ''
# 当前rpgm翻译文件的绝对路径
__curr_rpgm_project_path = ''


def start(project_name: str):
    '''
    启动界面
    '''

    global __curr_rpgm_project_name, __curr_rpgm_project_path

    __curr_rpgm_project_name = project_name
    __curr_rpgm_project_path = os.path.join(RPGM_PROJECT_PARENT_FOLDER, project_name)

    print(
        '''
===========================================================================================
                                   JSON文本机翻工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
'''
    )

    __select_serial_num()

    sys.exit()


def __initialize():
    '''
    初始化翻译器
    '''

    # 实例化翻译引擎
    global __interpreter
    __interpreter = Interpreter()
    # 开始翻译
    __translate()


def __translate(_filter=''):
    '''
    扫描缓存，逐条翻译并覆写
    '''

    print_info('正在翻译……')
    # 读取指定项目的翻译文件，未找到时返回
    if not __read_game_txt():
        print_warn('未找到需要翻译的项目，翻译结束！')
        return

    _count = 0
    _bak = True
    for k, v in __game_txt_cache.items():
        if not isinstance(k, str) or not isinstance(v, str):  # 键或值非字串的跳过
            continue
        v = v.strip()
        if v.upper() == GLOBAL_DATA['none_filter']:  # 无需显示的行，不翻译
            continue
        if v.upper() in GLOBAL_DATA['pass_filter']:  # 不翻译文本
            continue
        if (
            MARK_TODO in v.upper() and v.upper() != MARK_TODO
        ):  # 已经有翻译但不确定的不翻译
            continue
        if v != '' and v.upper() != MARK_TODO:  # 已翻译的
            continue

        txt = k.split('_')[-1]

        # 过滤指定语种文本
        if not matching_langs(txt, _filter):
            continue

        __game_txt_cache[k] = __interpreter.translate_txt(txt)
        __update_phoenix_mark(True)
        _count += 1
        if _count >= GLOBAL_DATA['json_max_cache']:
            __wirte_in_file(_bak)
            _bak = False
            _count = 0
    if _count > 0:
        __wirte_in_file(_bak)
    print_info('翻译完成！\n')


def __add_todo(_filter=''):
    '''
    查找漏翻字段，添加TODO
    '''

    print('正在扫描……')
    if not __read_game_txt():
        print_warn(f'未找到需要扫描的项目，扫描结束！')
        return

    # 漏翻字段数量
    _count = 0
    for k, v in __game_txt_cache.items():
        if not isinstance(k, str) or not isinstance(v, str):  # 键或值非字串的跳过
            continue
        # 这里只考虑值是否不为空，不考虑键的情况。
        # 因为某些情况下有可能会有翻译的值和键不对应的情况。比如键不为空，但值为空或只有换行符。
        if v != '':  # 如果已有值则pass
            continue

        # 若传入_filter，则只处理指定的语种
        if not matching_langs(k.split('_')[-1], _filter):
            continue

        _count += 1
        __game_txt_cache[k] = MARK_TODO

    if _count > 0:
        __game_txt_cache[KEY_PHOENIX] = True
    print_info(f'空值字段扫描结果为：{_count}\n')

    __wirte_in_file()


def __add_pass(_filter='ru'):
    '''
    查找指定语种，添加PASS
    '''

    if _filter.strip() == '':
        _inp = input('请输入指定语种缩写，直接回车默认为ru（俄语）：').strip()
        if _inp != '':
            _filter = _inp
        else:
            _filter = 'ru'

    print(f'当前指定语种为{_filter}\n')

    print('正在扫描……')
    if not __read_game_txt():
        print_warn('未找到需要扫描的项目，扫描结束！')
        return

    # 漏翻字段数量
    _count = 0
    for k, v in __game_txt_cache.items():
        if not isinstance(k, str) or not isinstance(v, str):  # 键或值非字串的跳过
            continue
        # 如果已有值则pass
        if v != '':
            continue
        # 处理指定语种
        if not matching_langs(k.split('_')[-1], _filter):
            continue

        _count += 1
        __game_txt_cache[k] = MARK_TODO + '_' + GLOBAL_DATA['pass_filter'][0]

    if _count > 0:
        __game_txt_cache[KEY_PHOENIX] = True
    print_info(f'指定字段扫描结果为：{_count}\n')

    __wirte_in_file()


def __read_game_txt() -> bool:
    '''
    读取指定项目的JSON翻译文件
    '''

    # 读取待翻译文本
    cache = read_json(__curr_rpgm_project_path)

    if cache is None or len(cache) < 1:
        return False

    global __game_txt_cache
    __game_txt_cache = cache

    # 将更新标记设置为False
    __update_phoenix_mark()

    return True


def __update_phoenix_mark(update=False):
    '''
    切换更新标记
    '''

    __game_txt_cache[KEY_PHOENIX] = update


def __wirte_in_file(bak=True):
    '''
    将结果写入文件
    '''

    if not __game_txt_cache[KEY_PHOENIX]:
        print(f'{__curr_rpgm_project_name} 未发生更改，无需写入！\n')
        return

    __update_phoenix_mark()
    write_json(__curr_rpgm_project_path, __game_txt_cache, backup=bak)


def __select_serial_num(serial_num='', first_select=True):
    '''
    输入序号选择对应的操作

    - serial_num: 选定的操作序号
    - first_select: 是否为重新选择
    '''

    # 用户输入内容
    _inp = ''
    # 首次进入选项
    if first_select:
        print(
            f'''1) 翻译JSON文本
2) 检索值为空的字段，并添加{MARK_TODO}
3) 检索指定语种字段，并添加{GLOBAL_DATA['pass_filter'][0]}
0) 返回上一级
'''
        )
        _inp = input('请输入要操作的序号或回车退出程序：').strip()
    else:
        _inp = input(
            f'列表中不存在序号 {serial_num}，请重新输入正确序号或回车退出程序：'
        ).strip()

    match _inp:
        case '':
            sys.exit()
        case '0':
            main.start_main()
        case '1':
            __initialize()
        case '2':
            __add_todo()
        case '3':
            __add_pass()
        case _:
            __select_serial_num(_inp, False)
