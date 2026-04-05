#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ast
import time

import volcenginesdktranslate20250301
from volcenginesdkcore import Configuration, rest

from modules.encryptor import SimpleAPIKeyEncryptor, SimpleKeyStore
from modules.translation_api.base_translation import BaseTranslation
from modules.utils import (acquire_token, check_langs, enpun_2_zhpun,
                           get_password_with_star, is_letters_and_digits,
                           print_debug, print_err, print_info, read_config,
                           remove_escape)


class HuoshanTranslation(BaseTranslation):
    '''
    火山翻译引擎
    '''

    def __init__(self, *, section='huoshan_api'):

        BaseTranslation.__init__(
            self,
            section=section,
            comment_langs=_HUOSHAN_COMMON_LANGS,
            from_langs=_HUOSHAN_FROM_LANGS,
            to_langs=_HUOSHAN_TO_LANGS,
        )
        self.__access_key_id = ''
        self.__secret_access_key = ''
        # 翻译接口客户端
        self.__client = None

        # 获取配置
        self.__get_config()
        # 检查翻译引擎是否已就绪
        if self.is_ready():
            # 实例化客户端
            self.__client = self.__init_client()

    def translate(self, source_txt: str, to_lang: str, **kwargs) -> str:
        '''
        开始翻译，必定有返回值

        - source_txt: 输入文本
        - to_lang: 目标语种
        - **kwargs: 其他参数
        '''

        if self.__client is None:
            print_err('API客户端未实例化！')
            return ''

        # 删除转义符
        source_txt = remove_escape(source_txt)
        # 源文本语种
        from_lang = kwargs.get('from_lang', 'auto')
        # deepl源语种无法使用auto，在未指定源语种时，获取语种
        if from_lang == 'auto':
            from_lang = check_langs(source_txt)
        # 校验文本及语种是否符合要求，不符合则直接返回空值
        if not self.check_text_and_lang(source_txt, from_lang, to_lang):
            return ''

        translate_txt_request = volcenginesdktranslate20250301.TranslateTextRequest(
            source_language=from_lang,
            target_language=to_lang,
            text_list=[source_txt],
        )

        # 重试次数
        retry = kwargs.get('retry', 3)
        for attempt in range(retry):
            # 获取令牌，未获取到时自动等待
            self._tokens, self._last_refill = acquire_token(
                self._max_qps, self._tokens, self._last_refill
            )

            try:
                response = self.__client.translate_text(translate_txt_request).to_dict()
                print_debug(str(response))
                if response:
                    if 'translation_list' in response:
                        target = response['translation_list'][0].get('translation', '')
                        # 翻译引擎返回的字符串可能存在一些\u开头的，但无法使用utf-8解码的字符串
                        # encode函数遇此问题默认是抛异常，这里修改参数调整为将字符串替换成“?”
                        target = target.encode('utf-8', 'replace').decode('utf-8')
                        target = enpun_2_zhpun(target)
                        return target
            except rest.ApiException as e:
                err = ast.literal_eval(e.reason)
                # 请求频率超限且还有重试次数时，阻塞N秒后重新发起请求
                if err.get('Code', '0') == '-429' and attempt < retry - 1:
                    err_code = err['Code']
                    msg = err['Message']
                    print_err(f'错误代码：{err_code}，报错信息：{msg}')
                    # 指数退避
                    wait = 2**attempt
                    print_info(f"{wait}秒后重试……")
                    time.sleep(wait)
                else:
                    print_err(f'翻译引擎出现异常！请查看报错信息：{str(e)}')
                    break
        # 未获取到正确结果时，返回空字串
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

        if self.__access_key_id and self.__secret_access_key:
            return True

        keys = {}
        if not self.__access_key_id:
            inp = get_password_with_star('未配置AccessKeyID！请输入：').strip()
            if inp == '' or not is_letters_and_digits(inp) or len(inp) < 47:
                print_err('未输入正确参数，引擎启动失败！')
                return False
            self.__access_key_id = keys['AccessKeyID'] = inp
        if not self.__secret_access_key:
            inp = get_password_with_star(
                '未配置SecretAccessKey！请输入（注意加上末尾两个“=”）：'
            ).strip()
            if inp == '' or not is_letters_and_digits(inp[:-2]) or len(inp) < 60:
                print_err('未输入正确参数，引擎启动失败！')
                return False
            self.__secret_access_key = keys['SecretAccessKey'] = inp

        store = SimpleKeyStore(SimpleAPIKeyEncryptor('huoshan_api_tokens'))
        store.add_keys(self._section, keys)
        return True

    def __init_client(self):
        '''
        初始化API客户端
        '''
        configuration = Configuration()
        configuration.ak = self.__access_key_id
        configuration.sk = self.__secret_access_key
        configuration.region = 'cn-beijing'
        # set default configuration
        Configuration.set_default(configuration)
        # use global default configuration
        return volcenginesdktranslate20250301.TRANSLATE20250301Api()

    def __get_config(self):
        '''
        获取配置
        '''

        conf = read_config()
        if conf is None:
            return

        api_keys = {}
        enc_key = conf.get(self._section, 'AccessKeyID')
        if enc_key:
            api_keys['AccessKeyID'] = enc_key
        enc_key = conf.get(self._section, 'SecretAccessKey')
        if enc_key:
            api_keys['SecretAccessKey'] = enc_key
        store = SimpleKeyStore(SimpleAPIKeyEncryptor('huoshan_api_tokens'), api_keys)
        self.__access_key_id = store.get_key('AccessKeyID')
        self.__secret_access_key = store.get_key('SecretAccessKey')

        self._activated = conf.getboolean(self._section, 'activate')
        self._max_qps = conf.getint(self._section, 'max_qps')
        if self._max_qps < 1:
            self._max_qps = 1
        self._max_char = conf.getint(self._section, 'max_char')
        if self._max_char < 50:
            self._max_char = 2000


