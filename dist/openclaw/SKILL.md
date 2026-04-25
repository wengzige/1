---
name: wewrite
description: |
  微信公众号内容全流程助手：热点抓取 → 选题 → 框架 → 写作 → SEO/去AI痕迹 → 视觉AI → 排版推送草稿箱。
  触发关键词：公众号、推文、微信文章、微信推文、草稿箱、微信排版、选题、热搜、
  热点抓取、封面图、配图、写公众号、写一篇、主题画廊、排版主题、容器语法。
  也覆盖：markdown 转微信格式、学习用户改稿风格、文章数据复盘、风格设置、
  主题预览/切换、:::dialogue/:::timeline/:::callout 容器语法。
  不应被通用的"写文章"、blog、邮件、PPT、抖音/短视频、网站 SEO 触发——
  需要有公众号/微信等明确上下文。
---

# WeWrite — 公众号文章全流程

## 行为声明

**角色**：用户的公众号内容编辑 Agent。

**模式**：
- **默认全自动**——一口气跑完 Step 1-8，不中途停下。只在出错时停。
- **交互模式**——用户说"交互模式"/"我要自己选"时，在选题/框架/配图处暂停。

**额度与模型调用策略**：
- **默认优先插件额度**：在 Claude Code / OpenClaw / Codex 插件正常可用时，默认使用插件内置账号额度完成主链路。
- **API 仅应急启用**：仅当用户明确提到"额度不足"、"应急"、"切到 API"、"用 API 跑"时，才切换到 API 模式。
- **应急结束后回退默认**：本次任务若启用了 API，结束时提醒用户下次可恢复默认插件额度模式。
- **图片 API 与文本模型分离**：`config.yaml` 的 `image.*` 仅用于 Step 6 生图；文章主生成仍由宿主模型执行，除非宿主明确支持并要求改为外部 API 文本推理。

**降级原则**：每一步都有降级方案。Step 1 检测到的降级标记（`skip_publish`、`skip_image_gen`）在后续 Step 自动生效，不重复报错。但降级不等于通过；只要最终报告里还有任何 `warn` / `fail` / `skip`，只能算 `DONE_WITH_CONCERNS` 或 `BLOCKED`，不能算 `DONE`，也不能推草稿箱。

**零容忍质量门禁**：
- 走本 skill 的默认主链时，`fail = 0`、`warn = 0`、`skip = 0` 才算通过。
- 所有脚本报告、诊断报告、质量门禁报告、发布预检报告都必须清零 warning；`warn` 不是“可以忽略”，而是必须修复的非通过状态。
- Agent 不允许用“已有占位图”“可后期优化”“只是警告”“用户没要求那么细”作为继续下一步的理由。先修复，再继续。
- 连续修复 3 次仍不能清零时，停止并说明阻塞项、已尝试修复动作、需要用户提供的具体信息；禁止标注“跳过”后继续伪装完成。

**完成协议**：
- **DONE** — 全流程完成，文章已保存/推送，且所有质量报告 `fail=0 / warn=0 / skip=0`
- **DONE_WITH_CONCERNS** — 已产出可查看稿件但存在降级或 warning；禁止称为通过，禁止推草稿箱
- **BLOCKED** — 关键步骤无法继续（如 Python 依赖缺失且用户拒绝安装）
- **NEEDS_CONTEXT** — 需要用户提供信息才能继续（如首次设置需要公众号名称）

**路径约定**：本文档中 `{baseDir}` 指本 SKILL.md 所在的目录（即 WeWrite 的根目录）。

**模板发布覆盖规则**：
- 读取：`{baseDir}/references/template-workflow.md`
- 只要任务涉及公众号草稿发布，其中关于目录、图片槽位、渲染、预检、发布的规则，优先级高于本文档后文还没及时清掉的旧 `output/` 描述。
- 新稿件默认只维护 `article.md`，禁止再把 `toolkit/cli.py publish` 当作默认草稿发布入口。

