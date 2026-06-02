# CCSwitch ImageGen Fallback

Codex App 使用 CCSwitch 或第三方中转 provider 时的图片生成 fallback。它绕过部分中转站对 OpenAI SDK 图片接口的拦截，直接用 raw HTTP 调用 `gpt-image-2`、`/images/generations` 和 `/images/edits`。

English keywords: Codex image generation relay fallback, CCSwitch imagegen, OpenAI compatible relay image API, `gpt-image-2`, `Your request was blocked`, `OPENAI_BASE_URL`.

## 你可能是因为这些问题找到这里

- Codex App 聊天已经切到第三方中转，但生图还是失败。
- 直接调用 Codex 内置 `image_gen` 时遇到 `Your request was blocked`。
- 中转站文字模型可用，但图片生成、图生图或 mask 编辑不稳定。
- `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`gpt-image-2` 配好后，OpenAI SDK 仍然不能正常生图。
- 想让 Codex 自动判断官方 provider / 第三方中转 provider，不想每次手动说明“走中转”。

配置完成后，你在 Codex App 里可以像平常一样直接说：

```text
生成一张中文海报
```

或：

```text
调用 imagegen 做一张产品宣传图
```

Codex 会自己判断当前用的是官方还是中转：

- 官方 provider：使用 Codex 内置 `image_gen`
- 第三方中转 provider：使用本工具的 raw HTTP fallback

## 快速开始

```bash
mkdir -p ~/.codex/bin
cp ccswitch-imagegen ~/.codex/bin/ccswitch-imagegen
cp ccswitch-image-gen.py ~/.codex/bin/ccswitch-image-gen.py
chmod +x ~/.codex/bin/ccswitch-imagegen ~/.codex/bin/ccswitch-image-gen.py
```

然后把 `AGENTS.snippet.md` 里的内容复制追加到：

```text
~/.codex/AGENTS.md
```

如果你使用 CCSwitch App 管理 Codex provider，切到非官方 Codex provider 后，本工具会优先从 `~/.cc-switch/cc-switch.db` 读取当前 provider 的 API key 和 `base_url`。如果不用 CCSwitch，也可以手动设置 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL`。

验证安装：

```bash
~/.codex/bin/ccswitch-imagegen --help
```

## 原理

简单说：**聊天和生图不是同一条路。**

Codex 主对话模型和图片生成不是同一个接口。

主对话通常走：

```text
/responses
```

图片生成走：

```text
/images/generations
```

CCSwitch 或其他 provider 切换工具通常负责切换 Codex 主对话 provider。也就是说，它主要影响 Codex 聊天请求。

但 Codex 内置 `image_gen` 不一定会自动跟随第三方 `base_url`。

另外，有些中转站虽然兼容 OpenAI API，但不完整兼容 OpenAI SDK 的图片请求，可能出现：

```text
Your request was blocked
```

本工具的做法是：不用 SDK，直接请求图片接口：

```text
POST <base_url>/images/generations
```

所以在中转模式下，它通常能更稳定地调用 `gpt-image-2`。

如果以前没有遇到这个问题，常见原因是：旧版本 Codex 或旧工作流里，图片生成可能仍然走官方内置 `image_gen`；而新版 Codex 更明确地区分主对话 provider、工具调用和图片接口。切换主模型 provider 不等于图片生成接口也自动切换到同一个中转站。

## 安装

下载后，在这个工具目录里打开终端，把两个脚本安装到 `~/.codex/bin`：

```bash
mkdir -p ~/.codex/bin
cp ccswitch-imagegen ~/.codex/bin/ccswitch-imagegen
cp ccswitch-image-gen.py ~/.codex/bin/ccswitch-image-gen.py
chmod +x ~/.codex/bin/ccswitch-imagegen ~/.codex/bin/ccswitch-image-gen.py
```

如果希望终端里可以直接输入 `ccswitch-imagegen`，把 `~/.codex/bin` 加入 PATH：

```bash
export PATH="$HOME/.codex/bin:$PATH"
```

如果希望永久生效，把这一行加入 shell 配置文件，例如：

```bash
~/.zshrc
```

## 配置 Codex 自动路由

把 `AGENTS.snippet.md` 里的内容复制追加到：

```text
~/.codex/AGENTS.md
```

这样 Codex 收到生图请求时，会自动判断当前 provider：

