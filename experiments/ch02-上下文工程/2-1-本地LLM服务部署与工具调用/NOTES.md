# 实验 2-1 · 本地 LLM 服务部署与工具调用

| | |
|---|---|
| 难度 | ★ |
| 书源码 | `chapter2/local_llm_serving/` |
| 状态 | ✅ 完成（7 条验收标准过了 6 条） |
| 日期 | 2026-09-28 |
| 环境 | Windows + Ollama + qwen3:0.6b（本地、免费、不用 API Key） |

## 这个实验在做什么

**这是第一个"服务层面"的实验** —— 前面的实验都在客户端，这个要**自己跑一个模型服务**。

书里的核心问题：

> 模型服务接收消息并生成文本或工具调用；客户端负责识别调用、执行工具和返回结果。
> **支持同一种 HTTP 接口，并不意味着所有模型都能稳定产生相同的工具结构。**

---

## 一、为什么必须是"本地"模型

**这是实验设计的前提，不是随便选的。**

| 要观测的东西 | 用云端 API 能测吗 | 为什么 |
|---|---|---|
| raw token 流 | ❌ | API 返回的是解析好的 JSON，原始 token 看不到 |
| TTFT（首字延迟） | 🟡 混着网络延迟 | 本地才干净 |
| **KV Cache 命中/未命中** | ❌ | **API 不告诉你缓存命中没命中** |
| 并发吞吐 | ❌ | 你控制不了 API 的并发度 |
| 模型冷启动 | ❌ | 云端早就热好了 |

> **结论：Ollama 的意义不是"省 API 钱"，而是"让你能看见服务的内部"。**

**而选 0.6B 是刻意的：够小（普通电脑跑得动）＋ 够快（能反复做性能实验）＋ 够笨（会犯错，能看到模型的能力边界）。**

---

## 二、环境搭建

```powershell
# ① 装 Ollama
winget install --id Ollama.Ollama

# ② 拉模型（522 MB）
ollama pull qwen3:0.6b

# ③ 装 Python 包
cd .\outputs\ai-agent-book
.\.venv\Scripts\python.exe -m pip install ollama PyPDF2 tzdata -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 踩的坑：`tzdata` 必须单独装

**第一次跑时间工具时报错：**

```json
{"error": "'No time zone found with key Asia/Tokyo'"}
```

**根因：Windows 不自带 IANA 时区数据库，Python 的 `zoneinfo` 需要 `tzdata` 包。**
**装上就好了 —— 这是环境问题，不是代码 bug。**

### 环境自检

```powershell
ollama ps        # 看模型在不在内存里、占多少、用什么算
ollama list      # 看装了哪些模型
```

**实测输出：**

```
NAME          ID              SIZE      PROCESSOR    CONTEXT    UNTIL
qwen3:0.6b    7df6b6e09427    930 MB    100% GPU     4096       About a minute from now
```

| 字段 | 值 | 含义 |
|---|---|---|
| SIZE | 930 MB | 加载后占 930MB（文件 522MB + 运行时开销） |
| **PROCESSOR** | **100% GPU** | **在用 GPU 算** → 所以快 |
| **CONTEXT** | **4096** | **上下文上限只有 4096 token**（比 GPT 的 128K 小得多） |
| **UNTIL** | About a minute from now | **空闲一会儿自动卸载** → 这就是冷启动的来源 |

---

## 三、七条验收标准（逐条）

### 1. Local ~0.6B model ✅

**证据：日志里的请求地址**

```
httpx - HTTP Request: POST http://127.0.0.1:11434/api/chat
                                     ↑ 127.0.0.1 = 本机，请求没出电脑
```

**连带学到的：** 本地部署意味着"模型有装入/卸出机制"→ 所以有**冷启动**。
云端 API 早就热好了，你根本看不到这个现象。

### 2. ReAct ✅

**一次真实运行的完整五步（东京时间那次）：**

```
🧠 Thinking: Okay, the user is asking for the current time in Tokyo.
             Let me check the tools available...
             I need to make sure the timezone is set to 'Asia/Tokyo'.
             ↓ ① Reason（想）

🔧 Tool Calls:
  → get_current_time: {'timezone': 'Asia/Tokyo'}
             ↓ ② Act（做）

    ✓ {"timezone": "Asia/Tokyo", "datetime": "2026-09-27 02:34:56", ...}
             ↓ ③ Observe（看）

Okay, the user asked for the current time in Tokyo... The response came back
with the datetime as 2026-09-27 02:34:56... a straightforward answer should work.
             ↓ ④ Reason again（再想）