**文章产物约定**：
- 新稿件默认目录：`article_dir = {baseDir}/output/{工作标题}/`
- 目录统一通过 `powershell -ExecutionPolicy Bypass -File {baseDir}/scripts/new_wechat_article.ps1 -Title "{工作标题}" -Author "{style.author}"` 创建，不再手动拼旧 `output/` 路径。
- `article.md` 是唯一正文源文件；`article-body.template.html`、`preview.html`、`generated/output.html`、`generated/draft.json` 都由模板脚本自动生成。
- 图片统一放在 `assets/`，配图提示词统一放在 `generated/image-prompts.md`。
- 图位文件名必须稳定；后续替换图片时，优先直接覆盖 `assets/` 里的同名文件，不要反复改 Markdown 路径。
- `output/` 目录是默认新稿目录。

**Onboard 例外**：Onboard 是交互式的（需要问用户问题），不受"全自动"约束。Onboard 完成后回到全自动管道。

**辅助功能**（按需加载，不在主管道内）：
- 用户说"重新设置风格" → `读取: {baseDir}/references/onboard.md`
- 用户说"学习我的修改" → `读取: {baseDir}/references/learn-edits.md`
- 用户说"看看文章数据" → `读取: {baseDir}/references/effect-review.md`
- 用户说"诊断配置"/"检查反AI"/"为什么AI检测没过" → 执行以下流程：
  1. `python3 {baseDir}/scripts/diagnose.py --json`
  2. 如果有 fail 或 warn 项 → 直接报告并按优先级给出修复动作；warn 必须修复，不能继续当作通过
  3. 只有全 pass 且 `fail=0 / warn=0 / skip=0` → 继续 LLM 深度分析：
     - 读取 `style.yaml` 的 tone/voice 与 writing_persona，判断是否矛盾
     - 读取 `writing-config.yaml`（如存在），检查是否有 AI 特征参数（emotional_arc: flat、paragraph_rhythm: structured、closing_style: summary）
     - 读取 `history.yaml` 最近 5 篇，检查 persona 使用和 web_search 降级情况
  4. 综合输出自然语言报告 + 按优先级排序的改进建议
- 用户说"更新"/"更新 WeWrite"/"升级" → 在 `{baseDir}` 执行 `git pull origin main`，完成后告知版本变化

---

## 主管道（Step 1-8）

### Step 1: 环境 + 配置

**1a. 环境检查**（静默通过或引导修复）：

```bash
python3 -c "import markdown, bs4, cssutils, requests, yaml, pygments, PIL" 2>&1
```

| 检查项 | 通过 | 不通过 |
|--------|------|--------|
| `config.yaml` 存在 | 静默 | 引导创建，或设 `skip_publish = true` |
| Python 依赖 | 静默 | 提供 `pip install -r requirements.txt` |
| `wechat.appid` + `secret` | 静默 | 设 `skip_publish = true` |
| `image.api_key` | 静默 | 设 `skip_image_gen = true` |

**1a-2. 版本检查**（静默通过或提醒）：

```bash
cd {baseDir} && git fetch origin main --quiet 2>/dev/null
```

比对本地 `{baseDir}/VERSION` 与远程 `git show origin/main:VERSION`：
- 相同 → 静默通过
- 不同 → 提示用户："WeWrite 有新版本可用（当前 X → 最新 Y），说「更新」即可升级。"**不阻断流程**，继续 Step 1b
- git 不可用（无 .git 目录或 fetch 失败）→ 静默跳过

**1b. 加载风格**：

```
检查: {baseDir}/style.yaml
```

- 存在 → 提取 `name`、`topics`、`tone`、`voice`、`blacklist`、`theme_mode`、`theme`、`cover_style`、`author`、`content_style`
- 不存在 → `读取: {baseDir}/references/onboard.md`，完成后回到 Step 1

如果用户直接给了选题 → 跳到 Step 3（仍需框架选择和素材采集，不可跳过）。

---

### Step 2: 选题

**2a. 热点抓取**：

```bash
python3 {baseDir}/scripts/fetch_hotspots.py --limit 30
```

**降级**：脚本报错 → web_search "今日热点 {topics第一个垂类}"

