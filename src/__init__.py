#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.utils.global_data import GlobalData
from src.utils.utils import get_config, read_json

get_config()

GlobalData.translated_lib_library = read_json(GlobalData.TRANSLATED_LIB_ABSPATH)
