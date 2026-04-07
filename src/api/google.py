#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import google_trans_new

from src.api.base_translation import BaseTranslation
from src.utils.utils import (
    acquire_token,
    enpun_2_zhpun,
    print_err,
    read_config,
    remove_escape,
)


class GoogleTranslation(BaseTranslation):
    """
    谷歌翻译第三方API
    """

    def __init__(self, section="google"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_GOOGLE_COMMON_LANGS,
            from_langs=_GOOGLE_FROM_LANGS,
            to_langs=_GOOGLE_TO_LANGS,
        )
        # 翻译接口客户端
        self.__translator = None

        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        """
        开始翻译，必定有返回值

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        """

        if self.__translator is None:
            print_err("API客户端未实例化！")
            return ""

        # 删除转义符
        source_txt = remove_escape(source_txt)
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
            target = self.__translator.translate(
                source_txt, lang_tgt=to_lang, lang_src=from_lang
            )
            # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
            # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
            target = target.encode("utf-8", "replace").decode("utf-8")
            target = enpun_2_zhpun(target)
        except Exception as e:
            print_err(f"翻译引擎出现异常！请检查报错信息：{str(e)}")
            target = ""
        finally:
            return target

    def is_ready(self) -> bool:
        """
        查询翻译引擎是否就绪
        """
        if self._activated:
            # 初始化谷歌翻译
            self.__translator = google_trans_new.google_translator()
        return self._activated

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        self._activated = conf.getboolean(self._section, "activate")
        self._max_qps = conf.getint(self._section, "max_qps")
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, "max_char")
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_GOOGLE_COMMON_LANGS = (
    "auto",
    "am",
    "sq",
    "ar",
    "ar-SA",
    "az",
    "ga",
    "et",
    "or",
    "eu",
    "be",
    "bg",
    "bs",
    "bs-Cyrl",
    "pl",
    "da",
    "de",
    "ru",
    "fr",
    "fr-CA",
    "fr-CH",
    "fil",
    "fi",
    "fy",
    "km",
    "ka",
    "gn",
    "gu",
    "ha",
    "nl",
    "nl-BE",
    "gl",
    "cs",
    "kn",
    "hr",
    "lo",
    "lv",
    "lt",
    "ln",
    "lb",
    "ro",
    "mt",
    "mk",
    "mr",
    "ml",
    "ms",
    "mn",
    "bn",
    "bn-IN",
    "my",
    "ne",
    "no",
    "nb",
    "pa",
    "pa-PK",
    "pt",
    "pt-BR",
    "pt-PT",
    "ja",
    "sv",
    "sr",
    "sk",
    "sl",
    "sw",
    "so",
    "tl",
    "tg",
    "te",
    "ta",
    "th",
    "tr",
    "cy",
    "uk",
    "ur",
    "uz",
    "es",
    "es-AR",
    "es-PY",
    "es-PA",
    "es-PR",
    "es-EC",
    "es-CO",
    "es-CR",
    "es-HT",
    "es-HN",
    "es-419",
    "es-PE",
    "es-MX",
    "es-NI",
    "es-SV",
    "es-GT",
    "es-VE",
    "es-UY",
    "es-ES",
    "es-US",
    "es-CL",
    "he",
    "iw",
    "el",
    "hu",
    "hy",
    "it",
    "hi",
    "id",
    "en",
    "en-AU",
    "en-PH",
    "en-CA",
    "en-US",
    "en-ZA",
    "en-GB",
    "en-NZ",
    "vi",
    "zh",
    "zh-Hans",
    "zh-TW",
    "zh-CN",
    "zh-Hant",
    "zh-HK",
    "zu",
)

