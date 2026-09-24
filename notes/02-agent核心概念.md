# Agent 核心概念

> 这一份是两天里最值钱的东西。面试能讲清楚这些，就超过大部分候选人了。

---

## 1. 模型没有记忆（一切的前提）

**LLM 完全无状态**——每次 API 调用，它都是**第一次见到你**。

那"记忆"是怎么来的？

> **是你每次把之前的对话，重新发一遍。**

```
第 1 次调用  发出： [user: 请计算…]
            ← 收： assistant（我要调工具）

第 2 次调用  发出： [user: 请计算…, assistant: 我要调工具, tool: 4000]
                   ↑ 把历史【又发了一遍】
            ← 收： assistant（答案是 4000）
```

**模型不是"记得"那条工具结果——是你第二次调用时又告诉它了一遍。**

### 重大推论：成本 = 历史长度 × 轮数

```
总花费 ≈ 历史长度 × 轮数
```

**这是乘法关系，不是加法。** 同一份历史，第 1 轮付一次钱，第 2 轮再付一次……

这就是为什么 Agent 比聊天机器人贵得多，也是为什么要研究"哪些上下文能删"。

（严格说服务端有 context caching 可以把重复前缀缓存起来，但**模型看到的仍是完整内容**，
只是算得快、算得便宜。）

---

## 2. messages 的结构

```python
messages = [
    {"role": "system",    "content": "你是助手…"},
    {"role": "user",      "content": "请计算…"},
    {"role": "assistant", "tool_calls": [...]},
    {"role": "tool",      "tool_call_id": "...", "content": "4000"},
]
```

| role | 谁说的 | 作用 |
|---|---|---|
| `system` | 你（设定规则） | 告诉模型它是谁、该怎么做 |
| `user` | 你（用户） | 你提的需求 |
| `assistant` | **模型** | 模型自己的回复 |
| `tool` | **你的代码** | 工具执行的结果 |

| 字段 | 谁有 | 含义 |
|---|---|---|
| `content` | 所有角色 | 说了什么 |
| `tool_calls` | 只有 assistant | 它要调用哪些工具 |
| `tool_call_id` | 只有 tool | 这条结果在回应哪次调用（快递单号） |

### 一条铁律

> **每条 `tool` 消息，前面必须有一条带 `tool_calls` 的 `assistant` 消息。**

违反会直接 400：

```
Messages with role 'tool' must be a response to a preceding message with 'tool_calls'
```

像回信一样——**没有来信，你没法回信**。

---

## 3. 工具的本质（最重要的一节）

### 模型不执行任何代码，它只会"请求"

```
① 你发请求（带上 tools 说明书）
      ↓
② 模型回答："请帮我调用 calculate，参数是 (125+375)*8"    ← 模型只做这些
      ↓
③ 【你的 Python 程序】执行 calculate(...)                 ← 真正算的地方
      ↓
④ 你的程序把结果塞回 messages
      ↓
⑤ 你再发一次请求
      ↓
⑥ 模型看到结果，组织语言："答案是 4000"                    ← 只是转述
```

**模型只做两件事：决定（用哪个工具、参数是什么）+ 转述（把结果说成人话）。**

### 两个"工具"是两个东西

| 概念 | 长什么样 | 给谁看 |
|---|---|---|
| **工具说明书** | `tools = [...]`（变量） | **模型**（靠它决定要不要用） |
| **工具实现** | `def calculate(...)`（函数） | **你的程序**（真正干活） |

**两者靠 `name` 字段对上：`"name": "calculate"` ↔ `def calculate`。**

### description 是写给模型看的

```python
"description": "计算一个数学表达式，支持 + - * / 和括号"    # ✅ 模型知道什么时候用
"description": "助我找到工作"                              # ❌ 模型看不懂
```

> **写 description 时，你是在给一个没见过世面的新人写使用说明。**

### 键名是接口契约，一字不能错

