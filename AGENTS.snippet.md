## Official / Relay Image Generation Routing

When the user asks Codex to generate or edit an image, first detect whether the current Codex provider is official OpenAI or a third-party relay.

Detection:

1. If `~/.cc-switch/cc-switch.db` exists, prefer the current Codex provider recorded by CCSwitch.
2. If the current CCSwitch Codex provider is official, treat it as official mode.
3. If the current CCSwitch Codex provider is non-official, treat it as relay mode.
4. If CCSwitch data is unavailable, read `~/.codex/config.toml`.
5. If root `model_provider` points to a custom provider and that provider has a non-official `base_url`, treat it as relay mode.
6. If `model_provider` is missing, `openai`, or the active provider is the official OpenAI endpoint, treat it as official mode.

Relay mode:

1. Use the raw HTTP fallback command instead of assuming the OpenAI SDK works with the relay image endpoint.
2. Write long or non-ASCII prompts to a prompt file and call:

```bash
~/.codex/bin/ccswitch-imagegen \
  --prompt-file <prompt.txt> \
  --output <output.png> \
  --model gpt-image-2 \
  --size 1024x1536 \
  --quality high
```

3. Save final deliverables under the current workspace `outputs/` directory.
4. Do not ask the user to paste API keys in chat.

Official mode:

Use the normal built-in `image_gen` path.


中转图片编辑补充：如果用户提供输入图、参考图或要求根据图片生成/编辑图片，使用 `/Users/anger/.codex/bin/ccswitch-imagegen --prompt-file <prompt.txt> --image <input.png> --output <output.png> --model gpt-image-2`。多图重复传 `--image`，局部编辑可传 `--mask <mask.png>`。
