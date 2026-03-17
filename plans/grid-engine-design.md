# 九宫格引擎 产品设计

## 一句话

用户扔一堆图进来 → 自动选出最强 9 张 → 排好封面和顺序 → 写整组文案。

## 用户流程

```
拖入 15-50 张图（一次拍摄/旅行/选品/探店）
         ↓
   全量 attention 分析
         ↓
   ┌─────────────────────────┐
   │  选（淘汰弱图）          │ → 淘汰理由
   │  封面（选最强 hook）      │ → 封面推荐 + 备选
   │  排（叙事顺序 2-9）      │ → 九宫格编排
   │  写（整组文案）          │ → 标题/正文/标签
   └─────────────────────────┘
         ↓
   九宫格预览 + 文案 + 可手动调整
```

## 评分维度（每张图）

Analyze 阶段已有的字段可以复用，新增维度用同一次 Vision 调用提取。

| 维度 | 字段名 | 含义 | 范围 |
|------|--------|------|------|
| 视觉冲击力 | `visual_impact` | 第一眼能不能让人停下来：构图张力、色彩对比、画面信息量 | 0-10 |
| 信息密度 | `info_density` | 图中有多少"可写的内容"：细节、文字、产品信息 | 0-10 |
| 独特性 | `uniqueness` | 和同批其他图比，有没有不可替代的视角或元素 | 0-10 |
| 情绪感染力 | `emotion_pull` | 能不能引发共鸣、好奇、向往、争议 | 0-10 |
| 封面潜力 | `cover_potential` | 作为第一张图出现时，点击欲有多强 | 0-10 |

综合分 = `visual_impact * 0.30 + info_density * 0.20 + uniqueness * 0.20 + emotion_pull * 0.20 + cover_potential * 0.10`

旧的 `relevance_score` 保留做兼容，但选图逻辑改用综合分。

## 封面选择逻辑

1. 取 `cover_potential` 最高的图为封面推荐
2. 如果 top2 差距 < 1 分，两张都推荐，让用户选
3. 封面必须满足：`visual_impact >= 7` 且 `emotion_pull >= 6`（硬门槛）
4. 不满足硬门槛时，降级为综合分最高的图 + 警告

## 九宫格编排逻辑

位置语义（小红书阅读习惯）：

```
┌───┬───┬───┐
│ 1 │ 2 │ 3 │  ← 第一屏：hook + 核心信息
├───┼───┼───┤
│ 4 │ 5 │ 6 │  ← 第二屏：展开细节
├───┼───┼───┤
│ 7 │ 8 │ 9 │  ← 第三屏：收尾 + 行动触发
└───┴───┴───┘
```

| 位置 | 角色 | 选择策略 |
|------|------|----------|
| 1（封面） | 视觉钩子 | `cover_potential` 最高 |
| 2-3 | 核心支撑 | 综合分 top2-3，且与封面视觉不重复 |
| 4-6 | 细节展开 | `info_density` 高的图优先，补充不同角度 |
| 7-8 | 氛围/场景 | `emotion_pull` 高的图，做情感收束 |
| 9 | 行动锚点 | 有价格/地址/购买信息的图，或整体感最强的图 |

去重规则：
- 同 `hero_element` 的图最多入选 2 张
- 同 `mood` 标签的图最多入选 3 张
- 构图极度相似的图（同场景同角度）只保留综合分更高的

不足 9 张时：
- 有几张排几张，位置 1 逻辑不变
- < 4 张时提示"图片不足以组九宫格，建议补拍"

## 输出格式

### 九宫格编排结果

```json
{
  "grid": {
    "cover": {
      "filename": "IMG_001.jpg",
      "position": 1,
      "role": "视觉钩子",
      "cover_potential": 9.2,
      "composite_score": 8.7,
      "reason": "高饱和甜品特写，第一眼就想吃"
    },
    "cover_alternatives": [...],
    "slots": [
      {"position": 1, "filename": "...", "role": "...", "reason": "..."},
      ...
      {"position": 9, "filename": "...", "role": "...", "reason": "..."}
    ],
    "excluded": [
      {"filename": "...", "composite_score": 3.2, "exclude_reason": "画面模糊，信息量低"}
    ],
    "grid_narrative": "开头用甜品特写制造食欲钩子 → 中段展开店铺环境和菜单细节 → 收尾用暖光氛围图做情感锚定"
  }
}
```

### 整组文案

从"单图文案"升级为"整组叙事文案"：

- 标题：基于封面图 hook + 整组主题
- 正文：涵盖九宫格里的关键图（不是每张都写，选 3-4 个关键节拍）
- 标签：综合全部 9 张图的高频元素
- 引导语：告诉用户"第 X 张有惊喜"类的翻页引导

```
===整组文案===
【封面图】：IMG_001.jpg
【标题A】：...
【标题B】：...
【正文】：...（120-250字，自然覆盖位置 1/3/5/9 的关键信息）
【翻页引导】：划到第 5 张看价格 👀
【标签】：...
```

## Pipeline 改动

```
现有：Ingest → Analyze → Select → Research → Generate
                          ↑ 只按 relevance_score 排序

新：  Ingest → Analyze → Arrange → Research → Generate
                          ↑ 替换 Select
                          多维评分 + 封面选择 + 九宫格编排
```

### 改动清单

| 文件 | 改动 |
|------|------|
| `steps/analyze.py` | INTENT_PROMPT 增加 5 个评分维度字段 |
| `steps/select.py` → `steps/arrange.py` | 重写为 ArrangeStep：综合评分 + 去重 + 编排 |
| `schemas.py` | 新增 `GridSlot`、`GridResult`，扩展 `IntentPayload` |
| `pipeline.py` | `PipelineState` 新增 `grid` 字段 |
| `steps/generate.py` | prompt 改为整组叙事模式 |
| `core.py` | `_build_pipeline` 替换 SelectStep → ArrangeStep |
| `app.py` | 九宫格预览 UI（后续） |

### 不改的

- `steps/ingest.py` — 已支持多图，不动
- `steps/research.py` — XHS 爬虫逻辑不变
- `providers/` — 不变
- `format/` — 后续迭代

## 实现顺序

1. **Analyze prompt 升级** — 加 5 维评分，验证 Gemini 能稳定返回
2. **ArrangeStep** — 替换 SelectStep，实现评分+封面+编排
3. **Schema 扩展** — GridSlot/GridResult 数据结构
4. **Generate prompt 升级** — 整组叙事文案
5. **Web UI** — 九宫格预览（Phase 4+）
