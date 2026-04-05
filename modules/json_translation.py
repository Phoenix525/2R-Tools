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
_game_txt_cache = None
# 翻译器实例
_interpreter = None
# 当前rpgm项目名称
_curr_rpgm_project_name = ''
# 当前rpgm翻译文件的绝对路径
_curr_rpgm_project_abspath = ''


def _translate(_filter=''):
    '''
    扫描缓存，逐条翻译并覆写
    '''

    # 读取指定项目的翻译文件，未找到时返回
    if not _read_game_txt():
        return

    _count = 0
    _bak = True
    for k, v in _game_txt_cache.items():
        if not isinstance(v, str):
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

        _game_txt_cache[k] = _interpreter.translate_txt(txt)
        _change_phoenix_mark(True)
        _count += 1
        if _count >= GLOBAL_DATA['json_max_cache']:
            _wirte_in_file(_bak)
            _bak = False
            _count = 0
    if _count > 0:
        _wirte_in_file(_bak)
    print_info('翻译完成！\n')


def _add_todo(_filter=''):
    '''
    查找漏翻字段，添加TODO
    '''

    print('扫描中，请稍候……')

    if not _read_game_txt():
        print_warn(f'当前目录中不存在{_curr_rpgm_project_name}文件，检索已结束！')
        return

    # 漏翻字段数量
    _count = 0
    for k, v in _game_txt_cache.items():
        # 如果已有值则pass
        # 这里只考虑值（且不去除首尾空格）是否不为空，不考虑键的情况。
        # 因为某些情况下有可能会有翻译的值和键不对应的情况。比如键不为空，但值为空或只有换行符。
        if v != '':
            continue

        # 若传入_filter，则只处理指定的语种
        if not matching_langs(k.split('_')[-1], _filter):
            continue

        _count += 1
        _game_txt_cache[k] = MARK_TODO

    if _count > 0:
        _game_txt_cache[KEY_PHOENIX] = True
    print_info(f'空值字段扫描结果为：{_count}\n')

    _wirte_in_file()


def _add_pass(_filter='ru'):
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
    print('扫描中，请稍候……')

    if not _read_game_txt():
        print_warn('检索已结束！')
        return

    # 漏翻字段数量
    _count = 0
    for k, v in _game_txt_cache.items():
        # 如果已有值则pass
        if v != '':
            continue
        # 处理指定语种
        if not matching_langs(k.split('_')[-1], _filter):
            continue

        _count += 1
        _game_txt_cache[k] = MARK_TODO + '_' + GLOBAL_DATA['pass_filter'][0]

    if _count > 0:
        _game_txt_cache[KEY_PHOENIX] = True
    print_info(f'指定字段扫描结果为：{_count}\n')

    _wirte_in_file()


def _read_game_txt() -> bool:
    '''
    读取指定项目的JSON翻译文件
    '''

    # 读取待翻译文本
    global _game_txt_cache
    _game_txt_cache = read_json(_curr_rpgm_project_abspath)

    if len(_game_txt_cache) < 1:
        print_warn(f'{_game_txt_cache} 不存在或内容为空！')
        return False

    # 将更新标记设置为False
    _change_phoenix_mark()

    return True


def _change_phoenix_mark(mark=False):
    '''
    切换更新标记
    '''

    _game_txt_cache[KEY_PHOENIX] = mark


def _wirte_in_file(bak=True):
    '''
    将结果写入文件
    '''

    if not _game_txt_cache[KEY_PHOENIX]:
        print(f'{_curr_rpgm_project_name} 未发生更改，无需写入！\n')
        return

    _change_phoenix_mark()
    write_json(_curr_rpgm_project_abspath, _game_txt_cache, backup=bak)


def _select_serial_num(reselect=False, serial_num=''):
    '''
    输入序号选择对应的操作
    '''

    if not reselect:
        print(
            f'''1) 翻译JSON文本
2) 检索值为空的字段，并添加{MARK_TODO}
3) 检索指定语种字段，并添加{GLOBAL_DATA['pass_filter'][0]}
0) 返回上一级
'''
        )

        _inp = input('请输入要操作的序号：').strip()
        if _inp == '1':
            _initialize()
        elif _inp == '2':
            _add_todo()
        elif _inp == '3':
            _add_pass()
        elif _inp == '0':
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
        _initialize()
    elif _tmp == '2':
        _add_todo()
    elif _tmp == '3':
        _add_pass()
    elif _tmp == '0':
        main.start_main()
    else:
        _select_serial_num(True, _tmp)


def _initialize():
    '''
    初始化翻译器
    '''

    # 实例化翻译引擎
    global _interpreter
    _interpreter = Interpreter()
    # 开始翻译
    _translate()


def start(project_name: str):
    '''
    启动界面
    '''

    global _curr_rpgm_project_name, _curr_rpgm_project_abspath

    _curr_rpgm_project_name = project_name
    _curr_rpgm_project_abspath = os.path.join(RPGM_PROJECT_PARENT_FOLDER, project_name)

    print(
        '''
===========================================================================================
                                   JSON文本机翻工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
'''
    )

    _select_serial_num()

    sys.exit(0)
