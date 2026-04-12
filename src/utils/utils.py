#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-10 23:33:35

工具集
"""

import ast
import base64
import copy
import getpass
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import time
import uuid
from configparser import ConfigParser
from datetime import datetime
from hashlib import md5
from itertools import cycle

import chardet

# import pwinput
import py3langid

from src.exception.tool_exception import ToolException


def print_debug(value: str):
    """
    打印调试信息，绿色字体，生产环境下屏蔽
    """
    if GLOBAL_DATA["debug"]:
        print(f"\033[0;32;40mDEBUG: {value}\033[0m")


def print_err(value: str):
    """
    打印错误消息，红色字体
    """
    print(f"\033[0;31;40mERROR: {value}\033[0m")


def print_info(value: str):
    """
    打印完成消息，绿色字体
    """
    print(f"\033[0;32;40mINFO: {value}\033[0m")


def print_warn(value: str):
    """
    打印警告消息，黄色字体
    """
    print(f"\033[0;33;40mWARNING: {value}\033[0m")


# 全局变量
GLOBAL_DATA = {
    "debug": False,
    "open_todo": False,
    "rpy_trans_input_abspath": "",
    "rpy_trans_bap_max_cache": 0,
    "rpy_update_old_abspath": "",
    "rpy_update_new_abspath": "",
    "rpy_update_bap_max_cache": 0,
    "none_filter": "NONE",
    "pass_filter": [],
    "json_max_cache": 0,
    "rpg_white_list": [],
    "rpg_duplicate_removal_list": [],
    "rpg_type_array_object": [],
    "rpg_script_regexp": [],
    "rpg_game_default_txt": "gameText.json",
    "tencent": False,
    "alibaba": False,
    "baidu": False,
    "caiyun": False,
    "huoshan": False,
    "xiaoniu": False,
    "xunfei": False,
    "youdao": False,
    "deepL": False,
    "google": False,
    "ollama": False,
    "hunyuan_mt": False,
}

# 项目所在绝对路径
BASE_ABSPATH = pathlib.Path(__file__).parent.parent.parent
# 项目代码绝对路径
SRC_ABSPATH = os.path.join(BASE_ABSPATH, "src")

# 配置文件绝对路径
CONFIG_ABSPATH = os.path.join(BASE_ABSPATH, "config.ini")

# rpgm项目工作区的绝对路径
RPGM_PROJECT_PARENT_FOLDER = os.path.join(BASE_ABSPATH, "RPGM Workspace")

# renpy项目工作区的绝对路径
RENPY_PROJECT_PARENT_FOLDER = os.path.join(BASE_ABSPATH, "RenPy Workspace")
# 存放rpgm初始data游戏数据目录的绝对路径
RPGM_INPUT_ABSPATH = os.path.join(BASE_ABSPATH, "RPGM Data Input")
# 存放生成的rpgm新data游戏数据目录的绝对路径
RPGM_OUTPUT_ABSPATH = os.path.join(BASE_ABSPATH, "RPGM Data Output")

# 译文库
TRANSLATED_LIB_LIBRARY_FILE = "TransLib.json"

# 待处理标记，此处写死，避免用户修改导致文本不通用
MARK_TODO = "TODO"

# json更新标记
KEY_PHOENIX = "__PHOENIX__"

# JSON翻译文本中标记当前率属于的文件名
TRANSLATED_FILE_MARK = "<==M==A==R==K==> "

# 正则：匹配空行
PATTERN_EMPTY_LINE = re.compile(r"^\s*$")
# 正则：匹配rpy的文本标识符行
PATTERN_IDENTIFIER = re.compile(r"^\s*translate\s*.*\s(.*):")
# 正则：匹配rpy的old语句
PATTERN_OLD = re.compile(r'^\s*old\s*"(.*)"')
# 正则：匹配rpy的new语句
PATTERN_NEW = re.compile(r'^\s*new\s*"(.*)"')
# 正则匹配rpy的say原文
PATTERN_OLD_SAY = re.compile(r'^\s*#+\s*(".*?[^\\]"|[\S\s]*?)\s*"(.*)"')
# 正则：匹配rpy的say译文
PATTERN_NEW_SAY = re.compile(r'(?!\s*#+)\s*(".*?[^\\]"|[\S\s]*?)\s*"(.*)"\s*(.*)')
# 正则：匹配rpy的who
PATTERN_WHO = re.compile(r'^"(.*?[^\\])"')
# 正则：匹配注释符号
PATTERN_ANNOTATION = re.compile(r"^\s*#\s*")
# 正则：匹配rpg的Mapxxx.json文件
PATTERN_MAP = re.compile(r"^Map\d{3}$")


def get_md5(parm_str: any, cut=False) -> str:
    """
    获取字符串32/16位md5值

    - parm_str: 要计算md5值的数据
    - cut：是否截取中间16位md5值，默认返回完整32位
    """

    # 创建一个md5对象
    m = md5()
    # 更新哈希对象，这里需要将字符串转换为字节
    m.update(str(parm_str).encode("utf-8"))
    # 获取十六进制格式的哈希值
    value = m.hexdigest()
    return value[8:-8] if cut else value


def merge_dicts(dicts: list[dict], rewrite=True) -> dict:
    """
    将多个字典合并成一个字典

    - dicts: 要合并的字典列表
    - rewrite: 遇到相同key时，后面字典的值是否覆盖前面字典的值。默认覆盖
    """

    if not dicts:
        return None

    if len(dicts) == 1:
        if not dicts[0] or not isinstance[dicts[0], dict]:
            return None

    # 若要后面字典的值不覆盖前面字典的值，则反转传入的字典列表
    if rewrite is False:
        dicts = dicts.reverse()

    # 深拷贝首个字典作为新字典的初始字典，避免影响原有字典
    merged_dict = copy.deepcopy(dicts[0])
    for idx, _dict in enumerate(dicts):
        if idx == 0 or not _dict or not isinstance(_dict, dict):
            continue
        # 此种合并方式遇到相同key，后面字典的值会覆盖前面的值
        merged_dict.update(_dict)

    return merged_dict


def del_key_from_dict(key: str, datas=None) -> bool:
    """
    删除字典中指定key元素

    - key: 要删除的key
    - datas: 要调整的字典
    """

    if not datas or not isinstance(datas, dict):
        return datas

    key = key.strip()
    if key == "" or key not in datas:
        return datas

    # 深拷贝字典，避免影响到原字典
    _dict = copy.deepcopy(datas)
    del _dict[key]
    return _dict


def read_json(file_path: str):
    """
    读取JSON文件，并将其转换成python对象

    - _file: 文件的绝对路径
    """

    filename = os.path.basename(file_path)
    if not os.path.exists(file_path):
        print_warn(f"{filename}的路径不存在！")
        return None
    if not os.path.isfile(file_path):
        print_warn(f"{filename}不是文件")
        return None

    try:
        with open(file_path, "r", encoding=get_file_encoding(file_path)) as f:
            json_data = json.load(f)
        print_debug(f"{filename}是标准JSON文件！")
        return json_data
    except json.JSONDecodeError:
        print_err(f"{filename}不是标准JSON文件！")
        return None


def write_json(_file: str, datas=None, *, indent=4, backup=True):
    """
    将python对象转换成JSON格式并写入文件

    - _file: 文件的绝对路径
    - datas: 要写入json的数据
    - indent: JSON每个层级的缩进长度
    - backup: 是否备份原文件。默认备份
    """

    if datas is None:
        print_warn(f"要写入JSON文件的数据不存在：{_file}")
        return

    file_is_exist = os.path.exists(_file)
    _path, _filename = os.path.split(_file)
    # 如果路径存在
    if file_is_exist:
        # 如果不是文件路径，返回
        if not os.path.isfile(_file):
            print_warn(f"路径非文件：{_file}")
            return
        # 如果文件需要备份
        if backup:
            copy_file(_file, os.path.join(_path, "bak"))

    try:
        with open(_file, "w", encoding=get_file_encoding(_file)) as fp:
            if file_is_exist:
                print(f"正在更新 {_filename} 中……")
            else:
                print(f"正在创建 {_filename} 中……")
            json.dump(datas, fp, indent=indent, skipkeys=True, ensure_ascii=False)
            if file_is_exist:
                print_info(f"{_filename} 已更新！\n")
            else:
                print_info(f"{_filename} 已创建！\n")
    except Exception as e:
        raise ToolException(
            "WriteFileErr", f"write_json()写入{_filename}异常：{str(e)}"
        ) from e


def copy_file(source_file: str, target_dir: str, time_mark=True):
    """
    将文件拷贝到指定路径。

    - source_file: 要拷贝的文件路径
    - target_dir: 拷贝文件存放目录路径
    - time_mark: 是否在文件名后面加上拷贝日期时间。默认添加
    """

    if not os.path.isfile(source_file) or not os.path.isdir(target_dir):
        return

    pathlib.Path(target_dir).mkdir(parents=True, exist_ok=True)

    new_file = source_file
    if time_mark:
        source_file_path = pathlib.Path(source_file)
        new_file = (
            source_file_path.stem
            + "_"
            + datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            + source_file_path.suffix
        )
    shutil.copy(source_file, os.path.join(target_dir, new_file))


def copy_directory(source_path: str, target_path: str):
    """
    拷贝目录和文件

    :param source_path: 原路径，可以是文件夹也可以是文件路径
    :param target_path: 目标路径
    """

    src_path = pathlib.Path(source_path)
    if not src_path.exists():
        print_err(f"待拷贝路径不存在：{src_path} ")
        return

    dest_path = pathlib.Path(target_path)
    # 确保目标路径存在
    dest_path.mkdir(parents=True, exist_ok=True)

    # 待拷贝对象是文件
    if src_path.is_file():
        shutil.copy(src_path, dest_path)
        return

    for item in src_path.iterdir():
        target = dest_path / item.name
        if item.is_dir():
            copy_directory(item, target)
        else:
            shutil.copy(item, target)


def to_int(val: any) -> int:
    """
    将数字字符串转成整形。非数字字符串则返回0
    """

    try:
        res = int(val)
        return res
    except ValueError:  # 报类型错误，说明不是整型的
        try:
            ress = float(val)  # 用这个来验证是不是浮点字符串
            return int(ress)
        # 如果报错，说明即不是浮点，也不是int字符串，是一个真正的字符串
        except ValueError:
            print_err(f"传入的值{val} 非数字符串！")
            return 0


def to_float(val: any) -> float:
    """
    将数字字符串转成浮点数。非数字字符串则返回0
    """

    try:
        float_num = float(val)
        return float_num
    except (ValueError, SyntaxError):
        print_err(f"传入的值{val} 非浮点数字符串！")
        return 0


def to_boolean(val: any) -> bool:
    """
    将布尔字符串转成布尔值。非布尔字符串则返回False
    """

    try:
        _bool = ast.literal_eval(val)
        return _bool
    except (ValueError, SyntaxError):
        print_err(f"传入的值{val} 非布尔字符串！")
        return False


def is_uuid_v1(val: str) -> bool:
    """
    验证字符串是否是UUID
    """
    # ^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}(?::(?:fx|adm))?$
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False


def is_int(val: any) -> bool:
    """
    判断传入参数是否是整型纯数字
    """

    try:
        int(val)
        return True
    except ValueError:
        return False


def is_all_digits(string: str, length: int) -> bool:
    """
    校验字串是否是全数字，若不指定长度，则检查整个字符串是否符合
    """

    if not string:
        return False

    if not length:
        length = len(string)
    pattern = r"^\d{" + str(length) + r"}$"
    return bool(re.match(pattern, string))


def is_letters_and_digits(string: str, length: int) -> bool:
    """
    检查字符串是否由指定长度的大小写字母和数字组成，若不指定长度，则检查整个字符串是否符合
    """
    if not string:
        return False

    if not length:
        length = len(string)
    pattern = r"^[A-Za-z0-9]{" + str(length) + r"}$"
    return bool(re.match(pattern, string))


def validate_lang(txt: str) -> str:
    """
    检测语言，查询结果参考ISO 639-1语言编码标准
    """

    if txt.strip() == "":
        return "auto"

    return py3langid.classify(txt)[0]


def match_lang(txt: str, lang: str) -> bool:
    """
    匹配符合指定列表中语种的文本。匹配返回True，反之返回False。
    由于语言检测程序的限制，此方法存在一定误差。

    - txt: 待匹配文本
    - langs: 语种列表只能是字符串的形式，多种语种可用','隔开的形式，如：'zh,ru'
    """

    # 传入的待匹配文本为空字符串或语种列表为空字符串时，返回True
    if txt.strip() == "" or lang.strip() == "":
        return True

    # try:
    #     if langid.classify(txt)[0] != 'en':
    #         return True
    # except Exception as e:
    #     return False

    # return False

    langlist = lang.split(",")

    for lang in langlist:
        lang = lang.strip()
        if lang == "":
            continue

        try:
            if py3langid.classify(txt)[0] == lang:
                return True
        except Exception:
            continue
    return False


def full_2_half(txt: str) -> str:
    """
    将字符串中的全角符号转换成半角符号
    """

    txt_new = ""

    for char in txt:
        s_int = ord(char)
        # 单独处理空格
        if s_int == 12288:
            s_int = 32
        elif 65281 <= s_int <= 65374:
            s_int -= 65248
        else:
            txt_new += char
            continue

        half = chr(s_int)
        txt_new += half

    return txt_new


def half_2_full(txt: str) -> str:
    """
    将字符串中的半角符号转换成全角符号
    """

    txt_new = ""
    for char in txt:
        s_int = ord(char)
        # 单独处理空格
        if s_int == 32:
            s_int = 12288
        elif 33 <= s_int <= 126:
            s_int += 65248
        else:
            txt_new += char
            continue

        full = chr(s_int)
        txt_new += full

    return txt_new


def zhpun_2_enpun(txt: str) -> str:
    """
    将字符串中的中文标点符号转换为英文标点符号
    """

    # 处理常用标点符号
    chs_pun = "，。！？：；（）【】《》`“”‘’"
    en_pun = ",.!?:;()[]<>·\"\"''"
    trantab = str.maketrans(chs_pun, en_pun)
    txt = txt.translate(trantab)
    return txt


def enpun_2_zhpun(txt: str, no_blank=False) -> str:
    """
    将字符串中的英文标点符号转换为中文标点符号
    """

    # 使用迭代器处理单引号。
    # 由于英文中存在使用'来表示名词的所有格以及缩写等作用，只存在单个单引号，所以不便直接使用迭代器进行替换。
    # def _obj():
    #     return next(cycle(['‘', '’']))

    # s = re.sub(r"[\']", _obj(), s)

    # 使用迭代器处理双引号
    def _obj2():
        return next(cycle(["“", "”"]))

    txt = re.sub(r"[\"]", _obj2(), txt)

    # 处理常用标点符号
    # E_pun = u',.!?:;[]()<>'
    # C_pun = u'，。！？：；【】（）《》'
    # E_pun = u',!?:;()<>'
    # C_pun = u'，！？：；（）《》'
    # trantab = str.maketrans(E_pun, C_pun)
    # s = s.translate(trantab)

    # 删除字符串中的空行
    if no_blank:
        txt = txt.replace(" ", "")
    return txt


def has_upper_letter(txt: str) -> bool:
    """
    查询字符串中是否含有大写英文字母，没有返回False；反之返回True
    """

    if txt.strip() == "":
        return False

    my_re = re.compile(r"[A-Z]", re.S)
    res = re.findall(my_re, txt)
    if not res:
        return False

    return True


def has_lower_letter(txt: str) -> bool:
    """
    查询字符串中是否含有小写英文字母，没有返回False；反之返回True
    """

    if txt.strip() == "":
        return False

    my_re = re.compile(r"[a-z]", re.S)
    res = re.findall(my_re, txt)
    if not res:
        return False

    return True


def remove_escapes(txt: str) -> str:
    """
    删除文本中的转义字符，避免云翻译因转义字符的影响导致漏翻或语意错误
    """

    if txt.strip() == "":
        return txt

    # TODO 这里的处理过于粗糙，需要进一步优化
    txt = txt.replace(r"\"", '"')
    txt = txt.replace(r"\'", "'")
    txt = txt.replace(r"\a", "")
    txt = txt.replace(r"\b", "")
    txt = txt.replace(r"\n", "")
    txt = txt.replace(r"\v", "")
    txt = txt.replace(r"\t", "")
    txt = txt.replace(r"\r", "")
    txt = txt.replace(r"\f", "")
    txt = txt.replace("‘", "'")
    txt = txt.replace("’", "'")
    txt = txt.replace("“", '"')
    txt = txt.replace("”", '"')
    return txt


def update_phoenix_mark(datas=None, update=False):
    """
    切换JSON文本更新标记
    """

    if datas is None or not isinstance(datas, dict) or KEY_PHOENIX not in datas:
        return

    datas[KEY_PHOENIX] = update


def switch_change_mark(base=False, change=False) -> bool:
    """
    切换更改标记
    """
    if not change:
        return base
    return change


def get_file_encoding(file_path: str) -> str:
    """
    获取文本编码
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result["encoding"]

        # Check for BOM
        if raw_data.startswith(b"\xef\xbb\xbf"):
            encoding = "utf-8-sig"
        elif raw_data.startswith(b"\xff\xfe"):
            encoding = "utf-16"
        elif raw_data.startswith(b"\xfe\xff"):
            encoding = "utf-16"
        else:
            encoding = "utf-8"
    except Exception:
        encoding = "utf-8"

    return encoding