| 引号里的东西 | 谁定的 | 能改吗 |
|---|---|---|
| `type` `function` `name` `description` `parameters` `properties` `required` | **API 规定** | ❌ 一个字母都不能错 |
| `"string"` `"object"` | JSON Schema | ❌ 只能填规定的值 |
| `"calculate"`（工具名） | 你 | ✅ |
| `"expression"`（参数名） | 你 | ✅ 但两处必须一致 |

⚠️ **Python 字典没有编译期检查**——`properties` 写成 `propreties` 照样能跑，
但模型收到一份没有参数定义的说明书，行为就玄学了。

### 模型的四条硬边界（为什么必须用工具）

| 边界 | 说明 |
|---|---|
| **时间** | 知识冻结在训练完成那一刻，不知道今天的事 |
| **可靠性** | 本质是概率生成器，不是计算器，输出"最像正确答案的东西" |
| **可审计** | 只有权重，没有"来源"这个概念 |
| **行动** | 只能输出文字，不能发邮件、改数据库、写文件 |

> **聪明 ≠ 无所不知 ≠ 不会出错 ≠ 能动手。**

### 工具的边界 = 模型能力的边界之外

| 任务 | 模型能吗 | 要工具吗 |
|---|---|---|
| `(125+375)*8` | ✅ 心算就行 | ❌ |
| 18 位乘法 | ⚠️ 不可靠 | ✅ |
| 读 PDF 里的表格 | ❌ 看不见文件 | ✅ |
| 查固定汇率表 | ❌ 不知道那张表 | ✅ |
| 访问实时数据 | ❌ | ✅ |

**出一道"模型本来就答得上来"的题，工具坏了你也看不出来。**

---

## 3.5 工具调用的完整生命周期（最高频操作）

### 谁写什么

```
【我写的】
  tools = [...]              ← 工具说明书
  def calculate(...)         ← 工具实现
  循环逻辑 / append 逻辑      ← 程序

【模型每次回复时生成的】
  message.tool_calls
    ├─ id             = "call_00_B96N..."   ← 服务端生成
    ├─ function.name  = "calculate"          ← 模型从清单里选
    └─ function.arguments                    ← 模型按 schema 生成
  message.content            ← 模型的文字回复

【我的代码生成的】
  tool 消息的 content         ← 工具执行的结果
```

### 方向相反，别绕晕

```
我   ──→  模型     tools 清单        "你有这些工具可用"     ← 我写的
模型 ──→  我       tool_calls 请求   "请帮我调这个工具"     ← 它生成的
```

| | 谁生成 | 内容 | 谁读 |
|---|---|---|---|
| `tools` | **我** | "我有这些工具" | **模型** |
| `tool_calls` | **模型** | "请你帮我调这个" | **我的代码** |

**我负责"摆工具"，模型负责"要工具"。**
`tool_calls` 完全不用我写——它是模型的输出，我只读不写。

### 三个关键字段的含义

**`tool_calls`** = 模型这一轮要调用的工具**清单**（列表，可能多个）

```python
[
    {"id": "call_A", "function": {"name": "convert_currency", "arguments": "..."}},
    {"id": "call_B", "function": {"name": "get_time",         "arguments": "{}"}},
]
```

**一轮可以同时要调好几个工具**，所以是列表、要遍历。

**`tool_call_id`** = 这次调用的**快递单号**

服务端生成的唯一 ID。回填结果时必须带上，否则模型不知道
哪条结果配哪个请求。

```python
"tool_call_id": call.id
                 ↑ 同一个值，只是字段名不同（请求里叫 id，回复里叫 tool_call_id）
```

⚠️ **不能自己编。** 服务端会逐条核对，编的话直接 400：
`must be a response to a preceding message with 'tool_calls'`

**`args["expression"]`** = 从字典里**按键取值**

```python
args = json.loads(call.function.arguments)   # 字符串 → 字典
result = calculate(args["expression"])       # 按键取值
```

C 类比：`args->expression` vs `args["expression"]`，同一个操作。

⚠️ **`"expression"` 这个名字是我自己在 `tools` 里定的**，四处必须一致：

