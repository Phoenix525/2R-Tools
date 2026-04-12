#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import base64
import json

from xfyunsdknlp.translate_client import TranslateClient

from src.api.base_translation import BaseTranslation
from src.utils.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from src.utils.utils import (
    acquire_token,
    enpun_2_zhpun,
    print_err,
    read_config,
    remove_escapes,
)


class XunFeiTranslation(BaseTranslation):
    """
    讯飞翻译引擎
    """

    def __init__(self, section="xunfei"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_XUNFEI_COMMON_LANGS,
            from_langs=_XUNFEI_FROM_LANGS,
            to_langs=_XUNFEI_TO_LANGS,
        )
        self.__app_id = ""
        self.__api_secret = ""
        self.__api_key = ""
        # 翻译接口客户端
        self.__client = None

        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        """
        开始翻译，必定有返回值

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        """

        if self.__client is None:
            print_err("API客户端未实例化！")
            return ""

        # 删除转义符
        source_txt = remove_escapes(source_txt)
        # 源文本语种
        from_lang = kwargs.get("from_lang", "auto")
        # 校验文本及语种是否符合要求，不符合则直接返回空值
        from_lang = self.check_text_and_lang(source_txt, from_lang, to_lang)
        if not from_lang:
            return ""

        # 重试次数
        # retry = kwargs.get('retry', 3)
        # for attempt in range(retry):
        # 获取令牌，未获取到时自动等待
        self._tokens, self._last_refill = acquire_token(
            self._max_qps, self._tokens, self._last_refill
        )
        try:
            target = ""
            resp = self.__client.send_ist_v2(source_txt, from_lang, to_lang)
            json_resp = json.loads(resp)
            if json_resp["header"]["code"] == 0:
                result = json_resp["payload"]["result"]["text"]
                fd = ast.literal_eval(base64.b64decode(result).decode("utf-8"))
                target = fd["trans_result"]["dst"]
                # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
                # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
                target = target.encode("utf-8", "replace").decode("utf-8")
                target = enpun_2_zhpun(target)
        except Exception as e:
            print_err(f"翻译引擎出现异常！请查看报错信息：{str(e)}")
        finally:
            return target

    def is_ready(self) -> bool:
        """
        查询翻译引擎是否就绪
        """

        if not self.__check_pass():
            self._activated = False
        else:
            # 实例化客户端
            self.__client = self.__init_client()
        return self._activated

    def __check_pass(self) -> bool:
        """
        检查API密钥是否配置
        """

        if self.__app_id and self.__api_secret and self.__api_key:
            return True

        keys = {}
        if not self.__app_id:
            inp = self.input_what_we_need(
                length=8,
                prompt="未配置APPID！请输入（敏感内容不显示）或回车返回引擎列表：",
            )
            if inp in ("", "\r", "\n"):
                return False
            self.__app_id = keys["APPID"] = inp
        if not self.__api_secret:
            inp = self.input_what_we_need(
                length=32,
                prompt="未配置APISecret！请输入（敏感内容不显示）或回车返回引擎列表：",
            )
            if inp in ("", "\r", "\n"):
                return False
            self.__api_secret = keys["APISecret"] = inp
        if not self.__api_key:
            inp = self.input_what_we_need(
                length=32,
                prompt="未配置APIKey！请输入（敏感内容不显示）或回车返回引擎列表：",
            )
            if inp in ("", "\r", "\n"):
                return False
            self.__api_key = keys["APIKey"] = inp

        store = SimpleKeyStore(SimpleAPIKeyEncryptor("xunfei_api_tokens"))
        store.add_keys(self._section, keys)
        return True

    def __init_client(self) -> TranslateClient:
        """
        初始化客户端
        """
        client = TranslateClient(
            app_id=self.__app_id, api_key=self.__api_key, api_secret=self.__api_secret
        )
        return client

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_key = conf.get(self._section, "APPID")
        if enc_key:
            api_keys["APPID"] = enc_key
        enc_key = conf.get(self._section, "APISecret")
        if enc_key:
            api_keys["APISecret"] = enc_key
        enc_key = conf.get(self._section, "APIKey")
        if enc_key:
            api_keys["APIKey"] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor("xunfei_api_tokens"), api_keys)
        self.__app_id = store.get_key("APPID")
        self.__api_secret = store.get_key("APISecret")
        self.__api_key = store.get_key("APIKey")

        self._activated = conf.getboolean(self._section, "activate")
        self._max_qps = conf.getint(self._section, "max_qps")
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, "max_char")
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_XUNFEI_COMMON_LANGS = (
    "am",
    "az",
    "ar",
    "ga",
    "et",
    "be",
    "bg",
    "pl",
    "fa",
    "nb",
    "da",
    "de",
    "ru",
    "fr",
    "tl",
    "fi",
    "km",
    "ka",
    "yue",
    "ha",
    "nl",
    "cn",
    "kka",
    "ko",
    "ca",
    "cs",
    "hr",
    "lv",
    "lo",
    "lt",
    "ro",
    "ms",
    "mr",
    "ml",
    "my",
    "bn",
    "mn",
    "ne",
    "ps",
    "pt",
    "ja",
    "sv",
    "sr",
    "si",
    "sk",
    "sl",
    "sw",
    "tl",
    "tg",
    "te",
    "ta",
    "th",
    "tr",
    "tk",
    "nm",
    "uk",
    "ur",
    "uz",
    "es",
    "he",
    "el",
    "hu",
    "hy",
    "ii",
    "it",
    "id",
    "en",
    "vi",
    "jv",
    "zu",
)