# 所有支持的源语种表
_GOOGLE_FROM_LANGS = (
    ("自动检测", "auto"),
    ("阿布哈兹语", "ab"),
    ("阿坎语", "ak"),
    ("阿拉伯语", "ar"),
    ("阿姆哈拉语", "am"),
    ("阿萨姆语", "as"),
    ("阿塞拜疆语", "az"),
    ("爱尔兰语", "ga"),
    ("爱沙尼亚语", "et"),
    ("奥里亚语", "or"),
    ("奥塞梯语", "os"),
    ("巴厘语", "ban"),
    ("巴斯克语", "eu"),
    ("白俄罗斯语", "be"),
    ("班巴拉语", "bm"),
    ("保加利亚语", "bg"),
    ("北恩德贝勒语", "nd"),
    ("北萨米语", "se"),
    ("本巴语", "bem"),
    ("比林语", "byn"),
    ("比斯拉马语", "bi"),
    ("俾路支语", "bal"),
    ("冰岛语", "is"),
    ("波兰语", "pl"),
    ("波斯尼亚语", "bs"),
    ("波斯语", "fa"),
    ("朝鲜语", "ko"),
    ("楚瓦什语", "cv"),
    ("茨瓦纳语", "tn"),
    ("达里语", "prs"),
    ("丹麦语", "da"),
    ("德语", "de"),
    ("迪维希语", "dv"),
    ("俄语", "ru"),
    ("厄尔兹亚语", "myv"),
    ("法罗语", "fo"),
    ("法语", "fr"),
    ("菲律宾语", "fil"),
    ("芬兰语", "fi"),
    ("弗留利语", "fur"),
    ("富拉语", "ff"),
    ("盖尔语", "gd"),
    ("刚果语", "kg"),
    ("高棉语", "km"),
    ("格鲁吉亚语", "ka"),
    ("瓜拉尼语", "gn"),
    ("古吉拉特语", "gu"),
    ("哈萨克语", "kk"),
    ("海地克里奥尔语", "ht"),
    ("豪萨语", "ha"),
    ("荷兰语", "nl"),
    ("吉尔吉斯语", "ky"),
    ("加利西亚语", "gl"),
    ("加泰罗尼亚语", "ca"),
    ("捷克语", "cs"),
    ("卡拜尔语", "kab"),
    ("卡纳达语", "kn"),
    ("卡努里语", "kr"),
    ("卡拉卡尔帕克语", "kaa"),
    ("克罗地亚语", "hr"),
    ("科萨语", "xh"),
    ("科西嘉语", "co"),
    ("克里语", "cr"),
    ("克里米亚鞑靼语", "crh"),
    ("库尔德语", "ku"),
    ("拉丁语", "la"),
    ("拉脱维亚语", "lv"),
    ("老挝语", "lo"),
    ("立陶宛语", "lt"),
    ("利古里亚语", "lij"),
    ("林堡语", "li"),
    ("林加拉语", "ln"),
    ("卢干达语", "lg"),
    ("卢森堡语", "lb"),
    ("卢旺达语", "rw"),
    ("罗马尼亚语", "ro"),
    ("马其顿语", "mk"),
    ("马尔加什语", "mg"),
    ("马耳他语", "mt"),
    ("马拉地语", "mr"),
    ("马拉雅拉姆语", "ml"),
    ("马来语", "ms"),
    ("马里语", "chm"),
    ("马普切语", "arn"),
    ("毛利语", "mi"),
    ("蒙古语", "mn"),
    ("孟加拉语", "bn"),
    ("缅甸语", "my"),
    ("米佐语", "lus"),
    ("苗语", "hmn"),
    ("南非荷兰语", "af"),
    ("南恩德贝勒语", "nr"),
    ("瑙鲁语", "na"),
    ("尼泊尔语", "ne"),
    ("挪威语", "no"),
    ("恩敦加语", "ng"),
    ("帕皮阿门托语", "pap"),
    ("旁遮普语", "pa"),
    ("波兰语", "pl"),
    ("葡萄牙语", "pt"),
    ("普什图语", "ps"),
    ("齐切瓦语", "ny"),
    ("日语", "ja"),
    ("瑞典语", "sv"),
    ("萨丁语", "sc"),
    ("萨摩亚语", "sm"),
    ("塞尔维亚语", "sr"),
    ("塞佩蒂语", "nso"),
    ("塞索托语", "st"),
    ("僧伽罗语", "si"),
    ("世界语", "eo"),
    ("斯洛伐克语", "sk"),
    ("斯洛文尼亚语", "sl"),
    ("斯瓦希里语", "sw"),
    ("苏格兰盖尔语", "gd"),
    ("梭托语", "st"),
    ("索马里语", "so"),
    ("塔吉克语", "tg"),
    ("塔加洛语", "tl"),
    ("塔马齐格特语", "tzm"),
    ("泰卢固语", "te"),
    ("泰米尔语", "ta"),
    ("泰语", "th"),
    ("汤加语", "to"),
    ("土耳其语", "tr"),
    ("土库曼语", "tk"),
    ("威尔士语", "cy"),
    ("文达语", "ve"),
    ("乌尔都语", "ur"),
    ("乌克兰语", "uk"),
    ("乌兹别克语", "uz"),
    ("西班牙语", "es"),
    ("希伯来语", "he"),
    ("希腊语", "el"),
    ("匈牙利语", "hu"),
    ("修纳语", "sn"),
    ("宿务语", "ceb"),
    ("亚美尼亚语", "hy"),
    ("伊博语", "ig"),
    ("伊洛卡诺语", "ilo"),
    ("意大利语", "it"),
    ("意第绪语", "yi"),
    ("印地语", "hi"),
    ("印度尼西亚语", "id"),
    ("英语", "en"),
    ("约鲁巴语", "yo"),
    ("越南语", "vi"),
    ("藏语", "bo"),
    ("爪哇语", "jv"),
    ("中文（繁体）", "zh-TW"),
    ("中文（简体）", "zh-CN"),
    ("中文", "zh"),
    ("祖鲁语", "zu"),
)

# 常用目标语种表
_GOOGLE_TO_LANGS = (
    ("中文（简体）", "zh-Hans"),
    ("中文（繁体）", "zh-Hant"),
    ("英语", "en"),
    ("日语", "ja"),
    ("韩语", "ko"),
    ("德语", "de"),
    ("法语", "fr"),
    ("俄语", "ru"),
    ("西班牙语", "es"),
    ("阿拉伯语", "ar"),
    ("印地语", "hi"),
    ("葡萄牙语", "pt"),
    ("意大利语", "it"),
    ("土耳其语", "tr"),
    ("越南语", "vi"),
    ("泰语", "th"),
    ("波兰语", "pl"),
    ("荷兰语", "nl"),
    ("瑞典语", "sv"),
    ("希腊语", "el"),
    ("捷克语", "cs"),
    ("匈牙利语", "hu"),
    ("罗马尼亚语", "ro"),
    ("乌克兰语", "uk"),
    ("印尼语", "id"),
    ("马来语", "ms"),
    ("希伯来语", "he"),
    ("芬兰语", "fi"),
    ("丹麦语", "da"),
    ("挪威语", "no"),
    ("保加利亚语", "bg"),
)
