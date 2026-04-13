#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import deepl

from src.api.base_translation import BaseTranslation, ValidateStringsType
from src.utils.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from src.utils.utils import (
    acquire_token,
    enpun_2_zhpun,
    print_err,
    read_config,
    remove_escapes,
)


class DeepLTranslation(BaseTranslation):
    """
    DeepL翻译引擎
    """

    def __init__(self, section="deepL"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_DEEPL_COMMON_LANGS,
            from_langs=_DEEPL_FROM_LANGS,
            to_langs=_DEEPL_TO_LANGS,
        )
        self.__auth_key: str = ""

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

        # 获取令牌，未获取到时自动等待
        self._tokens, self._last_refill = acquire_token(
            self._max_qps, self._tokens, self._last_refill
        )

        try:
            deepl.http_client.max_network_retries = 3
            deepl_client = deepl.DeepLClient(self.__auth_key)
            result = deepl_client.translate_text(
                source_txt, source_lang=from_lang, target_lang=to_lang
            )
            target = result.text
            # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
            # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
            target = target.encode("utf-8", "replace").decode("utf-8")
            target = enpun_2_zhpun(target)
        except Exception as e:
            print_err(f"DeepL翻译出现异常！请检查报错信息：{str(e)}")
            target = ""
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

        if self.__auth_key:
            return True

        inp = self.input_what_we_need(
            length=39,
            validate_type=ValidateStringsType.STRING_UUID,
            prompt="未配置auth_key！请输入（敏感内容不显示）或回车返回引擎列表：",
        )
        if inp in ("", "\r", "\n"):
            return False
        self.__auth_key = inp

        store = SimpleKeyStore(SimpleAPIKeyEncryptor("deepl_api_tokens"))
        store.add_keys(self._section, {"auth_key": inp})
        return True

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_key = conf.get(self._section, "auth_key")
        if enc_key:
            api_keys["auth_key"] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor("deepl_api_tokens"), api_keys)
        self.__auth_key = store.get_key("auth_key")

        self._activated = conf.getboolean(self._section, "activate")
        self._max_qps = conf.getint(self._section, "max_qps")
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, "max_char")
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_DEEPL_COMMON_LANGS = (
    "ACE",
    "AF",
    "SQ",
    "AR",
    "AN",
    "HY",
    "AS",
    "AY",
    "AZ",
    "BA",
    "EU",
    "BE",
    "BN",
    "BHO",
    "BS",
    "BR",
    "BG",
    "MY",
    "YUE",
    "CA",
    "CEB",
    "ZH-HANS",
    "ZH-HANT",
    "ZH",
    "HR",
    "CS",
    "DA",
    "PRS",
    "NL",
    "EN",
    "EN-US",
    "EN-GB",
    "EO",
    "ET",
    "FI",
    "FR",
    "GL",
    "KA",
    "DE",
    "EL",
    "GN",
    "GU",
    "HT",
    "HA",
    "HE",
    "HI",
    "HU",
    "IS",
    "IG",
    "ID",
    "GA",
    "IT",
    "JA",
    "JV",
    "PAM",
    "KK",
    "GOM",
    "KO",
    "KMR",
    "CKB",
    "KY",
    "LA",
    "LV",
    "LN",
    "LT",
    "LMO",
    "LB",
    "MK",
    "MAI",
    "MG",
    "MS",
    "ML",
    "MT",
    "MI",
    "MR",
    "MN",
    "NE",
    "NB",
    "OC",
    "OM",
    "PAG",
    "PS",
    "FA",
    "PL",
    "PT-BR",
    "PT-PT",
    "PT",
    "PA",
    "QU",
    "RO",
    "RU",
    "SA",
    "SR",
    "ST",
    "SCN",
    "SK",
    "SL",
    "ES",
    "ES-419",
    "SU",
    "SW",
    "SV",
    "TL",
    "TG",
    "TA",
    "TT",
    "TE",
    "TH",
    "TS",
    "TN",
    "TR",
    "TK",
    "UK",
    "UR",
    "UZ",
    "VI",
    "CY",
    "WO",
    "XH",
    "YI",
    "ZU",
)

