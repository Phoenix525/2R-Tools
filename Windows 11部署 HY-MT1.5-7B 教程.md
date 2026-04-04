# 准备工作：环境检查与工具安装
在开始之前，先看看电脑配置够不够。Hunyuan-MT1.5-7B虽然只有70亿参数，但毕竟是7B级别的大模型，对硬件还是有些要求的。


## 硬件要求

最低配置：

- 系统：Windows 11 64位
- 显卡：至少8GB显存的NVIDIA显卡（RTX3060 12G、RTX4060Ti 16G等）
- 内存：16GB以上，建议32GB
- 硬盘：至少20GB可用空间（模型文件就占了14GB左右）

如果你用的是RTX 4090这种24GB显存的卡，那体验会好很多，可以跑更高精度的版本。显存不够的话，后面我会教你怎么用量化版本来降低要求。

## 软件准备

确保你的系统已安装以下基础软件：
>本文着重hunyuan-mt模型本地部署教程，部署所需的基础软件默认已安装并配置完毕，此处不做赘述。

- Anaconda 或 Miniconda：用于安装、更新和管理Python包，及创建隔离的Python环境
- Python 3.10.x：最兼容本项目的版本
- CUDA 12.1+：NVIDIA显卡的加速库
- Git：用来下载代码和模型
- Visual Studio Build Tools：编译一些Python包需要

# 开始部署
## 创建虚拟环境

虚拟Python环境是个好东西，能隔离不同项目的依赖，避免版本冲突。

1. 打开Powershell窗口，后续操作大部分都要在这个窗口中运行。
2. 创建虚拟环境：
    ```Powershell
    # 成功安装conda后，命令行最前面应该有(base)标识，此为conda默认环境。
    # 不建议直接在base环境中部署，每种项目最好创建一个单独的虚拟环境，并使用该虚拟环境进行部署。
    # 如果conda无法使用，可能是安装后未对其进行初始化，可以先输入以下命令初始化，然后重新打开Powershell继续下一步操作
    (base) PS C:\Users\xxx\Desktop>conda init

    # 创建名叫2rtools的虚拟Python环境，Python版本指定为3.10.20
    (base) PS C:\Users\xxx\Desktop>conda create -n 2rtools python=3.10.20 -y

    # 激活环境
    (base) PS C:\Users\xxx\Desktop>conda activate 2rtools

     # 命令行最前面切换成(2rtools)，表明环境已经切换过来了。
    #(2rtools) PS C:\Users\xxx\Desktop>

    # 以下是conda操作虚拟环境的其他常用指令，了解即可，非此教程必要操作步骤
    # 列出所有虚拟环境
    (base) PS C:\Users\xxx\Desktop>conda env list

    # 退出当前环境
    (2rtools) PS C:\Users\xxx\Desktop>conda deactivate

    # 删除指定虚拟环境
    (base) PS C:\Users\xxx\Desktop>conda remove -n 2rtools --all
    ```


## 安装PyTorch

PyTorch是运行大模型的基础框架，安装时要注意选对CUDA版本。
可点击此处 [Pytorch.org](https://pytorch.org/get-started/locally/) 查询对应CUDA版本的PyTorch安装命令。

1. 首先检查CUDA的版本，以确定要安装PyTorch的版本。
    ```Powershell
    # 检查CUDA版本
    (2rtools) PS C:\Users\xxx\Desktop>nvidia-smi
    ```
2. 根据查询到的CUDA版本，进入上方网址查询对应PyTorch安装命令。
     ```Powershell
     # 安装PyTorch（CUDA 13.2版本）
    (2rtools) PS C:\Users\xxx\Desktop>pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
     ```

## 安装Transformers库

   Transformers 是 Hugging Face 推出的一个开源库，统一封装了各种主流 Transformer 模型（BERT、GPT、T5、Whisper、CLIP、LLaMA 等）。它的最大优点是：一行代码就能用 SOTA 模型完成各种任务。
```Powershell
# 安装transformers库（官方建议4.56.0版本）
(2rtools) PS C:\Users\xxx\Desktop>pip install transformers==4.56.0

# 如果安装过程中遇到网络问题，可以试试用国内的镜像源：
(2rtools) PS C:\Users\xxx\Desktop>pip install transformers==4.56.0 -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 安装其他必要依赖

```Powershell
# 安装其他依赖
(2rtools) PS C:\Users\xxx\Desktop>pip install accelerate sentencepiece protobuf bitsandbytes
```

## 下载模型文件

模型文件比较大，有14GB左右，下载需要一些时间。你可以从Hugging Face或者ModelScope下载，推荐用ModelScope，国内访问速度更快。

- 方法一：创建py文件执行ModelScope下载（推荐国内用户）
  
    在当前目录下新建一个download.py文件，将以下代码拷贝进去保存：

    ```Python
    from modelscope import snapshot_download

    model_dir = snapshot_download('Tencent-Hunyuan/Hunyuan-MT-7B', cache_dir='./models')

    print(f"模型下载到: {model_dir}")
    ```

    在命令行窗口中执行py文件下载模型。
    ```Powershell
    # 下载模型
    (2rtools) PS C:\Users\xxx\Desktop>python download.py
    ```

- 方法二：用命令行执行ModelScope下载

    ```Powershell
    # 安装ModelScope
    (2rtools) PS C:\Users\xxx\Desktop>pip install modelscope

    # 下载模型
    (2rtools) PS C:\Users\xxx\Desktop>python -c "from modelscope import snapshot_download; snapshot_download('Tencent-Hunyuan/Hunyuan-MT-7B', cache_dir='./models')"
    ```

    方法一和方法二下载完成后，你会看到一个models文件夹，里面就是模型文件了。

- 方法三：在Hugging Face网站下载（需要翻墙）

    点击 [此处](https://huggingface.co/tencent/HY-MT1.5-7B/tree/main) 进入网站直接下载。好处是下载过程可控，可以断点续传。

模型文件你可以随便找个地方存放，然后在config.ini配置文件中填上模型的绝对路径即可。

# 基础使用：让模型跑起来

若上述步骤一切顺利，即可宣告环境部署完毕。
先写个简单的脚本测试一下，确保一切正常。

创建一个test.py文件，内容如下：
```Python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

import time
import torch


def translate(model, tokenizer, source_txt: str, to_lang: str) -> str:
    '''
    开始翻译

    - source_txt: 输入文本
    - to_lang: 目标语种
    '''

    # 提示词。最好使用官方文档默认提示词
    prompts = f'将以下文本翻译为{to_lang}，注意只需要输出翻译后的结果，不要额外解释：\n{source_txt}\n\n'
    # 对话列表
    message = [
        {
            'role': 'user',
            'content': prompts,
        }
    ]
    # 编码输入
    inputs = tokenizer.apply_chat_template(
        message, tokensize=True, add_generation_prompt=False, return_tensors='pt'
    ).to(model.device)

    # 生成翻译
    outputs = model.generate(
        inputs,
        max_new_tokens=2048,
        temperature=1,
        top_p=0.8,
        top_k=30,
        repetition_penalty=1.05,
    )
    # 解码输出
    translated_text = tokenizer.decode(outputs[0], skip_special_tokens=True).split(
        '\n\n'
    )[-1]
    return translated_text


def load_model():
    '''
    加载模型与分词器
    '''

    print('正在加载模型和分词器...')
    start_time = time.time()
    model_path = r'你的模型路径'    # 例：D:\AI_Project\HY-MT1.5-7B
    activate_8bit = True

    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    # 量化加载类型，默认启用非量化加载
    config = None
    # 内存不足时，使用8位量化加载
    if activate_8bit:
        config = BitsAndBytesConfig(
                load_in_8bit=True,  # 启用8位量化加载
                llm_int8_threshold=6.0,  # 阈值，用于处理异常大的权重值
            )
    # 加载模型
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        device_map='auto',  # 自动分配GPU/CPU资源
        dtype=torch.bfloat16,  # 用bfloat16节省显存
        quantization_config = config,
        trust_remote_code=True,
    )
    load_time = time.time() - start_time
    print(f'模型加载完成，耗时: {load_time:.2f}秒\n')
    return model, tokenizer


