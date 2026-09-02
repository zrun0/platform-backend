# 0006 - Feign decorator fail-fast validation + PATCH for partial updates

## Status

**Accepted**(2026-08-30)

## Context

[0002](./0002-api-contracts-as-separate-packages.md) 的 Feign 风格端点装饰器把方法签名翻译成 HTTP 调用,但初版的全部解析都在**每次请求的 wrapper 内**临时完成,装饰那一刻(import / 服务启动)不做任何校验。代码审查与实测发现一串静默失败模式:

- `-> None`(delete/204)被当成"解析成 NoneType",对空响应执行 `response.json()` → JSONDecodeError;该 bug 真实存在且无测试覆盖;
- body 参数靠名字约定(`payload`/`body`/`data`)识别,起错名字时 Pydantic 模型被 `str()` 进 query string,请求体为空且不报错;
- 漏写返回注解 → 静默返回原始 `Response`;路径占位符与参数名不匹配 → 首次调用才 `KeyError`;路径参数不做 percent-encode;`None` 路径参数拼成字面量 `"None"`;
- PUT 与 PATCH 一律 `exclude_unset=True`:部分更新语义挂在了 PUT 上,而 PUT 按 REST 语义是全量替换。

共同根因:签名 ↔ HTTP 行为的契约没有任何机械保障,错误全部延迟到端点第一次被流量打到才暴露。

## Decision

1. 装饰器在装饰期(import 时)构建不可变的 `EndpointSpec` 并完成全部校验,wrapper 退化为纯取值转发:
   - body 参数**按类型**(注解为 `BaseModel` 子类)识别,不再按名字;body 方法(POST/PUT/PATCH)必须恰好有一个 body 参数,GET 等方法不允许有 body;
   - 路径占位符必须都有对应形参,否则 `TypeError`;
   - 返回注解必须存在;`-> None`(`type(None)`)显式表示 no-content,`_parse_response` 直接返回 `None` 不碰响应体;
   - 路径变量用 `urllib.parse.quote(safe="")` percent-encode;`None` 路径变量调用期 `TypeError`;
   - `typing.get_type_hints` 与 spec 只在装饰期计算一次。
2. 部分更新端点从 PUT 迁移到 **PATCH**(UC、Flow 的服务端路由与契约 client 同步改);PUT 保留为全量替换语义(发送完整 body)。
3. 契约包测试新增 `test_all_endpoints_have_valid_specs` 护栏:遍历 client 全部端点方法,断言都携带已校验的 `EndpointSpec`。

Why:

- 装饰期 = 服务启动必经之路,违约在 `just dev` / 测试收集的那一秒就爆炸,而不是生产环境首次调用;
- 按类型识别 body 与 FastAPI 自身的 body 推断规则一致,名字不再是承重约定;
- PATCH 才是部分更新的正确动词;全可选字段的 `UserUpdate`/`FlowUpdate` 模型本质是 PATCH 模型。

Alternatives Considered:

- **保持每请求解析 + 运行时报错**:✅ 实现最简 / ❌ 错误时机仍是"首次真实流量",未覆盖到的端点带病上线(delete bug 正是如此)
- **body 仍按名字约定但扩充白名单**:✅ 改动最小 / ❌ 名字约定无法防 typo/重构改名,静默 query 串损坏风险依旧
- **保留 PUT 做部分更新**:✅ 零路由改动 / ❌ 与 HTTP 语义冲突,将来真正的全量替换无路可走

## Consequences

**Positive:**

- 9 类失败模式中 6 类在启动期 `TypeError`,1 类(204)行为修正,2 类(路径编码、None 路径参数)显式处理;`packages/core/tests/test_feign.py` 锁定全部行为
- 顺带修复两个潜伏 bug:UC/Flow update 处理器 `UserResponse(..., updated_at=...)` 的重复关键字冲突(更新路径此前端到端必 500)、retry 循环 `assert result is not None` 与 no-content 返回值冲突

**Negative:**

- 装饰期 `get_type_hints` 要求端点引用的模型在 import 时可解析(本仓库契约模型均为运行时 import,无影响;若未来用 `TYPE_CHECKING`-only 模型做返回注解会在启动期报错)
- PUT 路由契约变更:外部调用方更新用户/流程需改用 PATCH(当前无外部 consumer,BFF 不代理 update)

**Mitigation:**

- 新增端点的规则写在 `feign.py` 模块 docstring;契约护栏测试防倒退

## Related Decisions

- [0002 - API contracts as separate packages](./0002-api-contracts-as-separate-packages.md)
- [0004 - Self-built MockRouter replacing respx](./0004-mock-router-replacing-respx.md)