- 当前是官方 provider：走内置 `image_gen`
- 当前是第三方中转 provider：走 `ccswitch-imagegen`

用户不需要额外说明“官方”或“中转”。

## API key 和 base_url

本工具需要 API key 和中转站地址。

如果你使用 CCSwitch App 管理 Codex provider，本工具会优先尝试从 CCSwitch 本地数据库读取当前 Codex provider 的 key 和地址。这样通常不需要手动设置环境变量。

如果没有使用 CCSwitch，或希望临时覆盖当前配置，可以使用环境变量。

### 推荐方式：使用 CCSwitch App

在 CCSwitch App 里切换到你要用的 Codex 中转 provider 即可。

`ccswitch-imagegen` 会自动读取：

```text
~/.cc-switch/cc-switch.db
```

并找到当前 Codex provider 的：

```text
OPENAI_API_KEY
base_url
```

脚本只会在本机运行时读取这些信息，不会打印 API key。

### 备用方式：终端临时设置

如果你不用 CCSwitch App，或者想临时指定某个中转站，可以在终端里这样设置。只对当前终端窗口生效：

```bash
export OPENAI_API_KEY="你的中转站 key"
export OPENAI_BASE_URL="https://你的中转站域名/v1"
```

### 备用方式：macOS GUI 持久化设置

如果不用 CCSwitch App，并且希望 Codex App 这类 GUI 应用也能读取环境变量：

```bash
launchctl setenv OPENAI_API_KEY "你的中转站 key"
launchctl setenv OPENAI_BASE_URL "https://你的中转站域名/v1"
```

设置后，完全退出 Codex App，再重新打开。

检查：

```bash
test -n "$(launchctl getenv OPENAI_API_KEY)" && echo "API key 已设置" || echo "API key 缺失"
launchctl getenv OPENAI_BASE_URL
```

不要把 API key 发到聊天里。

## 配置读取顺序

`ccswitch-imagegen` 会按顺序读取配置：

1. 当前进程的 `OPENAI_API_KEY` / `OPENAI_BASE_URL`
2. CCSwitch 当前 Codex provider：`~/.cc-switch/cc-switch.db`
3. `launchctl getenv OPENAI_API_KEY` / `launchctl getenv OPENAI_BASE_URL`
4. `~/.codex/config.toml` 当前 active provider 的 `base_url`

因此脚本不绑定任何固定中转站，也不要求每次切换 provider 后手动改 `OPENAI_BASE_URL`。

## 切换 provider 后是否要重新设置环境变量

通常不需要每次都重新设置 `OPENAI_BASE_URL`。

原因是：如果没有显式设置 `OPENAI_BASE_URL`，脚本会自动读取当前 `~/.codex/config.toml` active provider 的 `base_url`。也就是说，切换工具把 Codex provider 切到哪个中转站，脚本就会尝试读取那个 provider 的地址。

但 `OPENAI_API_KEY` 不一样。脚本不会从 Codex 官方登录文件里读取 key，因为那会有安全风险。

如果你使用 CCSwitch App，并且 key 已经保存在 CCSwitch 当前 provider 里，通常不需要额外设置 `OPENAI_API_KEY`。

如果你不用 CCSwitch App，或者 CCSwitch 数据读取失败，可以手动设置一次：

```bash
launchctl setenv OPENAI_API_KEY "你的中转站 key"
```

如果你在多个中转站或多个账号之间切换，并且它们使用不同 key，只要这些 key 都由 CCSwitch App 管理，脚本会跟随当前 provider 自动读取。否则才需要手动更新环境变量。

## 终端使用

### 文本生成图片

先创建提示词文件。建议把中文和长提示词都放进文件里：

```bash
cat > prompt.txt <<'EOF'
生成一张竖版中文科技海报。
主标题：中转站生图成功
风格：高级、干净、专业、现代科技感。
要求：中文文字清晰可读，居中排版，不要乱码，不要水印。
EOF
```

然后生成图片：

```bash
ccswitch-imagegen \
  --prompt-file prompt.txt \
  --output output.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

如果没有配置 PATH，用完整路径：

```bash
~/.codex/bin/ccswitch-imagegen \
  --prompt-file prompt.txt \
  --output output.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

### 根据图片生成图片 / 图片编辑

准备一张输入图，例如：

```text
input.png
```

再写一个提示词文件：

