# Python 基础

> 我会 C，所以下面都用 C 做对照。

---

## 1. 和 C 的快速对照

| C | Python |
|---|---|
| `#include <stdio.h>` | `import os` / `from openai import OpenAI` |
| `int x = 5;` | `x = 5`（不声明类型，不写分号） |
| `{ }` 包代码块 | **缩进 4 空格** |
| `struct {...}` | `{"role": "user", "content": "hi"}`（一行搞定） |
| `int a[3] = {1,2,3};` | `a = [1, 2, 3]` |
| `p->field` | `obj.field` |
| `NULL` / `true` | `None` / `True` |

---

## 2. 点链（attribute chain）

```python
response.choices[0].message.tool_calls
```

每一层点 = 往对象里取一个字段。就是 C 的 `a->b->c`。

### 三条规则

| 写法 | 作用 |
|---|---|
| `.名字` | 取字段 |
| `.名字()` | **调用方法**（有括号才是做事） |
| `[0]` | 取列表第 1 个元素 |

### 复数 = 列表 → 要加 `[0]`

```
response                       ← 单数：一个对象
└─ .choices[0]                 ← 复数！列表 → 加 [0]
   ├─ .index
   ├─ .finish_reason           ← 和 message 并列
   └─ .message                 ← 单数：一个对象 → 不加
      ├─ .role
      ├─ .content
      └─ .tool_calls[0]        ← 复数！列表 → 加 [0]
         ├─ .id
         └─ .function          ← 单数 → 不加
            ├─ .name
            └─ .arguments
```

### 最重要的一条

> **点链有几层不是你能选的——数据结构长什么样，你就得写几层。**

`content` 嵌在 `message` 里，而 `finish_reason` 和 `message` **并列**。
所以只能写 `choices[0].message.content`，不能写 `choices[0].content`。

### 怎么确定层数（不要靠猜）

| 方法 | 怎么做 |
|---|---|
| **打点看补全** | 敲到 `response.choices[0].` 停住，VS Code 弹出什么就有什么 |
| **打印出来看** | `print(response)`，对着 JSON 数层级 |

### 常用链子速查

| 链子 | 拿到什么 |
|---|---|
| `response.choices[0].message.content` | 模型说的话（文本） |
| `response.choices[0].message.tool_calls` | 工具调用列表 |
| `response.choices[0].finish_reason` | 为什么停下 |
| `response.usage.total_tokens` | 花了多少 token |
| `call.function.name` | 工具名 |
| `call.function.arguments` | 工具参数（JSON **字符串**） |
| `call.id` | 调用编号 |

---

## 3. 列表的 append

```python
messages.append(message)
```

往列表末尾追加元素。C 里你要自己管长度，Python 自动扩容。

| 坑 | 说明 |
|---|---|
| **原地修改** | 改变的是 `messages` 本身，不返回新列表 |
| **返回值是 `None`** | 别写 `a = b.append(x)`，`a` 会是空 |

---

## 4. dict（字典）

```python
{"role": "user", "content": "你好"}
```

Python 的键值对容器 = C 的 struct，但键是字符串、能动态增删。

### messages 就是"列表装字典"

```python
messages = [
    {"role": "system",    "content": "你是助手…"},
    {"role": "user",      "content": "请计算…"},
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool",      "tool_call_id": "...", "content": "4000"},
]
```

### 纯 dict vs SDK 对象

`response.choices[0].message` **不是 dict**，是 SDK 定义的对象，带一堆额外字段。

```
SDK 对象  =  一份带全部栏目的表格（姓名、电话、备注、审核意见、附件…）
纯 dict   =  只挑出需要的那两栏，重新抄在便签上
```

某些厂商（Moonshot）只收固定字段，回传整个 SDK 对象会触发
`tokenization failed` 400 错误。

修法：**手工重建**

```python
messages.append({
    "role": "assistant",
    "content": message.content or "",
    "tool_calls": [...],
})
```

---

## 5. json.load vs json.loads

| 写法 | 从哪读 |
|---|---|
| `json.load(fp)` | **文件对象** |
| `json.loads(s)` | **字符串** ← 解析工具参数用这个 |

> **记忆法：`loads` 的 s = string。**

```
'{"expression": "987654321 * 123456789"}'     ← 字符串（arguments 是这种）
{"expression": "987654321 * 123456789"}       ← 字典（json.loads 之后）
```

### 一定要兜底

模型偶尔生成**不合法的 JSON**，不处理会直接崩：

```python
try:
    args = json.loads(call.function.arguments or "{}")
except json.JSONDecodeError:
    args = {}          # 兜住，保持循环存活
```

