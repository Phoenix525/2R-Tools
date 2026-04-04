#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
from configparser import ConfigParser
from json import dumps

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import \
    TencentCloudSDKException
# 导入可选配置类
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
# 导入对应产品模块的client models
from tencentcloud.tmt.v20180321 import models, tmt_client

from modules.exception.tool_exception import ToolException
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import (BASE_ABSPATH, acquire_token, get_file_encoding,
                           print_err, print_info, remove_escape)


class TencentTranslation(BaseTranslation):
    '''
    腾讯翻译引擎
    '''

    def __init__(self, *, section='tencent_api'):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_TENCENT_COMMON_LANGS,
            from_langs=_TENCENT_FROM_LANGS,
            to_langs=_TENCENT_TO_LANGS,
        )
        self.__secret_id = ''
        self.__secret_key = ''
        # 获取配置
        self.__get_config()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        '''
        开始翻译

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        '''

        # 源文本语种
        from_lang = kwargs.get('from_lang', 'auto')
        if not self.check_from_and_to(from_lang, to_lang):
            return ''

        # 原文本长度超过API限制
        if len(source_txt) > self._max_char:
            raise ToolException(
                'TranslationAPIErr', '文本长度超过API限制，跳过本条语句！'
            )

        # 删除转义符
        source_txt = remove_escape(source_txt)

        client = self.__init_client()
        _params = {
            'SourceText': source_txt,
            'Source': from_lang,
            'Target': to_lang,
            'ProjectId': 0,
        }
        params = dumps(_params)
        req = models.TextTranslateRequest()
        req.from_json_string(params)

        # 重试次数
        retry = kwargs.get('retry', 3)
        for attempt in range(retry):
            # 获取令牌，未获取到时自动等待
            self._tokens, self._last_refill = acquire_token(
                self._max_qps, self._tokens, self._last_refill
            )

            try:
                resp = client.TextTranslate(req)
                return resp.TargetText
            except TencentCloudSDKException as e:
                if e.get_code() == 'RequestLimitExceeded' and attempt < retry - 1:
                    print_err(str(e))
                    # 指数退避
                    wait = 1.5 ** attempt
                    print_info(f"{wait}秒后重试……")
                    time.sleep(wait)
                else:
                    raise ToolException(
                        'TranslationAPIErr', f'翻译引擎出现异常！请查看报错信息：{str(e)}'
                    )
        return ''

    def is_ready(self) -> bool:
        '''
        查询翻译引擎是否就绪
        '''

        if not self.__check_pass():
            self._activated = False
        return self._activated

    def __check_pass(self):
        '''
        检查API密钥是否配置
        '''

        def _check():
            if self.__secret_id == '' or self.__secret_key == '':
                raise ToolException(
                    'TranslationAPIErr', '腾讯翻译启动失败，未配置token！'
                )

        try:
            _check()
        except ToolException as e:
            print_err(f'翻译引擎调用异常：{str(e)}')
            return False
        else:
            return True
        
    def __init_client(self):
        '''
        初始化API客户端
        '''

        cred = credential.Credential(self.__secret_id, self.__secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tmt.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        return tmt_client.TmtClient(cred, "ap-shanghai", clientProfile)

    def __get_config(self):
        '''
        获取配置
        '''

        config_path = os.path.join(BASE_ABSPATH, 'config.ini')
        if not os.path.isfile(config_path):
            return

        conf = ConfigParser()  # 调用读取配置模块中的类
        conf.optionxform = lambda option: option
        conf.read(config_path, encoding=get_file_encoding(config_path))

        self._activated = conf.getboolean(self._section, 'activate')
        self.__secret_id = conf.get(self._section, 'secretId')
        self.__secret_key = conf.get(self._section, 'secretKey')
        self._max_qps = conf.getint(self._section, 'max_qps')
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, 'max_char')
        if self._max_char < 50:
            self._max_char = 2000


# 错误码表
_TENCENT_ERROR_CODES = {
    'FailedOperation.NoFreeAmount': '本月免费额度已用完！如需继续使用您可以在机器翻译控制台升级为付费使用。',
    'FailedOperation.ServiceIsolate': '账号因为欠费停止服务！请在腾讯云账户充值。',
    'FailedOperation.UserNotRegistered': '服务未开通！请在腾讯云官网机器翻译控制台开通服务。',
    'InternalError': '内部错误！',
    'InternalError.BackendTimeout': '后台服务超时！请稍后重试。',
    'InternalError.ErrorUnknown': '未知错误！请稍后重试。',
    'InternalError.RequestFailed': '参数错误！请检查参数。',
    'LimitExceeded': '超过配额限制！',
    'MissingParameter': '缺少参数错误！请检查参数。',
    'UnauthorizedOperation.ActionNotFound': '请填写正确的Action字段名称！',
    'UnsupportedOperation': '操作不支持！',
    'UnsupportedOperation.TextTooLong': '单次请求text超过长度限制！请保证单次请求⻓度低于2000。',
    'UnsupportedOperation.UnSupportedTargetLanguage': '不支持的目标语言！请参照语言列表。',
    'UnsupportedOperation.UnsupportedLanguage': '不支持的语言！请参照语言列表。',
    'UnsupportedOperation.UnsupportedSourceLanguage': '不支持的源语言！请参照语言列表。',
}

# 所有支持的语种简写表
_TENCENT_COMMON_LANGS = (
    'auto',
    'zh',
    'zh-TW',
    'en',
    'ja',
    'ru',
    'fr',
    'ko',
    'es',
    'it',
    'de',
    'tr',
    'pt',
    'vi',
    'id',
    'th',
    'ms',
    'ar',
    'hi',
)

# 所有支持的源语种表
_TENCENT_FROM_LANGS = (
    ('自动检测', 'auto'),
    ('简体中文', 'zh'),
    ('繁体中文', 'zh-TW'),
    ('英语', 'en'),
    ('日语', 'ja'),
    ('俄语', 'ru'),
    ('法语', 'fr'),
    ('韩语', 'ko'),
    ('西班牙语', 'es'),
    ('意大利语', 'it'),
    ('德语', 'de'),
    ('土耳其语', 'tr'),
    ('葡萄牙语', 'pt'),
    ('越南语', 'vi'),
    ('印尼语', 'id'),
    ('泰语', 'th'),
    ('马来西亚语', 'ms'),
    ('阿拉伯语', 'ar'),
    ('印地语', 'hi'),
)

# 常用目标语种表
_TENCENT_TO_LANGS = (
    ('简体中文', 'zh'),
    ('繁体中文', 'zh-TW'),
    ('英语', 'en'),
    ('日语', 'ja'),
    ('俄语', 'ru'),
    ('法语', 'fr'),
    ('韩语', 'ko'),
    ('西班牙语', 'es'),
    ('意大利语', 'it'),
    ('德语', 'de'),
    ('土耳其语', 'tr'),
    ('葡萄牙语', 'pt'),
    ('越南语', 'vi'),
    ('印尼语', 'id'),
    ('泰语', 'th'),
    ('马来西亚语', 'ms'),
    ('阿拉伯语', 'ar'),
    ('印地语', 'hi'),
)
