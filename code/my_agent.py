import os
from dotenv import load_dotenv
from openai import OpenAI
import json
load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

def calculate(expression):
    result = eval(expression)
    return str(result)
tools=[
    {
        "type":"function",
        "function":{
            "name":"calculate",
            "description":"计算一个数学表达式，支持 + - * / 和括号",
            "parameters":{
                "type":"object",
                "properties":{
                    "expression":{
                        "type":"string",
                        "description":"要计算的数学表达式，例如 (125+375)*8"
                    },
                },
               "required":["expression"],
            },
        },
    },
]
messages = [
    {
       "role":"user","content": "帮我计算555*257等于多少"
    },
 ]
for turn in range(1,6):
    print(f"---第{turn} 轮---")

    response=client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=messages,
        tools=tools,
    )
    message=response.choices[0].message
    messages.append(message)

    if not message.tool_calls:
        print("最终答案", message.content)
        break
    for call in message.tool_calls:
        args=json.loads(call.function.arguments)
        result=calculate(args["expression"])
        print(f"  工具调用{result}")
        messages.append({
            "role":"tool",
            "tool_call_id":call.id,
            "content":""
        })

