# 0005 - Migrate HTTP stack from httpx to httpx2

## Status

**Accepted**(2026-08-29,补记:迁移实际发生在 commit 770b3b7,本 ADR 事后补写)

## Context

运行时 HTTP 栈(http client、错误映射、transport 扩展点)与测试栈(starlette `TestClient`)都建在 `httpx` 上。starlette testclient 已 deprecate httpx(见 [0004](./0004-mock-router-replacing-respx.md) 的 Context),deprecation warning 常驻测试输出;且 httpx 生态的配套(mock 库 respx、httpcore)不再跟进,继续留在旧栈意味着运行时与测试迟早被上游断供。httpx2(2.12.0,2026-08-18 发布于 PyPI)是同一架构血统的继任者:依赖 httpcore2/truststore,API 面与 httpx 一致(`AsyncClient`、`Limits`、`TransportError`、`HTTPStatusError`、`AsyncBaseTransport` 等全部同名同形)。

## Decision

全库将 HTTP 栈从 `httpx` 迁移到 `httpx2`:运行时代码(`zrun.core.http` 的 base client / feign)、测试工具(`zrun-test-utils` 的 helpers / mock_router)统一 `import httpx2`;根 `[tool.uv] constraint-dependencies` 声明 `httpx2>=2.12`,成员按 [0003](./0003-centralized-version-constraints-at-workspace-root.md) 只写 bare name;移除 `httpx` 与 `respx` 依赖。

Why:

- API 完全兼容,迁移是纯 rename diff(`import httpx` → `import httpx2`),`base_client`/`feign` 的错误映射与重试逻辑零改动,风险接近纯升级
- 消除 starlette testclient 的 deprecation warning,运行时与测试回到同一受维护的栈
- 趁代码库尚小(仅 4 个文件触及)时换栈,成本最低;拖到服务与 client 数量增长后成本线性放大

Alternatives Considered:

- **留在 httpx 不迁移**:✅ 零改动、生态工具(respx)现成 / ❌ starlette testclient deprecation 常驻,上游断供只是时间问题,且栈越老越难迁
- **锁定旧版 starlette 保住 httpx**:✅ 暂时无 warning / ❌ 把整个服务框架钉死在旧版,FastAPI/starlette 安全修复一并被锁死
- **换 aiohttp / urllib3 等其他 HTTP 库**:✅ 各自成熟 / ❌ API 模型不同,`base_client`/`feign`/错误映射需重写而非 rename,迁移风险与工作量都不在一个量级

## Consequences

**Positive:**

- 运行时与测试同栈且受维护,deprecation warning 清零
- `AsyncBaseTransport` 等扩展点同名保留,[0004](./0004-mock-router-replacing-respx.md) 的 `MockRouter` 与 `transport=` seam 不受影响

**Negative:**

- httpx2 尚年轻(2026-08 首发),发布节奏与长期维护需持续观察
- 旧生态工具不认 httpx2:respx 无法拦截 httpx2 client,迫使测试 mock 自建(已由 0004 解决)
- 文档与注释中的 "httpx" 字样已随迁移改为 "httpx2",外部读者需要知道这是同一套 API

**Mitigation:**

- 版本约束集中在根 `[tool.uv] constraint-dependencies`(`httpx2>=2.12`),升级与回退单点可控,见 [docs/dependencies.md](../dependencies.md)
- httpx2 若停止维护,因其 API 同形,回迁 httpx 或再迁后继者仍是 rename 级 diff

## Implementation Notes

- 迁移落地于 commit 770b3b7:4 个文件 import rename,根约束 `httpx2>=2.12`,同时移除 `httpx`/`respx`
- 错误映射(`httpx2.TransportError` → `ServiceCallError` 子类型)语义与迁移前逐条一致

## Related Decisions

- [0003 - Centralized version constraints at the workspace root](./0003-centralized-version-constraints-at-workspace-root.md)
- [0004 - Self-built MockRouter replacing respx](./0004-mock-router-replacing-respx.md)