def validate_renpy_trans_file(file_path: str) -> bool:
    """
    判断指定文件是否是Ren'Py翻译文件。

    - file_path: 文件绝对路径
    """

    if not os.path.exists(file_path):
        return False

    f = os.path.split(file_path)[-1]
    # 只处理可以被renPy直接读取的后缀，其他后缀的文件即便内容是标准renPy翻译文本，也不进行处理
    if not f.endswith((".rpy", ".rpym")):
        return False

    with open(file_path, "r", encoding=get_file_encoding(file_path)) as inp:
        # 只需要读取开头部分用来判断即可
        lines = inp.read(1024)
    for line in lines:
        # 如果能匹配到translate标识符，则返回True
        if PATTERN_IDENTIFIER.match(line) is not None:
            return True
    return False


def get_projects_list(_type: str) -> list:
    """
    获取现有项目的名称列表，否则返回空列表

    :param _type: 获取哪种引擎的列表
    """

    if _type == "renpy":
        # 判断ren'Py项目工作区是否存在，不存在则新建一个，并返回空列表
        _path = pathlib.Path(RENPY_PROJECT_PARENT_FOLDER)
        if not _path.exists():
            _path.mkdir(parents=True)
            return []

        # 获取所有翻译文件夹
        folders = [item.name for item in _path.iterdir() if item.is_dir()]
        return folders

    elif _type == "rpgm":
        # 判断rpgm项目工作区是否存在，不存在则新建一个，并返回空列表
        _path = pathlib.Path(RPGM_PROJECT_PARENT_FOLDER)
        if not _path.exists():
            _path.mkdir(parents=True)
            return []

        # 获取所有JSON文件
        files = [
            item.name
            for item in _path.iterdir()
            if item.is_file() and item.name.endswith(".json")
        ]
        return files

    else:
        return []


