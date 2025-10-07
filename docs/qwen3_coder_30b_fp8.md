# Qwen3-Coder-30B-A3B-Instruct-FP8 Reference

Source: [Hugging Face – Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8)

## Model Snapshot
- **Type**: decoder-only Mixture-of-Experts causal LM (pretrained + instruction tuned).
- **Active Parameters**: 30.5B total, ~3.3B active per token.
- **Layers**: 48; GQA (32 query heads, 4 KV heads).
- **Experts**: 128 total, 8 active.
- **Context**: native 262,144 tokens; extendable to 1M with Yarn.
- **Quantization**: fine-grained FP8 (block size 128). Good fit for single H200.
- **Thinking**: explicitly non-thinking – does not emit `<think></think>` blocks. No need to toggle `enable_thinking` flags.

## Capabilities & Positioning
- Optimized for **agentic coding**, browser/tool use, repository-scale reasoning.
- High performance on Qwen’s agentic benchmarks; the 30B FP8 variant is the “streamlined” release for resource-constrained deployments.
- Designed to interoperate with tool/function calling; same OpenAI-compatible schema as other Qwen agents.

## Inference Requirements
- `transformers >= 4.51.0` (older versions raise `KeyError: 'qwen3_moe'`).
- FP8 checkpoint works with `transformers`, `vllm`, `sglang`. For multi-GPU inference under transformers, set `CUDA_LAUNCH_BLOCKING=1` (known issue with FG-FP8).
- Example vLLM launch:
  ```bash
  python -m vllm.entrypoints.openai.api_server \
      --model Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8 \
      --tensor-parallel-size 1 \
      --enable-auto-tool-choice \
      --tool-call-parser hermes \
      --reasoning-parser qwen3 \
      --host 0.0.0.0 \
      --port 18010
  ```

## Sampling Recommendations (from Qwen)
- `temperature = 0.7`
- `top_p = 0.8`
- `top_k = 20`
- `repetition_penalty = 1.05`
- `max_new_tokens = 65536` for long coding outputs (we can dial these down for deterministic Nova workflows).

## Quickstart Snippet (transformers)
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)

prompt = "Write a quick sort algorithm."
messages = [{"role": "user", "content": prompt}]
text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer([text], return_tensors="pt").to(model.device)

output_ids = model.generate(**inputs, max_new_tokens=65536)[0][inputs.input_ids.size(-1):]
print(tokenizer.decode(output_ids, skip_special_tokens=True))
```

## Function/Tool Calling
Example from README (OpenAI-style client):
```python
client = OpenAI(base_url='http://localhost:8000/v1', api_key='EMPTY')
messages = [{'role': 'user', 'content': 'square the number 1024'}]
tools = [{
    "type": "function",
    "function": {
        "name": "square_the_number",
        "description": "output the square of the number.",
        "parameters": {
            "type": "object",
            "required": ["input_num"],
            "properties": {
                "input_num": {"type": "number", "description": "number to square"}
            }
        }
    }
}]
completion = client.chat.completions.create(
    model="Qwen3-Coder-30B-A3B-Instruct-FP8",
    messages=messages,
    tools=tools,
    max_tokens=65536,
)
```
Hermes parser (or vLLM’s tool-choice support) is required so the model’s tool decisions are parsed correctly.

## Deployment Notes
- FP8 quantization is fine-grained; verify your inference stack respects the block size (128).
- For large-context workloads, watch GPU memory and CPU RAM (256K tokens native still uses considerable RAM for KV cache).
- Because it’s non-thinking, responses arrive as final answers or tool calls—no need to strip `<think>` content.

## References
- [Hugging Face model card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8)
- [Qwen3-Coder blog announcement](https://qwen.ai/research)
- [Qwen3 documentation](https://qwen.readthedocs.io/en/latest/)
