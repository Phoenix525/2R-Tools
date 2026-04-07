#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author: Phoenix
@Date: 2020-07-04 23:33:35
"""

import os
import sys

import src.core.json_translation as json_translation
import src.core.renpy_translation as renpy_translation
import src.core.renpy_update as renpy_update
import src.core.rpgm_mv_extraction_writing as rpgm_mv_extraction_writing
import src.core.rpgm_mz_extraction_writing as rpgm_mz_extraction_writing
import src.core.rpgm_vx_ace_extraction_writing as rpgm_vx_ace_extraction_writing
import src.core.single_txt_tranlsation as single_txt_tranlsation
import src.core.translated_txt_lib as translated_txt_lib
from src.utils.utils import (
    RENPY_PROJECT_PARENT_FOLDER,
    get_projects_list,
    print_info,
    print_warn,
)


def start_main(serial_num="", first_select=True):

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

1) Ren'Py 提取文本翻译
2) Ren'Py 提取文本更新
3) RPG Maker MZ 文本提取写入
4) RPG Maker MV 文本提取写入
5) RPG Maker VXAce 文本提取写入
6) JSON 文本翻译
7) 单语句翻译
8) rpy/json 写入译文库
""")
        _inp = input("请输入要操作的序号或回车退出程序：").strip()
    else:
        _inp = input(
            f"列表中不存在序号 {serial_num}，请重新输入正确序号或回车退出程序："
        ).strip()

    match _inp:
        case "":
            sys.exit()
        case "1":
            # 选择renpy项目文件夹
            # _curr_renpy_project = get_renpy_project()
            # print_info(f'当前项目: {_curr_renpy_project}')
            renpy_translation.start()
        case "2":
            # 选择renpy项目文件夹
            # _curr_renpy_project = get_renpy_project()
            renpy_update.start()
        case "3":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project(_inp)
            rpgm_mz_extraction_writing.start(_curr_rpgm_project)
        case "4":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project(_inp)
            rpgm_mv_extraction_writing.start(_curr_rpgm_project)
        case "5":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project(_inp)
            rpgm_vx_ace_extraction_writing.start(_curr_rpgm_project)
        case "6":
            # 选择rpgm翻译文件
            _curr_rpgm_project = __get_rpgm_project(_inp)
            if _curr_rpgm_project == "":
                print_info("未选择翻译项目，返回主界面！")
                start_main()
            else:
                json_translation.start(_curr_rpgm_project)
        case "7":
            single_txt_tranlsation.start()
        case "8":
            translated_txt_lib.start()
        case _:
            start_main(_inp, False)


def __get_rpgm_project(
    select: str, serial_num="", first_select=True, *, projects_list=None
) -> str:
    """
    获取当前要操作的rpgm翻译文件路径
    """
    # 用户输入内容
    _inp = ""
    # 首次进入选项
    if first_select:
        projects_list = get_projects_list("rpgm")
        if not len(projects_list):
            # 当选择翻译rpgm翻译文件时，若工作区无项目则直接返回
            if select == "6":
                print_warn("工作区无项目！")
                return ""

            _inp = input(
                "工作区无项目，请新建一个项目，输入项目名称及版本号（例：Test_v0.1）或回车退出程序："
            ).strip()
            if _inp == "":
                sys.exit()
            print_info(f"当前RPGM翻译项目：{_inp}.json")
            return f"{_inp}.json"

        print_msg = """===========================================================================================
工作区现有项目如下：
0: 新建项目
"""
        for idx, project in projects_list.items():
            print_msg += f"{idx}: {project}\n"
        print_msg += "\n请输入相应序号选择项目，输入0则新建一个项目或回车退出程序："
        _inp = input(print_msg).strip()
        if _inp == "":
            sys.exit()
        elif _inp == "0":
            _inp = input(
                "请新建一个项目，输入项目名称及版本号（例：Test_v0.1）或回车退出程序："
            ).strip()
            if _inp == "":
                sys.exit()
            print_info(f"当前RPGM翻译项目：{_inp}.json")
            return f"{_inp}.json"
    else:
        _inp = input(
            f"列表中不存在序号 {serial_num}，请输入正确序号选择项目，输入0则新建一个项目或回车退出程序："
        ).strip()
        if _inp == "":
            sys.exit()

    for idx, project in projects_list.items():
        if _inp == idx:
            print_info(f"当前RPGM翻译项目：{project}")
            return project

    return __get_rpgm_project(select, _inp, False, projects_list=projects_list)


def __get_renpy_project() -> str:
    """
    选择当前要操作的ren\'Py项目名称，若不存在则新建一个
    """

    _projects = get_projects_list("renpy")
    if len(_projects) <= 0:
        _project_name = input(
            "ren'Py工作区无项目，请新建一个项目，输入项目名称及版本号（例：Test_v0.1）："
        ).strip()
        _project_abspath = os.path.join(RENPY_PROJECT_PARENT_FOLDER, _project_name)
        os.makedirs(_project_abspath)
        return _project_name

    print_msg = "\nren'Py工作区现有项目如下：\n0: 新建项目\n"
    for idx, project in _projects.items():
        print_msg += f"{idx}: {project}\n"
    print_msg += "\n请输入相应序号选择要处理的项目，输入0则新建一个项目："
    _imp = input(print_msg).strip()
    if _imp == "0":
        _project_name = input(
            "请新建一个项目，输入项目名称及版本号（例：Test_v0.1）："
        ).strip()
        _project_abspath = os.path.join(RENPY_PROJECT_PARENT_FOLDER, _project_name)
        os.makedirs(_project_abspath)
        return _project_name

    for idx, project in _projects.items():
        if _imp == idx or _imp == project.rsplit(".", 1)[0]:
            print_info(f"当前renPy翻译项目：{project}")
            return project

    _project_name = input(
        "无此序号项目，请新建一个项目，输入项目名称及版本号（例：Test_v0.1）："
    ).strip()
    _project_abspath = os.path.join(RENPY_PROJECT_PARENT_FOLDER, _project_name)
    os.makedirs(_project_abspath)
    return _project_name


if __name__ == "__main__":
    start_main()
