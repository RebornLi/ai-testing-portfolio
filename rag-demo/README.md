# rag-demo · RAG 系统 + 测试（W3）

## 目标
自建 RAG 问答系统（切分→embedding→向量库→检索→rerank→引用），
并用 pytest 覆盖每个环节，做到：**检索效果可量化、有测试覆盖、能讲清每个环节的坑**。

## 验收标准
1. 检索效果可量化 —— Recall@K / Precision@K / MRR / HitRate
2. 幻觉可检测 —— 确定性接地打分（grounding）
3. 答案质量可评估 —— 答案相关性 + 综合质量门 + 端到端报告
4. 全量测试全绿 —— 53 用例全绿

## 组件
本地 embedding (:8081) + ChromaDB/FAISS

> 注：当前用确定性词袋嵌入 + numpy 余弦相似度做原型（离线可跑、可复现）。
> 接入真实 embedding 服务后，可把"确定性替代"升级为真实语义相似度。

## 运行
```bash
cd ~/ai-testing-portfolio/rag-demo
pytest -q          # 期望: 53 passed
```

## 目录结构
```
rag-demo/
├── rag/
│   ├── rag_utils.py      # 分块 + 确定性嵌入 + 余弦检索（D1）
│   ├── embedders.py      # 工厂模式：真实 + mock 嵌入器（D2）
│   ├── store.py          # 向量库：Mock + FAISS（D2）
│   ├── pipeline.py       # 集成层：embedder + store 串起来（D2）
│   ├── eval_metrics.py   # 检索质量指标（D3）
│   ├── eval_engine.py    # golden 集聚合评估（D3）
│   ├── grounding.py      # 确定性幻觉/接地检测（D4）
│   ├── quality.py        # 答案相关性 + 综合质量门（D5）
│   ├── report.py         # 端到端评估报告 + 质量门（D6）
│   └── vector_search.py  # 向量检索基础（辅助）
└── test_rag_*.py         # 7 个测试文件
```

## 测试清单（53 用例全绿）

| 测试文件 | 用例数 | 覆盖 |
|---|---|---|
| test_rag_retrieval.py | 6 | 分块 + 嵌入 + 检索（D1） |
| test_rag_integration.py | 9 | 集成链路（D2） |
| test_rag_eval.py | 9 | 检索质量指标（D3） |
| test_rag_d4.py | 9 | 幻觉/接地检测（D4） |
| test_rag_quality.py | 11 | 答案相关性 + 质量门（D5） |
| test_rag_report.py | 9 | 端到端评估报告（D6） |

## 本周里程碑（W3）
- [x] D1：RAG 入门（分块 + 确定性嵌入 + 余弦检索）
- [x] D2：接入真实 Embedder（工厂模式解耦）
- [x] D3：检索质量评估（Recall/Precision/MRR/HitRate）
- [x] D4：幻觉检测（确定性接地打分）
- [x] D5：端到端答案质量打分（相关性 + 综合质量门）
- [x] D6：端到端评估报告（RagEvaluator）
- [x] D7：里程碑收尾 + 复盘（今天）

## 复盘要点
- **工厂模式解耦**：测试走 mock，真实模型手动切 mode="real"
- **确定性替代**：无真实服务时用词袋嵌入兜底，保证可跑可验证
- **质量门**：composite = 相关×0.5 + 忠实×0.5，阈值 0.6 卡质量
- **关键卡点**：空 golden 集 `np.mean([])` 返回 NaN → 空行兜底 0.0