**2b. 历史去重 + SEO**：

```
读取: {baseDir}/history.yaml（不存在则跳过）
```

```bash
python3 {baseDir}/scripts/seo_keywords.py --json {关键词}
```

**降级**：SEO 脚本报错 → LLM 判断

**2c. 生成 10 个选题**：

```
读取: {baseDir}/references/topic-selection.md
```

每个选题含标题、评分、点击率潜力、SEO 友好度、推荐框架。近 7 天已写的关键词降分。

- 自动模式 → 选最高分
- 交互模式 → 展示 10 个，等用户选

---

### Step 3: 框架 + 素材

**3a. 框架选择**：

```
读取: {baseDir}/references/frameworks.md
```

5 套框架（痛点/故事/清单/对比/热点解读），自动选推荐指数最高的。

**3b. 素材采集（关键——决定能否通过 AI 检测）**：

纯 LLM 生成的内容无论技巧多好，底层 token 分布仍是 AI 的。通过检测的文章都建立在真实外部信息源之上。

如果用户直接给了 `x.com` / `twitter.com` 链接，先读取：`{baseDir}/references/x-link-workflow.md`

```
web_search: "{选题关键词} site:36kr.com OR site:mp.weixin.qq.com OR site:zhihu.com"
web_search: "{选题关键词} 数据 报告 2025 2026"
```

采集 5-8 条真实素材（具名来源 + 具体数据/引述/案例）。**禁止编造**。如果来源是 X 帖文，只能把它当作线索和观点起点，**禁止复制粘贴原文**；必须补充外部来源，重写结构和表达，规避版权风险。

**降级**：web_search 无结果或不可用 → 用 LLM 训练数据中可验证的公开信息。但需告知用户："素材采集未能使用 web_search，文章的 AI 检测通过率会降低。建议在编辑锚点处多加入你自己的内容。"

---

### Step 4: 写作

```
读取: {baseDir}/references/writing-guide.md
读取: {baseDir}/references/layout-playbook.md
读取: {baseDir}/playbook.md（如果存在，逐条执行，优先于 writing-guide）
读取: {baseDir}/history.yaml（最近 3 篇的 dimensions 字段）
```

**4a. 维度随机化**：从 writing-guide.md 第 7 层维度池随机激活 2-3 个维度，对比历史去重。

**4b. 加载写作人格**：

```
读取: {baseDir}/personas/{style.yaml 的 writing_persona 字段}.yaml
如果 style.yaml 没有 writing_persona 字段 → 默认 midnight-friend
```

人格文件定义了：语气浓度、数据呈现方式、情绪弧线、段落节奏、不确定性表达模板等。作为 Step 4c 的硬性约束执行。

**优先级**：playbook.md > persona > writing-guide.md。writing-guide 是底线（禁用词等），persona 在此基础上特化风格参数，playbook 是用户个性化的最终覆盖。

**4c-0. 创建文章目录**：
- 根据当前工作标题/选题确定最终工作标题
- 运行：`powershell -ExecutionPolicy Bypass -File {baseDir}/scripts/new_wechat_article.ps1 -Title "{工作标题}" -Author "{style.author}"`
- 后续正文统一写在 `{baseDir}/output/{工作标题}/article.md`；`article-body.template.html` 和 `preview.html` 交给模板脚本自动生成

**4c-1. 选择排版方向**：
- 根据 `references/layout-playbook.md` 为本篇文章先选一个版式方向，再选一个对应的排版主题
- 如果 `style.yaml` 设置 `theme_mode: auto`，`theme` 只是兜底主题；渲染阶段会通过 `scripts/layout_strategy.py` 自动生成 `{article_dir}/generated/layout-plan.json`，并写入 `draft-metadata.json` 的 `theme`、`layout_family`、`layout_variant`、`module_pattern`
- 只有 `style.yaml` 设置 `theme_mode: fixed` 或用户显式要求某个主题时，才视为锁定主题；如果用户要求“风格多样一点/别太重复”，优先避开最近 2 篇文章已经使用过的同一主题家族
- 如果主题拿不准，可在正文定稿后运行 `python3 {baseDir}/toolkit/cli.py gallery {article_dir}/article.md --no-open -o {article_dir}/theme-gallery.html`，对比后再确定最终主题