🤖 Assistant: The current time in Tokyo is 2026-09-27 02:34:56 (Sunday).
             ↓ ⑤ 答（循环结束，因为这轮没有 tool_calls）
```

**关键：ReAct 跑了两轮，不是一条直线。**

| 轮次 | 模型调用 | 产出 |
|---|---|---|
| 第 1 轮 | 第 1 次 | `tool_calls` |
| 第 2 轮 | 第 2 次 | 最终回答（无 `tool_calls`） |

**循环的"转向点"：模型这次回复里有没有 `tool_calls`。**

**和实验 1-1 的联系：**

| 实验 1-1 的消融 | 拆掉了 ReAct 的哪一步 |
|---|---|
| `no_reasoning` | 拆掉 🧠 **想** |
| `no_tool_calls` | 拆掉 🔧 **做** |
| `no_tool_results` | 拆掉 👀 **看** |
| `no_history` | 拆掉**之前所有轮次** |

> **实验 1-1 是"逐个拆掉 ReAct 的零件"，实验 2-1 是"在真实服务上完整跑一遍"。**
> **一个做减法，一个做加法。**

### 3. streaming ✅

**代码分两层。**

**产出（`ollama_native.py`）：**

```python
stream_response = self._chat_with_think_fallback(..., stream=True)   # ① 声明要流式

for chunk in stream_response:                       # ② 一个个收
    thinking_chunk = chunk.get('message', {}).get('thinking', '')
    content_chunk  = chunk.get('message', {}).get('content', '')

    if thinking_chunk:
        collected_thinking.append(thinking_chunk)   # ③ 同时攒起来
        yield {"type": "thinking", "content": thinking_chunk}   # ④ 一块块吐出去
```

**消费（`main.py`）：**

```python
print(f"\033[90m{content}\033[0m", end="", flush=True)
         ↑ 灰色         ↑ 恢复色   ↑ 不换行  ↑ 立刻输出
```

**三个核心概念：**

| 概念 | 说明 |
|---|---|
| **chunk 是"增量"** | 装的是"新增的那几个字"，不是"到目前为止的全部"。客户端必须自己拼 |
| **`yield`（生成器）** | 可以返回**很多次**，每次返回后**暂停**，下次从暂停处继续（`return` 只能返回一次） |
| **`end=""` + `flush=True`** | 不换行 + 不缓冲。**流式必须这样，否则输出会碎或者攒着不显示** |

**流式是测 TTFT 的前提：**

```
非流式：你只能测"总耗时"
流式：  你能测"第一个 chunk 什么时候到" = TTFT
```

### 4. >100 tok/s observation ✅

**实测：277 tok/s**（书里记录 macOS 上是 106.7，我的机器是它的 2.6 倍）

#### 公式（`benchmark.py` 第 139~140 行）

```
tok/s = 输出 token 数 ÷ (总时长 − TTFT)
                          ↑ 注意是减掉 TTFT，不是总时长
```

**为什么要减掉 TTFT？因为生成分两个阶段：**

```
发请求 ──[① 预填充 prefill]──> 第一个 token ──[② 解码 decode]──> 最后一个 token
        读整个 prompt、建立            一个个生成
        KV Cache
        ↑ 这段时间 = TTFT              ↑ 这段才是"生成速度"
```

| 阶段 | 和什么有关 |
|---|---|
| **预填充** | 和 **prompt 长度**有关 |
| **解码** | 和 **输出长度**有关 |

**预填充是"一次性开销"，不排除掉的话，prompt 越长算出的 tok/s 越假。**

#### 我的 5 次实测

```
第 1 次: TTFT=3.562s, 解码=278.7 tok/s, 输出=256 tok
第 2 次: TTFT=0.058s, 解码=280.5 tok/s
第 3 次: TTFT=0.059s, 解码=275.8 tok/s
第 4 次: TTFT=0.059s, 解码=277.5 tok/s
第 5 次: TTFT=0.059s, 解码=272.4 tok/s
```

**关键对比：TTFT 差了 61 倍，但解码速度几乎一样。**

**→ 说明那 3.562 秒不是"推理慢"，而是"模型加载"（冷启动）。**
**如果是推理慢，tok/s 也会跟着掉。**

#### 100 这个门槛的意义

**人的阅读速度约 5~10 个词/秒（≈ 7~15 tok/s）。**
**100 tok/s 是它的 10 倍左右 —— 意味着模型写得比你读得快，这是"流畅交互"的门槛。**

**为什么对 Agent 重要：**

```
一个任务 = 3 轮模型调用，每轮输出约 100 token
@ 277 tok/s：≈ 1.1 秒
@ 20 tok/s ：= 15 秒      ← 只有 CPU 时