```bash
cat > edit-prompt.txt <<'EOF'
基于输入图片重新生成一张高级产品海报。
保持主体特征和大致构图，提升光影、材质和商业摄影质感。
不要添加水印，不要乱码。
EOF
```

调用：

```bash
ccswitch-imagegen \
  --prompt-file edit-prompt.txt \
  --image input.png \
  --output edited.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

如果有多张参考图，可以重复传 `--image`：

```bash
ccswitch-imagegen \
  --prompt-file edit-prompt.txt \
  --image subject.png \
  --image style-reference.png \
  --output edited.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

如果需要局部编辑，并且中转站支持 mask，可以传 PNG mask：

```bash
ccswitch-imagegen \
  --prompt-file edit-prompt.txt \
  --image input.png \
  --mask mask.png \
  --output edited.png \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

只要命令里有 `--image`，脚本就会自动改用：

```text
POST <base_url>/images/edits
```

## 参数

```text
--prompt-file
提示词文件路径。必填。

--output
输出图片路径。必填。

--model
图片模型。默认建议 gpt-image-2。

--size
图片尺寸，例如 1024x1024、1536x1024、1024x1536。

--quality
质量参数，例如 low、medium、high、auto。

--image
输入图或参考图路径。可重复传入。只要传了 --image，就会走图片编辑接口。

--mask
可选 PNG 蒙版。用于局部编辑，是否可用取决于中转站是否支持。
```

中文、长提示词、包含标点或换行的提示词建议始终写入 `--prompt-file`，不要直接放进命令行。

## 在 Codex App 中使用

安装脚本并配置 `AGENTS.snippet.md` 后，直接在 Codex App 里提出生图需求即可。

示例：

```text
生成一张公众号封面图，主题是 AI 工具效率提升
```

Codex 会根据当前配置自动路由：

- 官方模式：内置 `image_gen`
- 中转模式：`ccswitch-imagegen`

## 当前支持范围

当前版本支持：

```text
文本生成图片
根据图片生成图片
基础图片编辑
多张参考图
mask 局部编辑
```

对应关系：

```text
prompt -> image
prompt + image -> image
prompt + image + mask -> image
```

注意：图生图、mask、多图参考都依赖中转站是否支持 `/images/edits`。不同中转站兼容程度不一样，所以如果失败，要看具体 HTTP 错误信息。

官方模式下，Codex 内置 `image_gen` 仍然负责官方生图和编辑。中转模式下，本工具会优先尝试 raw HTTP fallback。

## 常见问题

### OPENAI_API_KEY is missing

没有设置 API key。

解决：

```bash
export OPENAI_API_KEY="你的中转站 key"
```

或：

```bash
launchctl setenv OPENAI_API_KEY "你的中转站 key"
```

### OPENAI_BASE_URL is missing

脚本没有找到中转站地址。

解决方式任选一个：

```bash
export OPENAI_BASE_URL="https://你的中转站域名/v1"
```

或：

```bash
launchctl setenv OPENAI_BASE_URL "https://你的中转站域名/v1"
```

也可以确认 `~/.codex/config.toml` 当前 active provider 是否包含：

```toml
base_url = "https://你的中转站域名/v1"
```

### OpenAI SDK 能不能直接用？

不一定。

部分中转站会拦截或不兼容 SDK 图片请求。本工具使用 raw HTTP，是为了绕开这类兼容性问题。

### 这会替代 CCSwitch 吗？

不会。

CCSwitch 或其他切换工具仍然负责 provider 切换。本工具只负责中转模式下的图片生成 fallback。

### 根据图片生成图片失败怎么办？

不同中转站对 `/images/edits`、多图输入、mask 的兼容程度不同。

如果失败，先看 HTTP 状态和错误正文。常见原因：

```text
中转站不支持 /images/edits
中转站只支持单图，不支持多图
中转站不支持 mask
模型名不支持图片输入
上传图片过大或格式不支持
```

这种情况下可以：

1. 先只传一张 `--image` 测试。
2. 去掉 `--mask` 测试。
3. 换成中转站明确支持的图片模型。
4. 切回官方 provider，用 Codex 内置 `image_gen`。

### 这会替代官方 image_gen 吗？

不会。

官方模式仍然使用 Codex 内置 `image_gen`。只有当前 provider 是第三方中转时，才使用本工具。
