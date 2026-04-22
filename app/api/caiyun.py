#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from json import dumps, loads

from requests import request

from app.api.base_translation import BaseTranslation
from app.exception.tool_exception import ToolException
from app.utils.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from app.utils.utils import (
    acquire_token,
    enpun_2_zhpun,
    print_err,
    read_config,
    remove_escapes,
)


class CaiyunTranslation(BaseTranslation):
    """
    彩云小译翻译引擎
    """

    def __init__(self, section="caiyun"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_CAIYUN_COMMON_LANGS,
            from_langs=_CAIYUN_FROM_LANGS,
            to_langs=_CAIYUN_TO_LANGS,
        )
        self.__token: str = ""

        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        """
        开始翻译，必定有返回值

        :param source_txt: 输入文本
        :param to_lang: 目标语种
        :param **kwargs: 其他参数
        """

        # 删除转义符
        source_txt = remove_escapes(source_txt)
        # 源文本语种
        from_lang = kwargs.get("from_lang", "auto")
        # 校验文本及语种是否符合要求，不符合则直接返回空值
        from_lang = self.check_text_and_lang(source_txt, from_lang, to_lang)
        if not from_lang:
            return ""

        # 删除转义符
        source_txt = remove_escapes(source_txt)
        payload = {
            "source": [source_txt],
            "trans_type": from_lang + "2" + to_lang,
            "request_id": "demo",
            "detect": from_lang == "auto",
        }
        headers = {
            "content-type": "application/json",
            "x-authorization": "token " + self.__token,
        }

        # 重试次数
        # retry = kwargs.get('retry', 3)

        # 获取令牌，未获取到时自动等待
        self._tokens, self._last_refill = acquire_token(
            self._max_qps, self._tokens, self._last_refill
        )

        try:
            response = request(
                "POST",
                "http://api.interpreter.caiyunai.com/v1/translator",
                data=dumps(payload),
                headers=headers,
            )
            text = loads(response.text)
            target = ""
            if "target" in text:
                target = text["target"][0]
                # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
                # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
                target = target.encode("utf-8", "replace").decode("utf-8")
                target = enpun_2_zhpun(target)
            else:
                err_msg = text["message"]
                raise ToolException("APIRequestErr", f"{err_msg}")
        except Exception as e:
            print_err(f"翻译引擎出现异常！请检查报错信息：{str(e)}")
        finally:
            return target

    def is_ready(self) -> bool:
        """
        查询翻译引擎是否就绪
        """

        if not self.__check_pass():
            self._activated = False
        return self._activated

    def __check_pass(self) -> bool:
        """
        检查API密钥是否配置
        """

        if self.__token:
            return True

        inp = self.input_what_we_need(
            length=20,
            prompt="未配置token！请输入（敏感内容不显示）或回车返回引擎列表：",
        )
        if inp in ("", "\r", "\n"):
            return False
        self.__token = inp

        store = SimpleKeyStore(SimpleAPIKeyEncryptor("caiyun_api_tokens"))
        store.add_keys(self._section, {"token": inp})
        return True

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_key = conf.get(self._section, "token")
        if enc_key:
            api_keys["token"] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor("caiyun_api_tokens"), api_keys)
        self.__token = store.get_key("token")

        self._activated = conf.getboolean(self._section, "activate")
        self._max_qps = conf.getint(self._section, "max_qps")
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, "max_char")
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_CAIYUN_COMMON_LANGS = (
    "auto",
    "zh",
    "zh-Hant",
    "en",
    "ja",
    "ko",
    "de",
    "ru",
    "fr",
    "pt",
    "tr",
    "es",
    "it",
    "vi",
)

# 所有支持的源语种表
_CAIYUN_FROM_LANGS = (
    ("自动检测", "auto"),
    ("中文", "zh"),
    ("繁体中文", "zh-Hant"),
    ("英语", "en"),
    ("日语", "ja"),
    ("韩语", "ko"),
    ("德语", "de"),
    ("俄语", "ru"),
    ("法语", "fr"),
    ("葡萄牙语", "pt"),
    ("土耳其语", "tr"),
    ("西班牙语", "es"),
    ("意大利语", "it"),
    ("越南语", "vi"),
)

# 常见目标语种表
_CAIYUN_TO_LANGS = (
    ("中文", "zh"),
    ("繁体中文", "zh-Hant"),
    ("英语", "en"),
    ("日语", "ja"),
    ("韩语", "ko"),
)
