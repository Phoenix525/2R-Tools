#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@Author: Phoenix
@Date: 2020-08-10 23:33:35
'''


import copy
import sys

from prettytable import PrettyTable

from modules.utils import (GLOBAL_DATA, MARK_TODO, get_value_from_library,
                           is_valid_index, print_err, to_int)

# 翻译引擎表，接口名称务必要和GLOBAL_DATA里一致
APIS = (
    ('tencent', '传统机翻：腾讯翻译（每月免费500W字符）'),
    ('baidu', '传统机翻：百度翻译（高级版每月免费100W字符）'),
    ('caiyun', '传统机翻：彩云小译（新用户免费100W字符，有效期一月）'),
    ('deepL', '传统机翻：DeepL翻译（免费版每月免费50W字符，注册需非大陆信用卡）'),
    ('google', '传统机翻：谷歌翻译（第三方，已失效）'),
    ('huoshan', '传统机翻：火山翻译（每月免费200W字符）'),
    ('xiaoniu', '传统机翻：小牛翻译（每日免费20W字符）'),
    ('xunfei', '传统机翻：讯飞翻译（新用户免费200W字符，有效期一年）'),
    ('youdao', '传统机翻：有道智云（新用户免费100W字符）'),
    (
        'ollama',
        '本地AI翻译：基于Ollama框架，可切换多种模型（完全免费，部署难度小，运行速度快）',
    ),
    (
        'hunyuan_mt',
        '本地AI翻译：基于Transformers库，调用Hunyuan-MT模型（完全免费，部署难度中，运行速度较慢）',
    ),
)


class Interpreter:
    '''
    翻译器
    '''

    def __init__(self, *, api_name=''):

        # 从翻译引擎表获取引擎名称表
        self.__api_names = self.__list_api_names()

        # 当前调用的翻译引擎
        self.__curr_api = None

        # 当前调用翻译引擎的名称
        self.__curr_api_name = ''

        # 源语种
        self._from_lang = 'auto'
        # 目标语种
        self._to_lang = 'zh'

        # 初始化翻译器时如果传入了合法翻译引擎名称，则直接实例化相应翻译引擎
        if api_name in self.__api_names:
            self.__curr_api_name = api_name
            self.__get_interpreter()
        # 反之进入翻译引擎选择列表
        else:
            self.__select_api_type()

    def translate_txt(
        self, source_txt='', *, open_todo=False, activate_context='-1'
    ) -> str:
        '''
        翻译文本

        所有可能出现的异常要在此函数处理完毕，并一定有返回值。

        - source_txt: 输入文本
        - open_todo: 是否在句首添加TODO标记，默认由config配置
        - activate_context: 是否启用上下文
        '''

        if not source_txt.strip():
            return ''

        print(f'原文：{source_txt}')

        # 先从译文库中查找，如果有则直接取值返回
        translated = get_value_from_library(source_txt)
        if translated:
            return translated

        try:
            translated = self.__curr_api.translate(
                source_txt,
                self._to_lang,
                from_lang=self._from_lang,
                activate_context=activate_context,
            )
            print(f'译文：{translated}\n')
            if open_todo and translated:
                translated = MARK_TODO + translated
        except Exception as e:
            translated = ''
            print_err(f'{str(e)}')
        return translated

    def translate_txt_dict(
        self, source_txt_dict=None, *, open_todo=False, activate_context='-1'
    ) -> dict:
        '''
        翻译文本字典

        - source_txt_dict: 输入文本
        - open_todo: 是否在句首添加TODO标记，默认由config配置
        - activate_context: 是否启用上下文
        '''

        if (
            source_txt_dict is None
            or not isinstance(source_txt_dict, dict)
            or len(source_txt_dict) < 1
        ):
            return None

        tmp_source_txt = copy.deepcopy(source_txt_dict)
        for key, text in tmp_source_txt.items():
            print(f'原文：{text}')

            # 先从译文库中查找，如果有则直接取值返回
            translated = get_value_from_library(text)
            if translated:
                tmp_source_txt[key] = translated
                continue

            try:
                translated = self.__curr_api.translate(
                    text,
                    self._to_lang,
                    from_lang=self._from_lang,
                    activate_context=activate_context,
                )
                print(f'译文：{translated}\n')
                if open_todo and translated:
                    translated = MARK_TODO + translated
            except Exception as e:
                translated = ''
                print_err(f'{str(e)}')

            tmp_source_txt[key] = translated
        return tmp_source_txt

    def translate_txt_list(
        self, source_txt_list: list, *, open_todo=False, activate_context='-1'
    ) -> list:
        '''
        翻译文本列表

        - source_txt_list: 输入文本
        - open_todo: 是否在句首添加TODO标记，默认由config配置
        - activate_context: 是否启用上下文
        '''

        if (
            source_txt_list is None
            or not isinstance(source_txt_list, list)
            or len(source_txt_list) < 1
        ):
            return None

        tmp_source_txt_list = []
        for text in source_txt_list:
            print(f'原文：{text}')
            # 先从译文库中查找，如果有则直接取值返回
            translated = get_value_from_library(text)
            if translated:
                tmp_source_txt_list.append(translated)
                continue

            try:
                translated = self.__curr_api.translate(
                    text,
                    self._to_lang,
                    from_lang=self._from_lang,
                    activate_context=activate_context,
                )
                print(f'译文：{translated}\n')
                if open_todo and translated:
                    translated = MARK_TODO + translated
            except Exception as e:
                translated = ''
                print_err(f'{str(e)}')

            tmp_source_txt_list.append(translated)
        return tmp_source_txt_list

    def clear_api_datas(self):
        '''
        清空翻译引擎相关数据
        '''
        self.__curr_api = None
        self.__curr_api_name = ''

    def __list_api_names(self) -> list:
        '''
        获取所有翻译引擎名称并组成列表
        '''
        lst = []
        for item in APIS:
            lst.append(item[0])
        return lst

    def __get_interpreter(self):
        '''
        实例化翻译引擎
        '''

        match self.__curr_api_name:
            # 腾讯翻译
            case 'tencent':
                from modules.translation_api.tencent import TencentTranslation

                self.__curr_api = TencentTranslation()
            # 百度翻译
            case 'baidu':
                from modules.translation_api.baidu import BaiduTranslation

                self.__curr_api = BaiduTranslation()
            # 彩云小译
            case 'caiyun':
                from modules.translation_api.caiyun import CaiyunTranslation

                self.__curr_api = CaiyunTranslation()
            # DeepL翻译
            case 'deepL':
                from modules.translation_api.deepL import DeepLTranslation

                self.__curr_api = DeepLTranslation()
            # 谷歌翻译
            case 'google':
                from modules.translation_api.google import GoogleTranslation

                self.__curr_api = GoogleTranslation()
            # 火山翻译
            case 'huoshan':
                from modules.translation_api.huoshan import HuoshanTranslation

                self.__curr_api = HuoshanTranslation()
            # 小牛翻译
            case 'xiaoniu':
                from modules.translation_api.xiaoniu import XiaoNiuTranslation

                self.__curr_api = XiaoNiuTranslation()
            # 讯飞翻译
            case 'xunfei':
                from modules.translation_api.xunfei import XunFeiTranslation

                self.__curr_api = XunFeiTranslation()
            # 有道智云
            case 'youdao':
                from modules.translation_api.youdao import YoudaoTranslation

                self.__curr_api = YoudaoTranslation()
            # Ollama平台
            case 'ollama':
                from modules.translation_api.ai_ollama import OllamaTranslation

                self.__curr_api = OllamaTranslation()
            # 腾讯Hunyuan-MT
            case 'hunyuan_mt':
                from modules.translation_api.ai_hunyuan_mt import \
                    HunYuanMTTranslation

                self.__curr_api = HunYuanMTTranslation()
            case _:
                self.__curr_api = None

        if self.__curr_api is None:
            self.clear_api_datas()
            return self.__select_api_type()

        self.__select_lang_type()

    def __select_api_type(self, first_select=True, serial_num=1, *, api_titles=[]):
        '''
        选择翻译引擎

        - first_select: 是否首次进入选择列表
        - serial_num: 选中的翻译引擎序号
        - api_titles: 可选参数。翻译引擎标题列表，用于输出供用户查看
        '''

        # 首次进入选择列表
        if first_select:
            str_api = '''
