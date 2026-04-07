#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from ollama import ChatResponse, chat

from src.exception.tool_exception import ToolException
from src.api.base_translation import BaseTranslation
from src.utils.utils import print_err, read_config, remove_escape


class OllamaTranslation(BaseTranslation):
    """
    基于Ollama（LLM）平台的本地AI翻译引擎，本地部署，无需联网，本地翻译。
    需自行下载安装Ollama，并下载要使用的AI模型，在当前api目录下的config.ini中配置该模型名称。
    使用该翻译引擎，需要先启动Ollama。
    """

    def __init__(self, section="ollama"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_OLLAMA_COMMON_LANGS,
            from_langs=_OLLAMA_FROM_LANGS,
            to_langs=_OLLAMA_TO_LANGS,
        )
        self.__model_name = ""  # Ollama当前调用模型名称
        self.__num_predict = 2048  # 设置生成的最大 token 数（即输出长度上限）
        self.__temperature = 1  # 控制输出的随机性，值越高越有创意，值越低越确定性
        self.__min_p = 0.0
        self.__top_p = (
            1.0  # 核采样（top-p sampling），限制概率累积最高的 token 选择范围
        )
        self.__top_k = 40  # 限制采样到概率最高的前 k 个 token
        self.__repeat_penalty = 1.1  # 惩罚重复内容，值越高越避免重复
        self.__seed = 0  # 设置用于生成的随机数种子
        self.__context = ""  # 上下文

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

        # 是否启用上下文翻译。1表示启用上下文，并保存上文；0表示不启用上下文，但不清除已有上文；-1表示不启用上下文，同时清除已有上文
        activate_context = kwargs.get("activate_context", "-1")
        # 提示词
        prompts = f"将以下文本翻译为{to_lang}，注意只需要输出翻译后的结果，不要额外解释：\n{source_txt}\n"
        if activate_context == "1":
            if self.__context:  # 如果启用上下文且上文有内容，则启用上下文翻译
                prompts = f"{self.__context}\n参考上面的信息，把下面的文本翻译成{to_lang}，注意不需要翻译上文，也不要额外解释：\n{source_txt}\n"
            self.__context = source_txt
        elif activate_context == "-1":
            self.__context = ""

        # 对话列表
        message = [
            {
                "role": "user",
                "content": prompts,
            }
        ]

        try:
            # 调用聊天
            response: ChatResponse = chat(
                model=self.__model_name,
                messages=message,
                options={
                    "temperature": self.__temperature,
                    "min_p": self.__min_p,
                    "top_p": self.__top_p,
                    "top_k": self.__top_k,
                    "num_predict": self.__num_predict,
                    "repeat_penalty": self.__repeat_penalty,
                    "seed": self.__seed,
                },
            )

            target = response["message"]["content"].rstrip("\n")
        except Exception as e:
            print_err(f"Ollama调用失败！请检查报错信息：{str(e)}")
            target = ""
        finally:
            return target

    def is_ready(self) -> bool:
        """
        查询翻译引擎是否就绪
        """
        if not self.__check_model():
            self._activated = False
        return self._activated

    def __check_model(self) -> bool:
        """
        检查是否配置模组名称
        """

        def _check():
            if not self.__model_name:
                raise ToolException(
                    "TranslationAPIErr", "模组调用失败：Ollama未配置模型名称！"
                )

        try:
            _check()
        except ToolException as e:
            print_err(f"翻译引擎调用异常：{str(e)}")
            return False
        else:
            return True

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        self.__model_name = conf.get(self._section, "model_name")
        self._activated = conf.getboolean(self._section, "activate")
        self.__num_predict = conf.getint(self._section, "num_predict")
        if self.__num_predict < -1:
            self.__num_predict = 2048
        self.__temperature = conf.getfloat(self._section, "temperature")
        if self.__temperature < 0 or self.__temperature > 2.0:
            self.__temperature = 0.8
        self.__min_p = conf.getfloat(self._section, "min_p")
        if self.__min_p < 0 or self.__top_p > 1.0:
            self.__min_p = 0.0
        self.__top_p = conf.getfloat(self._section, "top_p")
        if self.__top_p < 0 or self.__top_p > 1.0:
            self.__top_p = 0.9
        self.__top_k = conf.getint(self._section, "top_k")
        if self.__top_k < 1 or self.__top_k > 50:
            self.__top_k = 40
        self.__repeat_penalty = conf.getfloat(self._section, "repeat_penalty")
        if self.__repeat_penalty < 0:
            self.__repeat_penalty = 1.1
        self.__seed = conf.getint(self._section, "seed")
        if self.__seed < 0 or self.__top_k > 50:
            self.__seed = 0


