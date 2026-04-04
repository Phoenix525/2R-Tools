#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-06-12 12:11:24
Ren'Py翻译文本机器翻译工具

以下形式的代码块为一个“待处理区块（Block Awaiting Processing，简称BAP）”，即“标识符行 + 原文注释 + 译文”。缓存数以一个BAP为基数
translate chinese xxx_xxx_xxxxxxxx:

    # pov "xxxxx" with dissolve
    pov "" with dissolve
'''

import os
import sys
from datetime import datetime
from re import escape, sub

import main
from modules.interpreter import Interpreter
from modules.utils import (END_SAY, GLOBAL_DATA, MARK_TODO, PATTERN_EMPTY_LINE,
                           PATTERN_IDENTIFIER, PATTERN_NEW, PATTERN_NEW_SAY,
                           PATTERN_OLD, PATTERN_OLD_SAY, PATTERN_WHO,
                           RENPY_PROJECT_PARENT_FOLDER, copy_directory,
                           get_file_encoding, is_renpy_translation_file,
                           print_err, print_info, print_warn)

# pylint: disable=invalid-name
_input_abspath = GLOBAL_DATA['rpy_trans_input_abspath']
_output_abspath = ''

# BAP最大缓存量
_bap_max_cache = GLOBAL_DATA['rpy_trans_bap_max_cache']

# 是否覆盖所有译文
_rewrite_all = False

# 是否覆盖TODO译文
_rewrite_todo = False

# 翻译器实例
_interpreter = None

# 当前renpy项目名称
curr_renpy_project_name = 'Test_v0.1'
# 当前renpy项目的绝对路径
curr_renpy_project_abspath = os.path.join(
    RENPY_PROJECT_PARENT_FOLDER, curr_renpy_project_name
)


def walk_file():
    '''
    遍历文件夹内所有内容
    '''

    if os.path.isfile(_input_abspath):
        # 跳过非renPy翻译文本
        if not is_renpy_translation_file(_input_abspath):
            return

        root, f = os.path.split(_input_abspath)
        print(f'当前翻译文本：{f}')
        process_file(_input_abspath, _output_abspath, f)
        return

    for root, dirs, files in os.walk(_input_abspath, topdown=False):

        # 新文件目录
        relative_path = os.path.relpath(root, _input_abspath)
        new_path = (
            _output_abspath
            if relative_path == '.'
            else os.path.join(_output_abspath, relative_path)
        )
        # 若新目录不存在，创建它
        if not os.path.exists(new_path):
            os.makedirs(new_path)

        # 遍历所有文件
        for f in files:
            in_path = os.path.join(root, f)
            out_path = os.path.join(new_path, f)

            # 非renPy翻译文本直接拷贝至新目录
            if not is_renpy_translation_file(in_path):
                copy_directory(in_path, out_path)
                continue

            print(f'当前翻译文本：{f}')
            process_file(in_path, out_path, f)


def process_file(old_path: str, new_path: str, filename: str):
    '''
    读取文本、翻译并写入
    '''

    inp = open(old_path, 'r', encoding=get_file_encoding(old_path))
    lightSen = inp.readlines()
    inp.close()
    outp = open(new_path, 'w', encoding=get_file_encoding(new_path))

    _old_say = ''  # 原文
    _identifier = 'strings'  # 标识符
    _tmp_lines = ''  # 缓存文本
    _bap_count = 0  # BAP缓存计数

    for line in lightSen:
        # 空行
        if PATTERN_EMPTY_LINE.match(line) is not None:
            _tmp_lines += line
            continue

        # 标志符行
        identifier_match = PATTERN_IDENTIFIER.match(line)
        if identifier_match is not None:
            _tmp_lines += line
            _identifier = identifier_match.group(1)
            # 进入新的BAP，缓存计数+1
            _bap_count += 1
            # 扫描到标志符行，说明进入了新的BAP，清空原文
            # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
            _old_say = ''
            continue

        # 原文行
        old_say_match = PATTERN_OLD_SAY.match(line)
        if old_say_match is not None and _identifier not in ['', 'strings']:
            _tmp_lines += line
            # 跳过cv语音行
            if old_say_match.group(1) == 'voice':
                continue

            _old_say = old_say_match.group(2)
            continue

        # 译文行
        new_say_match = PATTERN_NEW_SAY.match(line)
        if new_say_match is not None and _identifier not in ['', 'strings']:
            group = new_say_match.groups()
            _err_code = ''
            _who = new_say_match.group(1)
            # 跳过cv语音行
            if _who == 'voice':
                _tmp_lines += line
                continue

            # 原文为空，直接写入
            if _old_say.strip() == '':
                _tmp_lines += line
                if _bap_count >= _bap_max_cache:
                    outp.write(_tmp_lines)
                    outp.flush()
                    _tmp_lines = ''
                    _bap_count = 0
                continue

            # 如果原文为END_SAY，说明当前BAP已结束，现在是多出来的译文行
            if _old_say == END_SAY:
                # 如果覆盖所有译文为开，则删除多余的译文行；反之保留
                if not _rewrite_all:
                    _tmp_lines += line
                    if _bap_count >= _bap_max_cache:
                        outp.write(_tmp_lines)
                        outp.flush()
                        _tmp_lines = ''
                        _bap_count = 0
                continue

            # 存在字符串形式的who
            who_match = PATTERN_WHO.match(_who)
            if who_match is not None and who_match.group(1) != '':
                who = who_match.group(1)
                who_new = _interpreter.translate_txt(who, activate_context='0')
                if who_new.strip() != '':
                    _who = sub(escape(repr(who))[1:-1], who_new, _who)

            original_new_say = new_say_match.group(2)
            with_transition = new_say_match.group(3)
            # 当译文不为空时，根据覆盖写入开关进行相应操作
            if original_new_say != '':
                # 当覆盖所有译文为开,或者译文为TODO，或者覆盖TODO译文为开，且已有译文开头为TODO时，发出翻译请求
                if (
                    _rewrite_all
                    or original_new_say.upper() == MARK_TODO
                    or (
                        _rewrite_todo and original_new_say.upper().startswith(MARK_TODO)
                    )
                ):
                    new_say = _interpreter.translate_txt(
                        _old_say,
                        activate_context='1',
                        open_todo=GLOBAL_DATA['mark_todo'],
                    )
                    # 如果翻译错误，则保持原样
                    if new_say.strip() == '':
                        _tmp_lines += line
                    else:
                        _tmp_lines += (
                            '    '
                            + ((_who + ' ') if _who != '' else _who)
                            + '\"'
                            + new_say
                            + '\"'
                            + (
                                (' ' + with_transition)
                                if with_transition != ''
                                else with_transition
                            )
                            + '\n'
                        )
                else:
                    _tmp_lines += line
            else:
                new_say = _interpreter.translate_txt(
                    _old_say, activate_context='1', open_todo=GLOBAL_DATA['mark_todo']
                )
                # 如果翻译错误，则保持原样
                if new_say.strip() == '':
                    _tmp_lines += line
                else:
                    _tmp_lines += (
                        '    '
                        + ((_who + ' ') if _who != '' else _who)
                        + '\"'
                        + new_say
                        + '\"'
                        + (
                            (' ' + with_transition)
                            if with_transition != ''
                            else with_transition
                        )
                        + '\n'
                    )
            if _bap_count >= _bap_max_cache:
                outp.write(_tmp_lines)
                outp.flush()
                _tmp_lines = ''
                _bap_count = 0
            # 当前BAP处理结束，若当前BAP的译文是多行翻译，除第一行外均删除
            _old_say = END_SAY
            continue

        # old行
        old_match = PATTERN_OLD.match(line)
        if old_match is not None and _identifier == 'strings':
            _tmp_lines += line
            _old_say = old_match.group(1)
            continue

        # new行
        new_match = PATTERN_NEW.match(line)
        if new_match is not None and _identifier == 'strings':
            if _old_say == '':
                _tmp_lines += line
                if _bap_count >= _bap_max_cache:
                    outp.write(_tmp_lines)
                    outp.flush()
                    _tmp_lines = ''
                    _bap_count = 0
                continue

            original_new = new_match.group(1)  # 译文
            # 当译文不为空时，根据覆盖写入开关进行相应操作
            if original_new != '':
                # 当覆盖所有译文为开,或者译文为TODO，或者覆盖TODO译文为开，且已有译文开头为TODO时，发出翻译请求
                if (
                    _rewrite_all
                    or original_new.upper() == MARK_TODO
                    or (_rewrite_todo and original_new.upper().startswith(MARK_TODO))
                ):
                    new = _interpreter.translate_txt(
                        _old_say,
                        activate_context='-1',
                        open_todo=GLOBAL_DATA['mark_todo'],
                    )
                    # 如果翻译错误，则保持原样
                    if new.strip() == '':
                        _tmp_lines += line
                    else:
                        _tmp_lines += '    new \"' + new + '\"\n'
                else:
                    _tmp_lines += line
            else:
                new = _interpreter.translate_txt(
                    _old_say, activate_context='-1', open_todo=GLOBAL_DATA['mark_todo']
                )
                if new.strip() == '':
                    _tmp_lines += line
                else:
                    _tmp_lines += '    new \"' + new + '\"\n'
            if _bap_count >= _bap_max_cache:
                outp.write(_tmp_lines)
                outp.flush()
                _tmp_lines = ''
                _bap_count = 0
            _old_say = ''
            continue

        # 其他行
        _tmp_lines += line

    if _tmp_lines != '':
        outp.write(_tmp_lines)
    print_info(f'{filename} 翻译完成！\n')
    outp.close()


def input_path(reselect=False):
    '''
    输入待翻文件/文件夹的绝对路径
    '''

    global _input_abspath, _output_abspath

    if not reselect:
        if _input_abspath:
            # 若路径不存在，则重新手动输入
            if not os.path.exists(_input_abspath):
                print_warn('config.ini配置的翻译文本路径不存在！请手动输入路径！\n')
                _input_abspath = ''
                input_path()
                return

            _input_abspath, _output_abspath = verify_path(
                _input_abspath, _output_abspath
            )
            return

        inp = input('请输入翻译文本的绝对路径：').strip()
        # 输入为空，重新输入
        if inp == '':
            input_path(True)
            return
        # 规范路径，不调整大小写
        inp = os.path.normpath(inp)
        # 若路径不存在，重新输入
        if not os.path.exists(inp):
            input_path(True)
            return

        _input_abspath, _output_abspath = verify_path(inp, _output_abspath)
        return

    tmp = input('路径错误，请重新输入正确的路径或回车关闭程序：').strip()
    # 输入为空，退出程序
    if tmp == '':
        sys.exit(0)
    # 规范路径，不调整大小写
    tmp = os.path.normpath(tmp)
    # 若路径不存在，重新输入
    if not os.path.exists(tmp):
        input_path(True)
        return

    _input_abspath, _output_abspath = verify_path(tmp, _output_abspath)


def verify_path(input_abspath: str, output_abspath: str) -> tuple:
    '''
    验证原路径和目标路径是否正确

    :param input_abspath: 原路径
    :param output_abspath: 目标路径
    '''

    # 如果输入路径是文件夹
    if os.path.isdir(input_abspath):
        # 输出路径也生成文件夹
        output_abspath = input_abspath + '-new'
        # 如果输出文件夹已存在，先将其更名，再新建空文件夹
        if os.path.exists(output_abspath):
            os.rename(
                output_abspath,
                output_abspath + '_' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S'),
            )
        os.makedirs(output_abspath)

    # 如果输出路径是文件
    elif os.path.isfile(input_abspath):
        _inp = os.path.splitext(input_abspath)
        output_abspath = _inp[0] + '-new' + _inp[-1]
        # 如果输出文件已存在，将其更名备份
        if os.path.exists(output_abspath):
            bak_output_abspath = (
                _inp[0]
                + '-new_'
                + datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
                + _inp[-1]
            )
            os.rename(output_abspath, bak_output_abspath)
    print_info('路径验证成功！\n')
    return input_abspath, output_abspath


def is_rewrite_all() -> bool:
    '''
    是否覆盖所有译文。如果提取翻译文本未勾选“为翻译生成空字串”，则务必选择覆盖写入
    '''

    print('\n！！！！！以下选项谨慎操作！！！！！')
    rewrite_tmp = input(
        '是否覆盖所有译文？输入“y”覆盖，输入其他内容不覆盖。\n注意：如果生成翻译文本未勾选“为翻译生成空字串”，则必须选择覆盖：'
    ).strip()

    if rewrite_tmp in ['Y', 'y']:
        print('=====================当前选择为：覆盖写入=====================\n')
        return True

    print('====================当前选择为：不覆盖写入====================\n')
    return False


def is_rewrite_todo() -> bool:
    '''
    是否覆盖TODO译文
    '''

    print('\n！！！！！以下选项谨慎操作！！！！！')
    rewrite_tmp = input('是否覆盖TODO译文？输入“y”覆盖，输入其他内容不覆盖：').strip()

    if rewrite_tmp in ['Y', 'y']:
        print('=====================当前选择为：覆盖写入=====================\n')
        return True

    print('====================当前选择为：不覆盖写入====================\n')
    return False


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
    翻译文本模式
    '''

    print(
        r'''
===========================================================================================
                                  Ren'Py 翻译文本机翻工具
                                      作者：Phoenix
                                      版权归作者所有
                            PS：本工具所有操作均不会影响原文件！
===========================================================================================
'''
    )

    # 选择操作选项
    _select_serial_num()

    # 输入待处理对象路径
    input_path()

    global _interpreter, _rewrite_all, _rewrite_todo

    _interpreter = Interpreter()

    # 是否开启覆盖所有译文
    _rewrite_all = is_rewrite_all()

    # 如果不覆盖所有译文，再询问是否开启覆盖TODO译文
    if not _rewrite_all:
        _rewrite_todo = is_rewrite_todo()

    walk_file()
    print_info('翻译已全部完成，请前往原路径查看翻译文本！')
    sys.exit(0)