```
① tools 里 properties 的键名
② tools 里 required 的名字
③ 模型生成的 arguments 的键名（它按说明书来）
④ 代码里 args["..."] 的名字
```

**对不上会报 `KeyError`。** 看到这个错，第一反应就是回去对名字。

### 完整时间线

```
时刻 1   我写：tools = [...]                              ← 我
时刻 2   我发请求，带上 tools                             ← 我
时刻 3   模型生成 tool_calls（id / name / arguments）      ← 模型 + 服务端
时刻 4   我的程序：读 tool_calls，执行工具                 ← 我读
时刻 5   我的程序：组装 tool 消息，把 call.id 抄进 tool_call_id ← 我抄
时刻 6   我发第二次请求                                   ← 我
时刻 7   服务端校验：每个 tool_call_id 都能找到对应 id      ← 服务端
时刻 8   模型看到结果，生成最终回答                        ← 模型
```

### 代码里的对应

```python
for call in message.tool_calls:              # tool_calls = 清单
    args = json.loads(call.function.arguments)   # arguments 是 JSON 字符串
    result = calculate(args["expression"])       # 按键取值
    messages.append({
        "role": "tool",
        "tool_call_id": call.id,                 # 快递单号，原样抄
        "content": result,                       # 我的代码产生的结果
    })
```

### 谁产生什么（速查）

| 东西 | 谁产生 | 我做什么 |
|---|---|---|
| `tools` | **我** | 写 |
| `tool_calls` | **模型** | 读 |
| `call.id` | **服务端** | 抄 |
| `function.name` | **模型**（从清单里选） | 读 |
| `function.arguments` | **模型**（按 schema 生成） | 解析 |
| tool 消息的 `content` | **我的代码** | 写 |

---

## 4. ReAct 循环

```
想（Reason） → 做（Act） → 看（Observe） → 再想 → …
```

对应代码就是一个循环：

```python
messages = [{"role": "user", "content": task}]

for turn in range(1, max_turns + 1):
    response = client.chat.completions.create(
        model=..., messages=messages, tools=tools)
    message = response.choices[0].message
    messages.append(message)                    # 记住它说了什么

    if not message.tool_calls:                  # 没要工具 = 说完了
        return message.content

    for call in message.tool_calls:             # 有工具请求 → 执行
        args = json.loads(call.function.arguments)
        result = calculate(args["expression"])
        messages.append({"role": "tool",
                         "tool_call_id": call.id,
                         "content": result})
return "撞到轮数上限"
```

**这 15 行就是 Agent 的全部心脏。** 大项目的 1000 行是围着它做工程化。

### 两种"判断该停了"的机制

| 机制 | 怎么做 | 可靠性 |
|---|---|---|
| **靠约定** | 让模型输出文本暗号 `FINAL ANSWER:` | ⚠️ **脆弱**——模型可能忘了写 |
| **靠 API 字段** | 看 `finish_reason`（`stop` / `tool_calls` / `length`） | ✅ **可靠**——协议层面保证 |

**实验 1-1 用第一种**，所以模型一旦糊涂就永远说不出暗号 → `no_terminal_response`。
**实验 1-2 用第二种**，几乎不会出现这种问题。

> **工程教训：不要靠模型"自觉表示自己说完了"，要靠协议的结构化信号。**

### `max_iterations` 是保险丝，不是正常流程

- 正常：模型 2~3 轮判断够了，给答案 → **碰不到上限**
- 异常：模型抽风一直调工具 → 上限强制掐断

**这是我们能控制的边界：模型可以自由飞，但飞不出这个笼子。**

---

## 5. 开发者的权力（最需要敬畏的一点）

| 权力 | 具体是什么 |
|---|---|
| ① 决定模型**看到什么** | `messages` 里放什么、不放什么、改写什么 |
| ② 决定模型**能用什么** | `tools` 清单里给哪些工具 |
| ③ 决定它**什么时候停** | 轮数上限、终止条件 |
| ④ 决定用户**最终看到什么** | 可以过滤、改写、甚至阻断输出 |

> **Agent 系统的"真相"，由开发者的代码定义，不由模型定义。**