# 所有支持的语种简写表
_HUOSHAN_COMMON_LANGS = (
    'auto',
    'ab',
    'sq',
    'af',
    'ar',
    'am',
    'az',
    'ay',
    'et',
    'om',
    'os',
    'ba',
    'bg',
    'nd',
    'kmr',
    'nso',
    'bi',
    'bs',
    'fa',
    'pl',
    'tt',
    'da',
    'de',
    'ru',
    'fr',
    'fj',
    'fi',
    'lg',
    'kg',
    'km',
    'kl',
    'ka',
    'gu',
    'ht',
    'ha',
    'ko',
    'nl',
    'gl',
    'ca',
    'kam',
    'kn',
    'xh',
    'hr',
    'kj',
    'lv',
    'lo',
    'lt',
    'ln',
    'lu',
    'umb',
    'ro',
    'mt',
    'mk',
    'mr',
    'ml',
    'ms',
    'mh',
    'mn',
    'bn',
    'nan',
    'my',
    'nr',
    'fuv',
    'nb',
    'no',
    'pa',
    'pt',
    'qu',
    'ny',
    'tw',
    'ja',
    'sv',
    'sm',
    'sr',
    'st',
    'sg',
    'sn',
    'eo',
    'ss',
    'sk',
    'sl',
    'sw',
    'tl',
    'ty',
    'te',
    'ta',
    'th',
    'to',
    'ti',
    'tk',
    'tr',
    'cy',
    'ug',
    'uk',
    'ur',
    'wuu',
    'es',
    'he',
    'ho',
    'el',
    'cmn',
    'hu',
    'hy',
    'ig',
    'iu',
    'it',
    'id',
    'en',
    'yo',
    'vi',
    'yue',
    'bo',
    'tn',
    'zh',
    'zh-Hant',
    'zh-Hant-tw',
    'lzh',
    'zh-Hant-hk',
    'ckb',
    'zu',
)

