"""
带注释版：Kimi Formula 工具的执行函数

原文件：chapter1/web-search-agent/agent.py 第 232~297 行
作用：把模型的"工具调用请求"真正发出去，拿回搜索结果

这份代码干什么：
    模型说"帮我搜 XXX" → 这个函数发一个 HTTP 请求给 Moonshot → 拿回搜索结果

阅读顺序：从函数签名往下读，每行注释在代码下面。
"""


def _execute_formula(self, name: str, raw_arguments: str) -> str:
    # def          定义函数
    # _execute_formula  函数名（下划线开头 = 内部使用，不对外）
    # self         就是这个对象自己（能不能用，取决于这个函数是不是写在 class 里）
    # name: str    参数 1，名叫 name，类型标注是 str（Python 的标注只是给人看的，不强制）
    # raw_arguments: str   参数 2，模型给的工具参数，是【字符串】
    # -> str       返回值类型标注：返回一个字符串

    """Execute one Kimi Formula Fiber exactly as the model requested."""
    # 上面这行是"文档字符串"，写在函数第一行，用来说明这个函数干什么
    # 它不参与运行，但 VS Code 悬停时会显示，help() 也会显示
    # 注意一个细节：exactly as the model requested（严格按模型要求执行）
    #   —— 说明这里【不做参数加工】，模型给什么就传什么。为什么？见下面第 241 行的注释

    if self.using_openrouter:
        raise RuntimeError("Kimi Formula tools are unavailable on OpenRouter")
    # if 条件:                       如果条件成立
    # self.using_openrouter          取 self 对象的 using_openrouter 字段（布尔值）
    # raise RuntimeError(...)        主动抛出一个错误，程序就此中断
    # 这一句的作用：如果当前走的是 OpenRouter 兜底通道，就直接报错退出
    # 为什么？因为 web_search 是 Moonshot 独有的服务，OpenRouter 上没有
    # 宁可明确报错，也不要静默返回错误结果

    url = (
        f"{self.base_url.rstrip('/')}/formulas/"
        f"{self.formula_uri}/fibers"
    )
    # 这一整句的作用：拼出一个完整的 URL 字符串
    #
    # url = ...            给 url 变量赋值
    # 外面那层 ()          只是为了能换行写。括号没闭合时 Python 允许换行，
    #                      否则这几行的字符串必须写在一行里
    # f"..."               f-string，花括号 {} 里的东西会被替换成实际的值
    #
    # 拆开看：
    #   {self.base_url.rstrip('/')}   取 base_url，再用 .rstrip('/') 去掉末尾的 '/'
    #   /formulas/                    固定文字，原样保留
    #   {self.formula_uri}            取 formula_uri 的值（这里应该是 "web_search"）
    #   /fibers                       固定文字
    #
    # 为什么要 rstrip('/')？因为下面要拼的 "/formulas/" 是以 / 开头的。
    # 如果 base_url 末尾也带 /，拼出来就会有两个斜杠 "//"，URL 就错了。
    # 这是防 URL 拼错的标准写法。
    #
    # 假设 self.base_url = "https://api.moonshot.cn/v1"
    #     self.formula_uri = "web_search"
    # 拼出来就是：
    #     https://api.moonshot.cn/v1/formulas/web_search/fibers

    body = {"name": name, "arguments": raw_arguments}
    # 作用：组装要发送的请求体（一个字典）
    #
    # { }= 字典字面量（大括号在 Python 里有两种含义：这里是"字典"，在 f-string 里是"占位符"）
    #
    # "name": name
    #   ↑      ↑
    #  键名    变量的值
    # 左边是固定的字符串（键名），右边是从变量取值。
    # 看起来像重复，其实不是——这是 Python 里最常见的写法。
    #
    # C 里要这么写：
    #     sprintf(body, "{\"name\": \"%s\", \"arguments\": \"%s\"}", name, raw_arguments);
    # Python 直接把这段 sprintf 换成了字面量，不用手写转义符、不用记 %s。
    #
    # 注意 arguments 传的是 raw_arguments（原始字符串），不是解析后的字典。
    # 因为这套公式协议要求传原文——这是这个工具的特殊要求，别的工具未必如此。

    started = time.monotonic()
    # 记一个开始时间，用来后面算"这次请求花了多久"
    # time.monotonic() 是"单调时钟"，只能往前不能往后（不受改系统时间影响），
    # 适合用来算时间差。不要用 time.time() 算耗时，因为系统时间可能被调整。

    response = None
    # 先给 response 赋一个空值（None）。
    # 为什么要提前赋值？因为下面 except 里要用到它。
    # 如果请求在发出去之前就失败了（比如网络断了），response 仍然是 None，
    # except 里就能通过"是不是 None"判断"请求到底发出去没有"。

    try:
        # try 开始：下面这些代码可能会出错，出错跳到 except

        response = requests.post(
            url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=body,
            timeout=self._request_timeout,
        )
        # 发一个 HTTP POST 请求
        #
        # requests.post(地址, 参数...)
        #   url                              要请求的地址（上面拼好的）
        #   headers={"Authorization": ...}   请求头，里面放身份凭证
        #       f"Bearer {self._api_key}"    → 拼成 "Bearer sk-xxxx"
        #       Bearer 是一种标准的认证格式，意思是"持有此令牌的人"
        #   json=body                        把上面那个字典自动转成 JSON 发出去
        #       注意参数名叫 json，不是 data。用 data= 发的是表单格式，用 json= 发的才是 JSON
        #   timeout=self._request_timeout    超时时间（秒）。不设的话请求可能永远卡住
        #
        # 返回值（服务器的响应）存进 response

        payload = response.json()
        # 把服务器返回的内容解析成 Python 字典
        # 服务器返回的是 JSON 字符串，response.json() 把它变成字典
        # 注意：是 .json() 带括号（调方法），不是 .json 属性

        response.raise_for_status()
        # 检查 HTTP 状态码。如果是 4xx / 5xx（比如 401 无权限、500 服务器错误），
        # 就直接抛异常，跳到 except。
        # 为什么要显式检查？因为 requests 默认不会因为状态码是 404 就报错，
        # 它会安静地把错误响应给你。必须手动 raise_for_status() 才会报错。

        if payload.get("status") != "succeeded":
            raise RuntimeError(
                f"Formula Fiber did not succeed: {payload.get('status')!r}"
            )
        # payload.get("status")   从字典里取 status 字段
        #   为什么用 .get() 而不是 payload["status"]？
        #   .get() 取不到时返回 None，不会报错；用 [] 取不到会 KeyError。
        #   对外部数据用 .get() 更安全，因为你不确定对方一定给了这个字段。
        #
        # != "succeeded"   不等于 "succeeded"
        #   注意：HTTP 200 只代表"请求成功送达"，不代表"任务执行成功"。
        #   业务层还有自己的状态，要单独检查。
        #   这是非常重要的区分：传输层成功 ≠ 业务层成功。
        #
        # {payload.get('status')!r}
        #   !r 的意思是"用 repr 格式显示"，好处是字符串会带引号，
        #   这样 "error" 和 空字符串 在报错信息里能分得清。

        context = payload.get("context") or {}
        # 从 payload 里取 context 字段
        # 后面的 " or {}" 是兜底：如果取到的是 None 或空字典，就换成空字典 {}
        # 为什么要兜底？因为下一行要 context.get(...)，如果 context 是 None 会报错。
        # 这是 Python 里很常见的"防御性写法"。

        result = context.get("output")
        # 从 context 里取 output 字段，这就是搜索结果

        if result in (None, ""):
            result = context.get("encrypted_output")
        # in (None, "")   判断 result 是不是"空"（None 或者空字符串）
        # 如果正常结果是空的，就退而求其次用 encrypted_output（加密输出）字段
        # 这是对服务端"有时不返回明文"的兼容处理

        if result in (None, ""):
            raise RuntimeError("Succeeded Formula Fiber returned no output")
        # 两个字段都空 → 说明服务端确实没给结果 → 主动报错
        # 宁可报错，也不要返回一个空结果骗上层

    except Exception as exc:
        # 上面任何一步出错，都会跳到这里
        # as exc = 把异常对象存进变量 exc，方便下面读取它的信息
        # Exception 是最常见的异常基类，捕获它能兜住绝大多数错误

        error_payload: Dict[str, Any] = {
            "class": type(exc).__name__,
            "message": str(exc),
        }
        # 组装一个错误信息字典
        # type(exc).__name__   取出异常的类型名，比如 "RuntimeError"、"Timeout"
        # str(exc)             把异常转成字符串，也就是错误描述

        if response is not None:
            try:
                error_payload["response"] = response.json()
            except ValueError:
                error_payload["response_text"] = response.text
        # 如果请求确实发出去了（response 不是 None），就把服务器的原始响应也记下来
        # 嵌套 try：有些错误响应不是合法 JSON，.json() 会抛 ValueError，
        # 那就退而记录原始文本 response.text
        # 目的：出错时留下尽可能多的现场证据，方便事后排查

        self.api_turns.append({
            "kind": "formula_fiber",
            "formula_uri": self.formula_uri,
            "request": {
                "method": "POST",
                "url": url,
                "body": body,
            },
            "http_status": getattr(response, "status_code", None),
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "error": error_payload,
        })
        # 把这次失败的完整信息追加到 api_turns 列表里（存证）
        # 这样事后能回放"当时到底发了什么、对方回了什么"
        #
        # getattr(response, "status_code", None)
        #   安全的取属性方式：如果 response 没有 status_code，就返回 None 而不是报错
        #   因为上面判断过 response 可能是 None
        #
        # round(..., 6)  保留 6 位小数
        # time.monotonic() - started   当前时间 - 开始时间 = 耗时

        raise
        # 空的 raise = "把刚才捕获的异常原样再抛出去"
        # 为什么要再抛？因为这里只是"记录现场"，记录完还是要让上层知道出错了。
        # 如果这里只 except 不 raise，异常就被"吞掉"了，上层会以为一切正常——
        # 这是非常危险的写法（静默失败）。

    self.api_turns.append({
        "kind": "formula_fiber",
        "formula_uri": self.formula_uri,
        "request": {"method": "POST", "url": url, "body": body},
        "http_status": response.status_code,
        "response": payload,
        "elapsed_seconds": round(time.monotonic() - started, 6),
    })
    # 成功的情况也要存证（和上面失败时的存证对应）
    # 这样无论成功失败，api_turns 里都有一条完整记录

    if isinstance(result, str):
        return result
    # isinstance(值, 类型)  判断这个值是不是某种类型
    # 如果已经是字符串，直接返回

    return json.dumps(result, ensure_ascii=False)
    # 如果不是字符串（比如是字典、列表），就转成 JSON 字符串再返回
    # 为什么要转？因为上层要把它放进 message 的 content 字段，那个字段必须是字符串
    # ensure_ascii=False 的意思是"中文不要转成 \uXXXX 转义"，否则中文会变成乱码一样的转义符


# ============================================================================
# 这份代码里最值得学的 5 个点
# ============================================================================
#
# 1. 传输层成功 ≠ 业务层成功
#    HTTP 200 只说明"请求送到了"，还要单独检查业务状态 payload["status"]
#
# 2. HTTP 错误不会自动抛异常
#    必须手动 response.raise_for_status()，否则 404/500 会被安静地当成正常响应
#
# 3. 对外部数据用 .get() 而不是 []
#    [] 取不到会 KeyError 崩掉，.get() 取不到返回 None，可以兜底
#
# 4. 出错时留全现场
#    url / body / 状态码 / 耗时 / 响应体全记下来，事后才能复现问题
#
# 5. except 里记完还要 raise
#    只记录不抛出 = 静默失败，上层会以为一切正常。这是生产事故的常见来源。
