# Azure 资源归属报错核对 · 2026-11-16

用户报告在未切换模型或供应商的情况下反复出现：

> The requested item was created under a different Azure OpenAI resource. Use the same resource that created the item to access it. [trace_id=cd1029ed932efc6b27addf90a80c08f0]

## 本地可核实的事实

- 会话 `01a1e221-c22a-7053-b45f-c481990e2492` 最后一轮状态为failed，记录中的错误与用户提供的文本及trace_id一致。完成/失败事件时间为2026-11-16 10:52:20（北京时间）。
- 原会话四个turn_context中的模型均为 `gpt-6-astra`，没有观察到模型切换。
- 原会话session_meta的供应商标识为 `custom`。当前本地配置同为 `custom`，入口是 `https://agentrouter.org/v1`，协议为 `responses`。配置读取只输出这几个非秘密字段，未输出认证密钥。
- 历史turn_context不含每轮完整上游地址或Azure资源标识，因此不能仅凭本地记录证明每一轮实际落到同一个Azure资源，也不能确认网关内部究竟发生了负载均衡、故障转移还是历史条目兼容问题。
- [Codex官方配置参考](https://developers.openai.com/codex/config-reference) 将 `model_providers.<id>.base_url` 定义为模型供应商API地址，将 `wire_api` 定义为供应商协议。这支持区分“客户端选中的供应商入口”与“入口之后的实际上游资源”；官方配置参考没有解释这次AgentRouter内部故障。

## 判断

错误描述的是服务端条目的Azure资源归属不匹配，而不是证明用户手动切换了模型或供应商。同一个模型名和同一个网关地址，仍可能被转发到不同Azure资源。结合当前AgentRouter入口，优先怀疑网关上游资源分配或Responses历史条目复用问题；这是有依据的排查方向，尚非已确认根因。

`item`可能是请求引用或携带的历史响应、推理等条目。本轮没有抓取完整出站请求或服务端日志，不能断言一定是 `previous_response_id`、某个加密推理条目或某次故障转移。此错误也不能直接归因于提示词太长，与之前的HTTP 413请求体限制不是同一条错误。

## 可向AgentRouter支持提供的内容

> Codex Desktop，Responses协议，同一会话四轮模型均为gpt-6-astra，客户端供应商标识custom，入口https://agentrouter.org/v1。北京时间2026-11-16 10:52:20报“item was created under a different Azure OpenAI resource”，trace_id为cd1029ed932efc6b27addf90a80c08f0。请核对该请求及前序条目的实际Azure资源，检查会话路由、故障转移和历史条目复用是否保持资源一致。

这段文本仅保存在本地，未代用户发送。必要的修复应由网关按实际日志确定，包括保持相关请求的资源一致，以及正确处理跨资源时不可复用的状态。不能在未验证的情况下通过随意修改客户端参数承诺修复。

新聊天用普通文本和项目文件续接，可以尝试绕开旧会话关联的状态，但若网关仍在同一轮请求间切换资源，仍可能再次报错，不能称为根治。本轮没有修改用户的模型、供应商或认证配置；项目工作已从本地备份与实际Blender状态续作。
