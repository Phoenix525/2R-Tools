#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from modules.exception.tool_exception import ToolException
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import print_err, print_info, print_warn, read_config, remove_escape

# 量化加载类型
FLAGS = {
    "1": "load_in_8bit",
    "2": "load_in_4bit",
    "3": "nf4",
    "4": "double_quant",
    "5": "QLoRA",
}


class HunYuanMTTranslation(BaseTranslation):
    """
    基于Transformers库，调用腾讯Hunyuan-MT模型的本地大型语言模型，无需联网，本地翻译。
    自行部署环境及下载模型，需一定动手能力。
    环境需求：
    系统Windows 11；Python 3.10.x；Transformers 4.56.0，PyTorch 2.11.0+（需与本机Cuda版本对应）及其他相应依赖
    """

    def __init__(self, section="hunyuan_mt"):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_HUNYUAN_MT_COMMON_LANGS,
            from_langs=_HUNYUAN_MT_FROM_LANGS,
            to_langs=_HUNYUAN_MT_TO_LANGS,
        )
        self.__model_path = ""  # AI模型的绝对路径
        self.__load_flag = ""  # 启用哪种量化加载
        self.__tokenizer = None  # 加载完毕的分词器
        self.__model = None  # 加载完毕的模型
        self.__max_new_tokens = 2048  # 设置生成的最大 token 数（即输出长度上限）
        self.__temperature = 0.7  # 控制输出的随机性，值越高越有创意，值越低越确定性
        self.__top_p = (
            0.6  # 核采样（top-p sampling），限制概率累积最高的 token 选择范围
        )
        self.__top_k = 20  # 限制采样到概率最高的前 k 个 token
        self.__repetition_penalty = 1.05  # 惩罚重复内容，值越高越避免重复
        self.__context = ""  # 上下文

        # 获取配置
        self.__get_config()

        # 加载模型和分词器
        self.__load_model()

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
        prompts = f"将以下文本翻译为{to_lang}，注意只需要输出翻译后的结果，不要额外解释：\n{source_txt}\n\n"
        if activate_context == "1":
            if self.__context:  # 如果启用上下文且上文有内容，则启用上下文翻译
                prompts = f"{self.__context}\n参考上面的信息，把下面的文本翻译成{to_lang}，注意不需要翻译上文，也不要额外解释：\n{source_txt}\n\n"
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
        # 编码输入
        inputs = self.__tokenizer.apply_chat_template(
            message, tokensize=True, add_generation_prompt=False, return_tensors="pt"
        ).to(self.__model.device)

        try:
            # 生成翻译
            outputs = self.__model.generate(
                inputs,
                max_new_tokens=self.__max_new_tokens,
                temperature=self.__temperature,
                top_p=self.__top_p,
                top_k=self.__top_k,
                repetition_penalty=self.__repetition_penalty,
            )
            # 解码输出
            target = self.__tokenizer.decode(
                outputs[0], skip_special_tokens=True
            ).split("\n\n")[-1]
        except Exception as e:
            print_err(f"Hunyuan-MT模型调用失败！请检查报错信息：{str(e)}")
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
        检查模组路径是否存在
        """

        def _check():
            if not self.__model_path:
                raise ToolException(
                    "TranslationAPIErr", "模组调用失败：未配置Hunyuan-MT模型路径！"
                )
            if not os.path.exists(self.__model_path):
                raise ToolException(
                    "TranslationAPIErr", "模组调用失败：路径不存在Hunyuan-MT模型！"
                )

        try:
            _check()
        except ToolException as e:
            print_err(f"翻译引擎调用异常：{str(e)}")
            return False
        else:
            return True

    def __load_model(self):
        """
        加载模型与分词器
        """

        # 如果模型路径错误，直接返回，此处无需抛出异常
        if not self.__model_path or not os.path.exists(self.__model_path):
            return

        # 如果分词器和模型都不为空，说明已加载，无需再次加载
        if self.__tokenizer is not None and self.__model is not None:
            return

        print_warn("请确保已关闭其他占用大量显存及内存的程序，否则可能加载失败!")
        print("正在加载模型和分词器……")
        start_time = time.time()

        try:
            # 加载分词器
            self.__tokenizer = AutoTokenizer.from_pretrained(
                self.__model_path, trust_remote_code=True
            )

            config: BitsAndBytesConfig
            match FLAGS[self.__load_flag]:
                case "load_in_8bit":  # 启用8位量化加载
                    config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0,  # 阈值，用于处理异常大的权重值
                    )
                case "load_in_4bit":  # 启用4位量化加载
                    config = BitsAndBytesConfig(load_in_4bit=True)
                case "nf4":  # 启用NF4量化加载
                    config = BitsAndBytesConfig(
                        load_in_4bit=True, bnb_4bit_quant_type="nf4"
                    )
                case "double_quant":  # 启用双量化加载
                    config = BitsAndBytesConfig(
                        load_in_4bit=True, bnb_4bit_use_double_quant=True
                    )
                case "QLoRA":  # 启用QLoRA量化加载
                    config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                    )
                case _:  # 完整加载
                    config = None

            # 加载模型
            self.__model = AutoModelForCausalLM.from_pretrained(
                self.__model_path,
                device_map="auto",  # 自动分配GPU/CPU资源
                dtype=torch.bfloat16,  # 用bfloat16节省显存
                quantization_config=config,
                trust_remote_code=True,
            )
        except Exception as e:
            self.__tokenizer = None
            self.__model = None
            raise ToolException(
                "TranslationAPIErr", f"Hunyuan-MT模型加载失败：请检查报错信息：{str(e)}"
            )
        else:
            load_time = time.time() - start_time
            print_info(f"模型加载完成，耗时: {load_time:.2f}秒")

    def __get_config(self):
        """
        获取配置
        """

        conf = read_config()
        if conf is None:
            return

        self.__model_path = conf.get(self._section, "model_path")
        self._activated = conf.getboolean(self._section, "activate")
        self.__load_flag = conf.get(self._section, "load_flag")
        self.__max_new_tokens = conf.getint(self._section, "max_new_tokens")
        if self.__max_new_tokens < 0 or self.__max_new_tokens > 2048:
            self.__max_new_tokens = 2048
        self.__temperature = conf.getfloat(self._section, "temperature")
        if self.__temperature < 0 or self.__temperature > 2.0:
            self.__temperature = 0.7
        self.__top_p = conf.getfloat(self._section, "top_p")
        if self.__top_p < 0 or self.__top_p > 1.0:
            self.__top_p = 0.6
        self.__top_k = conf.getint(self._section, "top_k")
        if self.__top_k < 1 or self.__top_k > 50:
            self.__top_k = 20
        self.__repetition_penalty = conf.getfloat(self._section, "repetition_penalty")
        if self.__repetition_penalty < 0:
            self.__repetition_penalty = 1.05


#  所有支持的语种简写表
_HUNYUAN_MT_COMMON_LANGS = (
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
_HUNYUAN_MT_FROM_LANGS = (
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
_HUNYUAN_MT_TO_LANGS = (
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
