#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-10 23:33:35
"""

from time import time

from app.exception.tool_exception import ToolException
from app.utils.utils import (
    get_password_with_mask,
    is_all_digits,
    is_letters_and_digits,
    is_uuid_v1,
    print_err,
    validate_lang,
)


class ValidateStringsType:
    """
    字符串校验类型
    """

    # 全数字 0-9
    STRING_NUM = "STRING_NUM"
    # 大小写英文字母和数字 A-Za-z0-9
    STRING_LETTER_NUM = "STRING_LETTER_NUM"
    # 36位标准UUID
    STRING_UUID = "STRING_UUID"
    # 特殊：火山翻译
    STRING_HUOSHAN = "STRING_HUOSHAN"


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
        comment_langs: tuple[str] = (),
        from_langs: tuple[tuple[str]] = (),
        to_langs: tuple[tuple[str]] = (),
    ):
        # 翻译接口配置文件中的节点名称
        self._section: str = section
        # 翻译接口是否已激活
        self._activated: bool = activated
        # api请求频率。次/每秒
        self._max_qps: int = max_qps
        # 当前令牌数，初始等于最大申请频率
        self._tokens: int = max_qps
        # 最新补充令牌时间
        self._last_refill: float = time()
        # 单次请求最大字符数
        self._max_char: int = max_char

        # 所有支持的语种简写表
        self.__api_comment_langs: tuple[str] = comment_langs
        # 所有支持的源语种表
        self.__api_from_langs: tuple[tuple[str]] = from_langs
        # 常见目标语种表
        self.__api_to_langs: tuple[tuple[str]] = to_langs

    def translate(self) -> str:
        pass

    def get_max_qps(self) -> int:
        """
        获取请求频率
        """
        return self._max_qps

    def get_from_langs(self) -> tuple[tuple[str]]:
        """
        获取源语种表
        """
        return self.__api_from_langs

    def get_to_langs(self) -> tuple[tuple[str]]:
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

    def input_what_we_need(
        self,
        length: int,
        first_config=True,
        *,
        validate_type=ValidateStringsType.STRING_LETTER_NUM,
        prompt="请输入：",
    ) -> str:
        """
        输入密钥，并验证是否合法，合法返回字串，反之返回空值

        :param length: 指定检查长度
        :param first_config: 首次调用函数
        :param validate_type: 验证类型。不同api的密钥组成方式或有不同，不同的密钥根据指定的类型来验证
        :param prompt: 控制台显示提示语
        """

        if not first_config:
            prompt = "参数输入不正确，请重新输入或回车返回引擎列表："

        inp = get_password_with_mask(prompt)
        if inp in ("", "\r", "\n"):
            return ""

        validated = False
        match validate_type:
            case ValidateStringsType.STRING_LETTER_NUM:
                validated = is_letters_and_digits(inp, length)
            case ValidateStringsType.STRING_NUM:
                validated = is_all_digits(inp, length)
            case ValidateStringsType.STRING_UUID:
                # 免费版
                if len(inp) == length:
                    validated = inp.endswith(":fx") and is_uuid_v1(inp[:-3])
                # pro付费版
                elif len(inp) == length - 3:
                    validated = is_uuid_v1(inp)
            case ValidateStringsType.STRING_HUOSHAN:
                validated = inp.endswith("==") and is_letters_and_digits(inp, length)

        if not validated:
            return self.input_what_we_need(length, False, validate_type=validate_type)
        return inp
