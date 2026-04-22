#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.utils.global_data import GlobalData
from app.utils.utils import get_config, read_json

get_config()

GlobalData.translated_lib_library = read_json(GlobalData.translated_lib_abspath)