# 所有支持的源语种表
_DEEPL_FROM_LANGS = (
    ("阿塞拜疆语", "AZ"),
    ("阿拉伯语", "AR"),
    ("阿姆哈拉语", "AM"),
    ("阿尔巴尼亚语", "SQ"),
    ("阿斯图里亚斯语", "AST"),
    ("阿非利卡语", "AF"),
    ("爱尔兰语", "GA"),
    ("爱沙尼亚语", "ET"),
    ("奥克语", "OC"),
    ("奥里亚语", "OR"),
    ("奥罗莫语", "OM"),
    ("巴斯克语", "EU"),
    ("白俄罗斯语", "BE"),
    ("保加利亚语", "BG"),
    ("冰岛语", "IS"),
    ("波斯尼亚语", "BS"),
    ("波斯语", "FA"),
    ("波兰语", "PL"),
    ("布列塔尼语", "BR"),
    ("丹麦语", "DA"),
    ("德语", "DE"),
    ("俄语", "RU"),
    ("法语", "FR"),
    ("菲律宾语", "TL"),
    ("芬兰语", "FI"),
    ("弗里斯兰语", "FY"),
    ("格鲁吉亚语", "KA"),
    ("瓜拉尼语", "GN"),
    ("海地克里奥尔语", "HT"),
    ("豪萨语", "HA"),
    ("荷兰语", "NL"),
    ("加泰罗尼亚语", "CA"),
    ("捷克语", "CS"),
    ("卡纳达语", "KN"),
    ("克罗地亚语", "HR"),
    ("拉丁语", "LA"),
    ("拉脱维亚语", "LV"),
    ("老挝语", "LO"),
    ("立陶宛语", "LT"),
    ("林加拉语", "LN"),
    ("卢森堡语", "LB"),
    ("罗马尼亚语", "RO"),
    ("马耳他语", "MT"),
    ("马来语", "MS"),
    ("马其顿语", "MK"),
    ("马拉地语", "MR"),
    ("马拉雅拉姆语", "ML"),
    ("毛利语", "MI"),
    ("孟加拉语", "BN"),
    ("缅甸语", "MY"),
    ("尼泊尔语", "NE"),
    ("挪威语", "NB"),
    ("旁遮普语", "PA"),
    ("葡萄牙语", "PT"),
    ("普什图语", "PS"),
    ("日语", "JA"),
    ("瑞典语", "SV"),
    ("塞尔维亚语", "SR"),
    ("塞索托语", "ST"),
    ("僧伽罗语", "SI"),
    ("世界语", "EO"),
    ("斯洛伐克语", "SK"),
    ("斯洛文尼亚语", "SL"),
    ("斯瓦希里语", "SW"),
    ("苏格兰盖尔语", "GD"),
    ("索马里语", "SO"),
    ("塔加洛语", "TL"),
    ("泰卢固语", "TE"),
    ("泰米尔语", "TA"),
    ("泰语", "TH"),
    ("土耳其语", "TR"),
    ("土库曼语", "TK"),
    ("威尔士语", "CY"),
    ("乌尔都语", "UR"),
    ("乌克兰语", "UK"),
    ("乌兹别克语", "UZ"),
    ("西班牙语", "ES"),
    ("希伯来语", "HE"),
    ("希腊语", "EL"),
    ("匈牙利语", "HU"),
    ("亚美尼亚语", "HY"),
    ("伊博语", "IG"),
    ("意大利语", "IT"),
    ("印地语", "HI"),
    ("印度尼西亚语", "ID"),
    ("英语", "EN"),
    ("约鲁巴语", "YO"),
    ("越南语", "VI"),
    ("中文", "ZH"),
)

# 常见目标语种表
_DEEPL_TO_LANGS = (
    ("中文（简体）", "ZH-HANS"),
    ("中文（繁体）", "ZH-HANT"),
    ("英语", "EN"),
    ("印地语", "HI"),
    ("西班牙语", "ES"),
    ("法语", "FR"),
    ("阿拉伯语", "AR"),
    ("孟加拉语", "BN"),
    ("葡萄牙语", "PT"),
    ("俄语", "RU"),
    ("乌尔都语", "UR"),
    ("印度尼西亚语", "ID"),
    ("德语", "DE"),
    ("日语", "JA"),
    ("旁遮普语", "PA"),
    ("土耳其语", "TR"),
    ("韩语", "KO"),
    ("泰语", "TH"),
    ("越南语", "VI"),
    ("意大利语", "IT"),
    ("泰米尔语", "TA"),
    ("马拉地语", "MR"),
    ("波兰语", "PL"),
    ("荷兰语", "NL"),
    ("瑞典语", "SV"),
    ("捷克语", "CS"),
    ("希腊语", "EL"),
    ("匈牙利语", "HU"),
    ("乌克兰语", "UK"),
    ("罗马尼亚语", "RO"),
    ("挪威语", "NB"),
)
