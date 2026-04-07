#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-10 23:33:35
"""

import time

from src.exception.tool_exception import ToolException
from src.utils.utils import print_err, validate_lang


class BaseTranslation(object):
    """
    翻译引擎的基础类
    """

    def __init__(
        self,
        *,
        section="",
        activated=False,
        max_qps=1,
        max_char=2000,
        comment_langs=(),
        from_langs=(),
        to_langs=(),
    ):
        # 翻译接口配置文件中的节点名称
        self._section = section
        # 翻译接口是否已激活
        self._activated = activated
        # api请求频率。次/每秒
        self._max_qps = max_qps
        # 当前令牌数，初始等于最大申请频率
        self._tokens = max_qps
        # 最新补充令牌时间
        self._last_refill = time.time()
        # 单次请求最大字符数
        self._max_char = max_char

        # 所有支持的语种简写表
        self.__api_comment_langs = comment_langs
        # 所有支持的源语种表
        self.__api_from_langs = from_langs
        # 常见目标语种表
        self.__api_to_langs = to_langs

    def translate(self) -> str:
        pass

    def get_max_qps(self) -> int:
        """
        获取请求频率
        """
        return self._max_qps

    def get_from_langs(self) -> tuple:
        """
        获取源语种表
        """
        return self.__api_from_langs

    def get_to_langs(self) -> tuple:
        """
        获取目标语种表
        """
        return self.__api_to_langs

    def is_ready(self) -> bool:
        """
        查询翻译引擎是否就绪
        """
        return self._activated

    def check_text_and_lang(self, source_txt, from_lang="", to_lang="") -> str:
        """
        校验文本长度、源语种和目标语种是否符合API要求
        传入的源语种不在支持范围内，会尝试通过文本识别语种，再校验一次
        如果校验不通过，会返回空值，校验通过，返回from_lang

        :param source_txt: 待翻译文本
        :param from_lang: 源语种
        :param to_lang: 目标语种
        """

        try:
            # 当目标语种等于源语种时，手动抛出异常
            if to_lang.casefold() == from_lang.casefold():
                raise ToolException("TranslationAPIErr", "传入的目标语种和源语种相同！")

            # 当源语言不在受支持的语种范围内时
            if not any(
                lang.casefold() == from_lang.casefold()
                for lang in self.__api_comment_langs
            ):
                # 尝试获取源文本语种，然后再次判断，若依旧不符合，手动抛出异常
                from_lang = validate_lang(source_txt)
                if not any(
                    lang.casefold() == from_lang.casefold()
                    for lang in self.__api_comment_langs
                ):
                    raise ToolException(
                        "TranslationAPIErr", "源语言语种不在受支持的语种范围内！"
                    )

            # 当源语言不在受支持的语种范围内时，手动抛出异常
            if not any(
                lang.casefold() == to_lang.casefold()
                for lang in self.__api_comment_langs
            ):
                raise ToolException(
                    "TranslationAPIErr", "传入的目标语言语种不在受支持的语种范围内！"
                )

            # 原文本长度超过API限制
            if isinstance(source_txt, str) and len(source_txt) > self._max_char:
                raise ToolException("TranslationAPIErr", "文本长度超过翻译引擎限制！")
        except ToolException as e:
            from_lang = ""
            print_err(str(e))
        finally:
            return from_lang