翻译引擎列表如下：
'''
            for idx, item in enumerate(APIS):
                title = item[1]
                if GLOBAL_DATA[f'{item[0]}'] is False:
                    title += ' (未启用)'
                str_api += f'{idx + 1}) {title}\n'
                api_titles.append(title)
            print(str_api)

            _inp = input(f'请选择翻译引擎，直接回车默认选1：').strip()
            # 如果输入为空，则选择默认引擎
            if _inp == '':
                print(
                    f'''
===========================================================================================
当前翻译引擎：【{api_titles[0]}】'''
                )
                self.__curr_api_name = self.__api_names[0]
                # 实例化翻译器
                self.__get_interpreter()
                return

            _serial_inp = to_int(_inp)
            # 如果输入序号不在列表中，重新进入选择
            if not is_valid_index(self.__api_names, _serial_inp - 1, False):
                self.__select_api_type(False, _serial_inp, api_titles=api_titles)
                return

            # 若翻译引擎未启用则重新选择
            if GLOBAL_DATA[f'{self.__api_names[_serial_inp - 1]}'] is False:
                self.__select_api_type(False, _serial_inp, api_titles=api_titles)
                return

            print(
                f'''
===========================================================================================
当前翻译引擎：【{api_titles[_serial_inp - 1]}】'''
            )
            self.__curr_api_name = self.__api_names[_serial_inp - 1]
            # 实例化翻译器
            self.__get_interpreter()
            return

        # 再次进入选择列表
        prin = (
            f'翻译引擎列表中不存在序号 {serial_num}，请重新输入正确序号或回车退出程序：'
        )
        if is_valid_index(self.__api_names, serial_num - 1, False):
            if GLOBAL_DATA[f'{self.__api_names[serial_num - 1]}'] is False:
                prin = '当前翻译引擎未启用，请重新输入正确序号或回车退出程序：'
        _tmp = input(prin).strip()
        if _tmp == '':
            sys.exit(0)

        _serial_tmp = to_int(_tmp)
        if not is_valid_index(self.__api_names, _serial_tmp, False):
            self.__select_api_type(False, _serial_tmp, api_titles=api_titles)
            return

        # 若翻译引擎未启用则重新选择
        if GLOBAL_DATA[f'{self.__api_names[_serial_tmp - 1]}'] is False:
            self.__select_api_type(False, _serial_tmp, api_titles=api_titles)
            return

        print(
            f'''
