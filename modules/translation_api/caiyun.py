#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
from configparser import ConfigParser
from json import dumps, loads

from requests import request

from modules.exception.tool_exception import ToolException
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import (BASE_ABSPATH, acquire_token, check_langs,
                           get_file_encoding, print_err, remove_escape)


class CaiyunTranslation(BaseTranslation):
    '''
    彩云小译翻译引擎
    '''

    def __init__(self, *, section='caiyun_api'):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_CAIYUN_COMMON_LANGS,
            from_langs=_CAIYUN_FROM_LANGS,
            to_langs=_CAIYUN_TO_LANGS,
        )
        self.__token = ''
        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        '''
        开始翻译

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        '''

        # 源文本语种
        from_lang = kwargs.get('from_lang', 'auto')
        # 由于彩云源语言无法使用auto，故在此检测语言语种
        if from_lang == 'auto':
            from_lang = check_langs(source_txt).lower()
        if not self.check_from_and_to(from_lang, to_lang):
            return ''

        # 删除转义符
        source_txt = remove_escape(source_txt)
        # 原文本长度超过API限制
        if len(source_txt) > self._max_char:
            raise ToolException(
                'TranslationAPIErr', '文本长度超过API限制，跳过本条语句！'
            )

        # 删除转义符
        source_txt = remove_escape(source_txt)
        payload = {
            'source': [source_txt],
            'trans_type': from_lang + '2' + to_lang,
            'request_id': 'demo',
            'detect': from_lang == 'auto',
        }
        headers = {
            'content-type': "application/json",
            'x-authorization': "token " + self.__token,
        }

        # 重试次数
        # retry = kwargs.get('retry', 3)

        # 获取令牌，未获取到时自动等待
        self._tokens, self._last_refill = acquire_token(
            self._max_qps, self._tokens, self._last_refill
        )

        try:
            response = request(
                'POST',
                'http://api.interpreter.caiyunai.com/v1/translator',
                data=dumps(payload),
                headers=headers,
            )
            return loads(response.text)['target'][0]
        except Exception as e:
            raise ToolException(
                'TranslationAPIErr', f'翻译引擎出现异常！请查看报错信息：{str(e)}'
            )

    def is_ready(self) -> bool:
        '''
        查询翻译引擎是否就绪
        '''

        if not self.__check_pass():
            self._activated = False
        return self._activated

    def __check_pass(self):
        '''
        检查API密钥是否配置
        '''

        def _check():
            if self.__token == '':
                raise ToolException(
                    'TranslationAPIErr', '彩云小译启动失败，未配置token！'
                )

        try:
            _check()
        except ToolException as e:
            print_err(f'翻译引擎调用异常：{str(e)}')
            return False
        else:
            return True

    def __get_config(self):
        '''
        获取配置
        '''

        config_path = os.path.join(BASE_ABSPATH, 'config.ini')
        if not os.path.isfile(config_path):
            return

        conf = ConfigParser()  # 调用读取配置模块中的类
        conf.optionxform = lambda option: option
        conf.read(config_path, encoding=get_file_encoding(config_path))

        self._activated = conf.getboolean(self._section, 'activate')
        self.__token = conf.get(self._section, 'token')
        self._max_qps = conf.getint(self._section, 'max_qps')
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, 'max_char')
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_CAIYUN_COMMON_LANGS = (
    'auto',
    'zh',
    'zh-Hant',
    'en',
    'ja',
    'ko',
    'de',
    'ru',
    'fr',
    'pt',
    'tr',
    'es',
    'it',
    'vi',
)

# 所有支持的源语种表
_CAIYUN_FROM_LANGS = (
    ('自动检测', 'auto'),
    ('中文', 'zh'),
    ('繁体中文', 'zh-Hant'),
    ('英语', 'en'),
    ('日语', 'ja'),
    ('韩语', 'ko'),
    ('德语', 'de'),
    ('俄语', 'ru'),
    ('法语', 'fr'),
    ('葡萄牙语', 'pt'),
    ('土耳其语', 'tr'),
    ('西班牙语', 'es'),
    ('意大利语', 'it'),
    ('越南语', 'vi'),
)

# 常见目标语种表
_CAIYUN_TO_LANGS = (
    ('中文', 'zh'),
    ('繁体中文', 'zh-Hant'),
    ('英语', 'en'),
    ('日语', 'ja'),
    ('韩语', 'ko'),
)
