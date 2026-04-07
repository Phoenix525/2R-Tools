#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time
from hashlib import sha256
from uuid import uuid1

from requests import post

from modules.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from modules.exception.tool_exception import ToolException
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import (
    acquire_token,
    enpun_2_zhpun,
    get_password_with_star,
    is_letters_and_digits,
    print_err,
    print_info,
    read_config,
    remove_escape,
)


class YoudaoTranslation(BaseTranslation):
    """
    有道智云翻译引擎
    """

    def __init__(self, section="youdao"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_YOUDAO_COMMON_LANGS,
            from_langs=_YOUDAO_FROM_LANGS,
            to_langs=_YOUDAO_TO_LANGS,
        )
        self.__app_id = ""
        self.__app_key = ""
        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        """
        开始翻译，必定有返回值

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        """

        # 删除转义符
        source_txt = remove_escape(source_txt)
        # 源文本语种
        from_lang = kwargs.get("from_lang", "auto")
        # 校验文本及语种是否符合要求，不符合则直接返回空值
        from_lang = self.check_text_and_lang(source_txt, from_lang, to_lang)
        if not from_lang:
            return ""

        def _encrypt(signStr: str):
            hash_algorithm = sha256()
            hash_algorithm.update(signStr.encode("utf-8"))
            return hash_algorithm.hexdigest()

        def _truncate(source: str):
            if source is None:
                return None
            size = len(source)
            return (
                source
                if size <= 20
                else source[0:10] + str(size) + source[size - 10 : size]
            )

        curtime = str(int(time.time()))
        salt = str(uuid1())
        signStr = (
            self.__app_id + _truncate(source_txt) + salt + curtime + self.__app_key
        )
        data = {
            "q": source_txt,
            "from": from_lang,
            "to": to_lang,
            "signType": "v3",
            "curtime": curtime,
            "appKey": self.__app_id,
            "salt": salt,
            "sign": _encrypt(signStr),
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        # 重试次数
        retry = kwargs.get("retry", 3)
        for attempt in range(retry):
            # 获取令牌，未获取到时自动等待
            self._tokens, self._last_refill = acquire_token(
                self._max_qps, self._tokens, self._last_refill
            )
            try:
                response = post(
                    "https://openapi.youdao.com/api", data=data, headers=headers
                )
                # print_debug(response.text)
                result = json.loads(response.text)
                if "translation" in result:
                    target = result["translation"][0]
                    # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
                    # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
                    target = target.encode("utf-8", "replace").decode("utf-8")
                    target = enpun_2_zhpun(target)
                    return target
                err_code = result["errorCode"]
                # 请求频率超限且还有重试次数时，阻塞N秒后重新发起请求
                if err_code == "411" and attempt < retry - 1:
                    print_err(
                        f"错误代码：{err_code}，报错信息：访问频率受限,请稍后访问！"
                    )
                    # 指数退避
                    wait = 2**attempt
                    print_info(f"{wait}秒后重试……")
                    time.sleep(wait)
                else:
                    raise ToolException("APIRequestErr", f"错误代码：{err_code}")
            except Exception as e:
                print_err(f"翻译引擎出现异常！请查看报错信息：{str(e)}")
                break
        # 未获取到正确结果时，返回空字串
        return ""

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

        if self.__app_id and self.__app_key:
            return True

        keys = {}
        if not self.__app_id:
            inp = get_password_with_star("未配置appId！请输入：").strip()
            if inp == "" or not is_letters_and_digits(inp) or len(inp) < 16:
                print_err("未输入正确参数，引擎启动失败！")
                return False
            self.__app_id = keys["appId"] = inp

        if not self.__app_key:
            inp = get_password_with_star("未配置appKey！请输入：").strip()
            if inp == "" or not is_letters_and_digits(inp) or len(inp) < 32:
                print_err("未输入正确参数，引擎启动失败！")
                return False
            self.__app_key = keys["appKey"] = inp
        store = SimpleKeyStore(SimpleAPIKeyEncryptor("youdao_api_tokens"))
        store.add_keys(self._section, keys)
        return True

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_key = conf.get(self._section, "appId")
        if enc_key:
            api_keys["appId"] = enc_key
        enc_key = conf.get(self._section, "appKey")
        if enc_key:
            api_keys["appKey"] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor("youdao_api_tokens"), api_keys)
        self.__app_id = store.get_key("appId")
        self.__app_key = store.get_key("appKey")

        self._activated = conf.getboolean(self._section, "activate")
        self._max_qps = conf.getint(self._section, "max_qps")
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, "max_char")
        if self._max_char < 50:
            self._max_char = 2000


