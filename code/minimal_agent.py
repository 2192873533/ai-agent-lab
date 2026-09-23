"""最小可用的 Agent —— 核心逻辑只有 15 行。

对照 agent.py（900+ 行）看你会明白：
  - 真正的"Agent"就是 run() 里那个 for 循环
  - 剩下的全是工程化：多厂商适配、5 种上下文模式、日志、统计、可视化

运行：
    python minimal_agent.py
    # 复现实验 1-1 的「移除工具结果」那一组：
    $env:HIDE_TOOL_RESULTS="1"; python minimal_agent.py
"""

import json
import os
import re
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

# ★ 实验 1-1 的「移除工具结果」消融开关 ★
HIDE_TOOL_RESULTS = os.getenv("HIDE_TOOL_RESULTS") == "1"


# ---------------------------------------------------------------- ① 工具实现
def calculate(expression: str) -> str:
    """工具背后真正干活的代码。"""
    allowed = set("0123456789+-*/(). ")
    if not set(expression) <= allowed:
        return "错误：表达式含非法字符"
    try:
        return str(eval(expression))
    except Exception as exc:  # noqa: BLE001
        return f"错误：{exc}"


# ---------------------------------------------------- ② 工具说明书（发给模型）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算一个数学表达式，支持 + - * / 和括号",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "要计算的表达式，例如 (125+375)*8",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]

# ------------------------------------------------------------ ③ 系统提示词
SYSTEM_PROMPT = """你是一个会用工具的助手。

需要计算时必须调用 calculate 工具，不要自己心算。
如果工具没有返回结果，不要自己估算，直接说明拿不到。
拿到结果后，用 "FINAL ANSWER:" 开头给出最终答案。"""


# ------------------------------------------------------------ ④ 主循环（心脏）
def run(task: str, max_turns: int = 8) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    seen_by_model = []  # 模型真正收到过的内容（工具结果被清空时，这里就是空的）

    for turn in range(1, max_turns + 1):
        print(f"--- 第 {turn} 轮 ---")

        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        messages.append(message)

        if not message.tool_calls:
            return report(message.content, task, seen_by_model)

        for call in message.tool_calls:
            args = json.loads(call.function.arguments)
            print(f"  调用工具 {call.function.name}({args})")
            result = calculate(**args)
            print(f"  工具返回 {result}")

            # 消融开关就应用在这一行
            content = "" if HIDE_TOOL_RESULTS else result
            seen_by_model.append(content)
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": content}
            )

    return "（撞到轮数上限，模型始终没说出 FINAL ANSWER）"


# ------------------------------------- ⑤ 可依据性检查（实验 1-1 的真正解药）
def report(answer: str, task: str, seen_by_model: list) -> str:
    """返回答案，并顺手检查：答案里的数字，模型真的见到过吗？

    这就是 grounding.py 在 1000 行项目里做的事的极简版：
    不关心模型怎么想，只拿答案里的数字去比对它收到过的观测。
    """

    def numbers(text: str) -> set:
        # 只看 4 位以上的数字，免得把"第1轮""2次"这种当成编造
        return set(re.findall(r"\d{4,}", text.replace(",", "")))

    observations = task + " " + " ".join(seen_by_model)
    unsupported = sorted(numbers(answer) - numbers(observations))

    print()
    if unsupported:
        print(f"⚠️  可依据性检查：这些数字模型从未收到过 → {unsupported}")
    else:
        print("✅ 可依据性检查：答案里的数字都能在观测里找到")
    return answer

if __name__ == "__main__":
    if HIDE_TOOL_RESULTS:
        print(">>> 实验 1-1 消融：工具结果已被清空 <<<\n")

    user_task = " ".join(sys.argv[1:]) or "请计算 987654321 * 123456789"
    print("任务：", user_task, "\n")
    print("最终答案：", run(user_task))