**4c. 写文章**：
- H1 标题（20-28 字） + H2 结构，1500-2500 字
- 真实素材锚定：Step 3b 的素材分散嵌入各 H2 段落
- **写作人格**：按 4b 加载的人格参数写作（数据呈现方式、个人声音浓度、不确定性表达等）
- 7 层去 AI 痕迹规则在初稿阶段全部生效
- 正文结构不能只是“连续 H2 + 大段正文”；必须按 `references/layout-playbook.md` 至少使用 2 种非纯正文模块，把重点结论、时间线、争议点或金句显式抬出来
- 优先使用 `:::callout`、`:::timeline`、`:::dialogue`、`:::quote`、表格、图位图例来制造节奏，不要把关键内容全塞进原生 `ul/ol/li`
- 不能连续 3 个大段纯正文没有任何节奏变化；不能每个 H2 都复用同一种内部模板
- 2-3 个编辑锚点：`<!-- ✏️ 编辑建议：在这里加一句你自己的经历/看法 -->`
- 可选容器语法：`:::dialogue`、`:::timeline`、`:::callout`、`:::quote`

初稿保存到 `{article_dir}/article.md`

---

### Step 5: SEO + 验证

```
读取: {baseDir}/references/seo-rules.md
```

**5a. SEO**：3 个备选标题 + 摘要（≤54 字）+ 5 标签 + 关键词密度优化

**5b. 去 AI 逐层验证**（writing-guide.md 自检清单，每项必须通过）：

| # | 检查项 | 标准 |
|---|--------|------|
| 0 | 真实信息锚定 | 每个 H2 至少 1 条真实素材，零编造 |
| 1 | 禁用词 | 命中数 = 0 |
| 2 | 词汇温度 | 冷/温/热/野 ≥ 3 种 |
| 3 | 破句 | ≥ 3 处 |
| 4 | 信息密度 | 高密度段后跟低密度段 |
| 5 | 连贯性打破 | ≥ 1 处跑题再拉回 |
| 6 | 情绪弧线 | ≥ 1 高点 + ≥ 1 犹豫 |
| 7 | 维度贯穿 | 激活维度全文可见 |
| 8 | 段落节奏 | 无连续 2 个相近长度段落 |

不通过 → 定向重写该段落。连续 3 次仍不过 → 停止并报告阻塞项，不允许标注跳过后继续。

**5c. 脚本强制验证**：
- 每次 render / publish 前，必须自动运行以下脚本并把结果写入 `{article_dir}/generated/`：
  - `python3 {baseDir}/scripts/humanness_score.py {article_dir}/article.md --json` → `humanness-report.json`
  - `python3 {baseDir}/scripts/diagnose.py --json` → `diagnose-report.json`
  - `powershell -ExecutionPolicy Bypass -File {baseDir}/skill2 paibanyouhua/scripts/project-doctor.ps1 -ArticleDir "{article_dir}"` → `article-doctor-report.json`
  - `python3 {baseDir}/scripts/seo_keywords.py --json "{title}"` → `seo-report.json`
  - `python3 {baseDir}/skill2 paibanyouhua/scripts/run-quality-gates.py --article-dir "{article_dir}" --strict` → `quality-gates.json`
- 上述脚本不是可选项；以后凡是走这个 skill 的默认主链，都必须执行并落报告。
- **零 warning 发布门槛**：`quality-gates.json` 的 `summary.fail`、`summary.warn`、`summary.skip` 必须全部为 0 才能继续；任何 warning 都必须先修复，禁止继续推草稿箱。
- `diagnose-report.json`、`article-doctor-report.json`、`humanness-report.json`、`seo-report.json` 中出现的 warning 也必须反映到 `quality-gates.json`，不得只看最终 HTML 是否能生成。

**5d. 最终稿落盘**：
- 将 SEO 优化和验证后的最终稿覆盖写回 `{article_dir}/article.md`
- 如果最终标题已经明显偏离工作标题，可同步重命名 `article_dir`，使目录名继续对应最终标题的英文语义名

