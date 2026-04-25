# 风格配置说明

## 快速开始

1. 复制 `style.example.yaml` 为 `style.yaml`
2. 修改配置项
3. 对 Agent 说：「写一篇公众号文章」

也可以跳过手动配置——首次使用时 Agent 会通过对话引导你自动生成 `style.yaml`。

## 必填字段

```yaml
name: "客户名称"
industry: "行业"
topics:                    # 内容方向（列表）
  - "方向1"
  - "方向2"
tone: "写作风格描述"
theme_mode: "auto"          # auto 自动轮换；fixed 固定使用 theme
theme: "professional-clean" # auto 模式下作为兜底主题
```

## 可选字段

```yaml
target_audience: "目标受众描述"
voice: "写作人称和语感"
writing_persona: "midnight-friend"  # 写作人格（见下方说明）
word_count: "1500-2500"
blacklist:
  words: ["禁忌词1", "禁忌词2"]
  topics: ["禁忌话题1"]
reference_accounts: ["参考账号1", "参考账号2"]
cover_style: "封面风格描述"
cover_template: "/path/to/cover.png"  # 设置后跳过 AI 生成封面
author: "署名"
```

### 排版轮换

如果你觉得每篇文章版式太像，保持：

```yaml
theme_mode: "auto"
theme: "professional-clean"
```

渲染时会根据文章内容、最近文章的主题/版式记录自动选择新的 `theme`、`layout_family` 和容器样式。只有明确想固定一种视觉时，才改成：

```yaml
theme_mode: "fixed"
theme: "sspai"
```

## 可用排版主题

运行 `python3 toolkit/cli.py gallery` 可在浏览器中预览所有主题的实际效果。

| 主题 | 说明 |
|------|------|
| professional-clean | 专业简洁（默认，适合大部分商业内容） |
| tech-modern | 科技风（蓝紫渐变，适合技术/产品类） |
| warm-editorial | 暖色编辑风（适合生活/文化类） |
| minimal | 极简黑白（适合文学/严肃内容） |
| bytedance | 字节风（品牌蓝，现代大间距） |
| sspai | 少数派风（暖白底，红色点缀，清爽文艺） |
| newspaper | 报纸风（米黄底，深棕文字，衬线感） |
| bauhaus | 包豪斯（黑白为主，红蓝黄色块点缀） |
| ink | 水墨风（宣纸底，中文衬线，留白多） |
| midnight | 午夜深色（深蓝黑底，蓝色高亮） |
| bold-green | 大胆绿（森林绿主色，适合环保/健康） |
| bold-navy | 大胆藏青（藏青主色，适合金融/商务） |
| elegant-rose | 优雅玫瑰（浅粉底，玫瑰点缀，适合女性/生活） |
| minimal-gold | 极简金（金色细线点缀，奢华但克制） |
| focus-red | 聚焦红（中国红标题，适合新闻/评论） |
| github | GitHub 风（蓝色链接，等宽代码块，开发者友好） |

## 排版选择建议

如果你不想每次都用同一种气质，可以按内容类型选主题：

- 行业分析、商业热点：`professional-clean`、`bytedance`、`github`
- AI、科技、未来趋势：`tech-modern`、`midnight`、`bauhaus`
- 评论、观察、编辑部气质：`sspai`、`warm-editorial`、`newspaper`
- 强观点、快评、结论感强：`focus-red`、`bold-navy`、`bold-green`
- 留白克制、文化品牌：`minimal`、`minimal-gold`、`ink`
- 审美、生活方式、女性向：`elegant-rose`、`warm-editorial`

如果用户明确说“风格多样一点”“别太单调”，优先不要连续复用最近一篇文章的同一主题家族。
