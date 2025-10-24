# Qwen3 Interactive CLI - 262K Context Window 🚀

A comprehensive command-line interface for interacting with Qwen3-30B-A3B-Thinking server featuring maximum 262,144 token context window and 40+ built-in tools.

## 🌟 Features

- **🔥 Maximum Context**: 262,144 tokens (262K) - Native capability
- **🤖 AI-Powered**: Built on Qwen3-30B-A3B-Thinking with advanced reasoning
- **🛠️ 40+ Tools**: File operations, system monitoring, network tools, AI assistance
- **💬 Conversational**: Natural chat interface with memory and context
- **📁 File Management**: Read, write, search, and analyze files
- **🖥️ System Monitoring**: GPU status, processes, network, disk usage
- **🌐 Network Tools**: HTTP requests, ping, WHOIS lookups
- **🔍 AI Analysis**: Intelligent file analysis, summarization, code generation
- **💾 Session Persistence**: Save and restore conversations

## 🚀 Quick Start

### 1. Start the Server
```bash
./start_qwen3_working.sh
```

### 2. Launch the CLI
```bash
python3 qwen3_interactive_cli.py
```

## 📋 Command Categories

### 💬 Conversation Commands
```
hi, hello                 - Start conversation
clear                     - Clear conversation history
history                   - Show conversation history
save                      - Save current session
context                   - Show context usage info
```

### 📁 File Tools
```
/read <file>              - Read a file
/write <file> <content>   - Write content to file
/list <dir>               - List directory contents
/search <dir> <pattern>   - Search for files/patterns
```

### 🖥️ System Tools
```
/status                   - Show server and system status
/gpu                      - Show GPU information
/ps                       - Show running processes
/net                      - Show network status
```

### 🌐 Network Tools
```
/curl <url>               - Make HTTP request
/ping <host>              - Ping a host
```

### 🎯 AI Tools
```
/analyze <file>           - AI analysis of file
/summary <text>           - Summarize text
/code <language> <task>   - Generate code
/translate <lang> <text>  - Translate text
```

### ⚙️ Settings
```
/model                    - Show current model info
```

## 🎯 Usage Examples

### Basic Conversation
```
💭 You: Hello! Can you help me understand quantum computing?
🤖 Assistant: [Detailed explanation about quantum computing]
```

### File Operations
```
💭 You: /read config.json
📄 Contents of config.json:
{
  "model": "Qwen3-30B-A3B-Thinking",
  "context": 262144
}
```

### System Monitoring
```
💭 You: /status
🖥️ System Status:
✅ Qwen3 Server: RUNNING
   Model: Qwen3-30B-A3B-Thinking
   Max Context: 262,144 tokens 🔥
```

### AI-Powered Analysis
```
💭 You: /analyze README.md
🤖 AI Analysis of README.md:
This is a comprehensive README for a Qwen3 project with...
[Detailed AI analysis]
```

## 🔧 Advanced Features

### Context Management
- **262,144 Token Window**: Handle extremely long conversations
- **Smart Truncation**: Automatically manages context when needed
- **Session Persistence**: Save and restore conversations

### Streaming Responses
- Real-time streaming of AI responses
- Natural conversation flow
- Immediate feedback

## 📊 Server Information

- **Model**: Qwen3-30B-A3B-Thinking (FP8)
- **Architecture**: Mixture of Experts (MoE)
- **Context Window**: 262,144 tokens
- **Quantization**: FP8 for efficiency
- **API**: OpenAI-compatible

## 🛠️ Installation Requirements

- Python 3.8+
- OpenAI Python package
- Requests library
- NVIDIA GPU with CUDA (for server)
- Qwen3 server running on port 8000

## 📝 Session Management

- Conversations are automatically saved to `qwen3_session.json`
- Use `save` command to manually save
- Use `clear` to start fresh
- Use `history` to review past conversations

## 🚪 Exiting

Type any of the following to exit:
- `quit`
- `exit`
- `/q`

## 🆘 Troubleshooting

### Server Not Running
```bash
❌ Qwen3 server is not running!
💡 Please start the server first with: ./start_qwen3_working.sh
```

### Connection Issues
```bash
# Check server status
curl http://localhost:8000/v1/models

# Restart server if needed
./start_qwen3_working.sh
```

## 🌟 Key Advantages

- **Massive Context**: 262K tokens enable book-length conversations
- **AI-Powered Tools**: Intelligent assistance for every task
- **Unified Interface**: One tool for files, system, and AI interaction
- **Streaming Chat**: Real-time conversation experience
- **Session Persistence**: Never lose your conversation state

---

**🚀 Experience the power of 262K token context with Qwen3-30B-A3B-Thinking!**