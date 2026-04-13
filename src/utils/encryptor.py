#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import hashlib

from cryptography.fernet import Fernet

from src.utils.global_data import GlobalData
from src.utils.utils import print_debug, print_err, write_config


class SimpleAPIKeyEncryptor:
    """
    简单的API密钥加密管理器
    """

    def __init__(self, password=""):
        """
        初始化加密器

        :param password: 加密密码
        """
        self.__password: bytes = password.encode("utf-8")

        self.__cipher: Fernet = self.__chipher(password)

    def encrypt(self, plain_text: str) -> str:
        """
        加密文本

        :param plain_text: 原始文本
        :return: 加密后的base64字符串
        """
        encrypted = self.__cipher.encrypt(plain_text.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, encrypted_text: str) -> str:
        """
        解密文本

        :param encrypted_text: 加密的base64字符串
        :return: 原始文本
        """
        decrypted = self.__cipher.decrypt(base64.b64decode(encrypted_text))
        return decrypted.decode()

    def __chipher(self, input_str="") -> Fernet:
        # 从密码生成确定的密钥
        hash_obj = hashlib.sha256(self.__password)
        salt = hash_obj.digest()[:32]
        key_bytes = hashlib.pbkdf2_hmac("sha256", input_str.encode(), salt, 100000, 32)
        key = base64.urlsafe_b64encode(key_bytes)
        return Fernet(key)


class SimpleKeyStore:
    """
    简单的密钥存储管理器
    """

    def __init__(self, encryptor: SimpleAPIKeyEncryptor, keys: dict[str, str] = None):
        """
        初始化密钥存储

        :param encryptor: 加密器实例
        """

        self.__encryptor = encryptor
        if keys is None:
            keys = {}
        self.__keys = keys

    def add_keys(self, section: str, keys=None):
        """
        添加并加密存储数据

        :param section: 配置文件的节点
        :param keys: 新增的键值对字典
        """

        if not keys or not isinstance(keys, dict):
            return
        for key, value in keys.items():
            encrypted = self.__encryptor.encrypt(value)
            self.__keys[key] = encrypted
            if GlobalData.debug:
                leng = len(value)
                msg = value.replace(value[3:-3], "*" * (leng - 6))
                print_debug(f"原始{key}数据：{msg}")
                msg = encrypted.replace(encrypted[10:-10], "*" * 20)
                print_debug(f"加密{key}数据：{msg}")
        self.__save(section)

    def get_key(self, key: str) -> str:
        """
        获取解密后的数据

        :param key: 查询的键
        """

        if key not in self.__keys:
            print_debug(f"✗ 密钥 '{key}' 不存在")
            return ""

        try:
            decrypted = self.__encryptor.decrypt(self.__keys[key])

            if GlobalData.debug:
                encrypted = self.__keys[key]
                msg = encrypted.replace(encrypted[10:-10], "*" * 20)
                print_debug(f"待解密{key}数据：{msg}")
                leng = len(decrypted)
                msg = decrypted.replace(decrypted[3:-3], "*" * (leng - 6))
                print_debug(f"解密{key}数据：{msg}")
        except Exception as e:
            print_err(f"解密失败: {e}")
            decrypted = ""
        else:
            return decrypted

    def __save(self, section: str):
        """
        保存到文件

        :param section: 配置文件节点
        """
        write_config(section, self.__keys)