---

### Step 6: 视觉 AI

**无论 `skip_image_gen` 是否为 true** → 都先执行 6a 和 6b。图位、占位图、提示词、正文引用必须同时完成。

```
读取: {baseDir}/references/visual-prompts.md
```

**6a.** 分析文章结构，生成封面 3 组创意 + 内文 3-6 张配图提示词，并保存到 `{article_dir}/generated/image-prompts.md`。
- 为封面和每张内文图分配稳定槽位与目标文件名：封面固定为 `assets/cover-wide.jpg` 和 `assets/cover-square.jpg`，内文固定为 `assets/img-01.jpg`、`assets/img-02.jpg`、`assets/img-03.jpg`……
- 每篇文章必须同时产出两张封面：
  - `assets/cover-wide.jpg`：横版封面，用于公众号草稿箱默认封面
  - `assets/cover-square.jpg`：1:1 方形封面，用于后续分发、卡片位、转发配图或备用视觉物料
- 两张封面必须属于同一个视觉主题和信息主题，但要分别适配比例；不能简单把横版封面粗暴裁成正方形交差。
- `image-prompts.md` 里的每个图项必须写明：槽位编号、目标文件名、插入位置、对应段落、alt 文案、图例说明、用途、正向提示词、负向提示词、后期覆字说明。
- 正文必须同步插入 Markdown 图片引用，并与槽位一一对应。示例：`![配图 1：这里写 alt 文案](img-01.jpg)`。正文里仍可写简短相对路径，模板渲染时会自动映射到 `assets/`。图位是正文结构的一部分，不允许只在提示词里写而不在正文里留位。
- 每张正文图片下方必须紧跟一小行图例说明，作为图下解释，不允许省略；图片引用行和图例说明行之间禁止空行。推荐写法：
  ```markdown
  ![配图 1：这里写 alt 文案](img-01.jpg)
  *图 1：这里用一句话解释这张图在说明什么。*
  ```
- 图例说明必须和该图的 alt 文案、提示词用途保持一致，但比 alt 更像给读者看的自然说明；长度控制在 12-36 个中文字符，简洁、具体、不写空话。
- 图位要放在对应段落之后，和提示词中的插入位置完全一致；`image-prompts.md` 与 `article.md` 必须互相能对上。
- 提示词必须使用中文撰写，输出的是可直接投喂中文生图工具的完整提示词，不是零散关键词。
- **反 PPT 审美硬规则**：image2 / gpt-image-2 能力足够强，提示词必须按“可直接发布的中文商业媒体视觉作品”来写，不能生成“单调背景 + 居中大字 + 几个装饰图标”的敷衍图。每张图必须有具体视觉主体、视觉类型、前景 / 中景 / 背景层次、材质、光线、镜头或视角、空间纵深和审美验收点；标题和标签只能是版式的一部分，不能替代画面主体。
- **每篇视觉必须有变化**：封面和内文图保持同一色调体系，但不能每张都长成深蓝 PPT 信息卡；至少混合 2 种视觉类型，例如杂志级信息图、场景摄影感、3D 静物装置、数据新闻图、编辑部插画、拼贴海报。提示词里必须明确禁止 PPT 模板感、纯色/渐变背景加大字、空背景、大字报、廉价科技光效。
- 只要图中涉及数字、图表、榜单、时间线、标签、结论，必须写入具体数据内容：数值、单位、时间、对比关系、来源名、图表类型、排版位置，禁止写成“若干数据”“一些图表”。
- 只要图中出现文字，必须明确要求：`仅使用简体中文，中文必须准确、完整、清晰可读，禁止乱码、错别字、异体字、繁简混用、无意义符号、拼音代替汉字`。
- 每张图至少包含：用途、对应段落、画面目标、必须出现的数据清单、必须出现的中文文案清单、版式说明、色调/风格、正向提示词、负向提示词；如果担心工具文字能力不稳，再额外给出后期覆字说明。
- **生图额度保护硬规则**：提示词不合格时禁止调用生图 API。每个待生图槽位必须先做“提示词可执行性预检”，确认画面主体、构图比例、主体占比、必须出现/禁止出现元素、中文文字清单、数据清单、版式层级、失败反例都写清楚；否则先重写提示词，不得用 API 试错。
- **提示词必须写反失败约束**：凡是信息图、价格卡、时间线、对比图，正向提示词必须明确写入“这不是抽象背景图/不是渐变壁纸/不是装饰图/不是 PPT 大字背景图”，并用硬约束描述主体占比（如主体占画面 80% 以上）、卡片数量、卡片位置、标题位置、数据行数、每行文字和数字。负向提示词必须点名排除：PPT 模板感、空白背景、纯渐变背景、无卡片、无数据、错误数字、乱码、密集小字、无意义图标。
- **信息图优先少字高确定性**：如果一张图需要精确中文或精确数字，最多保留 2-4 个核心数据块；超过这个数量先拆成多张图或改为正文卡片，不允许把大量小字塞给 image2 赌运气。