===========================================================================================
当前翻译引擎：【{api_titles[_serial_tmp - 1]}】'''
        )

        self.__curr_api_name = self.__api_names[_serial_tmp - 1]
        # 实例化翻译器
        self.__get_interpreter()

    def __select_lang_type(self, first_select=True, serial_num='', *, target_langs=()):
        '''
        选择目标语种

        - first_select: 是否为首次选择
        - serial_num: 选定的操作序号
        - target_langs 语种表
        '''

        if first_select:
            # 获取目标语种
            curr_langs = self.__curr_api.get_to_langs()

            table_header = (
                " 序号  ",
                " 语种名称  ",
                " 序号 ",
                " 语种名称 ",
                " 序号",
                " 语种名称",
                "  序号 ",
                "  语种名称 ",
            )
            header_length = len(table_header)
            table = PrettyTable(table_header)
            _row = []
            for idx, value in enumerate(curr_langs):
                _row.append(idx + 1)
                _row.append(value[0])
                if (idx + 1) % (header_length / 2) == 0:
                    # 添加数据行
                    table.add_row(_row)
                    _row = []
                    continue
                if idx == len(curr_langs) - 1 and len(_row) % header_length != 0:
                    for _ in range(header_length - len(_row)):
                        _row.append('')
                    # 添加数据行
                    table.add_row(_row)
            print(table)

            default = 0
            _inp = input(f'请选择目标语种序号，直接回车默认选 {default + 1}：').strip()
            if _inp == '':
                print(
                    f'''
===========================================================================================
当前目标语种：【{curr_langs[default][0]}】'''
                )
                self._to_lang = curr_langs[default][-1]
                return

            _inp_serial = to_int(_inp) - 1
            if _inp_serial < 0 or _inp_serial >= len(curr_langs):
                self.__select_lang_type(False, _inp, target_langs=curr_langs)
                return

            print(
                f'''
===========================================================================================
当前目标语种：【{curr_langs[_inp_serial][0]}】'''
            )
            self._to_lang = curr_langs[_inp_serial][-1]
            return

        _tmp = input(
            f'语种列表中不存在序号 {serial_num}，请重新输入正确序号或回车退出程序：'
        ).strip()
        if _tmp == '':
            sys.exit(0)

        # 输入的序号转换成整型
        _tmp_serial = to_int(_tmp) - 1
        if _tmp_serial < 0 or _tmp_serial >= len(target_langs):
            self.__select_lang_type(False, _tmp, target_langs=target_langs)
            return

        print(
            f'''
===========================================================================================
当前目标语种：【{target_langs[_tmp_serial][0]}】'''
        )
        self._to_lang = target_langs[_tmp_serial][-1]
