#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import time

from alibabacloud_alimt20181012 import models as alimt_20181012_models
from alibabacloud_alimt20181012.client import Client as alimt20181012Client
from alibabacloud_credentials import models as credential_models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models

from modules.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from modules.exception.tool_exception import ToolException
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import (acquire_token, get_password_with_star,
                           is_letters_and_digits, print_debug, print_err,
                           print_info, read_config, remove_escape)


class ALiBaBaTranslation(BaseTranslation):
    '''
    阿里翻译引擎（通用版）
    '''

    def __init__(self, *, section='alibaba'):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_ALIBABA_COMMON_LANGS,
            from_langs=_ALIBABA_FROM_LANGS,
            to_langs=_ALIBABA_TO_LANGS,
        )
        self.__access_key_id = ''
        self.__access_key_secret = ''

        self.__context = ''

        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        '''
        开始翻译，必定有返回值

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        '''

        # 删除转义符
        source_txt = remove_escape(source_txt)
        # 源文本语种
        from_lang = kwargs.get('from_lang', 'auto')
        # 校验文本及语种是否符合要求，不符合则直接返回空值
        if not self.check_text_and_lang(source_txt, from_lang, to_lang):
            return ''
        # 是否启用上下文翻译。1表示启用上下文，并保存上文；0表示不启用上下文，但不清除已有上文；-1表示不启用上下文，同时清除已有上文
        activate_context = kwargs.get('activate_context', '-1')
        # 如果启用上下文且上文有内容，则启用上下文翻译
        if activate_context == '1' and self.__context:
            self.__context = source_txt
        elif activate_context == '-1':
            self.__context = ''

        client = self.__create_client_with_ak()
        translate_general_request = alimt_20181012_models.TranslateGeneralRequest(
            context=self.__context,
            format_type='text',
            source_language=from_lang,
            source_text=source_txt,
            target_language=to_lang,
        )
        runtime = util_models.RuntimeOptions()

        # 重试次数
        retry = kwargs.get('retry', 3)
        for attempt in range(retry):
            # 获取令牌，未获取到时自动等待
            self._tokens, self._last_refill = acquire_token(
                self._max_qps, self._tokens, self._last_refill
            )

            try:
                resp = client.translate_general_with_options(
                    translate_general_request, runtime
                )
                # print_debug(json.dumps(resp, default=str, indent=2))
                code = resp.body.code
                if code == '200':
                    return resp.body.data.translated
                elif code == '10001' and attempt < retry - 1:
                    print_err(f'错误代码：{code}，报错信息：{resp.body.message}')
                    # 指数退避
                    wait = 1.5**attempt
                    print_info(f"{wait}秒后重试……")
                    time.sleep(wait)
                else:
                    raise ToolException(
                        'APIRequestErr', f'错误代码：{code}，报错信息：{resp.body.message}'
                    )
            except Exception as e:
                print_err(str(e))
                break
        return ''

    def is_ready(self) -> bool:
        '''
        查询翻译引擎是否就绪
        '''

        if not self.__check_pass():
            self._activated = False
        return self._activated

    def __check_pass(self) -> bool:
        '''
        检查API密钥是否配置
        '''

        if self.__access_key_id and self.__access_key_secret:
            return True

        keys = {}
        if not self.__access_key_id:
            inp = get_password_with_star(prompt="未配置AccessKeyID！请输入：")
            if inp == '' or not is_letters_and_digits(inp) or len(inp) < 24:
                print_err('未输入正确参数，引擎启动失败！')
                return False
            self.__access_key_id = keys['AccessKeyID'] = inp
        if not self.__access_key_secret:
            inp = get_password_with_star(prompt="未配置AccessKeySecret！请输入：")
            if inp == '' or not is_letters_and_digits(inp) or len(inp) < 30:
                print_err('未输入正确参数，引擎启动失败！')
                return False
            self.__access_key_secret = keys['AccessKeySecret'] = inp

        store = SimpleKeyStore(SimpleAPIKeyEncryptor('alibaba_api_tokens'))
        store.add_keys(self._section, keys)
        return True

    def __create_client_with_bearertoken(
        self, bearer_token: str
    ) -> alimt20181012Client:
        """
        使用BearerToken初始化账号Client
        @param bearer_token: string Bearer Token
        @return: Client
        @throws Exception
        """
        credential_config = credential_models.Config(
            type='bearer', bearer_token=bearer_token
        )
        credential = CredentialClient(credential_config)
        config = open_api_models.Config(
            credential=credential,
            region_id='cn-shanghai',
            endpoint='mt.aliyuncs.com',  # Endpoint 请参考 https://api.aliyun.com/product/alimt
        )
        return alimt20181012Client(config)

    def __create_client_with_ak(self) -> alimt20181012Client:
        """
        使用凭据初始化账号Client
        @return: Client
        @throws Exception
        """
        # 工程代码建议使用更安全的无AK方式，凭据配置方式请参见：https://help.aliyun.com/document_detail/378659.html。
        credential = CredentialClient()
        config = open_api_models.Config(
            credential=credential,
            access_key_id=self.__access_key_id,
            access_key_secret=self.__access_key_secret,
            region_id='cn-shanghai',
            endpoint='mt.aliyuncs.com',  # Endpoint 请参考 https://api.aliyun.com/product/alimt
        )
        return alimt20181012Client(config)

    def __get_config(self):
        '''
        获取配置
        '''

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_access_key_id = conf.get(self._section, 'AccessKeyID')
        if enc_access_key_id:
            api_keys['AccessKeyID'] = enc_access_key_id
        enc_key = conf.get(self._section, 'AccessKeySecret')
        if enc_key:
            api_keys['AccessKeySecret'] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor('alibaba_api_tokens'), api_keys)
        self.__access_key_id = store.get_key('AccessKeyID')
        self.__access_key_secret = store.get_key('AccessKeySecret')

        self._activated = conf.getboolean(self._section, 'activate')
        self._max_qps = conf.getint(self._section, 'max_qps')
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, 'max_char')
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_ALIBABA_COMMON_LANGS = (
    'auto',
    'zh',
    'cht',
    'wyw',
    'yue',
    'en',
    'jp',
    'kor',
    'ara',
    'est',
    'bul',
    'pl',
    'dan',
    'de',
    'ru',
    'fra',
    'fin',
    'nl',
    'cs',
    'rom',
    'pt',
    'slo',
    'th',
    'el',
    'spa',
    'hu',
    'it',
    'vie',
    'swe',
)