def hashlib_256(res: str) -> str:
    """
    对传入的字串进行SHA256计算，把计算结果进行Base64编码后输出

    :param res: 要加密的字串
    """
    m = hashlib.sha256(bytes(res.encode(encoding="utf-8"))).digest()
    result = base64.b64encode(m).decode(encoding="utf-8")
    return result


def validate_index(lst: list | tuple | str, index=0, with_negative=True) -> bool:
    """
    判断索引是否有效（支持负索引）

    :param lst: 要查询的对象
    :param index: 给定的索引值
    :param with_negative: 是否支持负索引
    """

    lst_length = len(lst)
    if lst_length < 1:
        return False
    if with_negative:
        return -lst_length <= index < lst_length
    return 0 <= index < lst_length


def acquire_token(qps=1, tokens=1, last_refill=0):
    """
    令牌桶限流器

    :param qps: 请求频率
    :param tokens: 当前令牌数
    :param last_refill: 最新补充令牌时间
    """

    now = time.time()
    # 补充令牌
    elapsed = now - last_refill
    tokens = min(qps, tokens + elapsed * qps)
    last_refill = now

    if tokens < 1:
        wait_time = (1 - tokens) / qps
        time.sleep(wait_time)
        tokens = 0
    else:
        tokens -= 1

    return tokens, last_refill