# 所有支持的源语种表
_XUNFEI_FROM_LANGS = (
    ("阿姆哈拉语", "am"),
    ("阿塞拜疆语", "az"),
    ("阿拉伯语", "ar"),
    ("爱尔兰语", "ga"),
    ("爱沙尼亚语", "et"),
    ("白俄罗斯语", "be"),
    ("保加利亚语", "bg"),
    ("波兰语", "pl"),
    ("波斯语", "fa"),
    ("博克马尔挪威语", "nb"),
    ("丹麦语", "da"),
    ("德语", "de"),
    ("俄语", "ru"),
    ("法语", "fr"),
    ("菲律宾语", "tl"),
    ("芬兰语", "fi"),
    ("高棉语", "km"),
    ("格鲁吉亚语", "ka"),
    ("广东话", "yue"),
    ("豪萨语", "ha"),
    ("荷兰语", "nl"),
    ("汉语普通话", "cn"),
    ("哈萨克语", "kka"),
    ("韩语", "ko"),
    ("加泰罗尼亚语", "ca"),
    ("捷克语", "cs"),
    ("克罗地亚语", "hr"),
    ("拉脱维亚语", "lv"),
    ("老挝语", "lo"),
    ("立陶宛语", "lt"),
    ("罗马尼亚语", "ro"),
    ("马来语", "ms"),
    ("马拉地语", "mr"),
    ("马拉雅拉姆语", "ml"),
    ("缅甸语", "my"),
    ("孟加拉语", "bn"),
    ("内蒙语", "mn"),
    ("尼泊尔语", "ne"),
    ("普什图语", "ps"),
    ("葡萄牙语", "pt"),
    ("日语", "ja"),
    ("瑞典语", "sv"),
    ("塞尔维亚语", "sr"),
    ("僧伽罗语", "si"),
    ("斯洛伐克语", "sk"),
    ("斯洛文尼亚语", "sl"),
    ("斯瓦希里语", "sw"),
    ("塔加路语（菲律宾）", "tl"),
    ("塔吉克语", "tg"),
    ("泰卢固语", "te"),
    ("泰米尔语", "ta"),
    ("泰语", "th"),
    ("土耳其语", "tr"),
    ("土库曼语", "tk"),
    ("外蒙语", "nm"),
    ("乌克兰语", "uk"),
    ("乌尔都语", "ur"),
    ("乌兹别克语", "uz"),
    ("西班牙语", "es"),
    ("希伯来语", "he"),
    ("希腊语", "el"),
    ("匈牙利语", "hu"),
    ("亚美尼亚语", "hy"),
    ("彝语", "ii"),
    ("意大利语", "it"),
    ("印尼语", "id"),
    ("英语", "en"),
    ("越南语", "vi"),
    ("爪哇语", "jv"),
    ("祖鲁语", "zu"),
)

# 常用目标语种表
_XUNFEI_TO_LANGS = (
    ("汉语普通话", "cn"),
    ("英语", "en"),
    ("日语", "ja"),
    ("西班牙语", "es"),
    ("阿拉伯语", "ar"),
    ("印地语", "hi"),
    ("葡萄牙语", "pt"),
    ("法语", "fr"),
    ("俄语", "ru"),
    ("德语", "de"),
    ("韩语", "ko"),
    ("意大利语", "it"),
    ("土耳其语", "tr"),
    ("越南语", "vi"),
    ("泰语", "th"),
    ("波兰语", "pl"),
    ("荷兰语", "nl"),
    ("乌克兰语", "uk"),
    ("印尼语", "id"),
    ("罗马尼亚语", "ro"),
    ("瑞典语", "sv"),
    ("捷克语", "cs"),
    ("希腊语", "el"),
    ("匈牙利语", "hu"),
    ("孟加拉语", "bn"),
    ("乌尔都语", "ur"),
    ("马来语", "ms"),
    ("波斯语", "fa"),
    ("豪萨语", "ha"),
    ("缅甸语", "my"),
)
