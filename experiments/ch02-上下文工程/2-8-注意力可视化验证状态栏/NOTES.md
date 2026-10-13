# 实验 2-8 ★★ 通过注意力可视化验证 Agent 状态栏的效果

> 来源：`book/chapter2.md:879`
> 代码目录：`ai-agent-book/chapter2/attention_visualization/`
> ⚠️ **运行目录用的是历史编号**：`runs/exp2-7-qwen3-0.6b-20260730-v1/v2`
> **状态：未跑。** 下面整理自书里的实测记录 + `status_bar_protocol.json`。

---

## 一、场景

一个客服 Agent 在处理退款。它**已经给 Xfinity 打了 3 次电话**，中间还穿插了网络搜索。

规则是：**每个商家最多打 3 次。**

现在用户又追问了一句：

> "Can you call Xfinity one more time to chase the refund?"

**问题就在这**：0.6B 这么小的模型，能数清自己已经打了 3 次吗？

---

## 二、两组对照

| | **对照组 A（无状态栏）** | **对照组 B（有状态栏）** |
|---|---|---|
| 上下文 | 完整轨迹，**没有**聚合状态信息 | **同一份轨迹**，末尾多一段 |
| 内容 | 3 次通话记录散落在各处 | 末尾追加： |

对照组 B 追加的那段（协议里写死的，**不是模型生成的**）：

```xml
<agent_status>
Current State:
- Tool call summary: 'phone_call' has been invoked 3 times (Xfinity: 3 times)
- Constraint check: Maximum calls to Xfinity reached (3/3)
</agent_status>
```

**除了这一段，两组的消息前缀完全一致**（协议里的 gate `same_base_trajectory` 就是验这个）。

---

## 三、要看的三件事

1. **行为**：会不会违反约束打第 4 次？
2. **注意力**：响应 token 的注意力落在哪个区域？（三次通话记录 / 搜索结果干扰 / 状态栏 / 最新提问）
3. **思考过程**：思考 token 里有没有"数数"的痕迹？

书里的预期：

> **A 组**：热力图注意力高度分散，在三次电话调用的区域形成明显"聚焦点"，**思考 token 体现出数数和统计的过程** —— 模型在从原始信息里做归纳。
>
> **B 组**：注意力高度集中在状态栏上，思考过程**直接使用已提炼好的信息**，不再从原始数据里统计。

---

## 四、实测结果（书里的记录）

> 每组三个种子（27 / 41 / 73），各生成一次。

| | 对照组 A（无状态栏） | 对照组 B（有状态栏） |
|---|---|---|
| **拒绝打第 4 次** | **2 / 3** | **3 / 3** |

书里的原话：

> **对于 Qwen3-0.6B 这样小的模型，对照组 A 经常违反约束继续拨打，而对照组 B 则能稳定地遵从约束。**

**这个结果的意义**：给模型一条**提前算好的状态栏**后，**小模型的准确率可以接近前沿大模型**。

而且书里还提到一个附加收益：**状态栏大幅降低思考成本**。不带状态栏时，每次查询的思考量随上下文变长而持续增长；带上之后**基本恒定** —— 思考 token 量、延迟、花费都降约一个数量级。

---

## 五、协议里几个值得学的设计

载入 `status_bar_protocol.json`：

```json
{
  "matched_trials": 3,
  "generation": { "max_new_tokens": 128, "temperature": 0.6, "top_p": 0.9,
                  "seeds": [27, 41, 73] },
  "attention": { "layer": -1, "heads": "mean",
                 "query_rows": "all generated response tokens" },
  "acceptance_gates": [
    "both arms use the same local model revision and base trajectory",
    "the status arm contains the exact Xfinity 3/3 state block at the trajectory end",
    "the control contains no agent_status block",
    "all generated texts are retained with real token IDs",
    "the last-layer attention tensor comes from a real eager-attention forward pass",
    "response attention mass is reported for each preregistered context region",
    "both heatmaps are rendered from the recorded matrices",
    "behavioral outcomes are reported even if they do not favor the hypothesis"
  ]
}
```

**四条值得抄的做法：**

| 设计 | 为什么 |
|---|---|
| **三个固定种子** | 单次生成可能是运气，三次才能看出倾向 |
| **注意力只取最后一层、头平均、覆盖全部生成 token** | 事先定好口径，不能事后挑好看的那层 |
| **区域在协议里预注册** | "看哪里"是事先定的，不是看到图之后再圈 |
| **最后一条 gate** | 结果不好看也要照报 —— 这就是**预注册**的意义 |

还有一条隐含的严谨：**没有用任何"响应条件"来筛选样本**（`no response-conditioned gate was used`）—— 不挑好看的。

---

## 六、这对我们意味着什么

1. **模型不擅长统计，但它擅长"看到结果就用"** —— 把 `3/3` 摆在它面前，它就不数了
2. **状态栏让 0.6B 表现接近大模型** —— 这是"上下文质量决定能力上限"最直接的证据
3. **状态栏还省思考** —— 不用再花 token 去归纳，思考量变恒定
4. **状态栏必须由代码维护** —— 协议里那段 `3/3` 是写死的，不是模型数的

> 接 [2-9 笔记](2-9-Agent状态栏技术/NOTES.md)：这个实验证明"状态栏有用"，2-9 讲"有哪些好用的状态栏技术"。

---

## 七、想跑的话

前置条件：`torch`（系统 Python311 已有）+ `transformers`（缺）+ Qwen3-0.6B 权重（缺）。

```powershell
cd C:\Users\Redmi\Documents\Codex\2026-09-22\ppt-ppt\outputs\ai-agent-book\chapter2\attention_visualization

# --output 指向的目录不能已存在（代码里是 exist_ok=False）
..\..\.venv\Scripts\python.exe run_status_bar_experiment.py --output "runs\exp2-8-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

脚本用的是 `local_files_only=True`，**不会自动下载模型**，得先手动下好。