def read_config(config_path="") -> ConfigParser | None:
    """
    读取项目配置文件
    """

    if not config_path:
        config_path = CONFIG_ABSPATH
    if not os.path.exists(config_path) or not os.path.isfile(config_path):
        return None
    conf = ConfigParser()  # 调用读取配置模块中的类
    conf.optionxform = lambda option: option
    conf.read(config_path, encoding=get_file_encoding(config_path))
    return conf


def write_config(section: str, keys=None, add=True) -> bool:
    """
    写入项目配置文件

    :param section: 配置文件节点名称
    :param keys: 键值对字典
    :param add: 新增/修改配置 or 删减配置
    """

    if not section or not isinstance(section, str):
        return False
    if not keys or not isinstance(keys, dict):
        return False

    # 读取配置文件，如果值为None说明未读取到，直接返回
    conf = read_config()
    if conf is None:
        return False

    section = section.strip()
    if not conf.has_section(section):
        conf.add_section(section)
        # 删减模式下直接返回
        if not add:
            return False

    for key, item in keys.items():
        if add:
            conf.set(section, key, item)
        else:
            conf.remove_option(section, key)

    copy_file(CONFIG_ABSPATH, BASE_ABSPATH)
    with open(CONFIG_ABSPATH, "w", encoding=get_file_encoding(CONFIG_ABSPATH)) as f:
        conf.write(f)
    return True


