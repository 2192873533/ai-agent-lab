# 实验 1-1 · 上下文的关键作用

| | |
|---|---|
| 难度 | ★★ |
| 书源码 | `chapter1/context/` |
| 状态 | ✅ 已完成 |
| 日期 | 2026-09-22 |

## 要验证什么

同一个任务、同一个模型，**每次故意去掉一类上下文**，观察 Agent 怎么退化。

去掉的四类：历史消息、思考过程、工具定义、工具结果。

## 跑了什么

```powershell
cd chapter1\context
python run_experiment_1_1.py --provider deepseek    # 书里的验收脚本
python main.py --mode ablation --provider deepseek  # 五种模式对照
```

## 观察到什么

| 组 | 轮数 | 工具调用 | 结果 |
|---|---:|---:|---|
| full | 3 | 7 | ✅ 正常收敛 |
| no_history | **10（撞满）** | **33** | ❌ 反复重做，没得出答案 |
| no_reasoning | 4 | 7 | ✅ **测不出退化**（书里也承认） |
| no_tool_calls | 1 | 0 | 没报数字，说明拿不到工具 |
| no_tool_results | 7 | 14 | ⚠️ 报出 **12 个无依据的数字** |

`no_tool_results` 组的原文：

> Converted to USD (**using GBP 1.27, JPY 0.0067, EUR 1.08, SGD 0.75**): ...
> Total global expenses: $12,000,000

括号里那四个汇率，它一个都没拿到过——全是自己补的。而这一组的 `completed` 字段是 `True`。

## 结论

> **`completed = True` 不代表任务做对了。**
> 上下文丢了一块，Agent 不会报错，它会**自信地编**。

而且这一组**不稳定**：同一道题跑两次，一次 7 轮 14 次工具调用，一次撞满 5 轮没答案。
书里对此的说明是"倾向而非定律"。

## 踩的坑

| 坑 | 教训 |
|---|---|
| `run_experiment_1_1.py` 不读 `.env` 的 `LLM_PROVIDER`，默认是 `kimi` | 跑这个脚本**必须**显式带 `--provider` |
| 用 ▶️ 按钮跑脚本 = 不带参数 = 用默认 provider | 要传参数的脚本，用 `Ctrl+Shift+B` 或终端 |
| `main.py --mode single` 默认覆盖 `task_result_full.json` | 加 `--output my_result.json` |
| 上游 bug：`agent.py` 用 `openai.APITimeoutError` 却没 `import openai`，任何 API 报错都被 `NameError` 盖住 | 已在本地补上，值得给上游开 issue |

## 最小复现

这段实验的核心，用 60 行就能复现。见 `code/my_agent.py`：

把 `"content": result` 改成 `"content": ""`，就复现了 `no_tool_results`。