差 14 倍
```

### 5. matched cache-hit/miss TTFT ✅

**实测：命中 0.098s vs 未命中 0.345s，加速 3.51 倍**

#### `matched` 是什么意思

**"受控对比"：两组只允许一个变量不同。**

代码注释原文：

> 两组的提示词**长度基本一致**，因此差异主要来自前缀缓存是否命中。

#### 实验设计

```python
base_prompt = build_padded_system_prompt(args.prefix_tokens)   # 约 1024 token

# 预热一次（不计入统计，排除冷启动干扰）
stream_once(client, model, warm_msgs, ...)

for i in range(args.repeats):
    # 命中组：完全相同的前缀
    hit = stream_once(client, model, warm_msgs, ...)

    # 未命中组：在【开头】插入唯一字符串 → 缓存全废
    mutated = f"[req-{i}-{time.time_ns()}] " + base_prompt
    miss = stream_once(client, model, [{"role":"system","content":mutated}, user_msg], ...)
```

| 设计细节 | 为什么 |
|---|---|
| 两组共用 `base_prompt` | 保证长度一致 → 差异只来自缓存 |
| 先预热一次不计入 | 排除冷启动 |
| `time.time_ns()` | 纳秒时间戳，保证每次插入都不同 |
| **插在开头** | ⭐ 最狠的破坏方式 |

#### KV Cache 的原理

**书里的 4-token 例子：上下文 `[A, B, C, D]`，要生成 E。**

```
D 的 Query 与 A、B、C、D 的 Key 做点积 → 算匹配度
再按匹配度对 A、B、C、D 的 Value 加权求和
→ 得到 D 位置的输出表示 → 预测出 E
```

| | 计算量 |
|---|---|
| 没有 KV Cache | 每生成一个 token 都要重算整个前缀 → **累计 ∝ N²** |
| 有 KV Cache | 每个 token 的 K、V 只算一次，之后直接取用 → **累计 ∝ N** |

**⚠️ 书里澄清的常见误解：**

> KV Cache 省去的是**历史 token 的 K、V 投影重算**；
> **但每个新 token 的注意力计算仍要遍历全部缓存的 K、V，计算量随上下文长度线性增长**。

**所以是 N² → N，不是 N² → 常数。**

#### ⭐ 为什么改前缀会让缓存失效

> 大模型由**多层 Transformer 堆叠**，每层**独立生成自己的 K、V 缓存**，层与层**串联**。
> 第 k 个 token 变了 → 第 0 层第 k 位输出变了 → 第 1 层从第 k 位起输入变了 → 逐层扩散……
>
> **缓存只能保留到首个不同 token 之前。**

**插在第 0 位 → 从第 0 位起全部失效 → 最坏的破坏。**

> **这就是书里反复强调"系统提示词一旦定下来就不要改"的原因。**

#### 为什么这条对 Agent 最重要

**书里的原话：**

> 这对于需要**几十轮工具调用的 Agent 任务**来说是不可接受的。

```
Agent 的 messages 每轮都增长，但【前缀大部分不变】
  system 提示词  → 不变
  tools 定义     → 不变
  历史消息       → 不变（只追加）

缓存命中   → 只有新增的片段要重算
缓存不命中 → 整个前缀（几千 token）全要重算，【而且每一轮都重算】
```

#### 书里由此推出的三条「架构约束」

> **当 Prompt Cache 的经济效益足够显著时，缓存一致性会反过来主导系统的架构选择。**

| 约束 | 含义 |
|---|---|
| **① 提示词结构由缓存边界决定** | 动态元素（时间、用户偏好、模式）**必须放在缓存边界之后**。否则每个二值条件都会让缓存变体翻倍：3 个条件 = 2³ = 8 种缓存键 |
| **② 子 Agent 必须与父 Agent 字节级对齐** | 派生时提示词、工具定义、消息前缀必须**逐字节匹配** |
| **③ 工具结果的替换字符串首次出现就冻结** | 即使重启也要用**完全相同**的字符串，保证字节流一致 |

**书里的例子很生动：**

> 提示词的排列顺序**首先由缓存的经济性决定**，其次才是语义逻辑。

#### 顺带：KV Cache vs Prompt Cache

| | **KV Cache** | **Prompt Cache** |
|---|---|---|
| 是什么 | **模型内部机制** | **推理引擎的优化** |
| 作用层 | **单次请求内** | **跨请求** |

**书里提到：缓存读取的成本约为首次计算的十分之一（Anthropic / DeepSeek / GPT-5）。**

**——我在实验 1-1 的日志里见过它：`cached_prompt_tokens: 15360`，当时还不知道那是什么。**

### 6. parallel tools ✅

**任务：** `What is the weather in Tokyo and what time is it there right now?`

**结果：**

```
🔧 Tool Calls:
  → get_current_temperature: {'location': 'Tokyo, Japan'}
  → get_current_time: {'timezone': 'America/New_York'}      ← 一轮里要了两个