**6b.** 先为封面和所有内文图生成本地占位图文件，并保存回 `{article_dir}/assets/`。
- 占位图是默认交付物的一部分，即使没有生图 API 也必须存在。
- 使用稳定文件名创建占位图：`assets/cover-wide.jpg`、`assets/cover-square.jpg`、`assets/img-01.jpg`、`assets/img-02.jpg`……
- 占位图要和对应提示词绑定，至少能让用户在预览里看见版面位置、顺序和图位规模，后续只需直接覆盖同名文件即可替换。
- 可调用：`python3 {baseDir}/scripts/make_placeholder_image.py --output {article_dir}/assets/img-01.jpg --label "IMG 01" --size article`
- 横版封面占位图：`python3 {baseDir}/scripts/make_placeholder_image.py --output {article_dir}/assets/cover-wide.jpg --label "COVER 2.35:1" --size cover`
- 方形封面占位图：`python3 {baseDir}/scripts/make_placeholder_image.py --output {article_dir}/assets/cover-square.jpg --label "COVER 1:1" --size square`

**6c.** 只有在 `skip_image_gen = false` 时才调用 image_gen.py 生成图片，并直接覆盖同名目标文件；不要额外改 Markdown 路径。
- OpenAI-compatible image2 路线已验证可用时，`config.yaml` 的图片段可设为：`image.provider: openai`、`image.model: gpt-image-2`、`image.base_url: https://xlabapi.com/v1`、`image.quality: low|medium|high`、`image.output_format: jpeg`。API key 只能放在本地私密配置或临时环境变量中，禁止写进 `SKILL.md`、文章正文或提示词文件。
- 对 `gpt-image-*` 模型，`toolkit/image_gen.py` 必须按 Image API 的 base64 返回格式处理图片；如果网关返回 URL，也要兼容下载并覆盖同名槽位。
- **API 生图必须使用本 skill 生成的提示词，这是硬约束，不是建议**：调用 image2 / OpenAI-compatible 图片 API 时，必须以 Step 6a 已生成并保存到 `{article_dir}/generated/image-prompts.md` 的对应槽位提示词为准。禁止临场绕过 `image-prompts.md` 手写一段新 prompt 直接调用 API；如果需要改 prompt，先改 `generated/image-prompts.md`，再按文件里的版本调用 API。
- **提示词变更必须先落盘**：如果生成结果不合格，需要优化提示词，必须先更新 `{article_dir}/generated/image-prompts.md` 中对应槽位的正向提示词、负向提示词和验收约束，再用更新后的提示词重新调用 API。API 调用内容必须能在 `image-prompts.md` 中追溯。
- **槽位一一对应**：每次 API 生图前必须确认槽位编号、目标文件名、正文图位、alt 文案、图例说明和 `image-prompts.md` 中的提示词一致；不得用 A 图提示词生成 B 图文件，不得把未记录在提示词文件里的临时创意覆盖正式槽位。
- **禁止批量盲跑**：使用 image2 生图时必须按槽位逐张生成、逐张验收，不能一次性批量生成全部图片后才检查。优先顺序：`cover-wide.jpg` → `cover-square.jpg` → `img-01.jpg` → `img-02.jpg`……每张通过后再进入下一张。
- **单张验收门槛**：生成后必须查看图片文件，按提示词逐项验收：主体是否存在、是否不是抽象背景、文字是否基本可读、关键数字是否出现且未明显错误、图像是否和正文图例一致、是否适合手机端阅读。验收不通过时，只重写该槽位提示词并覆盖该槽位，禁止重跑已经合格的图片。
- **额度节省策略**：同一槽位最多连续重试 2 次；第 1 次失败必须先指出失败原因并改提示词，第 2 次仍失败时保留当前最优图和提示词，向用户说明风险，不得继续无上限消耗额度。除非用户明确要求“继续重试”。
- **不允许用本地排版伪装生图结果**：用户要求 image2 生图时，失败修复必须通过优化 image2 提示词重新生成；本地脚本排字、PIL 合成、截图式替代只能在用户明确同意时使用。

