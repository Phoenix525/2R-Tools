# 2R-Tools

## 工具介绍
面向游戏本地化者的 RPG Maker & Ren'Py 翻译文本管理翻译工具。支持RPGM VX Ace、MV、MZ及Ren'Py引擎，一键提取、翻译、更新翻译文本，大大减少翻译工作量，缩短翻译时间。
>注：工具仅能提取引擎原生支持的文件及语法下的翻译文本，不支持游戏作者自行编写的部分代码。

## 运行环境
- windows 11操作系统；
- Python 3.10+；

## 项目结构
- libraries文件夹：译文库。
	- rpgmz_default_library.json：RPG Maker MZ引擎初始简中译文。
	- rpgmv_default_library.json：RPG Maker MV引擎初始简中译文。
	- rpgvxace_default_library.json：RPG Maker VX Ace引擎初始简中译文。
	- TransLib.json：本地译文库（暂时不支持区分语种）。可以通过工具进行扩充，适用于所有游戏引擎的文本翻译。译文库不宜储存存在多含义的文本，这可能会导致翻译文本词不达意。在提取待翻文本或进行文本翻译时，工具会先在本地译文库中查找。
	- gameText.json：RPGM游戏旧版本翻译文件（暂时不支持区分语种）。在提取RPGM游戏翻译文本时，工具会扫描该文件，若存在结果，则会覆盖从TransLib.json中获取的译文，并录入新的翻译文本中。
- modules文件夹：程序代码。
- RPGM Workspace文件夹：RPGM项目工作区。用于存放和管理翻译文件。
- RPGM Data Input文件夹：存放RPGM的初始json代码文件。
- RPGM Data Output文件夹：存放RPGM的新生成json代码文件。
- waiting-for-entry文件夹：放置json和rpy翻译文件，用于将翻译数据写入TransLib.json译文库。
- config.ini是工具默认设置及API接口通行证配置文件。
- main.py是工具的启动程序。
  
## 内置翻译引擎
- 本地AI翻译（需自行部署环境及下载模型）：
	- 基于Ollama框架。可切换多种模型（部署极简，运行速度快）
	- 基于Transformers库。调用腾讯Hunyuan-MT模型（部署难度中等，运行速度较慢），部署教程点击[此处](https://gitee.com/aeolus314/2R-Tools/blob/master/Windows%2011%E9%83%A8%E7%BD%B2%20HY-MT1.5-7B%20%E6%95%99%E7%A8%8B.md)。
- 机器翻译平台（非AI大模型翻译）：
	- [腾讯翻译](https://console.cloud.tencent.com/tmt)
	- [阿里翻译](https://mt.console.aliyun.com/basic)
	- [百度翻译](https://fanyi-api.baidu.com/register)
	- [彩云小译](https://docs.caiyunapp.com/lingocloud-api/index.html)
	- [火山翻译](https://www.volcengine.com/docs/4640/127682?lang=zh)
	- [小牛翻译](https://niutrans.com/documents/contents/transapi_text_v2#accessMode)
	- [讯飞翻译](https://console.xfyun.cn/services/its)
	- [有道智云](https://ai.youdao.com/doc.s#guide)
	- [DeepL翻译](https://www.deepl.com/zh/pro-api#api-pricing)
	- Google翻译（第三方，已失效）
 
	机器翻译平台API所需密钥需自行申请，将申请到的相关数据填入config.ini对应位置，即可启用相应翻译引擎。各平台收费标准不一，且时常有变动，使用前请先去官网查询相关资费。

## 使用方法
1. 启用机器翻译：
  
   在config.ini中修改activate为True以启用接口。
   在首次调用时会提示输入API通行证，并加密存入config.ini相应位置，下次再调用会自动读取config.ini已有通行证数据。
	```ini
	; 举例：百度翻译API
	[baidu]
	; 是否启用
	activate=True
	```
2. 启用本地AI翻译（前提环境已部署）：
	- Ollama需要在config.ini填写模型名称（model_name），调用哪个模型就填入相应的完整名称，并修改activate为True以启用接口。
		```ini
		[ollama]
		; Ollama调用的模型名称
		model_name=gemma3:4b
		; 是否启用
		activate=True
		```
	- Hunyuan-MT模型需要在config.ini填写模型所在绝对路径，并修改activate为True以启用接口。
		```ini
		[hunyuan_mt]
		; Hunyuan-MT模型所在路径
		model_path=D:\AI_Projects\Hunyuan-MT\Hunyuan-MT1.5-7B
		; 是否启用
		activate=True
		```
3. 执行main.py启动程序：
   - 项目未配置conda虚拟环境：
		```Powershell
		# 安装项目所使用的依赖
		# 注意先将torch所依赖cuda版本130修改成本机的cuda版本。例torch==2.11.0+cuda121
		PS D:\2R-Tools>pip install -r requirements.txt

		# 启动工具
		PS D:\2R-Tools>python main.py
		```
	- 项目配置了conda虚拟环境，先激活项目所属虚拟环境：
		```Powershell
		# 激活虚拟环境：2rtools
		(base) PS D:\2R-Tools>conda activate 2rtools
		
		# 安装项目所使用的依赖
		# 注意先将torch所依赖cuda版本130修改成本机的cuda版本。例torch==2.11.0+cuda121
		(2rtools) PS D:\2R-Tools>pip install -r requirements.txt

		# 启动工具
		(2rtools) PS D:\2R-Tools>python main.py
		```