### 推论：代码可以对模型"说谎"，模型无法察觉

```python
"content": result              → 模型看到 4000
"content": ""                  → 模型看到空
"content": "工具返回 8675309"   → 模型看到假数据，而且会当真
```

因为**模型唯一的输入就是 `messages`**。它看不见你的代码、看不见日志、
看不见工具的真实返回。

**这就是"数据投毒"和"提示注入"的原理**——模型读到的所有文本地位平等，
它分不清哪句是你说的、哪句是攻击者塞的。

---

## 6. 上下文消融（实验 1-1）

四种消融，全部发生在"你构造那封信"的那一刻：

| 模式 | 改的是 JSON 的哪里 | 结果 |
|---|---|---|
| `full` | 原样 | 正常 |
| `no_history` | `messages` 只留 system + 当前任务 | 反复重做，撞满轮数 |
| `no_reasoning` | 剥掉 assistant 的 `reasoning_content` | 实测测不出退化 |
| `no_tool_calls` | 不传 `tools` | 拒答，或用记忆里的数据作答 |
| `no_tool_results` | tool 消息的 `content` 置空 | 反复重试，或**自己编** |

### 我的实测结果（DeepSeek）

| 组 | 轮数 | 工具调用 | 结果 |
|---|---:|---:|---|
| full | 3 | 7 | ✅ |
| no_history | **10（撞满）** | **33** | ❌ |
| no_reasoning | 4 | 7 | ✅ 测不出退化 |
| no_tool_calls | 1 | 0 | 没报数字 |
| no_tool_results | 7 | 14 | ⚠️ **报出 12 个无依据的数字** |

### `completed = True` 不代表做对了

`no_tool_results` 那组给出了：

> Converted to USD (**using GBP 1.27, JPY 0.0067, EUR 1.08, SGD 0.75**): …

括号里那四个汇率，它一个都没拿到过。**而这一组的 `completed` 是 `True`。**

---

## 7. 可依据性（grounding）

### 核心命题

> **答案看起来合理 ≠ 答案有依据。**
> **答对了 ≠ 是读到的。**

### 审计思路（像会计查账）

```
答案里的数字  −  （任务文本里的数字 + 工具消息里的数字）  =  无依据的数字
```

**不判对错，只查"有没有出处"。**

### 为什么"让模型自己验证"没用

它验证用的还是**自己脑子里那点知识**——恰恰是幻觉的来源。

> **让模型自己验证 = 让嫌疑人当法官。**

真正的验证必须是**独立的第二个来源**（交叉验证），只能由你的代码实现。

### 五种判定

| verdict | 什么时候给 |
|---|---|
| `no_answer` | 模型没给终止回答 |
| `not_assessable` | 模型看到了观测，心算和编造分不清 → **拒绝判断** |
| `no_quantities` | 没看到观测，也没报数字（诚实拒绝） |
| `grounded` | 数字都能在任务文本里找到 |
| `ungrounded` | **没看到观测，却报出了任务里没有的数字** ⚠️ |

> `not_assessable` 这个设计值得学：**宁可说不知道，也不给假结论。**

### 最关键的实现细节

> **审计的对象是"模型看到了什么"（实际发出的 messages），
> 不是"程序做了什么"（工具实际执行的结果）。**

这就是为什么改一个 `""` 就能骗过检查。

---

## 8. 危险的三种故障形态

| 故障 | 模型能察觉吗 |
|---|---|
| 工具返回空 | ✅ 能（它会说"没拿到结果"） |
| 工具超时但程序用了缓存 | ❌ 察觉不到 |
| 返回了过期 / 错误但格式正常的数据 | ❌ **察觉不到** |

> **危险的故障不是"没有"，而是"看起来有，但不对"。**

`8675309` 之所以能被发现，是因为它**太离谱**。
换成看起来合理的数字，模型照样拿去用——**它只能判断"有没有数"，不能判断"数对不对"。**

---

## 9. 一句话版总结

> **模型负责"想"，工具负责"做"，上下文是唯一的信息通道，而你控制这个通道。**