#  所有支持的语种简写表
_OLLAMA_COMMON_LANGS = (
    "auto",
    "ar",
    "de",
    "ru",
    "fr",
    "tl",
    "zh-Hant",
    "km",
    "gu",
    "ko",
    "nl",
    "kk",
    "cs",
    "my",
    "ms",
    "mr",
    "mn",
    "bn",
    "pt",
    "ja",
    "sv",
    "te",
    "ta",
    "th",
    "tr",
    "ug",
    "ur",
    "uk",
    "es",
    "he",
    "hi",
    "id",
    "en",
    "it",
    "vi",
    "bo",
    "zh",
    "yue",
)

#  所有支持的语种表
_OLLAMA_FROM_LANGS = (
    ("自动检测", "auto"),
    ("阿拉伯语", "ar"),
    ("德语", "de"),
    ("俄语", "ru"),
    ("法语", "fr"),
    ("菲律宾语", "tl"),
    ("繁体中文", "zh-Hant"),
    ("高棉语", "km"),
    ("古吉拉特语", "gu"),
    ("韩语", "ko"),
    ("荷兰语", "nl"),
    ("哈萨克语", "kk"),
    ("捷克语", "cs"),
    ("缅甸语", "my"),
    ("马来语", "ms"),
    ("马拉地语", "mr"),
    ("蒙古语", "mn"),
    ("孟加拉语", "bn"),
    ("葡萄牙语", "pt"),
    ("日语", "ja"),
    ("瑞典语", "sv"),
    ("泰卢固语", "te"),
    ("泰米尔语", "ta"),
    ("泰语", "th"),
    ("土耳其语", "tr"),
    ("维吾尔语", "ug"),
    ("乌尔都语", "ur"),
    ("乌克兰语", "uk"),
    ("西班牙语", "es"),
    ("希伯来语", "he"),
    ("印地语", "hi"),
    ("印尼语", "id"),
    ("英语", "en"),
    ("意大利语", "it"),
    ("越南语", "vi"),
    ("藏语", "bo"),
    ("中文", "zh"),
    ("粤语", "yue"),
)

#  所有支持的语种表
_OLLAMA_TO_LANGS = (
    ("中文", "zh"),
    ("繁体中文", "zh-Hant"),
    ("粤语", "yue"),
    ("英语", "en"),
    ("日语", "ja"),
    ("阿拉伯语", "ar"),
    ("德语", "de"),
    ("俄语", "ru"),
    ("法语", "fr"),
    ("菲律宾语", "tl"),
    ("高棉语", "km"),
    ("古吉拉特语", "gu"),
    ("韩语", "ko"),
    ("荷兰语", "nl"),
    ("哈萨克语", "kk"),
    ("捷克语", "cs"),
    ("缅甸语", "my"),
    ("马来语", "ms"),
    ("马拉地语", "mr"),
    ("蒙古语", "mn"),
    ("孟加拉语", "bn"),
    ("葡萄牙语", "pt"),
    ("瑞典语", "sv"),
    ("泰卢固语", "te"),
    ("泰米尔语", "ta"),
    ("泰语", "th"),
    ("土耳其语", "tr"),
    ("维吾尔语", "ug"),
    ("乌尔都语", "ur"),
    ("乌克兰语", "uk"),
    ("西班牙语", "es"),
    ("希伯来语", "he"),
    ("印地语", "hi"),
    ("印尼语", "id"),
    ("意大利语", "it"),
    ("越南语", "vi"),
    ("藏语", "bo"),
)
