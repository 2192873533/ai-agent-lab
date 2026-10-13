# 实验 2-6 ★★ 使用 Agent Skills 从论文生成演示文稿

> 来源：`book/chapter2.md:828`
> 代码目录：`ai-agent-book/chapter2/agent-skills-ppt/`
> **状态：离线实跑通过；真模型路线未跑**（书作者用 Kimi Code 跑通的那次记录在 `runs/` 里）。

---

## 一、这个实验想证明什么

> **Agent 能通过动态加载专业领域 Skill，完成一件它原本不知道怎么干的事。**

具体任务：拿一篇学术论文 PDF（Attention Is All You Need），生成一份 10-15 页的演示文稿。

关键词是"**动态加载**"：Agent 启动时**并不知道做 PPT 的流程**，只在薄目录里看到一句"有个叫 pptx 的 Skill 能干这个"，然后自己决定去加载。

---

## 二、三层渐进式披露（实验的核心）

| 层 | 内容 | 什么时候进上下文 | 实测大小 |
|---|---|---|---|
| **第一层 · 元数据** | 每个 Skill 的 `name` + `description`（薄目录） | **每轮常驻** | **506 字符** |
| **第二层 · 核心流程** | 完整的 `SKILL.md` | Agent 判断需要时加载 | **1242 字符** |
| **第三层 · 细则** | `reference.md`、`scripts/` | 真去读的时候 | **1163 字符** |

**省在哪里**：常驻的只有 506 字符的目录，而不是 2405 字符的全文 —— 省 79%。

**注意一个容易误解的点**：目录不是"一次性"的，它**每轮都要进请求**，所以它是**持续成本**；而正文只在你真的用它的时候才进来。所以三层设计的目标是"**让昂贵的东西只在必要时付钱**"。

---

## 三、两条触发路径（都写进协议了）

| 路径 | 过程 | 代价 |
|---|---|---|
| **A · 模型自己选** | 读薄目录 → 判断命中 → 发起一次 Skill 工具调用 → Harness 加载正文 | **多一次 ReAct 往返** |
| **B · 用户打 `/pptx`** | 客户端在**本地**拦截并展开，正文直接注入 | 少一次往返，零误判 |

**而离线模式是路径 B 的极端形式** —— 连用户都不用打命令，脚本直接点名：

```python
dispatch(catalog, "read_skill", {"name": "pptx"}, out_path)   # pptx 写死
```

**所以离线模式演示不了"路由判断"** —— 而路由恰恰是 Agent Skills 最核心、最需要验证的一环。这是书里说它"不能算完成实验 2-6"的原因。

---

## 四、真模型的验收结果

书里 `agent-skills-ppt/runs/` 下有 5 次运行记录，其中：

| 运行 | 模型 | 结果 |
|---|---|---|
| `exp2-6-claude-pptx-20260730-v1~v4` | Claude Code | ❌ **全部 401 失败**（Anthropic 凭证问题），作为 fail-closed 证据保留 |
| `exp2-6-kimi-pptx-20260731-v1` | Kimi Code（`kimi-code/k3`） | ✅ **15 道 gates 全过** |

Kimi 那次的产出：

- **13 页**的 pptx（605 KB）
- 从论文 PDF 里**裁出 4 张图**，并写了带页码和标注的 `source_visuals/manifest.json`
- 走了官方脚本 `html2pptx.js` 和 `thumbnail.py`
- 生成了整本缩略图 `full-deck-thumbnail.jpg` 并**看过了**（`thumbnail_visually_inspected: true`）

**关键收获**：书里说"运行时可以替换"（runtime-agnostic）—— 只要有「元数据目录 + 按需加载」的机制就行。**Kimi 跑通了，Claude 没跑通，但这不影响实验结论。**

---

## 五、我们自己动手踩的坑 ⚠️

离线模式练手时，我照着"新建一个 markdown Skill"来做，结果**连着两次没生效**：

| 建成了什么样 | 为什么不行 |
|---|---|
| `agent-skills-ppt/markdown/SKILL.md` | 建在项目根目录，**在 `skills/` 文件夹外面** |
| `skills/pptx/markdown/SKILL.md` | 套在 `pptx` 里了，**多了一层** |
| 而且文件是 **0 字节** | 内容根本没保存 |

**根因在扫描规则**（`demo.py:75`）：

```python
for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
```

`*/SKILL.md` 的意思是：**在 `skills/` 底下，直接找「某个文件夹/SKILL.md」，只往下探一层**，不递归。

```
skills/                        ← 扫描起点
├─ pptx/SKILL.md               ✅ 第一层，扫得到
└─ markdown/SKILL.md           ✅ 第一层，扫得到
   └─ pptx/markdown/SKILL.md   ❌ 第二层，扫不到
```

**这个坑的普适教训**：**"文件在磁盘上"≠"模型知道它存在"。** 中间隔着 Harness 的一道筛选。

---

## 六、两个配套的小实验（证明"机制真的在跑"）

### 实验 A：改 `papers/sample_outline.json` 的 `title`

改完重跑，终端「校验」那段的第 1 页标题跟着变 → 证明**数据真的被读了**，不是写死在代码里。

### 实验 B：改 `skills/pptx/SKILL.md` 的长度

重跑后日志里这行的数字会变：

```
>>> [渐进式披露·第二层] Agent 调用 read_skill('pptx')，加载完整 SKILL.md（1242 字符）
```

→ 证明**文件真的被加载了**。

---

## 七、命令备忘

```powershell
cd C:\Users\Redmi\Documents\Codex\2026-09-22\ppt-ppt\outputs\ai-agent-book\chapter2\agent-skills-ppt

# 离线模式（不需要 API key）
..\..\.venv\Scripts\python.exe demo.py --offline

# 验证扫描器能扫到哪些 skill
..\..\.venv\Scripts\python.exe -c "import pathlib; [print(' ', p) for p in sorted(pathlib.Path('skills').glob('*/SKILL.md'))]"
```

---

## 八、结论

1. **渐进式披露的本质是"让昂贵的东西只在必要时付钱"** —— 目录常驻、正文按需
2. **`description` 是路由条件，不是功能介绍** —— 写歪了，正文再精彩也没有出场机会
3. **离线模式只能演示机制，演示不了路由** —— 而路由才是这类系统的核心风险点
4. **Skill 是不是被加载，取决于 Harness 扫不扫得到** —— 文件位置和目录层级是硬约束
