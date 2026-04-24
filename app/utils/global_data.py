#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from pathlib import Path
from re import Pattern, compile


class GlobalData:
    """
    全局变量类
    """

    # 常量
    # json更新标记
    KEY_PHOENIX: str = "__PHOENIX__"

    # JSON翻译文本中标记当前率属于的文件名
    TRANSLATED_FILE_MARK: str = "<==M==A==R==K==> "

    MARK_TODO: str = "TODO"
    """译文TODO标识符\n\n此处写死，避免用户修改导致文本不通用。由open_todo决定是否开启。"""

    RPGM_GAME_DEFAULT_TXT: str = "gameText.json"
    """RPGM旧版本翻译文件\n\n将翻译项目改成此名后置入[TRANS_LIBS]文件夹，程序在提取RPGM翻译文本时会自动从旧版本翻译文件中查询并写入已有译文。"""

    base_abspath = Path(__file__).parent.parent.parent
    """项目所在绝对路径"""

    rpgm_trans_abspath = base_abspath / "[RPGM_TRANS]"
    """rpgm项目工作区的绝对路径"""

    renpy_trans_abspath = base_abspath / "[RENPY_TRANS]"
    """renpy项目工作区的绝对路径"""

    rpgm_datas_abspath = base_abspath / "[RPGM_DATAS]"
    """存放rpgm初始data游戏数据目录的绝对路径"""

    wait_for_entry = base_abspath / "[WAIT_FOR_ENTRY]"
    """本地译文库更新目录。\n\n将rpy或json翻译文件置入其中，便可使用程序将其中的文本写入本地译文库。"""

    trans_libs_abspath = base_abspath / "[TRANS_LIBS]"
    """初始译文目录的绝对路径"""

    translib_abspath = trans_libs_abspath / "TransLib.json"
    """本地译文库绝对路径"""

    config_abspath = base_abspath / "config.ini"
    """配置文件绝对路径"""

    # 变量
    debug: bool = False
    """开启调试模式\n\n用于区分开发和生产环境。默认关闭，可在配置文件中调整。"""

    open_todo: bool = False
    """开启译文TODO标识符\n\n用于区分已润色译文和未润色译文。默认关闭，可在配置文件中调整。"""

    none_filter: str = "NONE"
    """JSON翻译文件文本写入忽略标记\n\n程序在写入data时会忽略带该标记的文本，以起到在游戏中屏蔽该文本的作用。可在配置文件中调整。"""

    pass_filter: list[str] = []
    """JSON翻译文件文本翻译忽略标记\n\n程序在翻译时，会忽略带有该标记的文本，以保持原文本。可在配置文件中调整。"""

    rpy_trans_input_abspath: str = ""
    """Ren'Py翻译项目的绝对路径。可在配置文件中调整。"""

    rpy_trans_bap_max_cache: int = 0
    """Ren'Py翻译最大缓存量。可在配置文件中调整。"""

    rpy_update_old_abspath: str = ""
    """Ren'Py更新中旧版本翻译项目的绝对路径。可在配置文件中调整。"""

    rpy_update_new_abspath: str = ""
    """Ren'Py更新中待更新翻译项目的绝对路径。可在配置文件中调整。"""

    rpy_update_bap_max_cache: int = 0
    """Ren'Py更新最大缓存量。可在配置文件中调整。"""

    json_max_cache: int = 0
    """JSON翻译最大缓存量。可在配置文件中调整。"""

    rpg_white_list: list[str] = []
    """RPGM扫描文本白名单\n\n除Mapxxx外，在此名单中的文件才会被扫描。可在配置文件中调整。"""

    rpg_duplicate_removal_list: list[str] = []
    """RPGM翻译文本可去重列表\n\n无需使用标识符区分相同文本的。可在配置文件中调整。"""

    rpg_type_array_object: list[str] = []
    """RPGM文件内容是list[dict]数据结构的。可在配置文件中调整。"""

    rpg_script_regexp: list[str] = []
    """RPGM脚本\n\n使用正则匹配。可同时匹配多项。可在配置文件中调整。"""

    translated_lib_library: dict = None
    """自定义本地译文库\n\n翻译器在发起翻译请求前会先查询本地译文库是否有该语句的译文。"""

    # 翻译引擎启用标记
    tencent: bool = False
    alibaba: bool = False
    baidu: bool = False
    caiyun: bool = False
    huoshan: bool = False
    xiaoniu: bool = False
    xunfei: bool = False
    youdao: bool = False
    deepL: bool = False
    google: bool = False
    ollama: bool = False
    hunyuan_mt: bool = False

    # 翻译引擎实例
    tencent_api = None
    alibaba_api = None
    baidu_api = None
    caiyun_api = None
    huoshan_api = None
    xiaoniu_api = None
    xunfei_api = None
    youdao_api = None
    deepL_api = None
    google_api = None
    ollama_api = None
    hunyuan_mt_api = None

    pattern_empty_line: Pattern[str] = compile(r"^\s*$")
    """正则：匹配空行"""
    pattern_identifier_line: Pattern[str] = compile(r"^\s*translate\s*.*\s(.*):")
    """正则：匹配rpy的文本标识符行"""
    pattern_old_strings_line: Pattern[str] = compile(r'^\s*old\s*"(.*)"')
    """正则：匹配rpy的old语句行"""
    pattern_new_strings_line: Pattern[str] = compile(r'^\s*new\s*"(.*)"')
    """正则：匹配rpy的new语句行"""
    pattern_old_say_line: Pattern[str] = compile(
        r'^\s*#+\s*(".*?[^\\]"|[\S\s]*?)\s*"(.*)"'
    )
    """正则匹配rpy的say原文注释行"""
    pattern_new_say_line: Pattern[str] = compile(
        r'(?!\s*#+)\s*(".*?[^\\]"|[\S\s]*?)\s*"(.*)"\s*(.*)'
    )
    """正则：匹配rpy的say译文行"""
    pattern_who: Pattern[str] = compile(r'^"(.*?[^\\])"')
    """正则：匹配rpy的who"""
    pattern_identifier: Pattern[str] = compile(r"^(?:\d+_)?([a-fA-F0-9]{8})(?:_.*)?$")
    """正则：匹配rpy8位标识符，从后往前匹配"""
    pattern_annotation: Pattern[str] = compile(r"^\s*#\s*")
    """正则：匹配注释符号"""
    pattern_map: Pattern[str] = compile(r"^Map\d{3}$")
    """正则：匹配rpg的Mapxxx.json文件"""

    @classmethod
    def __class_getitem__(cls, key):
        """使外部可以通过GlobalData["xxx"]的形式调用GlobalData的属性"""
        return getattr(cls, key)