def get_password_with_mask(prompt="请输入密码: "):
    """
    控制台输入敏感内容非明文显示，返回实际输入内容

    :param prompt: 控制台显示的提示语
    """

    # 掩码显示
    # todo 存在输入长度超过命令行窗口宽度自动换行后无法退格到上一行的问题，会导致命令行窗口卡死，只能关闭重启
    # inp = pwinput.pwinput(prompt, mask="*")
    # return inp.strip()

    # 空白显示，这个方法不会遇到掩码显示的超长自动换行的问题，但不够直观
    inp = getpass.getpass(prompt)
    return inp.strip()


def get_value_from_library(source_txt: str):
    """
    从译文库中获取译文
    """

    if (
        source_txt in TRANSLATED_LIB_LIBRARY
        and TRANSLATED_LIB_LIBRARY[source_txt] != ""
    ):
        target = TRANSLATED_LIB_LIBRARY[source_txt]
        print(f"库译文：{target}\n")
        return target
    return ""


def waiit_key_or_enter(prompt="按任意键继续或按回车退出程序："):
    """
    获取输入，回车返回True，任意键返回False

    :Param prompt: 控制台提示语
    """

    print(prompt, end="", flush=True)
    key = get_key()
    print()  # 换行
    return key in ("", "\r", "\n")  # 回车返回True


