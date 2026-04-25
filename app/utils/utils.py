#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-08-10 23:33:35

工具集
"""

from ast import literal_eval
from base64 import b64encode
from configparser import ConfigParser
from copy import deepcopy
from datetime import datetime
from getpass import getpass
from hashlib import md5, sha256
from itertools import cycle
from json import JSONDecodeError, dump, load
from pathlib import Path
from re import S, compile, findall, match, sub
from shutil import copy
from sys import platform, stdin
from time import sleep, time
from uuid import UUID

from chardet import detect
from py3langid import classify

from app.utils.global_data import GlobalData


def print_debug(value: str):
    """
    打印调试信息，绿色字体，生产环境下屏蔽
    """
    if GlobalData.debug:
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


def get_md5(parm_str: any, cut=False) -> str:
    """
    获取字符串32/16位md5值

    :param parm_str: 要计算md5值的数据
    :param cut：是否截取中间16位md5值，默认返回完整32位
    """

    # 创建一个md5对象
    m = md5()
    # 更新哈希对象，这里需要将字符串转换为字节
    m.update(str(parm_str).encode("utf-8"))
    # 获取十六进制格式的哈希值
    value = m.hexdigest()
    return value[8:-8] if cut else value


def merge_dicts(dicts: list[dict], rewrite: bool = True) -> dict:
    """
    将多个字典合并成一个字典

    :param dicts: 要合并的字典列表
    :param rewrite: 遇到相同key时，后面字典的值是否覆盖前面字典的值。默认覆盖
    """

    if not dicts:
        return {}

    if len(dicts) == 1:
        if not dicts[0] or not isinstance[dicts[0], dict]:
            return {}

    # 若要后面字典的值不覆盖前面字典的值，则反转传入的字典列表
    if rewrite is False:
        dicts = dicts.reverse()

    # 深拷贝首个字典作为新字典的初始字典，避免影响原有字典
    merged_dict = deepcopy(dicts[0])
    for idx, _dict in enumerate(dicts):
        if idx == 0 or not _dict or not isinstance(_dict, dict):
            continue
        # 此种合并方式遇到相同key，后面字典的值会覆盖前面的值
        merged_dict.update(_dict)

    return merged_dict


def del_key_from_dict(key: str, datas=None):
    """
    删除字典中指定key元素

    :param key: 要删除的key
    :param datas: 要调整的字典
    """

    if not datas or not isinstance(datas, dict):
        return datas

    key = key.strip()
    if key not in datas:
        return datas

    # 深拷贝字典，避免影响到原字典
    _dict = deepcopy(datas)
    del _dict[key]
    return _dict


def read_json(file_path: str | Path) -> list | dict | None:
    """
    读取JSON文件，并将其转换成python对象

    :param _file: 文件的绝对路径
    """

    file = Path(file_path)
    if not file.exists():
        print_warn(f"{file.name}的路径不存在！")
        return None
    if not file.is_file():
        print_warn(f"{file.name}不是文件！")
        return None

    try:
        with open(file_path, "r", encoding=get_file_encoding(file_path)) as f:
            json_data = load(f)
        return json_data
    except JSONDecodeError:
        print_err(f"{file.name}不是标准JSON文件！")
        return None


def write_json(
    file_abspath: str | Path, datas=None, *, indent: int = 4, backup: bool = True
):
    """
    将python对象转换成JSON格式并写入文件

    :param file_abspath: 文件的绝对路径
    :param datas: 要写入json的数据
    :param indent: JSON每个层级的缩进长度
    :param backup: 是否备份原文件。默认备份
    """

    if not datas:
        print_warn(f"要写入JSON文件的数据不存在：{file_abspath}")
        return

    file_abspath = Path(file_abspath)
    file_is_exist = file_abspath.exists()
    # 如果路径存在
    if file_is_exist:
        # 如果不是文件路径，返回
        if not file_abspath.is_file():
            print_warn(f"路径非文件：{file_abspath}")
            return
        # 如果文件需要备份
        if backup:
            copy_file(file_abspath, tar_dir_abspath=file_abspath.parent / "bak")

    try:
        with open(file_abspath, "w", encoding=get_file_encoding(file_abspath)) as fp:
            if file_is_exist:
                print(f"正在更新 {file_abspath.name} 中……")
            else:
                print(f"正在创建 {file_abspath.name} 中……")
            dump(datas, fp, indent=indent, skipkeys=True, ensure_ascii=False)
            if file_is_exist:
                print(f"{file_abspath.name} 已更新！\n")
            else:
                print(f"{file_abspath.name} 已创建！\n")
    except Exception as e:
        print_err(f"write_json()写入{file_abspath.name}异常：{str(e)}")


def copy_file(
    src_file_abspath: str | Path,
    *,
    tar_file_abspath: str | Path = None,
    tar_dir_abspath: str | Path = None,
) -> Path:
    """
    将文件拷贝到指定文件夹/文件。若不指定路径，则在当前目录下拷贝，并添加时间前缀。

    :param src_file_abspath: 要拷贝的文件路径
    :param tar_file_abspath: 拷贝到文件路径
    :param tar_dir_abspath: 拷贝到文件夹路径
    :param time_prefix: 是否在文件夹/文件名前面加上拷贝时间。默认添加，以防覆盖已有文件
    """

    src_file_abspath = Path(src_file_abspath)
    if not src_file_abspath.is_file():
        return None

    # 如果未传入目标路径，则默认在当前目录拷贝文件，并给拷贝文件添加时间前缀
    if not tar_dir_abspath and not tar_file_abspath:
        time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        tar_file_abspath = replace_complex_stem(src_file_abspath, prefix=f"{time}_")
    else:
        if tar_dir_abspath:  # 如果目标路径是文件夹
            tar_dir_abspath = Path(tar_dir_abspath)
            tar_dir_abspath.mkdir(parents=True, exist_ok=True)
            tar_file_abspath = tar_dir_abspath.joinpath(src_file_abspath.name)

        else:  # 如果目标路径是文件
            tar_file_abspath = Path(src_file_abspath)
            tar_file_abspath.parent.mkdir(parents=True, exist_ok=True)

        # 如果目标路径已存在该文件，则添加时间前缀
        if tar_file_abspath.exists():
            time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            tar_file_abspath = replace_complex_stem(tar_file_abspath, prefix=f"{time}_")

    # 拷贝文件
    new_file_abspath = Path(copy(str(src_file_abspath), str(tar_file_abspath)))
    return new_file_abspath


def copy_tree(src_dir_abspath: str | Path, tar_dir_abspath: str | Path = None):
    """
    递归拷贝文件夹，若拷贝的文件已存在，则会给拷贝文件添加时间前缀

    :param src_dir_abspath: 原文件夹路径
    :param tar_dir_abspath: 目标文件夹路径
    """

    src_dir_abspath = Path(src_dir_abspath)
    # 但原路径不存在或不是文件夹时，直接返回
    if not src_dir_abspath.is_dir():
        return

    # 如果未传入目标路径，则在当前路径的文件夹添加时间前缀
    if not tar_dir_abspath:
        time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        tar_dir_abspath = replace_complex_stem(src_dir_abspath, prefix=f"{time}_")
    else:
        tar_dir_abspath = Path(tar_dir_abspath)
        # 如果目标路径已存在，则在目标路径的文件夹添加时间前缀
        if tar_dir_abspath.exists():
            if tar_dir_abspath.is_file():
                tar_dir_abspath = tar_dir_abspath.parent
            time = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            tar_dir_abspath = replace_complex_stem(tar_dir_abspath, prefix=f"{time}_")

    # 确保目标路径存在
    tar_dir_abspath.mkdir(parents=True, exist_ok=True)

    for item in src_dir_abspath.iterdir():
        target = tar_dir_abspath / item.name
        if item.is_dir():
            copy_tree(item, target)
        else:
            copy(str(item), str(target))


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
        _bool = literal_eval(val)
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
        UUID(val)
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
    return bool(match(pattern, string))


def is_letters_and_digits(string: str, length: int) -> bool:
    """
    检查字符串是否由指定长度的大小写字母和数字组成，若不指定长度，则检查整个字符串是否符合
    """
    if not string:
        return False

    if not length:
        length = len(string)
    pattern = r"^[A-Za-z0-9]{" + str(length) + r"}$"
    return bool(match(pattern, string))


def validate_lang(txt: str = "") -> str:
    """
    检测语言，查询结果参考ISO 639-1语言编码标准
    """

    if not txt.strip():
        return "auto"

    return classify(txt)[0]


def match_lang(txt: str = "", lang: str = "") -> bool:
    """
    匹配符合指定列表中语种的文本。匹配返回True，反之返回False。
    由于语言检测程序的限制，此方法存在一定误差。

    :param txt: 待匹配文本
    :param langs: 语种列表只能是字符串的形式，多种语种可用','隔开的形式，如：'zh,ru'
    """

    # 传入的待匹配文本为空字符串或语种列表为空字符串时，返回True
    if not txt.strip() or not lang.strip():
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
        if not lang:
            continue

        try:
            if classify(txt)[0] == lang:
                return True
        except Exception:
            continue
    return False


def full_2_half(txt: str = "") -> str:
    """
    将字符串中的全角符号转换成半角符号
    """

    if not txt.strip():
        return txt

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


def half_2_full(txt: str = "") -> str:
    """
    将字符串中的半角符号转换成全角符号
    """

    if not txt.strip():
        return txt

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


def zhpun_2_enpun(txt: str = "") -> str:
    """
    将字符串中的中文标点符号转换为英文标点符号
    """

    if not txt.strip():
        return txt

    # 处理常用标点符号
    chs_pun = "，。！？：；（）【】《》`“”‘’"
    en_pun = ",.!?:;()[]<>·\"\"''"
    trantab = str.maketrans(chs_pun, en_pun)
    txt = txt.translate(trantab)
    return txt


def enpun_2_zhpun(txt: str = "", no_blank: bool = False) -> str:
    """
    将字符串中的英文标点符号转换为中文标点符号
    """

    if not txt.strip():
        return txt

    # 使用迭代器处理单引号。
    # 由于英文中存在使用'来表示名词的所有格以及缩写等作用，只存在单个单引号，所以不便直接使用迭代器进行替换。
    # def _obj():
    #     return next(cycle(['‘', '’']))

    # s = re.sub(r"[\']", _obj(), s)

    # 使用迭代器处理双引号
    def _obj2():
        return next(cycle(["“", "”"]))

    txt = sub(r"[\"]", _obj2(), txt)

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


def has_upper_letter(txt: str = "") -> bool:
    """
    查询字符串中是否含有大写英文字母，没有返回False；反之返回True
    """

    if not txt.strip():
        return False

    my_re = compile(r"[A-Z]", S)
    res = findall(my_re, txt)
    if not res:
        return False

    return True


def has_lower_letter(txt: str = "") -> bool:
    """
    查询字符串中是否含有小写英文字母，没有返回False；反之返回True
    """

    if not txt.strip():
        return False

    my_re = compile(r"[a-z]", S)
    res = findall(my_re, txt)
    if not res:
        return False

    return True


def remove_escapes(txt: str = "") -> str:
    """
    删除文本中的转义字符，避免云翻译因转义字符的影响导致漏翻或语意错误
    """

    if not txt.strip():
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


def update_phoenix_mark(datas=None, update: bool = False):
    """
    切换JSON文本更新标记。用于判断是否要对json文件进行更新写入。
    """

    if datas is None or not isinstance(datas, dict):
        return

    datas[GlobalData.KEY_PHOENIX] = update


def switch_change_mark(base: bool = False, change: bool = False) -> bool:
    """
    切换更改标记
    """
    if not change:
        return base
    return change


def get_file_encoding(file_path: str | Path) -> str:
    """
    获取文本编码
    """
    try:
        with open(file_path, "rb") as f:
            raw_data = f.read()
            result = detect(raw_data)
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


def validate_renpy_trans_file(file_path: str | Path) -> bool:
    """
    判断指定文件是否是Ren'Py翻译文件。

    :param file_path: 文件绝对路径
    """

    file_path = Path(file_path)
    if not file_path.exists():
        return False

    # 只处理可以被renPy直接读取的后缀，其他后缀的文件即便内容是标准renPy翻译文本，也不进行处理
    if file_path.suffix not in (".rpy", ".rpym"):
        return False

    with open(file_path, "r", encoding=get_file_encoding(file_path)) as inp:
        for line in inp:
            # 如果能匹配到translate标识符，则返回True
            if GlobalData.pattern_identifier_line.match(line) is not None:
                return True
    return False


def get_projects_list(engine_type: str) -> list[str]:
    """
    获取现有项目的名称列表，否则返回空列表

    :param engine_type: 引擎种类
    """

    if engine_type == "renpy":
        # 判断ren'Py项目工作区是否存在，不存在则新建一个，并返回空列表
        if not GlobalData.renpy_trans_abspath.exists():
            GlobalData.renpy_trans_abspath.mkdir(parents=True)
            return []

        # 获取所有翻译文件夹
        folders = [
            item.name
            for item in GlobalData.renpy_trans_abspath.iterdir()
            if item.is_dir()
        ]
        return folders

    elif engine_type == "rpgm":
        # 判断rpgm项目工作区是否存在，不存在则新建一个，并返回空列表
        if not GlobalData.rpgm_trans_abspath.exists():
            GlobalData.rpgm_trans_abspath.mkdir(parents=True)
            return []

        # 获取所有JSON文件
        files = [item.name for item in GlobalData.rpgm_trans_abspath.glob("*.json")]
        return files

    else:
        return []


def hashlib_256(res: str = "") -> str:
    """
    对传入的字串进行SHA256计算，把计算结果进行Base64编码后输出

    :param res: 要加密的字串
    """
    if not res.strip():
        return res

    m = sha256(bytes(res.encode(encoding="utf-8"))).digest()
    result = b64encode(m).decode(encoding="utf-8")
    return result


def validate_index(
    lst: list | tuple | str, index: int = 0, with_negative: bool = True
) -> bool:
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


def acquire_token(
    qps: int = 1, tokens: float = 1, last_refill: float = 0
) -> tuple[int | float]:
    """
    令牌桶限流器

    :param qps: 请求频率
    :param tokens: 当前令牌数
    :param last_refill: 最新补充令牌时间
    """

    now = time()
    # 补充令牌
    elapsed = now - last_refill
    tokens = min(qps, tokens + elapsed * qps)
    last_refill = now

    if tokens < 1:
        wait_time = (1 - tokens) / qps
        sleep(wait_time)
        tokens = 0
    else:
        tokens -= 1

    return tokens, last_refill


def read_config(
    config_abspath: str | Path = GlobalData.config_abspath,
) -> ConfigParser | None:
    """
    读取项目配置文件

    :param config_abspath: 配置文件绝对路径
    """

    config_abspath = Path(config_abspath)
    if not config_abspath.exists() or not config_abspath.is_file():
        return None
    conf = ConfigParser()  # 调用读取配置模块中的类
    conf.optionxform = lambda option: option
    conf.read(config_abspath, encoding=get_file_encoding(config_abspath))
    return conf


def write_config(
    section: str,
    keys=None,
    add: bool = True,
    config_abspath: str | Path = GlobalData.config_abspath,
) -> bool:
    """
    写入项目配置文件

    :param section: 配置文件节点名称
    :param keys: 键值对字典
    :param add: 新增/修改配置 or 删减配置
    """

    if not isinstance(section, str) or not section.strip():
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

    copy_file(config_abspath)
    with open(config_abspath, "w", encoding=get_file_encoding(config_abspath)) as f:
        conf.write(f)
    return True


def get_password_with_mask(prompt="请输入密码: ") -> str:
    """
    控制台输入敏感内容非明文显示，返回实际输入内容

    :param prompt: 控制台显示的提示语
    """

    # 掩码显示
    # todo 存在输入长度超过命令行窗口宽度自动换行后无法退格到上一行的问题，会导致命令行窗口卡死，只能关闭重启
    # inp = pwinput(prompt, mask="*")
    # return inp.strip()

    # 空白显示，这个方法不会遇到掩码显示的超长自动换行的问题，但不够直观
    inp = getpass(prompt)
    return inp.strip()


def waiit_key_or_enter(prompt="按任意键继续或按回车退出程序：") -> bool:
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

    todo 存在阻塞问题，暂时弃用
    """
    if platform == "win32":
        import msvcrt

        return msvcrt.getch().decode("utf-8", errors="ignore")
    else:
        import termios
        import tty

        fd = stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