# 错误码表
_ERROR_CODES = {
    "101": "缺少必填的参数！首先确保必填参数齐全，然后确认参数书写是否正确。",
    "102": "不支持的语言类型！",
    "103": "翻译文本过长！",
    "104": "不支持的API类型！",
    "105": "不支持的签名类型！",
    "106": "不支持的响应类型！",
    "107": "不支持的传输加密类型！",
    "108": "应用ID无效！注册账号，登录后台创建应用和实例并完成绑定，可获得应用ID和应用密钥等信息。",
    "109": "batchLog格式不正确！",
    "110": "无相关服务的有效实例！应用没有绑定服务实例，可以新建服务实例，绑定服务实例。注：某些服务的翻译结果发音需要tts实例，需要在控制台创建语音合成实例绑定应用后方能使用。",
    "111": "开发者账号无效！",
    "112": "请求服务无效！",
    "113": "q不能为空！",
    "114": "不支持的图片传输方式！",
    "116": "strict字段取值无效！请参考文档填写正确参数值。",
    "201": "解密失败！可能为DES,BASE64,URLDecode的错误。",
    "202": "签名检验失败！如果确认应用ID和应用密钥的正确性，仍返回202，一般是编码问题。请确保翻译文本 q 为UTF-8编码。",
    "203": "访问IP地址不在可访问IP列表！",
    "205": "请求的接口与应用的平台类型不一致！确保接入方式（Android SDK、IOS SDK、API）与创建的应用平台类型一致。如有疑问请参考入门指南。",
    "206": "因为时间戳无效导致签名校验失败！",
    "207": "重放请求！",
    "301": "辞典查询失败！",
    "302": "翻译查询失败！",
    "303": "服务端的其它异常！",
    "304": "会话闲置太久超时！",
    "401": "账户已经欠费！请进行账户充值。",
    "402": "offlinesdk不可用！",
    "411": "访问频率受限！请稍后访问。",
    "412": "长请求过于频繁！请稍后访问。",
}

# 所有支持的语种简写表
_YOUDAO_COMMON_LANGS = (
    "auto",
    "sq",
    "ar",
    "am",
    "az",
    "ga",
    "et",
    "eu",
    "be",
    "mww",
    "bg",
    "bs",
    "fa",
    "pl",
    "da",
    "de",
    "ru",
    "fr",
    "tl",
    "fj",
    "fi",
    "fy",
    "zh-CHT",
    "ka",
    "gu",
    "gl",
    "ca",
    "cs",
    "kn",
    "hr",
    "co",
    "tlh",
    "otq",
    "ku",
    "lv",
    "la",
    "lo",
    "lt",
    "lb",
    "ro",
    "mt",
    "mg",
    "mk",
    "mr",
    "ml",
    "ms",
    "mi",
    "mn",
    "bn",
    "my",
    "ne",
    "no",
    "pa",
    "ps",
    "pt",
    "ny",
    "ja",
    "sv",
    "sm",
    "sr-Latn",
    "sr-Cyrl",
    "st",
    "si",
    "eo",
    "sk",
    "sl",
    "sw",
    "ceb",
    "te",
    "ta",
    "th",
    "to",
    "tg",
    "ty",
    "tr",
    "cy",
    "uk",
    "ur",
    "uz",
    "es",
    "he",
    "el",
    "haw",
    "sd",
    "hu",
    "sn",
    "su",
    "hy",
    "ig",
    "it",
    "yi",
    "hi",
    "id",
    "en",
    "yua",
    "yo",
    "yue",
    "vi",
    "jw",
    "zh-CHS",
    "zu",
    "gd",
    "ky",
    "kk",
    "ht",
    "nl",
    "ha",
    "ko",
    "km",
    "is",
)

