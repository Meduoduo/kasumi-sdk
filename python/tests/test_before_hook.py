from examples.ppt_helper.summary import *
from requests import post
from json import loads

prompt = '''
你是一个PPT制作助手，你精通如何总结通过长文本制作PPT，现在总结下面的Markdown文档为PPT，以1000字左右的篇幅。
写出你的总结内容，列出关键内容，并且该总结将被用来做成PPT，因此你需要提取所有的表格、公式相关的信息，并将每一页PPT的内容展示出来。
最终需要的内容为：标题、导航、每个章节的内容、每个小节的内容、原文包含的公式和表格，并将表格和公式保存在每个对应小节中。

下面是需要制作为PPT的内容。
'''

content = '''
```
### 索引节点
在用户/程序操作目录/文件时，经常只需要使用到“文件名”这样的信息，因此，放到内存来看，我们其实面对的就是一个这样的映射
```math
f(filename) = \&File
```
文件是储存在磁盘上的，而磁盘的扫描是高IO需求的，它的速度相对内存非常缓慢，但是我们其实并不需要文件的所有信息来检索一个文件，我们只需要找到这个文件在硬盘上对应的地址即可，详细来说就是“扇区”“簇”这样的概念，现在，我们做一个基本假设，文件在磁盘上的地址编码为一个长整型，其编码规律为

##### 表1（每项数据64位+）

| 数据项 | 文件ID（对应表2的文件ID） | 扇区 | 簇 | 偏移 | 类型 | 文件名 |
| --- | --- | --- | --- | --- | --- | --- |
| 偏移 | 0 | 32 | 48 | 56 | 60 | 64 |

例如

| 文件ID（对应表2的文件ID） | 扇区 | 簇 | 偏移 | 类型 | 文件名 |
| --- | --- | --- | --- | --- | --- |
| 1 | 32 | 48 | 56 | 60 | /usr | 
| 2 | 32 | 48 | 56 | 60 | /usr/bin | 
| 3 | 32 | 48 | 56 | 60 | /usr/bin/python | 

一个文件的所有信息都被这样被操作系统进行维护，其可以精确定位到一个磁盘上的文件，现在，我们为操作系统创建一张表，用来保存所有的文件，如下

##### 表2 （每项数据256位以上）

| 文件ID | 文件其他数据 | 地址 | 保留段 |
| --- | --- | --- | --- | 
| 1 | 创建时间…… | 0x126487945abfc | 0 |
| 2 | 创建时间…… | 0x7894543acba | 0 |
| 3 | 创建时间…… | 0x12368abcdef | 0 |

现在，我们再将这一张表固定保存在1扇区偏移0x3600处，之后，操作系统在启动的时候，只需要扫描这个扇区的全部内容（可能不止一个扇区），即可将这张表扫描进内存进行保存，当然，不一定需要全量保存，全量保存可能会出现性能瓶颈，最优的做法是做近期缓存，这个涉及到了文件系统的另一个方向，这里不过多赘述

我们知道，表1是以树状（或别的类型）形式进行储存的，所以在检索的时候，时间复杂度为（其中N为目录长度）
```math
O(lnN)
```
因此，事实上我们扫描表2的速度是很快的，在没有表1的辅助的时候，我们找寻找一个文件，需要将表2从磁盘里加载进来，即使有缓存，也会相对较慢，同时会影响因内存IO速度，内核对IO的速度要求是很苛刻的，所以这个时候我们就需要“简化信息”，正如一开始所说的，我们只需要文件名即可，将较小的表1扫描进内存，然后利用树状结构加快扫描速度，找到目标“文件ID”，即索引值，再利用这个索引值去表2精确定位到数据项，这样就避免了复制的磁盘IO，不需要扫描多个磁盘扇区，只需较小的扫描即可，一方面降低了内存占用，另一方面加快了扫描速度

```
'''

def test_summary():
    token = input("token: ")

    response = post("http://127.0.0.1:8192/v1/sdk/llm_summary", data={
        "app_id": 66,
        "key": '',
        "token": token,
        "token_type": TokenType.PLAINTEXT.value,
        "content": content,
        "prompt": prompt
    })

    print(loads(response.text, encoding='utf-8', strict=False))