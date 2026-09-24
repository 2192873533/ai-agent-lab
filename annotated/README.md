# 带注释的源码

这里放**从书里抄出来的关键代码 + 逐行中文注释**。

为什么不直接在书仓库里加注释：书仓库是 git 克隆来的，改了会污染 `git status`，
以后 `git pull` 还会冲突。**抄一份出来注释，是更干净的做法。**

| 文件 | 对应源码 | 讲什么 |
|---|---|---|
| `01-execute-formula.py` | `chapter1/web-search-agent/agent.py` 的 `_execute_formula` | HTTP 请求、字典构造、异常处理 |
| `02-search-and-answer.py` | 同文件的 `search_and_answer`（待补） | ReAct 循环全文 |

> **推荐用法**：先自己读原版，读不懂的再来看注释；不要直接背注释。
