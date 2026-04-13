#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-07-04 23:33:35
"""

import os
import sys
from typing import Optional

import src.core.json_translation as json_translation
import src.core.renpy_translation as renpy_translation
import src.core.renpy_update as renpy_update
import src.core.rpgm_mv_extraction_writing as rpgm_mv_extraction_writing
import src.core.rpgm_mz_extraction_writing as rpgm_mz_extraction_writing
import src.core.rpgm_vx_ace_extraction_writing as rpgm_vx_ace_extraction_writing
import src.core.single_txt_tranlsation as single_txt_tranlsation
import src.core.translated_txt_lib as translated_txt_lib
from src.utils.global_data import GlobalData
from src.utils.utils import get_projects_list, print_info, to_int, validate_index


def start_main(first_select=True):

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        print(r"""
===========================================================================================
          ______  _____  _   _ ______ __   __      ______ ______  _____ ___  ___
          | ___ \|  ___|| \ | || ___ \\ \ / /___   | ___ \| ___ \|  __ \|  \/  |
          | |_/ /| |__  |  \| || |_/ / \ V /( _ )  | |_/ /| |_/ /| |  \/| .  . |
          |    / |  __| | . ` ||  __/   \ / / _ \/\|    / |  __/ | | __ | |\/| |
          | |\ \ | |___ | |\  || |      | || (_>  <| |\ \ | |    | |_\ \| |  | |
          \_| \_|\____/ \_| \_/\_|      \_/ \___/\/\_| \_|\_|     \____/\_|  |_/
          
                                      作者：Phoenix
                                      版权归作者所有
===========================================================================================

1) Ren'Py 翻译文本机翻
2) Ren'Py 翻译文本更新
3) RPGM MZ 翻译文本提取或写入 
4) RPGM MV 翻译文本提取或写入
5) RPGM VX Ace 翻译文本提取或写入
6) RPGM 翻译文本机翻
7) 单文本机翻
8) 译文库更新
""")
        _inp = input("请输入要操作的序号或回车退出程序：").strip()
    else:
        _inp = input("列表中不存在该序号，请重新输入正确序号或回车退出程序：").strip()

    match _inp:
        case "" | "\r" | "\n":
            sys.exit()
        case "1":
            # 选择renpy项目文件夹
            # _curr_renpy_project = __get_renpy_project()
            # if _curr_renpy_project in (None, ""):
            # start_main()
            # else:
            renpy_translation.start()
        case "2":
            # 选择renpy项目文件夹
            # _curr_renpy_project = __get_renpy_project()
            # if _curr_renpy_project in (None, ""):
            #     start_main()
            # else:
            renpy_update.start()
        case "3":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project()
            if _curr_rpgm_project in (None, ""):
                start_main()
            else:
                rpgm_mz_extraction_writing.start(_curr_rpgm_project)
        case "4":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project()
            if _curr_rpgm_project in (None, ""):
                start_main()
            else:
                rpgm_mv_extraction_writing.start(_curr_rpgm_project)
        case "5":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project()
            if _curr_rpgm_project in (None, ""):
                start_main()
            else:
                rpgm_vx_ace_extraction_writing.start(_curr_rpgm_project)
        case "6":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project("JSON")
            if _curr_rpgm_project in (None, ""):
                start_main()
            else:
                json_translation.start(_curr_rpgm_project)
        case "7":
            single_txt_tranlsation.start()
        case "8":
            translated_txt_lib.start()
        case _:
            start_main(False)


def __get_rpgm_project(
    select="", first_select=True, *, projects_list=None
) -> Optional[str]:
    """
    获取当前要操作的rpgm翻译文件路径
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        projects_list = get_projects_list("rpgm")
        if not projects_list:
            # 当选择翻译rpgm翻译文件时，若工作区无项目则直接返回
            if select == "JSON":
                print_info("工作区无项目，返回主界面！")
                return ""

            _inp = input(
                "工作区无项目，请新建一个项目，输入项目名称及版本号（例：Test_v0.1）或回车返回主菜单："
            ).strip()
            if _inp in ("", "\r", "\n"):
                return None
            print_info(f"当前RPGM翻译项目：{_inp}.json")
            return f"{_inp}.json"

        print_msg = """===========================================================================================
工作区现有项目如下：
"""
        for idx, project in enumerate(projects_list):
            print_msg += f"{idx + 1}: {project}\n"
        print_msg += "\n请输入相应序号选择项目，输入0则新建一个项目或回车返回主菜单："
        _inp = input(print_msg).strip()
    else:
        _inp = input(
            "列表中不存在该序号，请输入正确序号选择项目，输入0则新建一个项目或回车返回主菜单："
        ).strip()

    # 回车返回主界面
    if _inp in ("", "\r", "\n"):
        return None

    if _inp == "0":
        _inp = input(
            "请新建一个项目，输入项目名称及版本号（例：Test_v0.1）或回车返回主菜单："
        ).strip()
        if _inp in ("", "\r", "\n"):
            return None
        print_info(f"当前RPGM翻译项目：{_inp}.json")
        return f"{_inp}.json"

    # 索引
    index = to_int(_inp) - 1
    if validate_index(projects_list, index, False):
        project = projects_list[index]
        print_info(f"当前RPGM翻译项目：{project}")
        return project

    return __get_rpgm_project(select, False, projects_list=projects_list)


def __get_renpy_project(
    select="", first_select=True, *, projects_list=None
) -> Optional[str]:
    """
    选择当前要操作的ren\'Py项目名称，若不存在则新建一个
    """

    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        projects_list = get_projects_list("renpy")
        if not projects_list:
            _inp = input(
                "Ren'Py工作区无项目，请新建一个项目，输入项目名称及版本号（例：Test_v0.1）或回车返回主菜单："
            ).strip()
            if _inp in ("", "\r", "\n"):
                return None
            os.makedirs(os.path.join(GlobalData.RENPY_PROJECT_PARENT_FOLDER, _inp))
            print_info(f"当前Ren'Py翻译项目：{_inp}")
            return _inp

        print_msg = """===========================================================================================
    工作区现有项目如下：
    """
        for idx, project in enumerate(projects_list):
            print_msg += f"{idx + 1}: {project}\n"
        print_msg += "\n请输入相应序号选择项目，输入0则新建一个项目或回车返回主菜单："
        _inp = input(print_msg).strip()
    else:
        _inp = input(
            "列表中不存在该序号，请输入正确序号选择项目，输入0则新建一个项目或回车返回主菜单："
        ).strip()

    if _inp in ("", "\r", "\n"):
        return None

    if _inp == "0":
        _inp = input(
            "请新建一个项目，输入项目名称及版本号（例：Test_v0.1）或回车返回主菜单："
        ).strip()
        if _inp in ("", "\r", "\n"):
            return None
        os.makedirs(os.path.join(GlobalData.RENPY_PROJECT_PARENT_FOLDER, _inp))
        print_info(f"当前Ren'Py翻译项目：{_inp}")
        return _inp

    index = to_int(_inp) - 1
    if validate_index(projects_list, index, False):
        project = projects_list(index)
        print_info(f"当前Ren'Py翻译项目：{project}")
        return project

    return __get_rpgm_project(select, False, projects_list=projects_list)


if __name__ == "__main__":
    start_main()