### 它到底干什么（真实输入输出）

```
输入：'{"query": "比特币走势", "limit": 10}'
      类型是 str（字符串）

        ↓  json.loads(...)

输出：{'query': '比特币走势', 'limit': 10}
      类型是 dict（字典）
```

**把"一段文本"变成"能直接用的数据结构"。**

注意引号的变化：JSON 用**双引号**，Python 打印出来用**单引号**——同一个数据，换了身衣服。

### C 类比

```c
// C：手工拆字符串
char buf[] = "{\"name\": \"小明\", \"age\": 18}";
char name[50]; int age;
sscanf(buf, "{\"name\": \"%[^\"]\", \"age\": %d}", name, &age);
// 还要自己处理空格、转义、缺括号、嵌套……
```

```python
# Python：一行
data = json.loads('{"name": "小明", "age": 18}')
name = data["name"]      # 直接能用
```

### 四个函数一张表

| 函数 | 方向 | 从哪 / 到哪 |
|---|---|---|
| `json.load(fp)` | JSON → Python | 从**文件**读 |
| **`json.loads(s)`** | JSON → Python | 从**字符串**读 |
| `json.dump(obj, fp)` | Python → JSON | 写**到文件** |
| **`json.dumps(obj)`** | Python → JSON | 变成**字符串** |

> **记忆法：带 `s` 的是字符串（string），不带 `s` 的是文件（file）。**

### 为什么 Agent 里到处都是它

**模型和我的代码说的是两种"语言"：**

```
方向一：模型给的参数是字符串，我要变成字典
  模型生成    '{"expression": "987654321 * 123456789"}'    ← 字符串
                          ↓ json.loads()
  我的代码    {"expression": "987654321 * 123456789"}      ← 字典
                          ↓ ["expression"]
  计算函数    "987654321 * 123456789"

方向二：工具返回的字典，我要变成字符串
  工具返回    {"converted_amount": 1681969.62}             ← 字典
                          ↓ json.dumps()
  发给模型    '{"converted_amount": 1681969.62}'           ← 必须是字符串
```

**为什么模型给的是字符串？** 因为 API 协议规定 `arguments` 字段必须是字符串——
就像 HTTP 传的都是字节流，**文本是跨系统的通用格式**。

### `ensure_ascii=False` 是什么

```
默认 ensure_ascii=True   : {"query": "\u6bd4\u7279\u5e01\u8d70\u52bf", "limit": 10}
改成 ensure_ascii=False  : {"query": "比特币走势", "limit": 10}
```

| 参数 | 中文会怎样 |
|---|---|
| 默认（`True`） | 变成 `\u6bd4\u7279\u5e01...` 转义码 |
| `ensure_ascii=False` | **保持中文原样** |

**为什么要加它？** 一个中文字转义后占 6 个字符，发给模型白白浪费 token。
**一个抠细节的优化——这正是"上下文工程"里省钱的地方。**

### 坏 JSON 的报错长什么样

```
抛出的异常类型 : JSONDecodeError
异常信息       : Expecting ',' delimiter: line 1 column 19 (char 18)
```

**报错会告诉你"第几行第几列"**，这就是上面 `except json.JSONDecodeError` 捕获的东西。

### 可以玩的脚本

`work/json_demo.py`（在 ppt-ppt 目录下）——改一行跑一次，看输出怎么变。

---

## 6. 函数

```python
def calculate(expression):
    result = eval(expression)
    return str(result)
```

| C | Python |
|---|---|
| `double calculate(char* e)` | `def calculate(e):` |
| 要写返回类型和参数类型 | **都不写** |
| `{ }` | **冒号 `:` + 缩进** |
| `return x;` | `return x` |

**Python 从上往下执行，必须先定义后使用。** 写到调用之后会报 `NameError`。

---

## 7. 表达式不等于输出

```python
response.choices[0].message.content          # 算出了值，但什么都不显示
print(response.choices[0].message.content)   # 才会显示
```

| 你在哪 | 不加 print |
|---|---|
| 脚本文件 | **什么都不显示** |
| 交互模式（`>>>`） | 会自动显示 |

---

## 8. 环境变量与 .env

```python
api_key=os.getenv("DEEPSEEK_API_KEY")     # ← 参数是【名字】，不是值
```

写成 `os.getenv("sk-xxxxx")` 是错的——那是在问"有没有一个叫 sk-xxxxx 的环境变量"。

### 为什么要绕这一层

