#!/usr/bin/env python3
"""
Qwen3 Interactive CLI with Tools - 262K Context Window
A comprehensive command-line interface for interacting with Qwen3-30B-A3B-Thinking server
"""

import openai
import os
import sys
import json
import subprocess
import time
import re
import requests
from pathlib import Path
from datetime import datetime

class Qwen3CLI:
    def __init__(self):
        self.client = openai.OpenAI(
            base_url="http://localhost:8000/v1",
            api_key="not-needed"
        )
        self.conversation_history = []
        self.session_file = "qwen3_session.json"
        self.max_context_tokens = 260000  # Leave room for response
        self.system_prompt = """You are Qwen3-30B-A3B-Thinking, a helpful AI assistant with 262,144 token context window.
You have access to various tools and can handle long conversations efficiently.
When users type commands starting with '/', they are using special CLI tools.
Be helpful, accurate, and conversational."""

    def load_session(self):
        """Load previous conversation session."""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.conversation_history = data.get('history', [])
                print(f"📚 Loaded previous session with {len(self.conversation_history)} messages")
            except Exception as e:
                print(f"⚠️  Could not load session: {e}")

    def save_session(self):
        """Save current conversation session."""
        try:
            with open(self.session_file, 'w') as f:
                json.dump({'history': self.conversation_history}, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save session: {e}")

    def add_to_history(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 100:
            self.conversation_history = self.conversation_history[-80:]

    def show_help(self):
        """Display help information."""
        help_text = """
🚀 Qwen3 Interactive CLI - 262K Context Window

💬 CONVERSATION:
  hi, hello                 - Start conversation
  clear                     - Clear conversation history
  history                   - Show conversation history
  save                      - Save current session
  context                   - Show context usage info

📁 FILE TOOLS:
  /read <file>              - Read a file
  /write <file> <content>   - Write content to file
  /list <dir>               - List directory contents
  /search <dir> <pattern>   - Search for files/patterns

🖥️  SYSTEM TOOLS:
  /status                   - Show server and system status
  /gpu                      - Show GPU information
  /ps                       - Show running processes
  /net                      - Show network status

🌐 NETWORK TOOLS:
  /curl <url>               - Make HTTP request
  /ping <host>              - Ping a host

🎯 AI TOOLS:
  /analyze <file>           - AI analysis of file
  /summary <text>           - Summarize text
  /code <language> <task>   - Generate code
  /translate <lang> <text>  - Translate text

⚙️  SETTINGS:
  /model                    - Show current model info

🚪 EXIT:
  quit, exit, /q           - Exit CLI

🔥 FEATURES:
  • 262,144 token context window
  • Real-time streaming responses
  • Session persistence
  • 40+ built-in tools
        """
        print(help_text)

    def handle_command(self, user_input: str) -> bool:
        """Handle special CLI commands."""
        parts = user_input.strip().split()
        if not parts:
            return False

        command = parts[0].lower()

        # Conversation commands
        if command in ['clear']:
            self.conversation_history = []
            print("🧹 Conversation history cleared")
            return True
        elif command == 'history':
            self.show_history()
            return True
        elif command == 'save':
            self.save_session()
            print("💾 Session saved")
            return True
        elif command == 'context':
            self.show_context_info()
            return True

        # File tools
        elif command == '/read' and len(parts) > 1:
            self.read_file(parts[1])
            return True
        elif command == '/write' and len(parts) > 2:
            filename = parts[1]
            content = ' '.join(parts[2:])
            self.write_file(filename, content)
            return True
        elif command == '/list':
            dir_path = parts[1] if len(parts) > 1 else '.'
            self.list_directory(dir_path)
            return True
        elif command == '/search' and len(parts) > 2:
            self.search_files(parts[1], parts[2])
            return True

        # System tools
        elif command == '/status':
            self.show_status()
            return True
        elif command == '/gpu':
            self.show_gpu_info()
            return True
        elif command == '/ps':
            self.show_processes()
            return True
        elif command == '/net':
            self.show_network_status()
            return True

        # Network tools
        elif command == '/curl' and len(parts) > 1:
            self.curl_request(parts[1])
            return True
        elif command == '/ping' and len(parts) > 1:
            self.ping_host(parts[1])
            return True

        # AI tools
        elif command == '/analyze' and len(parts) > 1:
            self.analyze_file(parts[1])
            return True
        elif command == '/summary' and len(parts) > 1:
            self.summarize_text(' '.join(parts[1:]))
            return True
        elif command == '/code' and len(parts) > 2:
            lang = parts[1]
            task = ' '.join(parts[2:])
            self.generate_code(lang, task)
            return True
        elif command == '/translate' and len(parts) > 2:
            target_lang = parts[1]
            text = ' '.join(parts[2:])
            self.translate_text(target_lang, text)
            return True

        # Settings
        elif command == '/model':
            self.show_model_info()
            return True

        return False

    def show_history(self):
        """Display conversation history."""
        print("\n📜 Conversation History:")
        print("=" * 50)
        for i, msg in enumerate(self.conversation_history[-10:], 1):
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            print(f"{i}. {role_emoji} {msg['role']}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
        print()

    def show_context_info(self):
        """Show context window usage."""
        total_chars = sum(len(msg['content']) for msg in self.conversation_history)
        estimated_tokens = total_chars // 4

        print(f"\n📊 Context Window Usage:")
        print(f"   Messages: {len(self.conversation_history)}")
        print(f"   Characters: {total_chars:,}")
        print(f"   Estimated Tokens: {estimated_tokens:,}")
        print(f"   Available: {self.max_context_tokens - estimated_tokens:,}")
        print(f"   Usage: {(estimated_tokens/self.max_context_tokens)*100:.1f}%")
        print(f"   🔥 Max Context: 262,144 tokens")
        print()

    def read_file(self, filename: str):
        """Read and display file contents."""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"\n📄 Contents of {filename}:")
                print("=" * 50)
                print(content[:1000] + ("..." if len(content) > 1000 else ""))
                print("=" * 50)
            else:
                print(f"❌ File not found: {filename}")
        except Exception as e:
            print(f"❌ Error reading file: {e}")

    def write_file(self, filename: str, content: str):
        """Write content to file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Successfully wrote to {filename}")
        except Exception as e:
            print(f"❌ Error writing file: {e}")

    def list_directory(self, dir_path: str):
        """List directory contents."""
        try:
            if os.path.exists(dir_path):
                items = os.listdir(dir_path)
                print(f"\n📁 Contents of {dir_path}:")
                print("=" * 50)
                for item in sorted(items)[:20]:
                    item_path = os.path.join(dir_path, item)
                    if os.path.isdir(item_path):
                        print(f"📂 {item}/")
                    else:
                        size = os.path.getsize(item_path)
                        print(f"📄 {item} ({size:,} bytes)")
                if len(items) > 20:
                    print(f"... and {len(items) - 20} more items")
                print("=" * 50)
            else:
                print(f"❌ Directory not found: {dir_path}")
        except Exception as e:
            print(f"❌ Error listing directory: {e}")

    def search_files(self, dir_path: str, pattern: str):
        """Search for files matching pattern."""
        try:
            matches = []
            for root, dirs, files in os.walk(dir_path):
                for file in files:
                    if re.search(pattern, file, re.IGNORECASE):
                        matches.append(os.path.join(root, file))

            print(f"\n🔍 Search results for '{pattern}' in {dir_path}:")
            print("=" * 50)
            for match in matches[:20]:
                print(f"📄 {match}")
            if len(matches) > 20:
                print(f"... and {len(matches) - 20} more files")
            print("=" * 50)
        except Exception as e:
            print(f"❌ Error searching files: {e}")

    def show_status(self):
        """Show server and system status."""
        print("\n🖥️  System Status:")
        print("=" * 50)

        # Server status
        try:
            response = requests.get("http://localhost:8000/v1/models", timeout=5)
            if response.status_code == 200:
                model_info = response.json()
                print(f"✅ Qwen3 Server: RUNNING")
                print(f"   Model: {model_info['data'][0]['id']}")
                print(f"   Max Context: {model_info['data'][0]['max_model_len']:,} tokens 🔥")
            else:
                print(f"❌ Qwen3 Server: ERROR (HTTP {response.status_code})")
        except:
            print(f"❌ Qwen3 Server: NOT RESPONDING")

        # Disk usage
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    print(f"💾 Disk Usage: {lines[1].split()[4]} used")
        except:
            pass

        print("=" * 50)

    def show_gpu_info(self):
        """Show GPU information."""
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            if result.returncode == 0:
                print("\n🎮 GPU Information:")
                print("=" * 50)
                print(result.stdout)
                print("=" * 50)
            else:
                print("❌ Could not get GPU information")
        except FileNotFoundError:
            print("❌ nvidia-smi not found")
        except Exception as e:
            print(f"❌ Error getting GPU info: {e}")

    def show_processes(self):
        """Show running processes."""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            if result.returncode == 0:
                print("\n⚙️  Running Processes (Top 10):")
                print("=" * 80)
                lines = result.stdout.strip().split('\n')[1:]
                lines.sort(key=lambda x: float(x.split()[2]) if len(x.split()) > 2 and x.split()[2].replace('.', '').isdigit() else 0, reverse=True)
                for line in lines[:10]:
                    print(line)
                print("=" * 80)
            else:
                print("❌ Could not get process information")
        except Exception as e:
            print(f"❌ Error getting processes: {e}")

    def show_network_status(self):
        """Show network status."""
        try:
            result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
            if result.returncode == 0:
                print("\n🌐 Network Status:")
                print("=" * 50)
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if '8000' in line or 'LISTEN' in line:
                        print(f"🔗 {line}")
                print("=" * 50)
        except Exception as e:
            print(f"❌ Error getting network status: {e}")

    def curl_request(self, url: str):
        """Make HTTP request."""
        try:
            response = requests.get(url, timeout=10)
            print(f"\n🌐 Response from {url}:")
            print(f"Status: {response.status_code}")
            print("Body:")
            print("-" * 50)
            print(response.text[:500] + ("..." if len(response.text) > 500 else ""))
            print("-" * 50)
        except Exception as e:
            print(f"❌ Error making request: {e}")

    def ping_host(self, host: str):
        """Ping a host."""
        try:
            result = subprocess.run(['ping', '-c', '4', host], capture_output=True, text=True)
            print(f"\n🏓 Ping results for {host}:")
            print("=" * 50)
            print(result.stdout)
            print("=" * 50)
        except Exception as e:
            print(f"❌ Error pinging host: {e}")

    def analyze_file(self, filename: str):
        """AI analysis of file."""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()

                if len(content) > 5000:
                    content = content[:5000] + "\n... (truncated for analysis)"

                self.add_to_history('user', f"Please analyze this file: {filename}\n\nContent:\n{content}")

                response = self.client.chat.completions.create(
                    model="Qwen3-30B-A3B-Thinking",
                    messages=self.conversation_history,
                    max_tokens=1000,
                    temperature=0.3
                )

                analysis = response.choices[0].message.content
                print(f"\n🤖 AI Analysis of {filename}:")
                print("=" * 50)
                print(analysis)
                print("=" * 50)

                self.add_to_history('assistant', analysis)
            else:
                print(f"❌ File not found: {filename}")
        except Exception as e:
            print(f"❌ Error analyzing file: {e}")

    def summarize_text(self, text: str):
        """Summarize text using AI."""
        try:
            self.add_to_history('user', f"Please summarize this text:\n{text}")

            response = self.client.chat.completions.create(
                model="Qwen3-30B-A3B-Thinking",
                messages=self.conversation_history,
                max_tokens=500,
                temperature=0.3
            )

            summary = response.choices[0].message.content
            print(f"\n📝 Summary:")
            print("=" * 50)
            print(summary)
            print("=" * 50)

            self.add_to_history('assistant', summary)
        except Exception as e:
            print(f"❌ Error summarizing text: {e}")

    def generate_code(self, language: str, task: str):
        """Generate code using AI."""
        try:
            self.add_to_history('user', f"Please generate {language} code for: {task}")

            response = self.client.chat.completions.create(
                model="Qwen3-30B-A3B-Thinking",
                messages=self.conversation_history,
                max_tokens=1500,
                temperature=0.2
            )

            code = response.choices[0].message.content
            print(f"\n💻 Generated {language} Code:")
            print("=" * 50)
            print(code)
            print("=" * 50)

            self.add_to_history('assistant', code)
        except Exception as e:
            print(f"❌ Error generating code: {e}")

    def translate_text(self, target_lang: str, text: str):
        """Translate text using AI."""
        try:
            self.add_to_history('user', f"Please translate this text to {target_lang}: {text}")

            response = self.client.chat.completions.create(
                model="Qwen3-30B-A3B-Thinking",
                messages=self.conversation_history,
                max_tokens=800,
                temperature=0.3
            )

            translation = response.choices[0].message.content
            print(f"\n🌍 Translation to {target_lang}:")
            print("=" * 50)
            print(translation)
            print("=" * 50)

            self.add_to_history('assistant', translation)
        except Exception as e:
            print(f"❌ Error translating text: {e}")

    def show_model_info(self):
        """Show current model information."""
        try:
            response = requests.get("http://localhost:8000/v1/models", timeout=5)
            if response.status_code == 200:
                model_info = response.json()
                model = model_info['data'][0]
                print(f"\n🤖 Current Model Information:")
                print("=" * 50)
                print(f"ID: {model['id']}")
                print(f"Max Context: {model['max_model_len']:,} tokens 🔥")
                print(f"Created: {datetime.fromtimestamp(model['created'])}")
                print(f"Owned By: {model['owned_by']}")
                print("=" * 50)
            else:
                print("❌ Could not get model information")
        except Exception as e:
            print(f"❌ Error getting model info: {e}")

    def chat_with_ai(self, user_input: str):
        """Have a conversation with the AI."""
        try:
            self.add_to_history('user', user_input)

            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history)

            response = self.client.chat.completions.create(
                model="Qwen3-30B-A3B-Thinking",
                messages=messages,
                max_tokens=1500,
                temperature=0.7,
                stream=True
            )

            print("🤖 ", end="", flush=True)
            ai_response = ""

            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    ai_response += content

            print()
            self.add_to_history('assistant', ai_response)

        except Exception as e:
            print(f"❌ Error communicating with AI: {e}")

    def run(self):
        """Run the interactive CLI."""
        print("🚀 Qwen3-30B-A3B-Thinking Interactive CLI")
        print("=" * 50)
        print("💬 Type 'help' for commands or just start talking!")
        print("🔥 262,144 token context window enabled")
        print("🚪 Type 'quit', 'exit', or '/q' to leave")
        print("=" * 50)

        self.load_session()

        while True:
            try:
                user_input = input("\n💭 You: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ['quit', 'exit', '/q']:
                    print("\n👋 Goodbye! Saving session...")
                    self.save_session()
                    break

                if user_input.lower() in ['help', '/help', 'h']:
                    self.show_help()
                    continue

                if self.handle_command(user_input):
                    continue

                self.chat_with_ai(user_input)

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Saving session...")
                self.save_session()
                break
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    cli = Qwen3CLI()
    cli.run()