def replace_complex_stem(source_path: Path, prefix: str = "", suffix: str = "") -> Path:
    """
    精确替换文件名中最核心的stem部分，并保留所有扩展名。
    为避免文件或目录多后缀名的获取问题，更名只在名称最前面或后缀名最后面进行增加

    :param source_path: 待更名的文件夹/文件路径
    :param prefix: 前缀
    :param suffix: 后缀名
    """

    new_name = prefix + source_path.name + suffix
    return source_path.with_name(new_name)


def get_file_stem(file_name_suffix: str) -> list[str] | tuple[str]:
    """
    增加多个后缀名的文件的判断，正确获取不带后缀名的文件名及后缀。

    :param file_name_suffix: 带后缀名的文件名
    """
    if file_name_suffix.endswith((".tar.xz", ".tar.bz2", ".tar.gz")):
        return (file_name_suffix[:-7], file_name_suffix[-6:])
    else:
        return file_name_suffix.rsplit(".", maxsplit=1)


def get_config():
    """
    调用get方法，获取配置的数据
    """

    conf = read_config()
    if conf is None:
        return

    GlobalData.debug = conf.getboolean("common_settings", "debug")
    GlobalData.open_todo = conf.getboolean("common_settings", "open_todo")
    GlobalData.none_filter = conf.get("filter_texts", "none_filter")
    GlobalData.pass_filter = conf.get("filter_texts", "pass_filter").upper().split(",")

    GlobalData.rpy_trans_abspath = conf.get("rpy_trans_tool", "wait_trans_abspath")
    rpy_bap_max_cache = conf.getint("rpy_trans_tool", "rpy_bap_max_cache")
    if rpy_bap_max_cache > 0:
        GlobalData.rpy_trans_bap_max_cache = rpy_bap_max_cache

    GlobalData.rpy_update_old_abspath = conf.get("rpy_update_tool", "rpy_old_abspath")
    GlobalData.rpy_update_wait_abspath = conf.get("rpy_update_tool", "rpy_wait_abspath")

    rpy_bap_max_cache = conf.getint("rpy_update_tool", "rpy_bap_max_cache")
    if rpy_bap_max_cache > 0:
        GlobalData.rpy_update_bap_max_cache = rpy_bap_max_cache

    json_max_cache = conf.getint("json_trans_tool", "json_max_cache")
    if json_max_cache > 0:
        GlobalData.json_max_cache = json_max_cache

    GlobalData.RPGM_GAME_DEFAULT_TXT = conf.get(
        "rpgm_extraction_writing", "rpg_game_default_txt"
    )
    GlobalData.rpg_white_list = conf.get(
        "rpgm_extraction_writing", "rpg_white_list"
    ).split(",")
    GlobalData.rpg_duplicate_removal_list = conf.get(
        "rpgm_extraction_writing", "rpg_duplicate_removal_list"
    ).split(",")
    GlobalData.rpg_type_list_dict = conf.get(
        "rpgm_extraction_writing", "rpg_type_list_dict"
    ).split(",")
    GlobalData.rpg_script_regexp = conf.get(
        "rpgm_extraction_writing", "rpg_script_regexp"
    ).split(",")
    GlobalData.tencent = conf.getboolean("tencent", "activate")
    GlobalData.alibaba = conf.getboolean("alibaba", "activate")
    GlobalData.baidu = conf.getboolean("baidu", "activate")
    GlobalData.caiyun = conf.getboolean("caiyun", "activate")
    GlobalData.huoshan = conf.getboolean("huoshan", "activate")
    GlobalData.xiaoniu = conf.getboolean("xiaoniu", "activate")
    GlobalData.xunfei = conf.getboolean("xunfei", "activate")
    GlobalData.youdao = conf.getboolean("youdao", "activate")
    GlobalData.deepL = conf.getboolean("deepL", "activate")
    GlobalData.google = conf.getboolean("google", "activate")
    GlobalData.ollama = conf.getboolean("ollama", "activate")
    GlobalData.hunyuan_mt = conf.getboolean("hunyuan_mt", "activate")
