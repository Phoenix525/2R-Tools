#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class ToolException(Exception):
    """
    工具的异常类
    """

    def __init__(self, code=None, message=None, requestId=None):
        self.code = code
        self.message = message
        self.requestId = requestId

    def __str__(self):
        s = "[ToolException] code:%s message:%s requestId:%s" % (
            self.code,
            self.message,
            self.requestId,
        )
        return s

    def get_code(self):
        return self.code

    def get_message(self):
        return self.message

    def get_request_id(self):
        return self.requestId
