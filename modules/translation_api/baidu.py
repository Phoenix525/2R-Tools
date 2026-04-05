#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from hashlib import md5
from http.client import HTTPConnection
from json import loads
from random import randint
from urllib import parse

from modules.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from modules.exception.tool_exception import ToolException
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import (acquire_token, enpun_2_zhpun,
                           get_password_with_star, is_all_digits,
                           is_letters_and_digits, print_err, print_info,
                           read_config, remove_escape)


class BaiduTranslation(BaseTranslation):
    '''
    百度通用翻译引擎
    不包含词典、tts语音合成等资源，如有相关需求请联系translate_api@baidu.com
    '''

    def __init__(self, *, section='baidu_api'):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_BAIDU_COMMON_LANGS,
            from_langs=_BAIDU_FROM_LANGS,
            to_langs=_BAIDU_TO_LANGS,
        )
        self.__app_id = ''
        self.__secret_key = ''

        # 获取配置
        self.__get_config()
        # 检查翻译引擎是否已就绪
        self.is_ready()

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

        salt = randint(32768, 65536)
        sign = self.__app_id + source_txt + str(salt) + self.__secret_key
        sign = md5(sign.encode()).hexdigest()
        myurl = (
            '/api/trans/vip/translate'
            + '?appid='
            + self.__app_id
            + '&q='
            + parse.quote(source_txt)
            + '&from='
            + from_lang
            + '&to='
            + to_lang
            + '&salt='
            + str(salt)
            + '&sign='
            + sign
        )
        http_client = HTTPConnection('api.fanyi.baidu.com')

        # 重试次数
        retry = kwargs.get('retry', 3)
        for attempt in range(retry):
            # 获取令牌，未获取到时自动等待
            self._tokens, self._last_refill = acquire_token(
                self._max_qps, self._tokens, self._last_refill
            )

            try:
                http_client.request('GET', myurl)
                # response是HTTPResponse对象
                response = http_client.getresponse()
                result_all = response.read().decode('utf-8')
                result = loads(result_all)
                if 'trans_result' in result:
                    trans_result = result['trans_result']
                    target = ''
                    for idx, value in enumerate(trans_result):
                        src = value.get('dst', '')
                        # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
                        # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
                        src = src.encode('utf-8', 'replace').decode('utf-8')
                        src = enpun_2_zhpun(src)
                        target += src
                        if idx < len(trans_result) - 1:
                            target += r'\n'
                    return target

                err_code = result['error_code']
                err_msg = result['error_msg']
                if err_code in ('52002', '54003') and attempt < retry - 1:
                    print_err(f'错误代码：{err_code}，报错信息：{err_msg}')
                    # 指数退避
                    wait = 1.5**attempt
                    print_info(f"{wait}秒后重试……")
                    time.sleep(wait)
                else:
                    raise ToolException(
                        'APIRequestErr', f'错误代码：{err_code}，报错信息：{err_msg}'
                    )
            except Exception as e:
                print_err(f'翻译引擎出现异常！请查看报错信息：{str(e)}')
                break
            finally:
                if http_client:
                    http_client.close()
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

        if self.__app_id and self.__secret_key:
            return True

        keys = {}
        if not self.__app_id:
            inp = get_password_with_star(prompt="未配置appid！请输入：")
            if inp == '' or not is_all_digits(inp) or len(inp) < 17:
                print_err('未输入正确参数，引擎启动失败！')
                return False
            self.__app_id = keys['appid'] = inp
        if not self.__secret_key:
            inp = get_password_with_star(prompt="未配置secretKey！请输入：")
            if inp == '' or not is_letters_and_digits(inp) or len(inp) < 20:
                print_err('未输入正确参数，引擎启动失败！')
                return False
            self.__secret_key = keys['secretKey'] = inp

        store = SimpleKeyStore(SimpleAPIKeyEncryptor('baidu_api_tokens'))
        store.add_keys(self._section, keys)
        return True

    def __get_config(self):
        '''
        获取配置
        '''

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_appid = conf.get(self._section, 'appid')
        if enc_appid:
            api_keys['appid'] = enc_appid
        enc_key = conf.get(self._section, 'secretKey')
        if enc_key:
            api_keys['secretKey'] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor('baidu_api_tokens'), api_keys)
        self.__app_id = store.get_key('appid')
        self.__secret_key = store.get_key('secretKey')

        self._activated = conf.getboolean(self._section, 'activate')
        self._max_qps = conf.getint(self._section, 'max_qps')
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, 'max_char')
        if self._max_char < 50:
            self._max_char = 2000


# 错误码表
_BAIDU_ERROR_CODES = {
    '52000': '成功',
    '52001': '请求超时！请重试。',
    '52002': '系统错误！请重试。',
    '52003': '未授权用户！请检查appid是否正确或者服务是否开通。',
    '54000': '必填参数为空！请检查是否少传参数。',
    '54001': '签名错误！请检查您的签名生成方法。',
    '54003': '访问频率受限！请降低您的调用频率，或进行身份认证后切换为高级版/尊享版。',
    '54004': '账户余额不足！请前往管理控制台为账户充值。',
    '54005': '长query请求频繁！请降低长query的发送频率，3s后再试。',
    '58000': '客户端IP非法！检查个人资料里填写的IP地址是否正确，可前往开发者信息-基本信息修改。',
    '58001': '译文语言方向不支持！检查译文语言是否在语言列表里。',
    '58002': '服务当前已关闭！请前往管理控制台开启服务。',
    '90107': '认证未通过或未生效！请前往我的认证查看认证进度。',
}

# 所有支持的语种简写表
_BAIDU_COMMON_LANGS = (
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
_BAIDU_FROM_LANGS = (
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
_BAIDU_TO_LANGS = (
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
