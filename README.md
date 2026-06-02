# CCSwitch ImageGen Fallback

Codex App 使用第三方中转 provider 时的图片生成 fallback。

官方 provider 仍走 Codex 内置 `image_gen`；第三方中转 provider 走本工具，用 raw HTTP 调图片接口，绕过部分中转站对 SDK 图片请求的拦截。

## 你可能是因为这些问题找到这里

- Codex App 聊天已经切到第三方中转，但生图还是失败。
- 直接调用 Codex 内置 `image_gen` 时遇到 `Your request was blocked`。
- 中转站文字模型可用，但图片生成、图生图或 mask 编辑不稳定。
- `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`gpt-image-2` 配好后，OpenAI SDK 仍然不能正常生图。
- 想让 Codex 自动判断官方 provider / 第三方中转 provider，不想每次手动说明“走中转”。

## 安装

```bash
mkdir -p ~/.codex/bin
cp ccswitch-imagegen ~/.codex/bin/ccswitch-imagegen
cp ccswitch-image-gen.py ~/.codex/bin/ccswitch-image-gen.py
chmod +x ~/.codex/bin/ccswitch-imagegen ~/.codex/bin/ccswitch-image-gen.py
```

把 `AGENTS.snippet.md` 追加到：

```text
~/.codex/AGENTS.md
```

检查是否安装成功：

```bash
~/.codex/bin/ccswitch-imagegen --help
```

## 配置

如果你用 CCSwitch App 管理 Codex provider，通常不用额外配置。脚本会读取当前 Codex provider 的 key 和 `base_url`。

不用 CCSwitch 时，手动设置：

```bash
export OPENAI_API_KEY="你的中转站 key"
export OPENAI_BASE_URL="https://你的中转站域名/v1"
```

如果要让 Codex App 这类 macOS GUI 应用也读到：

```bash
launchctl setenv OPENAI_API_KEY "你的中转站 key"
launchctl setenv OPENAI_BASE_URL "https://你的中转站域名/v1"
```

不要把 API key 发到聊天里。

## 在 Codex App 里用

配置好后，直接正常说生图需求即可：

```text
生成一张公众号封面图，主题是 AI 工具效率提升
```

Codex 会自动判断当前 provider：

- 官方：内置 `image_gen`
- 中转：`ccswitch-imagegen`

## 终端用法

文本生成图片：

```bash
cat > prompt.txt <<'EOF'
生成一张竖版中文科技海报。
主标题：中转站生图成功
风格：高级、干净、专业。
不要水印，不要乱码。
EOF

~/.codex/bin/ccswitch-imagegen \
  --prompt-file prompt.txt \
  --output output.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

根据图片生成 / 编辑图片：

```bash
~/.codex/bin/ccswitch-imagegen \
  --prompt-file edit-prompt.txt \
  --image input.png \
  --output edited.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

多张参考图可以重复传 `--image`；局部编辑可以加 `--mask mask.png`，前提是中转站支持。

中文、长提示词、包含标点或换行的提示词，建议始终写进 `--prompt-file`。

## 出问题时

先看命令输出里的 HTTP 状态和错误正文。

常见原因：

- API key 或 `base_url` 没配好
- 中转站不支持 `/images/edits`
- 中转站不支持多图或 mask
- 图片过大、格式不支持，或模型名不支持图片输入

这个工具不替代 CCSwitch，也不替代官方 `image_gen`。它只负责第三方中转模式下的图片生成 fallback。
