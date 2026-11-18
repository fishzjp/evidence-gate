# 示例 10 · 真实 Agent 工作流：闸门如何改变一次回答

**教训：闸门不是回答后的装饰 —— 它在回答成形之前改变 Agent 的行为路径。**

```
Task: “升级到 fastify 5.x 后服务还能正常运行吗？”
   ↓
Reasoning: 读迁移文档，listen() 返回 Promise、用法兼容 → 起草 “服务可以正常运行”
   ↓
Evidence Gate (第一次): VERIFY_REQUIRED —— works 声明未执行，文档阅读只是 L2
   ↓
Verification: npm start 实际启动 → /health 200、日志无错误；独立 CI 容器复跑
   ↓
Evidence Gate (第二次): PASS —— 执行证据 L3 支撑声明
   ↓
Final Answer
```

## 第一次过闸（未执行）

```json
{
  "conclusion": "升级到 fastify 5.x 后服务可以正常运行",
  "type": "INFERENCE",
  "claimed_strength": "likely",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "official_doc",
      "detail": "迁移文档（本地副本）：listen 返回 Promise，用法与 4.x 兼容",
      "anchor": "tests/fixtures/fastify-server.md",
      "quote": "server.listen() returns a Promise",
      "content_supports": "supported",
      "group": "docs"
    }
  ],
  "verification": {
    "executed": false,
    "detail": "",
    "env_independent": "unknown",
    "validates_target": "unknown"
  },
  "counter_evidence": [],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

实际输出（节选）：

```text
Evidence Gate Result
Conclusion:
Type: INFERENCE
Claimed strength: likely  (risk: medium)
Evidence Level: L2  (claim requires L3)
Evidence (anchor three-stage check):
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/fastify-server.md
  execution: executed=False valid=False env_independent=unknown validates_target=unknown
Counter-evidence search context: isolated
Findings:
Confidence: LOW
Decision: VERIFY_REQUIRED  (exit 10)
Reason:
Allowed wording: 可能/初步判断 (possibly / preliminary) — 未实际运行验证 (not actually executed/verified)
Required actions:
  - execute the actual verification: run the program / tests / benchmark instead of reasoning about it
  - or downgrade the wording and rerun the gate with the lower claim
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "mechanical"}
```

Agent 服从决策：不输出原句，执行验证动作。

## 第二次过闸（执行后）

```json
{
  "conclusion": "升级到 fastify 5.x 后服务可以正常运行",
  "type": "INFERENCE",
  "claimed_strength": "verified",
  "risk_tier": "medium",
  "evidence": [
    {
      "kind": "official_doc",
      "detail": "迁移文档（本地副本）：listen 返回 Promise，用法与 4.x 兼容",
      "anchor": "tests/fixtures/fastify-server.md",
      "quote": "server.listen() returns a Promise",
      "content_supports": "supported",
      "group": "docs"
    }
  ],
  "verification": {
    "executed": true,
    "detail": "npm start 本地启动：/health 返回 200，启动日志无错误；独立 CI 容器复跑同样通过",
    "env_independent": true,
    "validates_target": true
  },
  "counter_evidence": [],
  "counter_search_context": "isolated",
  "evidence_obtainable": "yes",
  "generalization": null
}
```

实际输出（节选）：

```text
Evidence Gate Result
Conclusion:
Type: INFERENCE
Claimed strength: verified  (risk: medium)
Evidence Level: L3  (claim requires L3)
Evidence (anchor three-stage check):
  - [direct·mech✓] official_doc — quote verified in anchor: tests/fixtures/fastify-server.md
  execution: executed=True valid=True env_independent=True validates_target=True
Counter-evidence search context: isolated
Findings:
Confidence: HIGH
Decision: PASS  (exit 0)
Reason:
Allowed wording: 已通过实际验证 (verified)
Verifier: {"id": "unspecified", "protocol": "gate_check/2.0.0", "entailment_channel": "mechanical"}
```

## 最终回答

**“已通过实际验证：升级到 fastify 5.x 后服务正常启动（本地与独立 CI 容器各
验证一次，/health 200、启动日志无错误）。依据迁移文档 listen 用法与 4.x 兼容。”**

关键区别不是最终措辞多了一个“已验证”，而是中间真的发生了两次启动运行 ——
如果没有闸门，第一次推理就会直接变成回答。
