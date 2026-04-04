#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-08-10 23:33:35
'''

import copy
import os
import pathlib
import sys

import main
from modules.utils import (BASE_ABSPATH, PATTERN_EMPTY_LINE,
                           PATTERN_IDENTIFIER, PATTERN_NEW, PATTERN_NEW_SAY,
                           PATTERN_OLD, PATTERN_OLD_SAY,
                           TRANSLATED_LIB_LIBRARY, get_file_encoding,
                           is_renpy_translation_file, merge_dicts, print_err,
                           print_info, print_warn, read_json, write_json)

_WAITING_FOR_ENTRY = os.path.join(BASE_ABSPATH, 'waiting-for-entry')

_txt_library_cache = {}


def walk_file():
    '''
    遍历文件夹内所有文件
    '''

    global _txt_library_cache

    # 如果文件夹不存在，新建一个
    pathlib.Path(_WAITING_FOR_ENTRY).mkdir(parents=True, exist_ok=True)

    for root, dirs, files in os.walk(_WAITING_FOR_ENTRY, topdown=False):
        # 遍历所有文件
        for _file in files:
            _file_path = os.path.join(root, _file)
            # 扫描rpy文件
            if is_renpy_translation_file(_file_path):
                print(f'当前扫描文本：{_file}')
                _txt_library_cache = scanning_rpy_file(
                    root, _file, _txt_library_cache, True
                )

            # 扫描json文件
            elif _file.endswith('.json'):
                _txt_library_cache = read_json(_file_path)


def scanning_rpy_file(
    file_path: str, filename: str, txt_list=None, rewrite=False
) -> dict:
    '''
    扫描原翻译文本，将需要的数据存入缓存器

    - file_path: 文件路径
    - filename: 文件名称
    - txt_list: 文本字典
    - rewrite: 是否覆盖文本字典内已有的值。默认不覆盖
    '''

    _tmp_txt_list = None
    if txt_list is None:
        _tmp_txt_list = {}
    else:
        _tmp_txt_list = copy.deepcopy(txt_list)

    inp = open(
        os.path.join(file_path, filename),
        'r',
        encoding=get_file_encoding(os.path.join(file_path, filename)),
    )
    light_sen = inp.readlines()
    inp.close()

    _old_say = ''  # 原文
    _identifier = 'strings'  # 标识符

    try:
        for line in light_sen:
            # 空行
            if PATTERN_EMPTY_LINE.match(line) is not None:
                continue

            # 标志符行
            identifier_match = PATTERN_IDENTIFIER.match(line)
            if identifier_match is not None:
                _identifier = identifier_match.group(1)
                # 扫描到标志符行，说明进入了新的原译组，则初始化原文
                # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
                _old_say = ''
                continue

            # 原文本行
            old_say_match = PATTERN_OLD_SAY.match(line)
            if (
                old_say_match is not None
                and old_say_match.group(1) != 'voice'
                and _identifier not in ['', 'strings']
            ):
                _old_say = old_say_match.group(2)
                continue

            # 译文行
            new_say_match = PATTERN_NEW_SAY.match(line)
            if (
                new_say_match is not None
                and new_say_match.group(1) != 'voice'
                and _identifier not in ['', 'strings']
            ):
                if _old_say.strip() == '':
                    continue
                new_say = new_say_match.group(2)  # 译文
                if new_say == '':
                    continue
                if not _old_say in _tmp_txt_list or rewrite:
                    _tmp_txt_list[_old_say] = new_say
                # 如果单条语句中有多行译文，只扫描第一行的译文
                _old_say = ''
                continue

            # old行
            old_match = PATTERN_OLD.match(line)
            if old_match is not None and _identifier == 'strings':
                _old_say = old_match.group(1)
                continue

            # new 行
            new_match = PATTERN_NEW.match(line)
            if new_match is not None and _identifier == 'strings':
                if _old_say.strip() == '':
                    continue
                new_say = new_match.group(1)  # 译文
                if new_say == '':
                    continue
                if not _old_say in _tmp_txt_list or rewrite:
                    _tmp_txt_list[_old_say] = new_say
                _old_say = ''
    except Exception as e:
        print_err(f'{filename} 数据读写异常：{str(e)}！\n扫描终止！\n')
        sys.exit(0)
    else:
        print_info(f'{filename} 扫描完成！\n')

    return _tmp_txt_list


def write_translib():
    '''
    写入译文库
    '''

    if (
        _txt_library_cache is None
        or not isinstance(_txt_library_cache, dict)
        or len(_txt_library_cache) < 2
    ):
        print_warn(f'待扩增文本为空，未写入{TRANSLATED_LIB_LIBRARY}译文库')
        return

    translib_path = os.path.join(BASE_ABSPATH, 'libraries', TRANSLATED_LIB_LIBRARY)
    translated_txt_lib = read_json(translib_path)

    for k, v in _txt_library_cache.items():
        # 译文库中已有该文本，跳过
        if k in translated_txt_lib:
            continue

        if v.strip() == '':
            continue

        translated_txt_lib[k] = v

    write_json(
        translib_path,
        translated_txt_lib, backup=False
    )


def _select_serial_num(reselect=False, serial_num=''):
    '''
    输入序号选择对应的操作

    - reselect: 是否为重新选择
    - serial_num: 选定的操作序号
    '''

    if not reselect:
        print(
            '''1) 写入译文库
2) 更新基础文本库
0) 返回上一级
'''
        )

        _inp = input('请输入要操作的序号（如1）：').strip()
        if _inp == '1':
            print('正在更新译文库中，请稍候……\n')
            walk_file()
            write_translib()
            print_info('译文库更新已完成！')
            return

        if _inp == '2':
            _file1 = input('\n请输入原文本库路径：').strip()
            _file2 = input('\n请输入新文本库路径：').strip()
            print('扫描中，请稍等……')
            _dict1 = read_json(_file1)
            _dict2 = read_json(_file2)
            merge_dicts([_dict1, _dict2])
            file_2_path = pathlib.Path(_file2)
            write_json(
                os.path.join(
                    file_2_path.parent, file_2_path.stem + '_new' + file_2_path.suffix
                ),
                _file2,
            )
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
        print('正在更新译文库中，请稍候……\n')
        walk_file()
        write_translib()
        print_info('译文库更新已完成！')
        return

    if _tmp == '2':
        _file1 = input('\n请输入原文本库路径：').strip()
        _file2 = input('\n请输入新文本库路径：').strip()
        print('扫描中，请稍等……')
        _dict1 = read_json(_file1)
        _dict2 = read_json(_file2)
        merge_dicts([_dict1, _dict2])
        file_2_path = pathlib.Path(_file2)
        write_json(
            os.path.join(
                file_2_path.parent, file_2_path.stem + '_new' + file_2_path.suffix
            ),
            _file2,
        )
        return

    if _tmp == '0':
        main.start_main()
    else:
        _select_serial_num(True, _tmp)


def start():

    print(
        r'''
===========================================================================================
                                  rpy/json 写入译文库工具
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================
'''
    )

    _select_serial_num()

    sys.exit(0)