**降级**：生图失败或无 API → 保留 `{article_dir}/generated/image-prompts.md` 和同名占位图作为降级交付物，可以继续生成预览；但这属于 warning，不能算通过，不能推草稿箱，除非用户明确接受降级且本次结果标记为 `DONE_WITH_CONCERNS`。

---

### Step 7: 预检 + 排版 + 发布

**7a. Metadata 预检**（发布前必须通过）：

| 检查项 | 标准 | 不通过时 |
|--------|------|---------|
| H1 标题 | 存在且 5-64 字节 | 自动修正；修不掉则 BLOCKED |
| 摘要 | 存在且 ≤ 120 UTF-8 字节 | converter 自动生成；仍不合格则 BLOCKED |
| 封面图 | `assets/cover-wide.jpg` 与 `assets/cover-square.jpg` 都存在 | 立即补齐；无封面不允许推送 |
| 正文字数 | ≥ 200 字 | 立即补写；内容过短不允许作为 warn 放行 |
| 图片数量 | ≤ 10 张且所有本地图片存在 | 立即修正；缺图或超量不允许发布 |

预检全部通过且 warning 数为 0 后才进入排版。任何 warning 都必须改成 pass，不允许“先发再说”。

**7b. 排版 + 发布**：

**如果 `skip_publish = true`** → 直接走 preview。
- 先读取：`{baseDir}/references/template-workflow.md`，发草稿时一律以这份规则为准。
- `toolkit/cli.py publish` 不再是默认草稿发布入口；默认发布只走 `scripts/publish_wechat_article.ps1`。

```
读取: {baseDir}/references/wechat-constraints.md
读取: {baseDir}/references/layout-playbook.md
```

Converter 自动处理：CJK 加空格、加粗标点外移、列表转 section、外链转脚注、暗黑模式、容器语法。
- 预览和发布都基于 `article.md` 中已经插入好的图位执行，因此占位图和正式图都必须使用正文中的同一路径。
- 草稿箱发布默认使用 `draft-metadata.json` 里的 `cover_image`；未显式指定时默认取 `assets/cover-wide.jpg`，配套方封面保存在 `assets/cover-square.jpg`。
- `scripts/render_wechat_article.ps1` 会自动补跑 `quality-gates`；`scripts/publish_wechat_article.ps1` 会以零容忍严格模式再次执行，出现任何 `fail`、`warn` 或 `skip` 都直接中止发布。
- 发布前再做一次排版验收：开头 4 段内是否已经亮出冲突/判断；全文是否至少有 2 种非纯正文模块；是否存在连续 3 个大段纯正文；图位和图例是否都已经补齐；`layout_diversity` 是否没有重复最近 2 篇的主题/版式/模块序列。任意一项不满足都算 warning，必须修复到 0。
- 如果用户强调“排版别太单调”或当前成稿明显偏平，先额外生成 `{article_dir}/theme-gallery.html` 对比不同主题渲染效果，再决定最终 `--theme`

