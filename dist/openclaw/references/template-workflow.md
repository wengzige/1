# 模板草稿链默认规则

这份规则定义 WeWrite 默认的模板草稿链。只要任务是“写公众号 / 推草稿 / 微信排版 / 推送草稿箱”，一律优先执行这份规则。

## 目录与源文件

- 新稿件默认工作区是 `{skill_dir}/output/<文章标题>/`。
- 目录统一通过 `powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/new_wechat_article.ps1 -Title "<标题>"` 创建。
- `article.md` 是唯一正文源文件。除非用户明确要求，不要再手工维护 `article-body.template.html` 和 `preview.html`。
- `article-body.template.html`、`preview.html`、`generated/output.html`、`generated/draft.json` 都是渲染脚本生成的交付物。

## 图片与提示词

- 所有封面和正文配图统一放在 `assets/`。
- 封面默认使用 `assets/cover-wide.jpg`，方形封面使用 `assets/cover-square.jpg`，正文图统一使用 `assets/img-01.jpg` 这种稳定槽位名。
- 正文 Markdown 里可以继续写 `![配图 1](img-01.jpg)`，渲染脚本会自动映射到 `assets/img-01.jpg` 并替换成 `{{IMAGE:assets/img-01.jpg}}`。
- 提示词统一写到 `generated/image-prompts.md`。

## 渲染与发布

- 本地渲染 / 预览统一使用 `powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/render_wechat_article.ps1 -ArticleDir "<文章目录>"`。
- 推草稿统一使用 `powershell -ExecutionPolicy Bypass -File {skill_dir}/scripts/publish_wechat_article.ps1 -ArticleDir "<文章目录>"`。
- `toolkit/cli.py publish` 不再作为默认草稿入口，只保留给旧流程或主题画廊辅助命令。

## 强制预检

发布前必须拦截以下风险：

- HTML 注释
- 原生 `ul / ol / li` 在关键信息区
- `???` 连续问号串
- replacement character `�`
- mojibake 字节汤（如 `åäç` 这类断裂高位字节）

只要命中任意一项，就直接拒绝发稿，而不是“带病发布”。

