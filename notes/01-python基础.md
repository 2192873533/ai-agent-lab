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