```bash
# 本地渲染 / 预览
powershell -ExecutionPolicy Bypass -File {baseDir}/scripts/render_wechat_article.ps1 -ArticleDir "{article_dir}"

# 单独查看质量门禁报告
powershell -ExecutionPolicy Bypass -File {baseDir}/scripts/check_wechat_article.ps1 -ArticleDir "{article_dir}"

# 发布到公众号草稿箱
powershell -ExecutionPolicy Bypass -File {baseDir}/scripts/publish_wechat_article.ps1 -ArticleDir "{article_dir}"
```

---

### Step 8: 收尾

**8a. 写入历史**（推送成功或降级都要写，文件不存在则创建）：

```yaml
# → {baseDir}/history.yaml
- date: "{日期}"
  title: "{标题}"
  topic_source: "热点抓取"  # 或 "用户指定"
  topic_keywords: ["{词1}", "{词2}"]
  framework: "{框架}"
  theme: "{本次 theme}"
  theme_mode: "{auto/fixed}"
  layout_family: "{本次 layout_family}"
  layout_variant: "{本次 layout_variant}"
  module_pattern: "{本次 module_pattern}"
  word_count: {字数}
  media_id: "{id}"  # 降级时 null
  writing_persona: "{人格名}"
  dimensions:
    - "{维度}: {选项}"
  stats: null
```

**8b. 回复用户**：

- 最终标题 + 2 备选 + 摘要 + 5 标签 + media_id
- 本次文章目录：`{article_dir}`；其中至少包含 `article.md`、`draft-metadata.json`、`assets/`、`generated/image-prompts.md`、`article-body.template.html`
- 编辑建议："文章有 2-3 个编辑锚点，建议花 3-5 分钟加入你自己的话，效果更好。"
- 飞轮提示："编辑完成后说**'学习我的修改'**，下次初稿会更接近你的风格。"

**8c. 后续操作**：

| 用户说 | 动作 |
|--------|------|
| 润色/缩写/扩写/换语气 | 编辑文章 |
| 封面换暖色调 | 重新生图 |
| 用框架 B 重写 | 回到 Step 4 |
| 换一个选题 | 回到 Step 2c |
| 看看有什么主题 | `python3 {baseDir}/toolkit/cli.py gallery` |
| 换成 XX 主题 | 重新渲染 |
| 看看文章数据 | `读取: {baseDir}/references/effect-review.md` |
| 学习我的修改 | `读取: {baseDir}/references/learn-edits.md` |
| 做一个小绿书/图片帖 | `python3 {baseDir}/toolkit/cli.py image-post img1.jpg img2.jpg -t "标题"` |
| 诊断配置 / 检查反AI / 为什么AI检测没过 | `python3 {baseDir}/scripts/diagnose.py --json` + LLM 交叉分析 |

---

## 错误处理

| 步骤 | 降级 |
|------|------|
| 环境检查 | 逐项引导，设降级标记；降级产物只能 DONE_WITH_CONCERNS，不能 DONE |
| 热点抓取 | web_search 替代；若素材不足导致 warning，必须补足后继续 |
| 选题为空 | 请用户手动给选题 |
| SEO 脚本 | LLM 判断仅作临时分析；最终 `seo-report.json` 不得有 warn |
| 素材采集（web_search） | LLM 训练数据中可验证的公开信息；必须明确标注素材不足，不能作为发布通过 |
| 维度随机化 | history 空时跳过去重；不得产生 `quality-gates` warning |
| Persona 文件不存在 | 先修复 persona 配置；不得静默回退后继续通过 |
| 去 AI 验证 | 3 次重写不过则 BLOCKED，不允许跳过该项 |
| 生图失败 | 保留提示词和占位图仅作降级交付；发布通过仍要求 warn=0 |
| 推送失败 | 本地 HTML 可作为降级产物，但不能 DONE |
| 历史写入 | 写入失败必须报告并重试；仍失败则 DONE_WITH_CONCERNS |
| 效果数据 | 告知等 24h |
| Playbook 不存在 | 先生成或说明阻塞；不得把缺失 playbook 当作通过状态 |
