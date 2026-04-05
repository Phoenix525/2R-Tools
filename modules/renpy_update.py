#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-07-20 23:33:35

以下形式的代码块为一个“待处理区块（Block Awaiting Processing，简称BAP）”，即“标识符行 + 原文注释 + 译文”。缓存数以一个BAP为基数
translate chinese xxx_xxx_xxxxxxxx:

    # pov "xxxxx" with dissolve
    pov "" with dissolve
'''

import copy
import os
import sys
from datetime import datetime

import main
from modules.utils import (END_SAY, GLOBAL_DATA, MARK_TODO, PATTERN_EMPTY_LINE,
                           PATTERN_IDENTIFIER, PATTERN_NEW, PATTERN_NEW_SAY,
                           PATTERN_OLD, PATTERN_OLD_SAY,
                           RENPY_PROJECT_PARENT_FOLDER, del_key_from_dict,
                           get_file_encoding, has_lower_letter, is_int,
                           is_renpy_translation_file, print_err, print_info)

# pylint: disable=invalid-name

# 旧版本翻译文本路径
_old_abspath = GLOBAL_DATA['rpy_update_old_abspath']
# 新版本翻译文本路径
_new_abspath = GLOBAL_DATA['rpy_update_new_abspath']

# 更新后的翻译文本路径
_output_abspath = ''

# 标识符缓存库。以标识符作为key进行储存，不可储存who和strings。格式：{identifier:[new_say,new_say]}
_identifier_library_cache = {}
# 文本缓存库。以文本作为key进行储存，可储存who和strings。格式：{old_say:{identifier:[new_say,new_say]}}
_txt_library_cache = {}

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

    if os.path.isfile(_old_abspath):
        # 跳过非renPy翻译文本
        if not is_renpy_translation_file(_old_abspath):
            return

        root, f = os.path.split(_old_abspath)
        print(f'当前扫描文本：{f}')
        scanning_file(root, f)
    else:
        for root, dirs, files in os.walk(_old_abspath, topdown=False):
            for f in files:
                # 跳过非renPy翻译文本
                if not is_renpy_translation_file(os.path.join(root, f)):
                    continue

                print(f'当前扫描文本：{f}')
                scanning_file(root, f)

    # if len(_txt_library_cache) < 1 and len(_identifier_library_cache) < 1:
    #     return

    if os.path.isfile(_new_abspath):
        # 跳过非renPy翻译文本
        if not is_renpy_translation_file(_new_abspath):
            return

        root, f = os.path.split(_new_abspath)
        print(f'当前更新文本：{f}')
        process_file(_new_abspath, _output_abspath, f)
        return

    for root, dirs, files in os.walk(_new_abspath, topdown=False):

        # 创建文件所在目录
        relative_path = os.path.relpath(root, _new_abspath)
        output_path = (
            _output_abspath
            if relative_path == '.'
            else os.path.join(_output_abspath, relative_path)
        )
        # 若新目录不存在，创建它
        if not os.path.exists(output_path):
            os.makedirs(output_path)

        # 遍历所有文件
        for f in files:
            new_path = os.path.join(root, f)
            # 跳过非renPy翻译文本
            if not is_renpy_translation_file(new_path):
                continue

            print(f'当前更新文本：{f}')
            process_file(new_path, os.path.join(output_path, f), f)


def scanning_file(file_path: str, filename: str):
    '''
    扫描旧版本翻译文本，将需要的数据存入缓存器
    '''

    inp = open(
        os.path.join(file_path, filename),
        'r',
        encoding=get_file_encoding(os.path.join(file_path, filename)),
    )
    # todo 读出所有行，文件较大时可能会报错，需优化
    lightSen = inp.readlines()
    inp.close()

    # _old_who = ''  # 字符串形式的who
    _old_say = ''  # 原文say
    _identifier = 'strings'  # strings标识符，用来区分who_say和old_new
    _curr_bap_processed = ''  # 标志当前BAP处理结束

    for line in lightSen:
        # 空行
        if PATTERN_EMPTY_LINE.match(line) is not None:
            continue

        # 标志符行
        identifier_match = PATTERN_IDENTIFIER.match(line)
        if identifier_match is not None:
            _identifier = identifier_match.group(1)
            # 扫描到标志符行，说明进入了新的BAP，清空原文
            # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
            # _old_who = ''
            _old_say = ''
            # 重置BAP结束标志
            _curr_bap_processed = False
            continue

        # 原文本行
        old_say_match = PATTERN_OLD_SAY.match(line)
        if old_say_match is not None and _identifier not in ['', 'strings']:
            old_say_list = old_say_match.groups()
            _who = old_say_list[0]
            # 跳过cv语音行
            if _who == 'voice':
                continue

            # 存在字符串形式的who，在存入缓存库之前，不能修改_old_who
            # who_match = PATTERN_WHO.match(_who)
            # if who_match is not None and who_match.group(1) != '':
            #     _old_who = who_match.group(1)

            # 获取原文
            _old_say = old_say_list[1]
            continue

        # old行
        old_match = PATTERN_OLD.match(line)
        if old_match is not None and _identifier == 'strings':
            # 获取原文，在存入缓存库之前，不能修改_old_say
            _old_say = old_match.group(1)
            _curr_bap_processed = False
            continue

        # 如果当前BAP已处理结束，则不论原译文下面还有多少行，直接进入新的BAP。
        if _curr_bap_processed:
            continue

        # 译文行
        new_say_match = PATTERN_NEW_SAY.match(line)
        if new_say_match is not None and _identifier not in ['', 'strings']:
            new_say_list = new_say_match.groups()
            _who = new_say_list[0]
            # 跳过cv语音行
            if _who == 'voice':
                continue

            # 写入标识符缓存库
            new_say = new_say_list[1]
            write_in_identifier_library_cache(_identifier, new_say)

            # 原文say为空时，不写入文本缓存库
            if _old_say == '':
                continue

            # 字符串形式的who
            # who_match = PATTERN_WHO.match(_who)
            # if who_match is not None and who_match.group(1) != '':
            #     write_in_txt_library_cache(_old_who, who_match.group(1), 'who')

            # 写入文本缓存库，并返回当前BAP处理标志
            _curr_bap_processed = write_in_txt_library_cache(
                _old_say, new_say, _identifier
            )
            continue

        # new 行
        new_match = PATTERN_NEW.match(line)
        if new_match is not None and _identifier == 'strings':
            # 写入文本缓存库
            write_in_txt_library_cache(_old_say, new_match.group(1), _identifier)
            # 当前BAP处理结束
            _curr_bap_processed = True

    print_info(f'{filename} 扫描完成！\n')


def process_file(new_path: str, output_path: str, filename: str):
    '''
    将缓存区中原文相匹配的译文写入到新翻译文本中
    '''

    inp = open(new_path, 'r', encoding=get_file_encoding(new_path))
    # todo 读出所有行，文件较大时可能会报错，需优化
    lightSen = inp.readlines()
    inp.close()

    # 临时文本列表，写入文件用
    _tmp_lightSen = copy.copy(lightSen)
    # 原文say
    _old_say = ''
    # 标识符
    _identifier = 'strings'
    # BAP当前缓存量
    _bap_count = 0

    _tmp_idx = -1
    for line in lightSen:
        _tmp_idx += 1
        # 空行
        if PATTERN_EMPTY_LINE.match(line) is not None:
            continue

        # 标志符行
        identifier_match = PATTERN_IDENTIFIER.match(line)
        if identifier_match is not None:
            _identifier = identifier_match.group(1)
            # 进入新的BAP，缓存量+1
            _bap_count += 1
            # 扫描到标志符行，说明进入了新的BAP，原文清空
            # 此步非常重要，避免在没有原文且选择覆盖的情况下出错
            _old_say = ''
            continue

        # 原文本行
        old_say_match = PATTERN_OLD_SAY.match(line)
        if old_say_match is not None and _identifier not in ('', 'strings'):
            _old_say_list = old_say_match.groups()
            # 跳过cv语音行
            if _old_say_list[0] == 'voice':
                continue
            _old_say = _old_say_list[1]
            continue

        # 译文行
        new_say_match = PATTERN_NEW_SAY.match(line)
        if new_say_match is not None and _identifier not in ('', 'strings'):
            _new_say_list = new_say_match.groups()
            _who = _new_say_list[0]
            # 跳过cv语音行
            if _who == 'voice':
                continue

            # 原文say为空时
            if _old_say == '':
                if _new_say_list[1].strip() == '':  # 当译文行为空时，尝试获取已有译文
                    translated_list = read_from_identifier_library_cache(_identifier)
                    if len(translated_list):
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

                if _bap_count >= GLOBAL_DATA['rpy_update_bap_max_cache']:
                    with open(
                        output_path, 'w', encoding=get_file_encoding(output_path)
                    ) as outp:
                        outp.writelines(_tmp_lightSen)
                        outp.close()
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
            # if who_match is not None and who_match.group(1) != '':
            #     original_new_who = who_match.group(1)
            #     _list = read_from_txt_library_cache(original_new_who, 'who')
            #     if len(_list) > 0:
            #         _who = sub(
            #             escape(repr(original_new_who))[1:-1], _list[0], _who, 1
            #         )

            # 以下为原文say不为空时的处理逻辑
            if _new_say_list[1].strip() == '':  # 当译文行为空时，尝试获取已有译文
                translated_list = read_from_identifier_library_cache(_identifier)
                # 如果从identifier_library_cache未匹配到，可以通过标识符在txt_library_cache中再匹配一次
                if len(translated_list) < 1:
                    translated_list = read_from_txt_library_cache(_old_say, _identifier)

                if len(translated_list):
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

            if _bap_count >= GLOBAL_DATA['rpy_update_bap_max_cache']:
                with open(
                    output_path, 'w', encoding=get_file_encoding(output_path)
                ) as outp:
                    outp.writelines(_tmp_lightSen)
                    outp.close()
                # 清空BAP缓存
                _bap_count = 0
            # 当前BAP处理结束，若当前BAP的译文是多行翻译，除第一行外均删除
            _old_say = END_SAY
            continue

        # old行
        old_match = PATTERN_OLD.match(line)
        if old_match is not None and _identifier == 'strings':
            _old_say = old_match.group(1)
            continue

        # new 行
        new_match = PATTERN_NEW.match(line)
        if new_match is not None and _identifier == 'strings':
            if _old_say == '':
                if _bap_count >= GLOBAL_DATA['rpy_update_bap_max_cache']:
                    with open(
                        output_path, 'w', encoding=get_file_encoding(output_path)
                    ) as outp:
                        outp.writelines(_tmp_lightSen)
                        outp.close()
                    # 清空BAP缓存
                    _bap_count = 0
                continue

            original_new_say = new_match.group(1)  # 译文
            # 当译文不为空时，如果覆盖写入，则发出请求
            if original_new_say == '':
                translated_list = read_from_txt_library_cache(_old_say, _identifier)
                if len(translated_list):
                    # strings只可能有一行，所以直接取首位索引值即可
                    _tmp_lightSen[_tmp_idx] = '    new \"' + translated_list[0] + '\"\n'

            if _bap_count >= GLOBAL_DATA['rpy_update_bap_max_cache']:
                with open(
                    output_path, 'w', encoding=get_file_encoding(output_path)
                ) as outp:
                    outp.writelines(_tmp_lightSen)
                    outp.close()
                # 清空BAP缓存
                _bap_count = 0
            _old_say = ''

    if _bap_count > 0:
        with open(output_path, 'w', encoding=get_file_encoding(output_path)) as outp:
            outp.writelines(_tmp_lightSen)
            outp.close()
    print_info(f'{filename} 更新完成！\n')


def write_in_identifier_library_cache(identifier='', translated_txt=''):
    '''
    写入标识符缓存库
    '''

    # 如果标识符为空或who或strings，不写入缓存库
    identifier = identifier.strip()
    if identifier in ('', 'who', 'strings'):
        return

    global _identifier_library_cache
    # 如果译文为空，或译文中含有TODO，不写入缓存库，已写入缓存库的也删除
    if translated_txt.strip() == '' or MARK_TODO in translated_txt:
        if identifier in _identifier_library_cache:
            _identifier_library_cache = del_key_from_dict(
                identifier, _identifier_library_cache
            )
        return

    if identifier not in _identifier_library_cache:
        _identifier_library_cache[identifier] = [translated_txt]
    else:
        _identifier_library_cache[identifier].append(translated_txt)


def write_in_txt_library_cache(
    source_txt='', translated_txt='', identifier='strings'
) -> bool:
    '''
    写入文本缓存库
    '''

    # 如果原文为空，直接返回
    if source_txt.strip() == '':
        return True

    # 如果标识符为空，表明数据非法，直接返回
    identifier = identifier.strip()
    if identifier == '':
        return True

    # 去除首尾空行，who和strings的空行往往都是有意而为，故不剔除
    if identifier not in ('who', 'strings'):
        source_txt = source_txt.strip()

    # 将文本全部转为大写。这里需要判断下原字符串是否含有小写英文字符。
    q_upper = ''
    if has_lower_letter(source_txt):
        q_upper = source_txt.upper()

    global _txt_library_cache
    # 如果译文为空，或译文中含有TODO，不写入缓存库，已写入缓存库的也删除
    if translated_txt.strip() == '' or MARK_TODO in translated_txt:
        if identifier not in ('who', 'strings'):
            if (
                source_txt in _txt_library_cache
                and identifier in _txt_library_cache[source_txt]
            ):
                _txt_library_cache[source_txt] = del_key_from_dict(
                    identifier, _txt_library_cache[source_txt]
                )
            if (
                q_upper
                and q_upper in _txt_library_cache
                and identifier in _txt_library_cache[q_upper]
            ):
                _txt_library_cache[q_upper] = del_key_from_dict(
                    identifier, _txt_library_cache[q_upper]
                )
        return True

    if source_txt not in _txt_library_cache:
        _txt_library_cache[source_txt] = {}
    # 相同文本有可能存在不同标识符，也表示有可能存在不同的翻译，所以要通过标识符进行分别储存
    if identifier not in _txt_library_cache[source_txt]:
        # 译文行存在一条原文对应多条译文的情况，所以这里应该用列表来储存译文
        _txt_library_cache[source_txt][identifier] = [translated_txt]
    else:
        if identifier not in ('who', 'strings'):
            _txt_library_cache[source_txt][identifier].append(translated_txt)

    # 原文本无大写形式时，直接return
    if not q_upper:
        return False

    # 将文本转为大写后再储存一遍，增加匹配成功几率
    if q_upper not in _txt_library_cache:
        _txt_library_cache[q_upper] = {}
    if identifier not in _txt_library_cache[q_upper]:
        _txt_library_cache[q_upper][identifier] = [translated_txt]
    else:
        if identifier not in ('who', 'strings'):
            _txt_library_cache[q_upper][identifier].append(translated_txt)

    return False


def read_from_identifier_library_cache(identifier: str) -> list:
    '''
    从标识符缓存库读取
    '''

    identifier = identifier.strip()
    if identifier in ('', 'who', 'strings'):
        return []

    if _identifier_library_cache is None or not len(_identifier_library_cache):
        return []

    if identifier in _identifier_library_cache:
        txt_list = _identifier_library_cache[identifier]
        for txt in txt_list:
            if txt.startswith(MARK_TODO):
                return []
        return txt_list

    # 当标识符不匹配时，有可能因存在label不同导致标识符不同的情况，将标识符分割获取8位标识符后再匹配一次
    ident = get_identifier(identifier)
    if ident == 'wrong':
        return []

    for key, value in _identifier_library_cache.items():
        cache_ident = get_identifier(key)
        if cache_ident == 'wrong':
            continue
        if ident == cache_ident:
            for tex in value:
                if tex.startswith(MARK_TODO):
                    return []
            return value

    return []


def read_from_txt_library_cache(source_txt: str, identifier: str) -> list:
    '''
    从文本缓存库读取

    1. 直接匹配文本。匹配成功，则根据标识符获取译文；若为找到相应标识符，则选择首位索引下的译文
    2. 将文本所有字母转为大写再进行匹配
    '''

    if source_txt.strip() == '':
        return []

    # 去除首尾空行
    identifier = identifier.strip()
    if identifier == '':
        return []

    if _txt_library_cache is None or not len(_txt_library_cache):
        return []

    # 去除首尾空行，strings下的空行往往都是有意而为，故不剔除
    if identifier != 'strings':
        source_txt = source_txt.strip()

    if source_txt not in _txt_library_cache:
        source_txt = source_txt.upper()
        if source_txt not in _txt_library_cache:
            return []

    li = _txt_library_cache[source_txt]
    if len(li) < 1:
        return []

    if identifier in li:
        txt_list = li[identifier]
        for txt in txt_list:
            if txt.startswith(MARK_TODO):
                return []
        return txt_list

    # 当标识符不匹配时，有可能因存在label不同导致标识符不同的情况，将标识符分割获取8位标识符后再匹配一次
    if identifier not in ('who', 'strings'):
        ident = get_identifier(identifier)
        if ident == 'wrong':
            return []

        for key, value in li.items():
            cache_ident = get_identifier(key)
            if cache_ident == 'wrong':
                continue
            if ident == cache_ident:
                for tex in value:
                    if tex.startswith(MARK_TODO):
                        return []
                return value

    for key, value in li.items():
        succ = True
        for txt in value:
            if txt.startswith(MARK_TODO):
                succ = False
                break
        if not succ:
            continue
        return value

    return []


def get_identifier(ident: str) -> str:
    '''
    获取除“strings”外的8位标识符，标识符有可能是纯字母、纯数字或字母数字。

    将标识符字符串通过“_”分割成多个字符后，一般最后一位便是8位标识符。
    但同时也存在多个文本相同且都在同一个label语句中的情况，Ren'Py会在标识符行末尾添加一个递增数字来加以区分，此时倒数第二位才是8位标识符。

    如果标识符不是“strings”，且长度不符合标准标识符的位数，那么说明该标识符可能出现了错误，不处理该数据。
    '''
    ident = ident.strip()
    if ident == '':
        return 'wrong'

    ident_split = ident.split('_')
    if len(ident_split) <= 1:
        return ident

    # 末尾值要么是标识符，要么是递增数字，先获取它
    identifier_last = ident_split[-1]

    # 递增数字长度达到8的几率可以忽略不计，故可以认为只要长度等于8，便是我们要找的8位标识符，直接返回结果
    if len(identifier_last) == 8:
        return identifier_last

    # 如果不是纯数字，或长度大于2（文本中出现两位数以上的相同标识符的可能性微乎其微），则将其归为错误数据，返回错误标记
    if not is_int(identifier_last) or len(identifier_last) > 2:
        return 'wrong'

    # 如果是纯数字，则大概率是递增数字，此时我们获取倒数第二位
    identifier = ident_split[-2]
    # 如果倒数第二位的长度依然不等于8，则将其归为错误数据，返回错误标记
    if len(identifier) != 8:
        return 'wrong'

    # 返回8位标识符+递增数字
    return identifier + '_' + identifier_last


def input_path(folder_type='OLD', reselect=False):
    '''
    输入待翻文件/文件夹的绝对路径
    '''

    global _old_abspath, _new_abspath, _output_abspath

    if not reselect:
        inp = ''
        if folder_type == 'OLD':
            # 若存在默认路径
            if _old_abspath != '':
                # 若路径不存在，重新手动输入
                if not os.path.exists(_old_abspath):
                    print_err('config.ini配置的旧翻译文本路径不存在！\n')
                    _old_abspath = ''
                    input_path(folder_type)
                    return

                print_info('路径验证成功！\n')
                return

            inp = input('请输入旧翻译文本的绝对路径：').strip()
            # 输入为空，重新输入
            if inp == '':
                input_path(folder_type, True)
                return
            # 规范路径，不调整大小写
            inp = os.path.normpath(inp)
            # 若路径不存在，重新输入
            if not os.path.exists(inp):
                input_path(folder_type, True)
                return
            _old_abspath = inp
            print_info('路径验证成功！\n')

        elif folder_type == 'NEW':
            # 若存在默认路径
            if _new_abspath != '':
                # 若路径不存在，则重新手动输入
                if not os.path.exists(_new_abspath):
                    print_err('config.ini配置的新翻译文本路径不存在！\n')
                    _new_abspath = ''
                    input_path(folder_type)
                    return

                _output_abspath = verify_path(_new_abspath, _output_abspath)
                return

            inp = input('请输入新翻译文本的绝对路径：').strip()
            # 输入为空，重新输入
            if inp == '':
                input_path(folder_type, True)
                return
            # 规范路径，不调整大小写
            inp = os.path.normpath(inp)
            # 若路径不存在，重新输入
            if not os.path.exists(inp):
                input_path(folder_type, True)
                return
            _new_abspath = inp
            _output_abspath = verify_path(_new_abspath, _output_abspath)
        return

    tmp = input('不存在该路径，请重新输入正确的路径或回车关闭程序：').strip()
    # 输入为空，退出程序
    if tmp == '':
        sys.exit(0)
    # 规范路径，不调整大小写
    tmp = os.path.normpath(tmp)
    # 若路径不存在，重新输入
    if not os.path.exists(tmp):
        input_path(folder_type, True)
        return

    if folder_type == 'OLD':
        _old_abspath = tmp
        print_info('路径验证成功！\n')
    else:
        _new_abspath = tmp
        _output_abspath = verify_path(_new_abspath, _output_abspath)


def verify_path(new_abspath: str, output_abspath: str) -> str:
    '''
    验证待翻文本路径和目标路径是否正确

    :param new_abspath: 待翻译文本路径
    :param output_abspath: 新翻译文本路径
    '''

    # 如果输入路径是文件夹
    if os.path.isdir(new_abspath):
        # 输出路径也生成文件夹
        output_abspath = new_abspath + '-new'
        # 如果输出文件夹已存在，先将其更名，再新建空文件夹
        if os.path.exists(output_abspath):
            os.rename(
                output_abspath,
                output_abspath + '_' + datetime.now().strftime('%Y_%m_%d_%H_%M_%S'),
            )
        os.makedirs(output_abspath)

    # 如果输入路径是文件
    elif os.path.isfile(new_abspath):
        _inp = os.path.splitext(new_abspath)
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
    return output_abspath


def _select_serial_num(reselect=False, serial_num=''):
    '''
    输入序号选择对应的操作
    '''

    if not reselect:
        print(
            '''1) 更新翻译文本
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

    print(
        r'''
===========================================================================================
                                 Ren'Py 翻译文本更新工具
                                      作者：Phoenix
                                      版权归作者所有
                            PS：本工具所有操作均不会影响原文件！
===========================================================================================
'''
    )

    _select_serial_num()

    input_path('OLD')
    input_path('NEW')

    print('正在更新翻译文本中，请稍候……\n')
    walk_file()
    print_info('翻译文本更新已完成！')
    sys.exit(0)