# 所有支持的源语种表
_YOUDAO_FROM_LANGS = (
    ("自动检测", "auto"),
    ("阿尔巴尼亚语", "sq"),
    ("阿拉伯语", "ar"),
    ("阿姆哈拉语", "am"),
    ("阿塞拜疆语", "az"),
    ("爱尔兰语", "ga"),
    ("爱沙尼亚语", "et"),
    ("巴斯克语", "eu"),
    ("白俄罗斯语", "be"),
    ("白苗语", "mww"),
    ("保加利亚语", "bg"),
    ("波斯尼亚语", "bs"),
    ("波斯语", "fa"),
    ("波兰语", "pl"),
    ("丹麦语", "da"),
    ("德语", "de"),
    ("俄语", "ru"),
    ("法语", "fr"),
    ("菲律宾语", "tl"),
    ("斐济语", "fj"),
    ("芬兰语", "fi"),
    ("繁体中文", "zh-CHT"),
    ("格鲁吉亚语", "ka"),
    ("古吉拉特语", "gu"),
    ("加利西亚语", "gl"),
    ("加泰隆语", "ca"),
    ("捷克语", "cs"),
    ("卡纳达语", "kn"),
    ("克罗地亚语", "hr"),
    ("科西嘉语", "co"),
    ("克林贡语", "tlh"),
    ("克雷塔罗奥托米语", "otq"),
    ("库尔德语", "ku"),
    ("拉脱维亚语", "lv"),
    ("拉丁语", "la"),
    ("老挝语", "lo"),
    ("立陶宛语", "lt"),
    ("卢森堡语", "lb"),
    ("罗马尼亚语", "ro"),
    ("马耳他语", "mt"),
    ("马尔加什语", "mg"),
    ("马其顿语", "mk"),
    ("马拉地语", "mr"),
    ("马拉雅拉姆语", "ml"),
    ("马来语", "ms"),
    ("毛利语", "mi"),
    ("蒙古语", "mn"),
    ("孟加拉语", "bn"),
    ("缅甸语", "my"),
    ("尼泊尔语", "ne"),
    ("挪威语", "no"),
    ("旁遮普语", "pa"),
    ("普什图语", "ps"),
    ("葡萄牙语", "pt"),
    ("齐切瓦语", "ny"),
    ("日语", "ja"),
    ("瑞典语", "sv"),
    ("萨摩亚语", "sm"),
    ("塞尔维亚语(拉丁文)", "sr-Latn"),
    ("塞尔维亚语(西里尔文)", "sr-Cyrl"),
    ("塞索托语", "st"),
    ("僧伽罗语", "si"),
    ("世界语", "eo"),
    ("斯洛伐克语", "sk"),
    ("斯洛文尼亚语", "sl"),
    ("斯瓦希里语", "sw"),
    ("宿务语", "ceb"),
    ("泰卢固语", "te"),
    ("泰米尔语", "ta"),
    ("泰语", "th"),
    ("汤加语", "to"),
    ("塔吉克语", "tg"),
    ("塔希提语", "ty"),
    ("土耳其语", "tr"),
    ("威尔士语", "cy"),
    ("乌克兰语", "uk"),
    ("乌尔都语", "ur"),
    ("乌兹别克语", "uz"),
    ("西班牙语", "es"),
    ("希伯来语", "he"),
    ("希腊语", "el"),
    ("夏威夷语", "haw"),
    ("信德语", "sd"),
    ("匈牙利语", "hu"),
    ("修纳语", "sn"),
    ("巽他语", "su"),
    ("亚美尼亚语", "hy"),
    ("伊博语", "ig"),
    ("意大利语", "it"),
    ("意第绪语", "yi"),
    ("印地语", "hi"),
    ("印度尼西亚语", "id"),
    ("英语", "en"),
    ("尤卡坦玛雅语", "yua"),
    ("约鲁巴语", "yo"),
    ("粤语", "yue"),
    ("越南语", "vi"),
    ("爪哇语", "jw"),
    ("简体中文", "zh-CHS"),
    ("祖鲁语", "zu"),
    ("苏格兰盖尔语", "gd"),
    ("柯尔克孜语", "ky"),
    ("哈萨克语", "kk"),
    ("海地克里奥尔语", "ht"),
    ("荷兰语", "nl"),
    ("豪萨语", "ha"),
    ("韩语", "ko"),
    ("高棉语", "km"),
    ("弗里西语", "fy"),
    ("冰岛语", "is"),
)

# 常用目标语种表
_YOUDAO_TO_LANGS = (
    ("简体中文", "zh-CHS"),
    ("繁体中文", "zh-CHT"),
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
    ("越南语", "vi"),
    ("泰语", "th"),
    ("荷兰语", "nl"),
    ("印度尼西亚语", "id"),
)
