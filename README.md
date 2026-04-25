# WeChat Official Account Content Studio

> 面向微信公众号的内容生产工作室：选题、素材、写作、视觉、排版、质量门禁、草稿箱发布一条链路完成。

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![WeChat](https://img.shields.io/badge/WeChat-Official%20Account-07C160?style=flat-square&logo=wechat&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-black?style=flat-square)

![GZH Content Studio workflow](assets/repo/hero.jpg)

## 项目来源与致谢

本仓库是我在尊重原始开源项目及其许可的前提下，结合自己在公众号内容生产、排版规范、视觉提示词、质量门禁和发布流程上的想法做的整合与修改版本。

- 原始内容工作流来源之一：[`oaker-io/wewrite`](https://github.com/oaker-io/wewrite)，作者 / 维护者为 GitHub 组织 `oaker-io`
- 原始 Markdown 转公众号排版能力来源之一：[`geekjourneyx/md2wechat-skill`](https://github.com/geekjourneyx/md2wechat-skill)，作者 / 维护者为 GitHub 用户 `geekjourneyx`
- 当前仓库不是对原项目的原样镜像，而是结合我自己的使用场景做的二次开发与流程重组

更完整的说明见 [NOTICE.md](NOTICE.md)。

公众号文章全流程 AI Skill —— 从热点抓取到草稿箱推送，一句话搞定。

兼容 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 和 [OpenClaw](https://github.com/anthropics/openclaw) 的 skill 格式。安装后说「写一篇公众号文章」即可触发完整流程。

## 它能做什么

```
"写一篇公众号文章"
  → 抓热点 → 选题评分 → 素材采集 → 框架选择
  → 写作（真实信息锚定 + 7层去AI痕迹 + 编辑锚点）
  → SEO优化 → AI配图 → 微信排版 → 推送草稿箱
```

![从热点到草稿箱的工作流](assets/repo/workflow.jpg)

首次使用时会引导你设置公众号风格，之后每次只需一句话。生成的文章带有 2-3 个编辑锚点——花 3-5 分钟加入你自己的话，文章就会从"AI 初稿"变成"你的作品"。

## 核心能力

| 能力 | 说明 | 实现 |
|------|------|------|
| 热点抓取 | 微博 + 头条 + 百度实时热搜 | `scripts/fetch_hotspots.py` |
| SEO 评分 | 百度 + 360 搜索量化评分 | `scripts/seo_keywords.py` |
| 选题生成 | 10 选题 × 3 维度评分 + 历史去重 | `references/topic-selection.md` |
| 素材采集 | WebSearch 真实数据/引述/案例 | SKILL.md Step 3b |
| 框架生成 | 5 套写作骨架（痛点/故事/清单/对比/热点） | `references/frameworks.md` |
| 文章写作 | 真实信息锚定 + 7 层去 AI + 编辑锚点 | `references/writing-guide.md` |
| SEO 优化 | 标题策略 / 摘要 / 关键词 / 标签 | `references/seo-rules.md` |
| 质量门禁 | 人味打分 + 结构体检 + 环境诊断 + SEO 报告 | `scripts/check_wechat_article.ps1` |
| 视觉 AI | image2 / gpt-image-2 优先，封面 + 内文配图逐张验收 | `toolkit/image_gen.py` / `references/visual-prompts.md` |
| 模板发布 | 模板渲染 + 预检拦截 + 推送草稿箱 | `scripts/render_wechat_article.ps1` / `scripts/publish_wechat_article.ps1` |
| 效果复盘 | 微信数据分析 API 回填阅读数据 | `references/effect-review.md` |
| 风格飞轮 | 学习你的修改，越用越像你 | `references/learn-edits.md` |

## 视觉工作流：优先 image2

本仓库默认把封面和内文图当作正文结构的一部分，而不是最后补一张装饰图。

- 默认推荐 `image.provider: openai` + `image.model: gpt-image-2`
- 所有图片先生成 `generated/image-prompts.md`，API 调用必须使用这个文件里的槽位提示词
- 每张图必须有明确用途、插入位置、alt、图例说明、正向提示词、负向提示词和验收标准
- 禁止“单调背景 + 居中大字 + 几个图标”的 PPT 模板感
- 逐张生成、逐张验收；失败时只重写当前槽位提示词，不批量盲跑

推荐配置见 `config.example.yaml`。真实 API key 只放本地 `config.yaml`，该文件已被 `.gitignore` 排除。

## 写作人格

像选排版主题一样选写作风格。在 `style.yaml` 里一行配置：

```yaml
writing_persona: "midnight-friend"
```

| 人格 | 适合 | 朱雀实测 |
|------|------|---------|
| `midnight-friend` | 个人号/自媒体 | **39% 人工 / 10% AI** |
| `warm-editor` | 生活/文化/情感 | 10% 人工 / 33% AI |
| `industry-observer` | 行业媒体/分析 | 10% 人工 / 40% AI |
| `sharp-journalist` | 新闻/评论 | 28% 疑似AI / 72% AI |
| `cold-analyst` | 财经/投研 | 26% 疑似AI / 74% AI |

每个人格定义了语气浓度、数据呈现方式、情绪弧线、不确定性表达模板等参数。详见 `personas/` 目录。

## 关于 AI 检测

WeWrite 生成的是**高质量初稿**。我们用朱雀 AI 实测了从无优化到完整 pipeline 的效果：

```
100% AI（无优化）→ 52% AI（加 WebSearch 素材）→ 10% AI（midnight-friend 人格）
```

策略是让你的编辑成本最低：
1. **写作人格**：选择个人声音浓度高的人格，开箱即用就能降低 AI 特征
2. **素材采集**：自动 WebSearch 真实数据/引述/案例，锚定在文章中（不编造）
3. **编辑锚点**：在 2-3 个关键位置标记"在这里加一句你自己的话"
4. **学习飞轮**：每次你编辑后说"学习我的修改"，下次初稿更接近你的风格

个人声音越强的人格，AI 检测通过率越高。专业/客观风格的人格（journalist、analyst）建议配合编辑锚点使用。

## 排版引擎

### 自动轮换版式

如果 `style.yaml` 中设置：

```yaml
theme_mode: "auto"
theme: "professional-clean"
```

渲染时会自动生成 `generated/layout-plan.json`，根据文章内容和最近历史选择 `theme`、`layout_family`、`layout_variant` 与 `module_pattern`，避免每篇都长成同一个模板。

### 16 个主题

```bash
# 浏览器内预览所有主题（并排对比 + 一键复制）
python3 toolkit/cli.py gallery

# 列出主题名称
python3 toolkit/cli.py themes
```

| 类别 | 主题 |
|------|------|
| 通用 | `professional-clean`（默认）、`minimal`、`newspaper` |
| 科技 | `tech-modern`、`bytedance`、`github` |
| 文艺 | `warm-editorial`、`sspai`、`ink`、`elegant-rose` |
| 商务 | `bold-navy`、`minimal-gold`、`bold-green` |
| 风格 | `bauhaus`、`focus-red`、`midnight` |

所有主题均支持微信暗黑模式。容器模块（`callout` / `timeline` / `dialogue` / `quote`）也会随 `layout_variant` 改变形态，不只是换颜色。

### 微信兼容性自动修复

| 问题 | 自动修复 |
|------|---------|
| 外链被屏蔽 | 转为上标编号脚注 + 文末参考链接 |
| 中英混排无间距 | CJK-Latin 自动加空格 |
| 加粗标点渲染异常 | 标点移到 `</strong>` 外 |
| 原生列表不稳定 | `<ul>/<ol>` 转样式化 `<section>` |
| 暗黑模式颜色反转 | 注入 `data-darkmode-*` 属性 |
| `<style>` 被剥离 | 所有 CSS 内联注入 |

### 容器语法

````markdown
:::dialogue
你好，请问这个功能怎么用？
> 很简单，直接在 Markdown 里写就行。
:::

:::timeline
**2024 Q1** 立项启动
**2024 Q3** MVP 上线
:::

:::callout tip
提示框，支持 tip / warning / info / danger。
:::

:::quote
好的排版不是让读者注意到设计，而是让读者忘记设计。
:::
````

## 安装

**Claude Code**：

```bash
git clone --depth 1 https://github.com/wengzige/WeChat-Official-Account-content-studio.git ~/.claude/skills/wewrite
cd ~/.claude/skills/wewrite && pip install -r requirements.txt
```

**OpenClaw**：

```bash
git clone --depth 1 https://github.com/wengzige/WeChat-Official-Account-content-studio.git ~/.openclaw/skills/wewrite
cd ~/.openclaw/skills/wewrite && pip install -r requirements.txt
```

安装后 skill 会在每次运行时自动检查新版本。有更新时说"更新"即可升级。

### 配置（可选）

```bash
cp config.example.yaml config.yaml
```

填入微信公众号 `appid`/`secret`（推送需要）和图片 API key（生图需要）。不配也能用——自动降级为本地 HTML + 输出图片提示词。

推荐 image2 配置：

```yaml
image:
  provider: "openai"
  api_key: "your_api_key"
  model: "gpt-image-2"
  base_url: "https://api.openai.com/v1"
  quality: "medium"
  output_format: "jpeg"
```

`config.yaml`、`style.yaml`、`history.yaml`、`output/`、`.venv/` 等本地生成或私密文件默认不会进入 Git。

## 快速开始

```
你：写一篇公众号文章
你：写一篇关于 AI Agent 的公众号文章
你：交互模式，写一篇关于效率工具的推文
你：帮我润色一下刚才那篇
你：学习我的修改                  → 飞轮学习
你：看看有什么主题                → 主题画廊
你：换成 sspai 主题               → 切换主题
你：看看文章数据怎么样            → 效果复盘
你：做一个小绿书                  → 图片帖（横滑轮播）
你：检查一下反 AI 配置              → 诊断报告
```

## 额度切换（Codex 常规 + API 应急）

默认建议：**优先用插件内置额度**（平时最省事）。

- 你的常规模式：Codex 插件额度可用时，直接正常下指令，不提 API。
- 你的应急模式：只有当插件额度不够时，再明确说"用 API 跑这次"。

### 1) 平时不用 API（走插件 Codex 额度）

直接发：

```
按默认模式跑，不用 API。写一篇关于 AI Agent 的公众号文章。
```

或更简短：

```
默认模式，写一篇公众号文章。
```

### 2) 额度不足时（应急切到 API）

先确保本地 `config.yaml` 已填好 API 配置，然后发：

```
Codex 额度不够了，这次用 API 应急跑。文本模型用 gpt-5.4，按现有流程生成并发布。
```

如果只想先验证 API 可用性，再正式跑正文：

```
先用 API（gpt-5.4）做一次连通性测试，成功后再开始写作流程。
```

### 3) 应急结束后切回默认

下次直接发：

```
恢复默认模式，走插件 Codex 额度，不用 API。
```

## 目录结构

```
wewrite/
├── SKILL.md                  # 主管道（273行，Step 1-8）
├── config.example.yaml       # API 配置模板
├── style.example.yaml        # 风格配置模板
├── writing-config.example.yaml # 写作参数模板（可用 optimize loop 调优）
├── requirements.txt
│
├── dist/openclaw/            # OpenClaw 兼容版（CI 自动构建）
│
├── scripts/                  # 数据采集 + 优化 + 构建
│   ├── fetch_hotspots.py       # 多平台热点抓取
│   ├── seo_keywords.py         # SEO 关键词分析
│   ├── fetch_stats.py          # 微信文章数据回填
│   ├── build_playbook.py       # 从历史文章生成 Playbook
│   ├── learn_edits.py          # 学习人工修改
│   ├── humanness_score.py      # 文章"人味"打分器（客观 checklist + LLM 判官）
│   ├── layout_strategy.py      # 自动选择主题/版式并检查排版重复
│   ├── optimize_loop.py        # autoresearch 风格迭代优化框架
│   └── build_openclaw.py       # SKILL.md → OpenClaw 格式转换
│
├── skill2 paibanyouhua/      # 模板脚本与模板资源
│   ├── templates/              # article.md / metadata / html 模板
│   ├── scripts/                # new-article / render-article / publish-article
│   └── <文章标题>/              # 每篇文章一个独立目录
│
├── toolkit/                  # Markdown → 微信工具链
│   ├── cli.py                  # CLI（preview / publish / gallery / themes / image-post）
│   ├── converter.py            # Markdown → 内联样式 HTML + 微信兼容修复
│   ├── theme.py                # YAML 主题引擎
│   ├── publisher.py            # 微信草稿箱 API + 小绿书图片帖
│   ├── wechat_api.py           # access_token / 图片上传
│   ├── image_gen.py            # AI 图片生成（doubao / OpenAI）
│   └── themes/                 # 16 套排版主题（含暗黑模式）
│
├── personas/                 # 5 套写作人格预设（含朱雀实测数据）
│
├── references/               # Agent 按需加载
│   ├── writing-guide.md        # 写作规范 + 7 层去 AI 痕迹 + 自检清单
│   ├── frameworks.md           # 5 种写作框架
│   ├── topic-selection.md      # 选题评估规则
│   ├── seo-rules.md            # 微信 SEO 规则
│   ├── visual-prompts.md       # 视觉 AI 提示词规范
│   ├── wechat-constraints.md   # 微信平台限制 + 自动修复
│   ├── style-template.md       # 风格配置字段 + 16 主题列表
│   ├── onboard.md              # 首次设置流程
│   ├── learn-edits.md          # 学习飞轮流程
│   └── effect-review.md        # 效果复盘流程
│
├── output/                   # 默认文章工作目录
├── corpus/                   # 历史语料（可选）
└── lessons/                  # 修改记录（自动生成）
```

运行时自动生成（不入 git）：`style.yaml`、`history.yaml`、`playbook.md`、`writing-config.yaml`

## 工作流程

```
Step 1  环境检查 + 加载风格（不存在则 Onboard）
  ↓
Step 2  热点抓取 → 历史去重 + SEO → 选题
  ↓
Step 3  框架选择 → 素材采集（WebSearch 真实数据）
  ↓
Step 4  维度随机化 → 写作（7层规范 + 真实素材锚定 + 编辑锚点）
  ↓
Step 5  SEO 优化 → 去 AI 逐层验证（9 项自检）
  ↓
Step 6  视觉 AI（封面 + 内文配图）
  ↓
Step 7  预检 + 排版 + 发布（16 主题 + 微信兼容修复）
  ↓
Step 8  写入历史 → 回复用户（含编辑建议 + 飞轮提示）
```

默认全自动。说"交互模式"可在选题/框架/配图处暂停确认。

## 优化循环（实验性）

借鉴 [autoresearch](https://github.com/karpathy/autoresearch) 的 change→score→keep/rollback 模式，WeWrite 提供写作参数自动调优框架：

```bash
# 对一篇文章打分（客观 checklist + 主观 LLM 判官）
python3 scripts/humanness_score.py article.md --verbose

# 迭代优化写作参数
python3 scripts/optimize_loop.py --topic "AI Agent" --iterations 10
```

框架开源，但优化后的 `writing-config.yaml` 不入 git——每个用户跑出自己的最优参数。

## 默认模板工作流

```bash
# 新建文章目录
powershell -ExecutionPolicy Bypass -File scripts/new_wechat_article.ps1 -Title "标题"

# 从 article.md 渲染模板预览
powershell -ExecutionPolicy Bypass -File scripts/render_wechat_article.ps1 -ArticleDir "文章目录名"

# 单独执行质量门禁
powershell -ExecutionPolicy Bypass -File scripts/check_wechat_article.ps1 -ArticleDir "文章目录名"

# 直接推送公众号草稿箱
powershell -ExecutionPolicy Bypass -File scripts/publish_wechat_article.ps1 -ArticleDir "文章目录名"
```

新稿默认写在 `output/<文章标题>/article.md`。`article-body.template.html`、`preview.html`、`generated/output.html`、`generated/draft.json` 都由模板脚本自动生成；图片统一放在 `assets/`，横版封面固定为 `assets/cover-wide.jpg`，方形封面固定为 `assets/cover-square.jpg`，提示词统一放在 `generated/image-prompts.md`。从现在开始，`render` 和 `publish` 都会自动生成 `generated/humanness-report.json`、`generated/diagnose-report.json`、`generated/article-doctor-report.json`、`generated/seo-report.json`、`generated/quality-gates.json`，不再靠人工记得补跑。

## Toolkit 独立使用

```bash
# Markdown → 微信 HTML
python3 toolkit/cli.py preview article.md --theme sspai

# 主题画廊
python3 toolkit/cli.py gallery

# 小绿书/图片帖（横滑轮播，3:4 比例，最多 20 张）
python3 toolkit/cli.py image-post photo1.jpg photo2.jpg photo3.jpg -t "周末探店" -c "在望京发现的宝藏咖啡馆"

# 抓热点
python3 scripts/fetch_hotspots.py --limit 20

# SEO 分析
python3 scripts/seo_keywords.py --json "AI大模型" "科技股"

# 诊断反 AI 配置
python3 scripts/diagnose.py
```

## 公开仓库安全约定

本仓库默认只提交源码、模板和示例配置；以下内容属于本地运行产物或私密数据，不应上传：

- `config.yaml`：微信 AppID / Secret、图片 API key
- `style.yaml`、`history.yaml`、`playbook.md`、`writing-config.yaml`
- `output/` 下的文章、图片、草稿 payload 和质量报告
- `.venv/`、`corpus/`、`lessons/` 等本地环境或语料

推送前可运行：

```bash
python scripts/git_privacy_guard.py --commit HEAD
```

## License

MIT