def get_key() -> str:
    """
    跨平台获取单个按键（Windows用msvcrt，Unix-like用termios）
    """
    if sys.platform == "win32":
        import msvcrt

        return msvcrt.getch().decode("utf-8", errors="ignore")
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


def get_config():
    """
    调用get方法，获取配置的数据
    """

    conf = read_config()
    if conf is None:
        return

    GLOBAL_DATA["debug"] = conf.getboolean("common_settings", "debug")
    GLOBAL_DATA["open_todo"] = conf.getboolean("common_settings", "open_todo")
    GLOBAL_DATA["none_filter"] = conf.get("filter_texts", "none_filter")
    GLOBAL_DATA["pass_filter"] = (
        conf.get("filter_texts", "pass_filter").upper().split(",")
    )
    GLOBAL_DATA["rpy_trans_input_abspath"] = conf.get(
        "rpy_trans_tool", "rpy_input_abspath"
    )

    rpy_bap_max_cache = conf.getint("rpy_trans_tool", "rpy_bap_max_cache")
    if rpy_bap_max_cache > 0:
        GLOBAL_DATA["rpy_trans_bap_max_cache"] = rpy_bap_max_cache

    GLOBAL_DATA["rpy_update_old_abspath"] = conf.get(
        "rpy_update_tool", "rpy_old_abspath"
    )
    GLOBAL_DATA["rpy_update_new_abspath"] = conf.get(
        "rpy_update_tool", "rpy_new_abspath"
    )

    rpy_bap_max_cache = conf.getint("rpy_update_tool", "rpy_bap_max_cache")
    if rpy_bap_max_cache > 0:
        GLOBAL_DATA["rpy_update_bap_max_cache"] = rpy_bap_max_cache

    json_max_cache = conf.getint("json_trans_tool", "json_max_cache")
    if json_max_cache > 0:
        GLOBAL_DATA["json_max_cache"] = json_max_cache

    GLOBAL_DATA["rpg_game_default_txt"] = conf.get(
        "rpgm_extraction_writing", "rpg_game_default_txt"
    )
    GLOBAL_DATA["rpg_white_list"] = conf.get(
        "rpgm_extraction_writing", "rpg_white_list"
    ).split(",")
    GLOBAL_DATA["rpg_duplicate_removal_list"] = conf.get(
        "rpgm_extraction_writing", "rpg_duplicate_removal_list"
    ).split(",")
    GLOBAL_DATA["rpg_type_array_object"] = conf.get(
        "rpgm_extraction_writing", "rpg_type_array_object"
    ).split(",")
    GLOBAL_DATA["rpg_script_regexp"] = conf.get(
        "rpgm_extraction_writing", "rpg_script_regexp"
    ).split(",")
    GLOBAL_DATA["tencent"] = conf.getboolean("tencent", "activate")
    GLOBAL_DATA["alibaba"] = conf.getboolean("alibaba", "activate")
    GLOBAL_DATA["baidu"] = conf.getboolean("baidu", "activate")
    GLOBAL_DATA["caiyun"] = conf.getboolean("caiyun", "activate")
    GLOBAL_DATA["huoshan"] = conf.getboolean("huoshan", "activate")
    GLOBAL_DATA["xiaoniu"] = conf.getboolean("xiaoniu", "activate")
    GLOBAL_DATA["xunfei"] = conf.getboolean("xunfei", "activate")
    GLOBAL_DATA["youdao"] = conf.getboolean("youdao", "activate")
    GLOBAL_DATA["deepL"] = conf.getboolean("deepL", "activate")
    GLOBAL_DATA["google"] = conf.getboolean("google", "activate")
    GLOBAL_DATA["ollama"] = conf.getboolean("ollama", "activate")
    GLOBAL_DATA["hunyuan_mt"] = conf.getboolean("hunyuan_mt", "activate")


TRANSLATED_LIB_LIBRARY = read_json(
    os.path.join(BASE_ABSPATH, "Translated Libraries", TRANSLATED_LIB_LIBRARY_FILE)
)
