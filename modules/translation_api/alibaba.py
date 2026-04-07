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

    def __init__(self, section='alibaba'):

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
        from_lang = self.check_text_and_lang(source_txt, from_lang, to_lang)
        if not from_lang:
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
                    wait = 2**attempt
                    print_info(f"{wait}秒后重试……")
                    time.sleep(wait)
                else:
                    raise ToolException(
                        'APIRequestErr',
                        f'错误代码：{code}，报错信息：{resp.body.message}',
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
        '''
        使用BearerToken初始化账号Client

        @param bearer_token: string Bearer Token
        @return: Client
        @throws Exception
        '''
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
        '''
        使用凭据初始化账号Client

        @return: Client
        @throws Exception
        '''

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
    'ab',
    'sq',
    'ak',
    'ar',
    'an',
    'am',
    'as',
    'az',
    'ast',
    'nch',
    'ee',
    'ay',
    'ga',
    'et',
    'oj',
    'oc',
    'or',
    'om',
    'os',
    'tpi',
    'ba',
    'eu',
    'be',
    'ber',
    'bm',
    'pag',
    'bg',
    'se',
    'bem',
    'byn',
    'bi',
    'bal',
    'is',
    'pl',
    'bs',
    'fa',
    'bho',
    'br',
    'ch',
    'cbk',
    'cv',
    'ts',
    'tt',
    'da',
    'shn',
    'tet',
    'de',
    'nds',
    'sco',
    'dv',
    'kdx',
    'dtp',
    'ru',
    'fo',
    'fr',
    'sa',
    'fil',
    'fj',
    'fi',
    'fur',
    'fvr',
    'kg',
    'km',
    'ngu',
    'kl',
    'ka',
    'gos',
    'gu',
    'gn',
    'kk',
    'ht',
    'ko',
    'ha',
    'nl',
    'cnr',
    'hup',
    'gil',
    'rn',
    'quc',
    'ky',
    'gl',
    'ca',
    'cs',
    'kab',
    'kn',
    'kr',
    'csb',
    'kha',
    'kw',
    'xh',
    'co',
    'mus',
    'crh',
    'tlh',
    'hbs',
    'qu',
    'ks',
    'ku',
    'la',
    'ltg',
    'lv',
    'lo',
    'lt',
    'li',
    'ln',
    'lg',
    'lb',
    'rue',
    'rw',
    'ro',
    'rm',
    'rom',
    'jbo',
    'mg',
    'gv',
    'mt',
    'mr',
    'ml',
    'ms',
    'chm',
    'mk',
    'mh',
    'kek',
    'mai',
    'mfe',
    'mi',
    'mn',
    'bn',
    'my',
    'hmn',
    'umb',
    'nv',
    'af',
    'ne',
    'niu',
    'no',
    'pmn',
    'pap',
    'pa',
    'pt',
    'ps',
    'ny',
    'tw',
    'chr',
    'ja',
    'sv',
    'sm',
    'sg',
    'si',
    'hsb',
    'eo',
    'sk',
    'sl',
    'sw',
    'so',
    'tl',
    'tg',
    'ty',
    'te',
    'ta',
    'th',
    'to',
    'toi',
    'ti',
    'tvl',
    'tyv',
    'tr',
    'tk',
    'wa',
    'war',
    'cy',
    've',
    'vo',
    'wo',
    'udm',
    'ur',
    'uz',
    'es',
    'ie',
    'fy',
    'szl',
    'he',
    'hil',
    'haw',
    'el',
    'lfn',
    'sd',
    'hu',
    'sn',
    'ceb',
    'syr',
    'su',
    'hy',
    'ace',
    'iba',
    'ig',
    'io',
    'ilo',
    'iu',
    'it',
    'yi',
    'ia',
    'hi',
    'id',
    'inh',
    'en',
    'yo',
    'vi',
    'zza',
    'jv',
    'zh',
    'zh-tw',
    'yue',
    'zu',
)