# 所有支持的源语种表
_HUOSHAN_FROM_LANGS = (
    ('自动检测', 'auto'),
    ('阿布哈兹语', 'ab'),
    ('阿尔巴尼亚语', 'sq'),
    ('阿非利堪斯语', 'af'),
    ('阿拉伯语', 'ar'),
    ('阿姆哈拉语', 'am'),
    ('阿塞拜疆语', 'az'),
    ('艾马拉语', 'ay'),
    ('爱沙尼亚语', 'et'),
    ('奥洛莫语', 'om'),
    ('奥塞梯语', 'os'),
    ('巴什基尔语', 'ba'),
    ('保加利亚语', 'bg'),
    ('北恩德贝勒语', 'nd'),
    ('北库尔德语', 'kmr'),
    ('北索托语', 'nso'),
    ('比斯拉玛语', 'bi'),
    ('波斯尼亚语', 'bs'),
    ('波斯语', 'fa'),
    ('波兰语', 'pl'),
    ('鞑靼语', 'tt'),
    ('丹麦语', 'da'),
    ('德语', 'de'),
    ('俄语', 'ru'),
    ('法语', 'fr'),
    ('斐济语', 'fj'),
    ('芬兰语', 'fi'),
    ('干达语', 'lg'),
    ('刚果语', 'kg'),
    ('高棉语', 'km'),
    ('格陵兰语', 'kl'),
    ('格鲁吉亚语', 'ka'),
    ('古吉拉特语', 'gu'),
    ('海地克里奥尔语', 'ht'),
    ('豪萨语', 'ha'),
    ('韩语', 'ko'),
    ('荷兰语', 'nl'),
    ('加利西亚语', 'gl'),
    ('加泰隆语', 'ca'),
    ('坎巴语', 'kam'),
    ('坎纳达语', 'kn'),
    ('科萨语', 'xh'),
    ('克罗地亚语', 'hr'),
    ('宽亚玛语', 'kj'),
    ('拉脱维亚语', 'lv'),
    ('老挝语', 'lo'),
    ('立陶宛语', 'lt'),
    ('林加拉语', 'ln'),
    ('卢巴卡丹加语', 'lu'),
    ('卢欧语', 'umb'),
    ('罗马尼亚语', 'ro'),
    ('马耳他语', 'mt'),
    ('马其顿语', 'mk'),
    ('马拉提语', 'mr'),
    ('马拉亚拉姆语', 'ml'),
    ('马来语', 'ms'),
    ('马绍尔语', 'mh'),
    ('蒙古语', 'mn'),
    ('孟加拉语', 'bn'),
    ('闽南语', 'nan'),
    ('缅甸语', 'my'),
    ('南恩德贝勒语', 'nr'),
    ('尼日利亚富拉语', 'fuv'),
    ('挪威布克莫尔语', 'nb'),
    ('挪威语', 'no'),
    ('旁遮普语', 'pa'),
    ('葡萄牙语', 'pt'),
    ('奇楚瓦语', 'qu'),
    ('齐切瓦语', 'ny'),
    ('契维语', 'tw'),
    ('日语', 'ja'),
    ('瑞典语', 'sv'),
    ('萨摩亚语', 'sm'),
    ('塞尔维亚语', 'sr'),
    ('塞索托语', 'st'),
    ('桑戈语', 'sg'),
    ('绍纳语', 'sn'),
    ('世界语', 'eo'),
    ('史瓦帝语', 'ss'),
    ('斯洛伐克语', 'sk'),
    ('斯洛文尼亚语', 'sl'),
    ('斯瓦希里语', 'sw'),
    ('他加禄语', 'tl'),
    ('塔希提语', 'ty'),
    ('泰卢固语', 'te'),
    ('泰米尔语', 'ta'),
    ('泰语', 'th'),
    ('汤加语', 'to'),
    ('提格里尼亚语', 'ti'),
    ('土库曼语', 'tk'),
    ('土耳其语', 'tr'),
    ('威尔士语', 'cy'),
    ('维吾尔语', 'ug'),
    ('乌克兰语', 'uk'),
    ('乌尔都语', 'ur'),
    ('吴语', 'wuu'),
    ('西班牙语', 'es'),
    ('希伯来语', 'he'),
    ('希里莫图语', 'ho'),
    ('现代希腊语', 'el'),
    ('西南官话', 'cmn'),
    ('匈牙利语', 'hu'),
    ('亚美尼亚语', 'hy'),
    ('伊博语', 'ig'),
    ('伊努克提图特语', 'iu'),
    ('意大利语', 'it'),
    ('印尼语', 'id'),
    ('英语', 'en'),
    ('约鲁巴语', 'yo'),
    ('越南语', 'vi'),
    ('粤语', 'yue'),
    ('藏语', 'bo'),
    ('札那语', 'tn'),
    ('中文(简体)', 'zh'),
    ('中文(繁体)', 'zh-Hant'),
    ('中文(台湾繁体)', 'zh-Hant-tw'),
    ('中文(文言文)', 'lzh'),
    ('中文(香港繁体)', 'zh-Hant-hk'),
    ('中库尔德语', 'ckb'),
    ('祖鲁语', 'zu'),
)

# 常用目标语种表
_HUOSHAN_TO_LANGS = (
    ('中文(简体)', 'zh'),
    ('中文(繁体)', 'zh-Hant'),
    ('中文(文言文)', 'lzh'),
    ('英语', 'en'),
    ('日语', 'ja'),
    ('印地语', 'hi'),
    ('西班牙语', 'es'),
    ('法语', 'fr'),
    ('阿拉伯语', 'ar'),
    ('孟加拉语', 'bn'),
    ('葡萄牙语', 'pt'),
    ('俄语', 'ru'),
    ('乌尔都语', 'ur'),
    ('印尼语', 'id'),
    ('德语', 'de'),
    ('土耳其语', 'tr'),
    ('韩语', 'ko'),
    ('越南语', 'vi'),
    ('泰语', 'th'),
    ('意大利语', 'it'),
    ('旁遮普语', 'pa'),
    ('泰米尔语', 'ta'),
    ('马拉地语', 'mr'),
    ('波兰语', 'pl'),
    ('荷兰语', 'nl'),
    ('乌克兰语', 'uk'),
    ('瑞典语', 'sv'),
    ('捷克语', 'cs'),
    ('希腊语', 'el'),
    ('匈牙利语', 'hu'),
    ('罗马尼亚语', 'ro'),
    ('缅甸语', 'my'),
)