```
.env 文件       DEEPSEEK_API_KEY=sk-cc54...
      ↓ load_dotenv() 读进来
环境变量        DEEPSEEK_API_KEY = "sk-cc54..."
      ↓ os.getenv("DEEPSEEK_API_KEY")
代码里的变量     api_key = "sk-cc54..."
```

**因为代码要传给别人、要传到 GitHub。** 密钥写在代码里 = 泄露。
`.env` 被 `.gitignore` 忽略，永远不会上传。

### 改完 .env 必须重启程序

`load_dotenv()` 只在**启动时执行一次**。改完不重启，读到的还是旧值。

---

## 9. 其他小语法

### f-string（格式化字符串）

```python
print(f"--- 第 {turn} 轮 ---")     # 花括号里可以放变量
```

### 列表推导式

```python
[f(x) for x in items]
```

**等价于：**

```python
result = []
for x in items:
    result.append(f(x))
```

看到 `[ ... for x in y ]`，在心里展开成"循环 + append"。

### 括号内可以换行

```python
client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=messages,
    tools=tools,
)
```

括号没闭合时换行是允许的（不像 C 要写 `\`）。

⚠️ **除最后一个参数外，每个参数后面都要有逗号**——漏了会报
`SyntaxError: Perhaps you forgot a comma?`

### 三元表达式：`A if 条件 else B`

```python
tool_content = (
    tool_result
    if isinstance(tool_result, str)
    else json.dumps(tool_result, ensure_ascii=False)
)
```

**和 C 的 `? :` 是同一个东西**，只是条件写在中间：

```c
// C
tool_content = isinstance(...) ? tool_result : json.dumps(...);
```

**完全等价于这个 if/else 块：**

```python
if isinstance(tool_result, str):
    tool_content = tool_result
else:
    tool_content = json.dumps(tool_result, ensure_ascii=False)
```

外面那层 `( )` 只是为了能换行，和功能无关。

`isinstance(值, 类型)` = "这个值是不是这个类型"，返回 `True`/`False`。
C 里没有对应物（C 声明了类型就知道，Python 的类型是运行时才知道的）。

---

## 10. 怎么逐行读一行代码（四步法）

看到任何一行 Python，按这个顺序问自己：

| 步骤 | 问什么 | 怎么做 |
|---|---|---|
| **① 先找 `=`** | 结果是什么？ | 左边变量名，右边是"怎么算出来的" |
| **② 按符号切开** | 由几个片段组成？ | 按 `,` `.` `+` 切开 |
| **③ 每个片段是什么** | 字符串？变量？函数调用？ | 逐个判断类型 |
| **④ 不确定就查** | 这个字段/方法是什么 | 打点看补全、print、查文档 |

**核心心态：一行代码不是"一句话"，是"一串原子操作的组合"。**

### 示范一：拼一个 URL

```python
url = f"{self.base_url.rstrip('/')}/formulas/{self.formula_uri}/fibers"
```

切成四块：

| 片段 | 是什么 |
|---|---|
| `f"..."` | **f-string**，里面 `{}` 会被替换成实际的值 |
| `{self.base_url.rstrip('/')}` | 取 `base_url`，再 `.rstrip('/')` **去掉末尾的 `/`** |
| `/formulas/` | 固定文字 |
| `{self.formula_uri}` | 取 `formula_uri` |

**为什么要 `rstrip('/')`？** 因为后面要拼的 `/formulas/` 以 `/` 开头。
如果 base_url 末尾也带 `/`，会拼出 `//`，URL 就错了。这是防拼错的标准写法。

### 示范二：构造一个字典

```python
body = {"name": name, "arguments": raw_arguments}
```

**左边是固定的字符串（键名），右边是从变量取值。** 看起来像重复，其实不是。

C 里要这么写：

```c
sprintf(body, "{\"name\": \"%s\", \"arguments\": \"%s\"}", name, raw_arguments);
```

**Python 直接把它换成了字典字面量——不用手写转义符、不用记 `%s`。**

### Python 符号字典（同一个符号，多种含义）

这是新手最困惑的地方：**同一个符号在不同位置意思完全不同。**

| 符号 | 在哪 | 含义 |
|---|---|---|
| 大括号 | `{"a": 1}` | **字典**字面量 |
| 大括号 | `f"{name}"` | f-string 里的**占位符** |
| 方括号 | `[1, 2, 3]` | **列表**字面量 |
| 方括号 | `arr[0]` | **下标取值** |
| 方括号 | `d["key"]` | **按键取值** |
| 圆括号 | `f(x)` | **函数调用** |
| 圆括号 | `(a + b)` | **分组**（改运算顺序） |
| 冒号 | `{"a": 1}` | 分隔**键和值** |
| 冒号 | `def f():` | 代码块开始 |
| 点 | `obj.field` | 取**字段** |
| 点 | `obj.method()` | **调方法**（有括号） |

