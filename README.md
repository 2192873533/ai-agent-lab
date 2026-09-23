# AI Agent 实验记录

跟着《深入理解 AI Agent：设计原理与工程实践》（李博杰 著）做实验的过程记录。

这个仓库只放**我自己的笔记和代码**，不放书的源码。
书源码在本地：`outputs/ai-agent-book/`

---

## 目录结构

```
ai-agent-lab/
├── README.md            ← 你在这里
├── PROGRESS.md          ← 全书 109 个实验清单 + 进度勾选
├── ROADMAP.md           ← 两个月学习路线
├── commit.ps1           ← 一键提交+推送（自动重试）
├── code/                ← 我自己写的代码
├── notes/               ← 跨实验的通用知识（Python 基础、Agent 概念…）
└── experiments/         ← 每个实验的笔记
    └── ch01-AI-Agent入门/
        ├── 1-1-上下文的关键作用/NOTES.md
        └── 1-2-Kimi原生Agent能力/NOTES.md
```

### notes/ 里有什么

| 文件 | 内容 |
|---|---|
| [01-python基础.md](notes/01-python基础.md) | 点链、append、dict、JSON、函数、环境变量 |
| [02-agent核心概念.md](notes/02-agent核心概念.md) | 消息结构、工具本质、ReAct 循环、可依据性 |
| [03-工程踩坑.md](notes/03-工程踩坑.md) | 10 个坑 + "能演示 vs 能上生产"的差异 |
| [04-术语速查.md](notes/04-术语速查.md) | 中英对照 + 常见报错 + 模型差异 |

---

## 环境怎么起

书源码用的是仓库根的共享虚拟环境：

```powershell
cd outputs\ai-agent-book
code .          # 用 VS Code 打开
```

VS Code 里按 `` Ctrl+` `` 开终端，会自动激活 `.venv`（已配好）。

`.env` 里的 API Key 配置在 `chapter1/context/.env`，目前已配 DeepSeek。

### 换个实验目录时

每个实验目录的依赖不一样，进到目录后看它的 `requirements.txt`：

```powershell
..\..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 怎么写笔记

每个实验一个 `NOTES.md`，用同一个模板：

| 段落 | 写什么 |
|---|---|
| **要验证什么** | 用自己的话写一遍，别抄书 |
| **跑了什么命令** | 方便复现 |
| **观察到什么** | 贴关键输出，不要全贴 |
| **结论** | 一句话说不清楚就是还没想明白 |
| **踩的坑** | **最重要的一段**，面试就问这个 |

> 只记"跑通了"没有价值。**记"哪里错了、为什么错、怎么发现的"才有价值。**

---

## 进度

见 [PROGRESS.md](PROGRESS.md)。做完一个把 `[ ]` 改成 `[x]`。

---

## 提交习惯

每做完一个实验提交一次。**用 `commit.ps1`，它会自动重试推送**（国内网络到 github.com 不稳定）：

```powershell
.\commit.ps1 "实验 1-2：完成联网搜索 Agent，发现模型会自己决定搜索轮数"
```

**提交历史本身就是学习轨迹**——两个月后回看，能看出自己是怎么长起来的。

如果脚本执行被拦，先跑一次：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