15:32:14,678 - Executing tool: get_current_temperature
15:32:14,678 - Executing tool: get_current_time      ← 同一个时间戳 = 并行执行
```

**✅ 一轮里同时请求多个工具，框架并行执行。**

**书里的判据：**

> 这两个工具的参数都能直接确定，所以框架**可以并行执行**。
> 如果后一个工具的参数必须来自前一个的结果，就只能**串行**。

**⚠️ 但它把东京的时区搞错了 —— 原因很值得学。**

**它的 thinking 原文：**

> The example in the tool uses **'America/New_York'**, so I'll use that.

**它照抄了工具描述里的第一个示例值。**

而工具描述里明明写着：

```python
description="Timezone name (e.g., 'America/New_York', 'Europe/London', 'Asia/Tokyo'). ..."
```

**`'Asia/Tokyo'` 就在里面，但在第三个位置。**

> **教训：放在最前面的示例，最容易被照抄。示例的顺序会影响模型行为。**

**而且上次跑同类任务时它正确用了 `Asia/Tokyo` —— 同一模型、同一描述，两次不同。**

### 7. raw token/thinking stream 🟡 部分完成

| 观测点 | 状态 |
|---|---|
| thinking 流 | ✅ 看到了（`🧠 Thinking:`） |
| **raw token 流** | 🟡 还差 —— 需要用 `run_experiment.py` 的 `/api/generate` + `raw=true` |

**为什么书里要用 `raw=true`：**

> 这个 runner 故意使用 Ollama 的 `/api/generate` 端点并设 `raw=true`。
> 这样 Qwen chat template 产出的**确切字符串**就在证据里可见，
> **包括角色标记和模型的 XML 工具调用协议**。

**要补这一项需要：** 装 `transformers` + 下载 Qwen tokenizer
（`huggingface.co` 不通，但 **`hf-mirror.com` 通**）。

**README 里提到的一个有趣现象（还没亲手验证）：**

> 书里说支持思维链的模型会先在 `<think>` 标签内思考，但实际跑起来 `content` 里根本看不到 `<think>`，
> 思考内容出现在单独的 `thinking` 字段里。
>
> **两种说法都没错 —— `<think>` 是模型原始 token 流里的标签，
> Ollama 在把响应交给客户端之前就已经把它解析掉了。**

---

## 四、真实运行中的发现（书上没有的）

### 发现 1：模型从"错误信息"里挑数据用 ⚠️

**第一次跑时间工具（缺 tzdata）时，工具返回的是错误：**

```json
{"error": "'No time zone found with key Asia/Tokyo'",
 "fallback_error": "...",
 "timezone": "Asia/Tokyo",
 "timestamp": "2026-09-26T17:28:40.519295"}
```

**模型的回答：**

> The current time in Tokyo is **17:28** (as per the tool's response).

**它把 UTC 时间当成了东京时间 —— 差了 9 小时。**

> **教训：工具失败时，返回结构应该和正常返回截然不同。
> 别让"错误对象"里混着"看起来能当数据用"的字段。**

### 发现 2：工具诚实标注了"模拟数据"，模型却吃掉了警告 🔴

**天气工具连不上 API，降级到模拟数据，而且诚实标注了：**

```json
{"location": "Tokyo, Japan", "temperature": 25.5, "unit": "°C",
 "conditions": "sunny",
 "note": "Simulated data (API unavailable)"}
```

**但模型的最终回答：**

> The current weather in Tokyo is **25.5°C** with **sunny** conditions.

**一个字都没提 `note`。**

> **工具诚实 ≠ 用户知情。中间隔着一个模型，而模型可能把警告吃掉。**
> **这就是为什么"可依据性检查"必须做在外部。**

### 发现 3：`success: true` 掩盖了"什么都没有"

**代码解释器任务：**

```
→ code_interpreter: {'code': '987654321 * 123456789'}
  ✓ {"result": null, "output": null, "stderr": null, "success": true}