```python
user = "小明"
a = {"name": user}      # 大括号 = 字典
b = f"{user} 你好"       # 大括号 = 占位符（在 f 开头的字符串里）
```

---

## 11. 练习法：中文注释重写

**给代码逐行加中文注释，是提升"逐行理解力"最快的方法。**

```python
# 拼出调用 Formula 服务的 URL
url = f"{self.base_url.rstrip('/')}/formulas/{self.formula_uri}/fibers"

# 组装要发送的请求体：工具名 + 参数
body = {"name": name, "arguments": raw_arguments}

# 发 POST 请求，把请求体作为 JSON 发送
response = requests.post(url, headers=..., json=body)

# 把响应体解析成字典
payload = response.json()
```

### 但注释不是越多越好

```python
# ❌ 废话注释（重复了代码本身）
i = i + 1        # i 加 1

# ✅ 有用的注释（解释"为什么"）
i = i + 1        # 从 1 开始计数，和书里的 iteration 编号对齐
```

> **好注释解释"为什么这么做"，不是"这行在干什么"。**
> 后者看代码就知道，前者只有写的人知道。

**自测方法：写不出注释的地方，说明那行还没懂。**

---

## 12. 类与对象（C 程序员视角）

**C 里没有"类"，最接近的是"struct + 一堆操作它的函数"。Python 把数据和操作打包在一起。**

```python
class ToolCallingAgent:
    """文档字符串：说明这个类是干什么的"""

    def __init__(self, backend=None):        # ← 构造函数
        self.agent = None                    # ← 实例属性
        self.backend_type = backend or self._detect_best_backend()

    def chat(self, message):                 # ← 方法
        return self.agent.chat(message)
```

### 三个必须记住的点

| 点 | 说明 |
|---|---|
| **`__init__`** | 构造函数。**前后各两个下划线**是 Python 对"特殊方法"的标记 |
| **`self`** | **就是 C 里的 `this`**，但 Python 要求你**显式写在第一个参数位置** |
| **`_名字`** | 下划线开头 = "内部方法，外部别直接调"。**只是约定，不强制** |

### `self` 的对照

```c
// C：this 是隐式的
void chat(Agent* this, char* msg) {
    this->agent->chat(msg);
}
```

```python
# Python：self 必须显式写
def chat(self, message):
    return self.agent.chat(message)
```

**C 里 `p->field`，Python 里 `self.field`。同一个意思。**

---

## 13. `A or B` 的短路取值（不是判断 NULL！）

```python
self.backend_type = backend or self._detect_best_backend()
```

**读作：如果 `backend` 是"真值"就用它，否则用后面那个。**

### ⚠️ 它判断的是"真值"，不是"是不是 None"

```c
// C 里你写的
if (p != NULL) { use(p); } else { default(); }
```

```python
# Python 里可以简写成
p or default()
```

**但 Python 的"假值"有六个：**

```python
None、""（空串）、0、[]（空列表）、{}（空字典）、False
```

**所以 `backend=""` 也会触发自动检测——这跟 C 的"指针空不空"不是一回事。**

### 常见变体

```python
config = payload.get("context") or {}      # 取不到就换成空字典（防止下一步 .get 报错）
```

---

## 14. `try / except` 的三种典型用法

### 用法 1：可选依赖（没装也不崩）

```python
try:
    import torch
    if torch.cuda.is_available():
        return "vllm"
except ImportError:
    pass                    # ← 没装 torch，直接跳过，不算错误
```

**读作："试着导入；没装就算了。"**

### 用法 2：把错误变成信息返回（兜住）

```python
try:
    args = json.loads(call.function.arguments or "{}")
except json.JSONDecodeError:
    args = {}               # ← 用空对象继续，保持循环存活
    logger.warning(...)
```

**适合"中间态"错误——错误本身能变成信息传给上游纠正。**

### 用法 3：分层错误，给不同提示

```python
try:                        # 外层：管"包装没装"
    import ollama
    try:                    # 内层：管"服务没跑"
        ...
    except Exception as e:
        logger.error(f"Ollama is not running: {e}")
        logger.info("Please start Ollama: ...")      # ← 带解决方案
except ImportError:
    logger.error("Ollama not installed")
    logger.info("Install with: pip install ollama")  # ← 带解决方案
```

**原则：错误提示的粒度，应该匹配用户需要做的动作。**

### 什么时候不该兜住

**"没法继续了"的错误要立刻抛，不要静默吞掉。**

