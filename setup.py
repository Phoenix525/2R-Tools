#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import find_packages, setup


def read_requirements():
    with open("requirements.txt", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


setup(
    name="2r-tools",
    version="0.6.4",
    author="Phoenix",
    author_email="fire_phoenix@aliyun.com",
    description="一款傻瓜式提取、翻译和更新RPG Maker & Ren'Py翻译文本的工具。",
    url="https://github.com/Phoenix525/2R-Tools",
    packages=find_packages(exclude=["tests", "Game Scripts"]),
    entry_points={
        "console_scripts": [
            "2rtools=src.main:start_main",
        ],
    },
    install_requires=read_requirements(),
    licence="Apache-2.0",
    python_requires=">=3.10",
)
