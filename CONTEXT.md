# Zrun Backend Platform

Zrun 的后端平台:一个 BFF 聚合多个独立领域服务(UC、Flow),共享代码抽取为 workspace 包。

## Language

**Service(服务)**:
`apps/` 下可独立部署的 HTTP 应用(BFF、UC、Flow)。
_Avoid_: microservice、app

**BFF(Backend-for-Frontend)**:
面向前端的服务——前端唯一调用的服务;通过各服务的 contract package 聚合 UC 与 Flow。
_Avoid_: gateway、aggregator

**UC(User Center,用户中心)**:
拥有用户账户与资料的服务。
_Avoid_: user service、auth(auth 是共享包,不是服务)

**Flow(流程服务)**:
拥有 flow 资源的服务:带生命周期 status 的命名 workflow 定义。

**Contract Package(契约包)**:
`packages/<service>-api` 包,持有单个服务的 wire contract——models、protocol、client——provider 与所有 consumer 共同依赖它(见 ADR 0002)。
_Avoid_: API package、SDK、client package
