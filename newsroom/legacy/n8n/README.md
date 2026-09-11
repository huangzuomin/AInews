# n8n 工作流存档（脱敏）

## 这是什么

2025-06 至 2025-09 期间用于 neican.ai 内容生产的 n8n 工作流导出存档，共 27 个文件。
归档目的是**考古编辑方法论**——分类闸、多维加权评分、结构五型、写作与日报规范等。

方法论已被逐条提取进：

- `newsroom/SPEC-selection-and-style-2026-09-11.md`（选题机制与风格规范）
- `newsroom/DESIGN-automation-2026-09-11.md` §10（与 n8n 的关系决策）

## 脱敏说明

原始存档位于 `D:\Work\n8n\`（**不在本仓库**），其中含明文凭据。入库前经
`newsroom/_desensitize_n8n.py` 做字符级替换：

| 类型 | 替换为 |
|---|---|
| GitHub PAT | `<REDACTED:GITHUB_PAT>` |
| Tavily key | `<REDACTED:TAVILY_KEY>` |
| OpenAI 风格 key | `<REDACTED:OPENAI_KEY>` |
| 邮箱 | `<REDACTED:EMAIL@domain>` |
| JSON 敏感键（apiKey/token/password…） | `<REDACTED>` |

已验证：`ghp_` / `gho_` / `ghu_` / `ghs_` / `tvly-` / `AIza` 残留均为 0。
（`sk-` 与 `Bearer` 的命中经人工核对为误报：前者来自 `elon-musk-buy-openai` 文本，
后者为 `Bearer {{ $credentials... }}` 模板占位符。）

## 重要：脱敏不等于止损

**删除/替换此处的字符串不会使已泄漏的凭据失效。** 原始存档中的凭据在其签发平台
上仍然有效，必须按 `PLAN-master-2026-09-11.md` 的 **P0.1 / P0.2** 在平台侧轮换。

轮换完成后，旧工作流的发布能力自动失效（push 必然 401）——这是把"停用旧产线"
从状态位（可被推翻）升级为物理约束的做法。

## 勘误

- `修改.json` 原始导出即为非法 JSON（非脱敏所致），仅作纯文本保留。