if __name__ == '__main__':
    # 加载模型和分词器，程序启动时，模型和分词器只需要加载一次，所以要将模组加载单独提出来
    model, tokenizer = load_model()

    # 文本列表。这里就是你要翻译的文本
    txts = [
        'Hello, how are you today?',
        'I\'m the One!',
    ]
    print('正在生成翻译...\n')
    for i, item in enumerate(txts):
        print(f'原文：{item}')
        translated_text = translate(model, tokenizer, item, 'Chinese')
        print(f'译文：{translated_text}\n')
```

运行这个脚本：

```Powershell
(2rtools) PS C:\Users\xxx\Desktop>python test.py
```

如果一切正常，你会看到类似这样的输出：

```Powershell
正在加载模型和分词器...
模型加载完成，耗时: xx.xx秒
正在生成翻译...

原文: Hello, how are you today?
译文: 你好，今天过得怎么样？

原文：I'm the One!
译文：我就是那个人！
```

首次运行时会比较慢，因为模型需要加载到显存里。稍等片刻后，若能看到翻译结果就说明部署成功了！

# 支持的语言列表

| Languages           | Abbr.   | Chinese Names |
| ------------------- | ------- | ------------- |
| Chinese             | zh      | 中文          |
| English             | en      | 英语          |
| French              | fr      | 法语          |
| Portuguese          | pt      | 葡萄牙语      |
| Spanish             | es      | 西班牙语      |
| Japanese            | ja      | 日语          |
| Turkish             | tr      | 土耳其语      |
| Russian             | ru      | 俄语          |
| Arabic              | ar      | 阿拉伯语      |
| Korean              | ko      | 韩语          |
| Thai                | th      | 泰语          |
| Italian             | it      | 意大利语      |
| German              | de      | 德语          |
| Vietnamese          | vi      | 越南语        |
| Malay               | ms      | 马来语        |
| Indonesian          | id      | 印尼语        |
| Filipino            | tl      | 菲律宾语      |
| Hindi               | hi      | 印地语        |
| Traditional Chinese | zh-Hant | 繁体中文      |
| Polish              | pl      | 波兰语        |
| Czech               | cs      | 捷克语        |
| Dutch               | nl      | 荷兰语        |
| Khmer               | km      | 高棉语        |
| Burmese             | my      | 缅甸语        |
| Persian             | fa      | 波斯语        |
| Gujarati            | gu      | 古吉拉特语    |
| Urdu                | ur      | 乌尔都语      |
| Telugu              | te      | 泰卢固语      |
| Marathi             | mr      | 马拉地语      |
| Hebrew              | he      | 希伯来语      |
| Bengali             | bn      | 孟加拉语      |
| Tamil               | ta      | 泰米尔语      |
| Ukrainian           | uk      | 乌克兰语      |
| Tibetan             | bo      | 藏语          |
| Kazakh              | kk      | 哈萨克语      |
| Mongolian           | mn      | 蒙古语        |
| Uyghur              | ug      | 维吾尔语      |
| Cantonese           | yue     | 粤语          |