```

**根因：模型写的是表达式（`987654321 * 123456789`），不是 `print`。
表达式求值了但没有输出 → `output_buffer` 是空的。**

**—— 这和我在自己写的 `my_agent.py` 里踩的坑一模一样（当时删掉了 `print`）。**

**而 `success: true` 的原因只是"没抛异常" —— "没报错"被当成了"成功"。**

**模型面对这种情况的反应（thinking 原文）：**

> the response was null. Hmm, maybe the code didn't execute properly...
> **But the success field is true, so maybe the code executed successfully**...
> **I need to clarify that the calculation was performed and that the result is as expected.**

**它准备告诉用户"计算已完成"—— 但根本没给出数字。**

**根因在工具描述：**

```python
description="Execute Python code for calculations...",
"code": {"description": "Python code to execute. Use Python operators:
          ** for exponentiation (2 ** 10), not ^ ..."}
```

**它说了"`**` 是幂运算"，但没说"必须 print 才能看到结果"。**

**修法（两处）：**

```python
# ① 改描述（最便宜）
"description": "... IMPORTANT: to see a result you MUST either print(...) it,
                or assign it to a variable named `result`.
                A bare expression like `2+2` produces no output."

# ② 改实现（更彻底）
if result is None and not printed_output and not error_output:
    return {"success": False,
            "error": "代码执行了，但没有产生任何输出。请用 print(...) 或赋值给 result。"}
```

### 发现 4：小模型的稳定短板 —— AM/PM

**两次运行，两次都错：**

| 工具返回 | 模型的回答 |
|---|---|
| `02:34:56` | "The time is **2:34 PM**" ❌（是凌晨） |
| `03:32:14` | "The time is **3:32 PM**" ❌（是凌晨） |

> **0.6B 的模型"能调用工具"，但"做基本推理"会出错。**
> **这就是为什么生产要用大模型 —— 不是"不会用工具"，是"细节会错"。**

### 发现 5：这台机器的最优并发度是 2

```
[batching] 并发度对聚合吞吐的影响
    并发 |    聚合tok/s |     单请求tok/s |   平均TTFT(s) |    墙钟(s)
  -----+------------+--------------+-------------+---------
     1 |       83.6 |         83.6 |       2.023 |     3.06
     2 |      239.7 |        119.9 |       0.580 |     2.14   ← 最优
     4 |      239.8 |         59.9 |       1.637 |     4.27
     8 |      234.4 |         29.3 |       3.724 |     8.60
```

**并发 1→2：聚合吞吐涨了 2.9 倍**（服务端有批处理能力）
**并发 2→4→8：聚合吞吐不动了（饱和），但单请求吞吐持续下降**

> **超过最优并发度之后，加负载只会让所有人的体验都变差。**

---

## 五、结论

> **实验 2-1 让我第一次从"服务提供方"的角度看 Agent。**
>
> 前面的实验都在客户端（我写循环、我调工具）；
> 这个实验里，**服务是我自己跑的**，所以我第一次能看到：
> - token 是怎么一块块流出来的
> - 首字延迟里有多少是"加载模型"
> - 缓存命中能省掉多少时间
> - 服务能承受多少并发
>
> **同一个 ReAct 循环，在客户端看是"日志"，在服务端看是"性能指标"。**

---

## 六、踩的坑汇总

| # | 坑 | 教训 |
|---|---|---|
| 1 | 缺 `tzdata`，时区工具报错 | Windows 不自带 IANA 时区库 |
| 2 | 工具报错时返回的 `timestamp` 被模型当数据用 | **错误对象别混入"看起来像数据"的字段** |
| 3 | 工具诚实标注"模拟数据"，模型吃掉了警告 | **不能指望模型转述警告，检查要做在外部** |
| 4 | 代码解释器 `success: true` 但 `result: null` | **"没报错" ≠ "有结果"**；工具描述要写清"必须 print" |
| 5 | 模型照抄工具描述里的第一个示例 | **示例的顺序会影响模型行为** |
| 6 | 天气 API 被代理拦住（`127.0.0.1:9`） | 环境代理问题，工具降级处理得不错 |

---

## 七、下一步

- **补最后一项**：装 `transformers` + 走 `hf-mirror.com` 下 tokenizer，跑官方 `run_experiment.py`
- **进实验 2-2**：注意力机制可视化
  （书里说"点积的直观含义见实验 2-2"—— 和这次学的 K、V 直接相关）