# 常见源语种表
_ALIBABA_FROM_LANGS = (
    ('自动检测', 'auto'),
    ('中文', 'zh'),
    ('繁体中文', 'cht'),
    ('文言文', 'wyw'),
    ('粤语', 'yue'),
    ('英语', 'en'),
    ('日语', 'jp'),
    ('韩语', 'kor'),
    ('阿拉伯语', 'ara'),
    ('爱沙尼亚语', 'est'),
    ('保加利亚语', 'bul'),
    ('波兰语', 'pl'),
    ('丹麦语', 'dan'),
    ('德语', 'de'),
    ('俄语', 'ru'),
    ('法语', 'fra'),
    ('芬兰语', 'fin'),
    ('荷兰语', 'nl'),
    ('捷克语', 'cs'),
    ('罗马尼亚语', 'rom'),
    ('葡萄牙语', 'pt'),
    ('斯洛文尼亚语', 'slo'),
    ('泰语', 'th'),
    ('希腊语', 'el'),
    ('西班牙语', 'spa'),
    ('匈牙利语', 'hu'),
    ('意大利语', 'it'),
    ('越南语', 'vie'),
    ('瑞典语', 'swe'),
)

# 常用目标语种表
_ALIBABA_TO_LANGS = (
    ('中文', 'zh'),
    ('繁体中文', 'cht'),
    ('文言文', 'wyw'),
    ('粤语', 'yue'),
    ('英语', 'en'),
    ('日语', 'jp'),
    ('韩语', 'kor'),
    ('阿拉伯语', 'ara'),
    ('爱沙尼亚语', 'est'),
    ('保加利亚语', 'bul'),
    ('波兰语', 'pl'),
    ('丹麦语', 'dan'),
    ('德语', 'de'),
    ('俄语', 'ru'),
    ('法语', 'fra'),
    ('芬兰语', 'fin'),
    ('荷兰语', 'nl'),
    ('捷克语', 'cs'),
    ('罗马尼亚语', 'rom'),
    ('葡萄牙语', 'pt'),
    ('斯洛文尼亚语', 'slo'),
    ('泰语', 'th'),
    ('希腊语', 'el'),
    ('西班牙语', 'spa'),
    ('匈牙利语', 'hu'),
    ('意大利语', 'it'),
    ('越南语', 'vie'),
    ('瑞典语', 'swe'),
)