```python
if result in (None, ""):
    raise RuntimeError("... returned no output")   # ← 继续只会让错的流下去
```

**判断标准：这个错误能不能变成有用的信息，传给上游纠正？能就兜住，不能就放手。**

---

## 15. 函数是一等公民（C 里没有）

**Python 里函数可以像数字、字符串一样被存进字典、当参数传。**

```python
self.tools[name] = {
    "function": self.get_current_temperature,   # ← 存的是【函数本身】，不是调用结果
    "description": "...",
}

# 用的时候
result = self.tools[name]["function"](**arguments)   # ← 取出来直接调
```

**注意 `self.get_current_temperature` 后面**没有括号**：
有括号是"调用它、拿返回值"；没有括号是"把函数本身当值传过去"。**

**C 里最接近的是"函数指针"。**

---

## 16. ⭐ 生成器 `yield`（C 里没有）

```python
def chat_stream(...):
    for chunk in stream_response:
        yield {"type": "thinking", "content": chunk}    # ← 不是 return
```

### `yield` 和 `return` 的区别

| | 行为 |
|---|---|
| **`return`** | 返回**一次**，函数就**结束了** |
| **`yield`** | 可以返回**很多次**，每次返回后**暂停**，下次从暂停处**继续** |

**`yield` 的准确含义：**

> "我先交出这个值，然后**暂停**在这里。等你下次来要，我**从这里继续**往下跑。"

### 用了 yield 的函数叫"生成器函数"

**调用它不会立刻执行**，而是返回一个"可以不断取值的东西"：

```python
for chunk in agent.chat(task, stream=True):    # ← 每取一次，函数就跑一段，yield 一个值
    处理(chunk)
```

**C 里最接近的是"回调函数"——每收到一块就调用一次回调。
但 `yield` 让代码写起来像普通循环，不用把逻辑拆成回调。**

### 典型场景

**流式输出**：服务端一块块给，你就一块块 `yield` 出去，调用方一块块显示。

---

## 17. `print` 的两个关键参数

```python
print(f"\033[90m{content}\033[0m", end="", flush=True)
```

| 参数 | 默认 | 作用 |
|---|---|---|
| **`end=""`** | `"\n"`（换行） | 改成空串 → **不换行，接着上一次继续打** |
| **`flush=True`** | `False` | **立刻输出，不要缓冲** |

**为什么流式必须用这两个：**

- 不加 `end=""` → 每块都换一行，输出会碎成几十行
- 不加 `flush=True` → Python 可能攒一批才输出，**流式就白做了**

### ANSI 转义码（控制终端颜色）

```python
print("\033[90m这是灰色\033[0m 这是默认色")
```

| 码 | 作用 |
|---|---|
| `\033[90m` | 开始：暗灰色 |
| `\033[0m` | 恢复：默认颜色 |

**`\033` 是 ESC 字符（ASCII 27）。你在终端里看到"思考文字是灰色"，就是它在起作用。**

---

## 18. 实用内置函数与语法速查

| 函数/语法 | 作用 | 例子 |
|---|---|---|
| `isinstance(值, 类型)` | 判断类型 | `isinstance(x, str)` |
| `hasattr(对象, '属性')` | 判断对象有没有这个属性 | `hasattr(resp, 'models')` |
| `值 in 容器` | 判断在不在里面 | `"qwen3:0.6b" in models` |
| `字典.items()` | 遍历键值对 | `for name, tool in self.tools.items():` |
| `字典.get(键, 默认)` | 安全取值 | `payload.get("status")` |
| `len(容器)` | 长度 | `len(tool_calls)` |
| `round(数, 位数)` | 四舍五入 | `round(x, 6)` |
| `sys.exit(1)` | 立刻退出（1 = 出错） | 等价于 C 的 `exit(1)` |
| `eval("1+1")` | 把字符串当代码**算**并返回结果 | `eval("2+3")` → 5 |
| `exec(code)` | 把字符串当代码**执行**（不返回结果） | 用来跑一段脚本 |

> **`eval` 和 `exec` 的区别：`eval` 求值（有返回值），`exec` 执行（没返回值）。**
> **两个都很危险**（能执行任意代码），生产环境不能直接用在用户输入上。

### `**` 字典解包（C 里没有）

```python
arguments = {"location": "Tokyo", "unit": "celsius"}
func(**arguments)
# 等价于
func(location="Tokyo", unit="celsius")
```

**`**` 把字典拆成一组关键字参数；单个 `*` 用于列表解包：**

```python
args = [1, 2, 3]
func(*args)      # 等价于 func(1, 2, 3)
```