# 所有支持的源语种表
_ALIBABA_FROM_LANGS = (
    ('自动检测', 'auto'),
    ('阿布哈兹语', 'ab'),
    ('阿尔巴尼亚语', 'sq'),
    ('阿肯语', 'ak'),
    ('阿拉伯语', 'ar'),
    ('阿拉贡语', 'an'),
    ('阿姆哈拉语', 'am'),
    ('阿萨姆语', 'as'),
    ('阿塞拜疆语', 'az'),
    ('阿斯图里亚斯语', 'ast'),
    ('阿兹特克语', 'nch'),
    ('埃维语', 'ee'),
    ('艾马拉语', 'ay'),
    ('爱尔兰语', 'ga'),
    ('爱沙尼亚语', 'et'),
    ('奥杰布瓦语', 'oj'),
    ('奥克语', 'oc'),
    ('奥里亚语', 'or'),
    ('奥罗莫语', 'om'),
    ('奥塞梯语', 'os'),
    ('巴布亚皮钦语', 'tpi'),
    ('巴什基尔语', 'ba'),
    ('巴斯克语', 'eu'),
    ('白俄罗斯语', 'be'),
    ('柏柏尔语', 'ber'),
    ('班巴拉语', 'bm'),
    ('邦阿西楠语', 'pag'),
    ('保加利亚语', 'bg'),
    ('北萨米语', 'se'),
    ('本巴语', 'bem'),
    ('比林语', 'byn'),
    ('比斯拉马语', 'bi'),
    ('俾路支语', 'bal'),
    ('冰岛语', 'is'),
    ('波兰语', 'pl'),
    ('波斯尼亚语', 'bs'),
    ('波斯语', 'fa'),
    ('博杰普尔语', 'bho'),
    ('布列塔尼语', 'br'),
    ('查莫罗语', 'ch'),
    ('查瓦卡诺语', 'cbk'),
    ('楚瓦什语', 'cv'),
    ('聪加语', 'ts'),
    ('鞑靼语', 'tt'),
    ('丹麦语', 'da'),
    ('掸语', 'shn'),
    ('德顿语', 'tet'),
    ('德语', 'de'),
    ('低地德语', 'nds'),
    ('低地苏格兰语', 'sco'),
    ('迪维西语', 'dv'),
    ('侗语', 'kdx'),
    ('杜順語', 'dtp'),
    ('俄语', 'ru'),
    ('法罗语', 'fo'),
    ('法语', 'fr'),
    ('梵语', 'sa'),
    ('菲律宾语', 'fil'),
    ('斐济语', 'fj'),
    ('芬兰语', 'fi'),
    ('弗留利语', 'fur'),
    ('富尔语', 'fvr'),
    ('刚果语', 'kg'),
    ('高棉语', 'km'),
    ('格雷罗纳瓦特尔语', 'ngu'),
    ('格陵兰语', 'kl'),
    ('格鲁吉亚语', 'ka'),
    ('格罗宁根方言', 'gos'),
    ('古吉拉特语', 'gu'),
    ('瓜拉尼语', 'gn'),
    ('哈萨克语', 'kk'),
    ('海地克里奥尔语', 'ht'),
    ('韩语', 'ko'),
    ('豪萨语', 'ha'),
    ('荷兰语', 'nl'),
    ('黑山语', 'cnr'),
    ('胡帕语', 'hup'),
    ('基里巴斯语', 'gil'),
    ('基隆迪语', 'rn'),
    ('基切语', 'quc'),
    ('吉尔吉斯斯坦语', 'ky'),
    ('加利西亚语', 'gl'),
    ('加泰罗尼亚语', 'ca'),
    ('捷克语', 'cs'),
    ('卡拜尔语', 'kab'),
    ('卡纳达语', 'kn'),
    ('卡努里语', 'kr'),
    ('卡舒比语', 'csb'),
    ('卡西语', 'kha'),
    ('康沃尔语', 'kw'),
    ('科萨语', 'xh'),
    ('科西嘉语', 'co'),
    ('克里克语', 'mus'),
    ('克里米亚鞑靼语', 'crh'),
    ('克林贡语', 'tlh'),
    ('克罗地亚语', 'hbs'),
    ('克丘亚语', 'qu'),
    ('克什米尔语', 'ks'),
    ('库尔德语', 'ku'),
    ('拉丁语', 'la'),
    ('拉特加莱语', 'ltg'),
    ('拉脱维亚语', 'lv'),
    ('老挝语', 'lo'),
    ('立陶宛语', 'lt'),
    ('林堡语', 'li'),
    ('林加拉语', 'ln'),
    ('卢干达语', 'lg'),
    ('卢森堡语', 'lb'),
    ('卢森尼亚语', 'rue'),
    ('卢旺达语', 'rw'),
    ('罗马尼亚语', 'ro'),
    ('罗曼什语', 'rm'),
    ('罗姆语', 'rom'),
    ('逻辑语', 'jbo'),
    ('马达加斯加语', 'mg'),
    ('马恩语', 'gv'),
    ('马耳他语', 'mt'),
    ('马拉地语', 'mr'),
    ('马拉雅拉姆语', 'ml'),
    ('马来语', 'ms'),
    ('马里语（俄罗斯）', 'chm'),
    ('马其顿语', 'mk'),
    ('马绍尔语', 'mh'),
    ('玛雅语', 'kek'),
    ('迈蒂利语', 'mai'),
    ('毛里求斯克里奥尔语', 'mfe'),
    ('毛利语', 'mi'),
    ('蒙古语', 'mn'),
    ('孟加拉语', 'bn'),
    ('缅甸语', 'my'),
    ('苗语', 'hmn'),
    ('姆班杜语', 'umb'),
    ('纳瓦霍语', 'nv'),
    ('南非语', 'af'),
    ('尼泊尔语', 'ne'),
    ('纽埃语', 'niu'),
    ('挪威语', 'no'),
    ('帕姆语', 'pmn'),
    ('帕皮阿门托语', 'pap'),
    ('旁遮普语', 'pa'),
    ('葡萄牙语', 'pt'),
    ('普什图语', 'ps'),
    ('齐切瓦语', 'ny'),
    ('契维语', 'tw'),
    ('切罗基语', 'chr'),
    ('日语', 'ja'),
    ('瑞典语', 'sv'),
    ('萨摩亚语', 'sm'),
    ('桑戈语', 'sg'),
    ('僧伽罗语', 'si'),
    ('上索布语', 'hsb'),
    ('世界语', 'eo'),
    ('斯洛伐克语', 'sk'),
    ('斯洛文尼亚语', 'sl'),
    ('斯瓦希里语', 'sw'),
    ('索马里语', 'so'),
    ('他加禄语', 'tl'),
    ('塔吉克语', 'tg'),
    ('塔希提语', 'ty'),
    ('泰卢固语', 'te'),
    ('泰米尔语', 'ta'),
    ('泰语', 'th'),
    ('汤加语（汤加群岛）', 'to'),
    ('汤加语（赞比亚）', 'toi'),
    ('提格雷尼亚语', 'ti'),
    ('图瓦卢语', 'tvl'),
    ('图瓦语', 'tyv'),
    ('土耳其语', 'tr'),
    ('土库曼语', 'tk'),
    ('瓦隆语', 'wa'),
    ('瓦瑞语（菲律宾）', 'war'),
    ('威尔士语', 'cy'),
    ('文达语', 've'),
    ('沃拉普克语', 'vo'),
    ('沃洛夫语', 'wo'),
    ('乌德穆尔特语', 'udm'),
    ('乌尔都语', 'ur'),
    ('乌孜别克语', 'uz'),
    ('西班牙语', 'es'),
    ('西方国际语', 'ie'),
    ('西弗里斯兰语', 'fy'),
    ('西里西亚语', 'szl'),
    ('希伯来语', 'he'),
    ('希利盖农语', 'hil'),
    ('夏威夷语', 'haw'),
    ('现代希腊语', 'el'),
    ('新共同语言', 'lfn'),
    ('信德语', 'sd'),
    ('匈牙利语', 'hu'),
    ('修纳语', 'sn'),
    ('宿务语', 'ceb'),
    ('叙利亚语', 'syr'),
    ('巽他语', 'su'),
    ('亚美尼亚语', 'hy'),
    ('亚齐语', 'ace'),
    ('伊班语', 'iba'),
    ('伊博语', 'ig'),
    ('伊多语', 'io'),
    ('伊洛卡诺语', 'ilo'),
    ('伊努克提图特语', 'iu'),
    ('意大利语', 'it'),
    ('意第绪语', 'yi'),
    ('因特语', 'ia'),
    ('印地语', 'hi'),
    ('印度尼西亚语', 'id'),
    ('印古什语', 'inh'),
    ('英语', 'en'),
    ('约鲁巴语', 'yo'),
    ('越南语', 'vi'),
    ('扎扎其语', 'zza'),
    ('爪哇语', 'jv'),
    ('中文', 'zh'),
    ('中文繁体', 'zh-tw'),
    ('中文粤语', 'yue'),
    ('祖鲁语', 'zu'),
)

# 常用目标语种表
_ALIBABA_TO_LANGS = (
    ('中文', 'zh'),
    ('中文繁体', 'zh-tw'),
    ('中文粤语', 'yue'),
    ('英语', 'en'),
    ('印地语', 'hi'),
    ('西班牙语', 'es'),
    ('阿拉伯语', 'ar'),
    ('法语', 'fr'),
    ('孟加拉语', 'bn'),
    ('葡萄牙语', 'pt'),
    ('俄语', 'ru'),
    ('乌尔都语', 'ur'),
    ('印度尼西亚语', 'id'),
    ('德语', 'de'),
    ('日语', 'ja'),
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
