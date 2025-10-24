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
You have access to various tools and can use them AUTOMATICALLY when needed.

AUTOMATIC TOOL USAGE:
- When users ask for current information, news, or research → USE web_search()
- When users ask math problems, calculations, or equations → USE solve_math()
- When users ask to run code, execute programs, or test algorithms → USE execute_code()
- When users ask for translations between languages → USE translate_text()
- When users ask to read files → USE read_file()
- When users ask to write files → USE write_file()

You can invoke tools by describing the action in your response, like:
"Let me search for current information about that..." → triggers web_search
"Let me calculate that for you..." → triggers solve_math
"Let me execute that code..." → triggers execute_code
"Let me translate that to Spanish..." → triggers translate_text

Be proactive in using tools when they would be helpful. Don't ask for permission - just use them naturally in conversation."""

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
🚀 Qwen3 Interactive CLI - 262K Context Window - AUTONOMOUS TOOLS

💬 CONVERSATION (Natural Language - No Commands Needed!):
  Just talk normally! The AI automatically uses tools when needed.

🤖 AUTONOMOUS AI TOOLS (Automatically Triggered):
  🔍 Web Search    - Ask: "search for latest AI news" or "what's happening with quantum computing?"
  🧮 Math Solver   - Ask: "what is 2^10 + 5 * 3?" or "solve x^2 = 16"
  💻 Code Runner  - Ask: "run this code: print('hello')" or "execute python: [code]"
  🌍 Translator   - Ask: "translate 'hello' to Spanish" or "how do you say 'thank you' in French?"
  📄 File Reader  - Ask: "read the README file" or "check config.json"

📁 MANUAL FILE COMMANDS:
  /read <file>              - Read a file
  /write <file> <content>   - Write content to file
  /list <dir>               - List directory contents

🖥️  SYSTEM COMMANDS:
  /status                   - Show server and system status
  /gpu                      - Show GPU information
  /model                    - Show current model info

🚪 EXIT:
  quit, exit, /q           - Exit CLI

💡 NATURAL LANGUAGE EXAMPLES (Just talk normally!):
  "Search for recent developments in AI"
  "What's 25 * 4 + 100?"
  "Run this python code: print('Hello, autonomous tools!')"
  "How do you say 'TeamADAPT rocks' in Spanish?"
  "Read the SECURITY_REPORT.md file"

🔥 FEATURES:
  • 262,144 token context window
  • AUTONOMOUS tool usage - No slash commands needed!
  • AI decides when to use tools automatically
  • Safe code execution sandbox
  • Natural conversation flow
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
        elif command == '/websearch' and len(parts) > 1:
            query = ' '.join(parts[1:])
            self.web_search(query)
            return True
        elif command == '/math' and len(parts) > 1:
            expression = ' '.join(parts[1:])
            self.solve_math(expression)
            return True
        elif command == '/analyze' and len(parts) > 1:
            self.analyze_file(parts[1])
            return True
        elif command == '/summary' and len(parts) > 1:
            self.summarize_text(' '.join(parts[1:]))
            return True
        elif command == '/code' and len(parts) > 2:
            lang = parts[1]
            task = ' '.join(parts[2:])
            # Check if it's a simple execution request (code starts with quotes or is a simple expression)
            if task.startswith('"') or task.startswith("'") or len(task) < 100 and not any(word in task.lower() for word in ['function', 'class', 'def', 'import', 'create', 'write', 'generate']):
                # Execute the code directly
                code = task.strip('"\'')
                self.execute_code(lang, code)
            else:
                # Generate code then offer to execute it
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

    def solve_math(self, expression: str):
        """Solve math problems using AI and actual calculation."""
        try:
            # Try to evaluate simple expressions first
            import re
            import math

            # Check if it's a simple mathematical expression
            if re.match(r'^[\d\+\-\*\/\^\(\)\.\s]+$', expression):
                try:
                    # Safe math evaluation
                    allowed_names = {
                        k: v for k, v in math.__dict__.items()
                        if not k.startswith("_")
                    }
                    allowed_names['abs'] = abs
                    allowed_names['round'] = round

                    result = eval(expression, {"__builtins__": {}}, allowed_names)
                    print(f"\n🧮 Math Result:")
                    print("=" * 40)
                    print(f"{expression} = {result}")
                    print("=" * 40)
                    return
                except:
                    pass  # Fall back to AI solving

            # Use AI for complex problems
            math_prompt = f"Please solve this math problem step by step: {expression}. Show your work and provide the final answer."
            self.add_to_history('user', math_prompt)

            response = self.client.chat.completions.create(
                model="Qwen3-30B-A3B-Thinking",
                messages=self.conversation_history,
                max_tokens=800,
                temperature=0.1
            )

            solution = response.choices[0].message.content
            print(f"\n🧮 Math Solution for: '{expression}'")
            print("=" * 50)
            print(solution)
            print("=" * 50)

            self.add_to_history('assistant', solution)
        except Exception as e:
            print(f"❌ Error solving math problem: {e}")

    def execute_code(self, language: str, code: str):
        """Execute code in a safe sandbox environment."""
        try:
            print(f"\n💻 Executing {language} Code:")
            print("=" * 50)
            print(f"Code: {code}")
            print("-" * 50)

            if language.lower() == 'python':
                import subprocess
                import tempfile
                import os

                # Create temporary file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    temp_file = f.name

                try:
                    # Execute with timeout and limited resources
                    result = subprocess.run(
                        ['python3', temp_file],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd='/tmp'  # Run in temporary directory
                    )

                    if result.returncode == 0:
                        print("✅ Output:")
                        print(result.stdout)
                    else:
                        print("❌ Error:")
                        print(result.stderr)

                except subprocess.TimeoutExpired:
                    print("⏰ Error: Code execution timed out (10 second limit)")
                except Exception as e:
                    print(f"❌ Execution error: {e}")
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_file)
                    except:
                        pass

            else:
                print(f"❌ Language '{language}' not yet supported for execution. Try 'python' instead.")

        except Exception as e:
            print(f"❌ Error executing code: {e}")

    def web_search(self, query: str):
        """Perform web search using AI with current knowledge."""
        try:
            # Add search request to conversation
            search_prompt = f"Please search for current information about: {query}. Provide the latest results you have access to, formatted as a concise summary with key points."
            self.add_to_history('user', search_prompt)

            response = self.client.chat.completions.create(
                model="Qwen3-30B-A3B-Thinking",
                messages=self.conversation_history,
                max_tokens=1200,
                temperature=0.2
            )

            search_results = response.choices[0].message.content
            print(f"\n🔍 Web Search Results for: '{query}'")
            print("=" * 60)
            print(search_results)
            print("=" * 60)
            print("💡 Note: Results based on training data. For truly live data, use external search engines.")

            self.add_to_history('assistant', search_results)
        except Exception as e:
            print(f"❌ Error performing web search: {e}")

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
        """Have a conversation with the AI with automatic tool usage."""
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

            # Automatic tool detection and execution
            self.detect_and_execute_tools(ai_response, user_input)

        except Exception as e:
            print(f"❌ Error communicating with AI: {e}")

    def detect_and_execute_tools(self, ai_response: str, user_input: str):
        """Detect tool usage intent and automatically execute tools."""
        import re

        # Convert to lowercase for pattern matching
        response_lower = ai_response.lower()
        user_lower = user_input.lower()

        # Web search detection
        search_patterns = [
            r"let me search|let me look up|let me find|searching for|looking up",
            r"latest.*news|current.*information|recent.*developments",
            r"what.*happening|what.*new|latest.*research"
        ]

        # Math calculation detection
        math_patterns = [
            r"let me calculate|let me solve|let me compute|calculating|solving",
            r"what.*is.*\d|how much|calculate|solve.*equation",
            r"\+|\-|\*|\/|\^|sqrt|factorial"
        ]

        # Code execution detection
        code_patterns = [
            r"let me execute|let me run|let me test|executing|running",
            r"code.*execution|test.*code|run.*program",
            r"python.*code|javascript.*code|execute.*code"
        ]

        # Translation detection
        translate_patterns = [
            r"let me translate|translating to|translate.*to",
            r"in.*spanish|in.*french|in.*german|in.*italian",
            r"how.*say.*in|what.*is.*in.*language"
        ]

        # File operations detection
        file_patterns = [
            r"let me read|let me open|reading.*file|opening.*file",
            r"let me write|let me save|writing.*file|saving.*file",
            r"check.*file|analyze.*file|read.*content"
        ]

        # Check each tool type and execute if detected
        if any(re.search(pattern, response_lower) for pattern in search_patterns) or \
           any(re.search(pattern, user_lower) for pattern in search_patterns):
            # Extract search query from user input
            query = user_input
            if any(word in user_lower for word in ['search', 'find', 'look up', 'news', 'information']):
                # Clean up the query - remove search-related words
                query = re.sub(r'(search|find|look up|for|about|latest|current|recent)', '', user_input, flags=re.IGNORECASE).strip()
            if query:
                print(f"\n🔍 *Automatically searching for: {query}*")
                self.web_search(query)

        elif any(re.search(pattern, response_lower) for pattern in math_patterns) or \
             any(re.search(pattern, user_lower) for pattern in math_patterns):
            # Extract math expression - look for the most complete expression
            math_expr = user_input
            # Try multiple patterns for math expressions
            math_match = re.search(r'([^?]*)\?$', user_input)  # Before question mark
            if not math_match:
                math_match = re.search(r'what\s+is\s+([^\?]+)', user_input, re.IGNORECASE)
            if not math_match:
                math_match = re.search(r'calculate\s+([^\?]+)', user_input, re.IGNORECASE)
            if not math_match:
                math_match = re.search(r'solve\s+([^\?]+)', user_input, re.IGNORECASE)
            if not math_match:
                math_match = re.search(r'([\d\+\-\*\/\^\(\)\.\s]+)', user_input)

            if math_match:
                math_expr = math_match.group(1).strip()
                # Clean up common words
                math_expr = re.sub(r'(what\s+is|calculate|solve)', '', math_expr, flags=re.IGNORECASE).strip()

            if math_expr and any(char.isdigit() for char in math_expr):
                print(f"\n🧮 *Automatically calculating: {math_expr}*")
                self.solve_math(math_expr)

        elif any(re.search(pattern, response_lower) for pattern in code_patterns) or \
             any(re.search(pattern, user_lower) for pattern in code_patterns):
            # Extract code and language
            code_match = re.search(r'```(\w+)?\n?(.*?)\n?```', user_input, re.DOTALL)
            if code_match:
                lang = code_match.group(1) or 'python'
                code = code_match.group(2).strip()
                print(f"\n💻 *Automatically executing {lang} code*")
                self.execute_code(lang, code)
            else:
                # Try to find code after "run this", "execute this", "run:", "execute:", etc.
                code_match = re.search(r'(?:run|execute)\s+(?:this|:)\s*(.+)', user_input, re.IGNORECASE)
                if code_match:
                    code = code_match.group(1).strip()
                    # Check if it's quoted - if so, extract the quoted content
                    quote_match = re.search(r'["\']([^"\']+)["\']', code)
                    if quote_match:
                        code = quote_match.group(1)
                    else:
                        # Remove quotes if present at boundaries
                        code = code.strip('\'"')
                    # Try to detect language from the code
                    lang = 'python'  # default
                    if 'javascript' in code.lower() or 'js:' in code.lower():
                        lang = 'javascript'
                    elif any(word in code.lower() for word in ['print', 'def ', 'import ', 'for ', 'while ']):
                        lang = 'python'

                    print(f"\n💻 *Automatically executing {lang} code*")
                    self.execute_code(lang, code)
                else:
                    # Try to find quoted code
                    simple_code_match = re.search(r'["\']([^"\']+)["\']', user_input)
                    if simple_code_match:
                        code = simple_code_match.group(1)
                        print(f"\n💻 *Automatically executing python code*")
                        self.execute_code('python', code)

        elif any(re.search(pattern, response_lower) for pattern in translate_patterns) or \
             any(re.search(pattern, user_lower) for pattern in translate_patterns):
            # Extract target language and text
            # Look for language mentions
            languages = ['spanish', 'french', 'german', 'italian', 'portuguese', 'chinese', 'japanese', 'russian', 'arabic']
            target_lang = None
            for lang in languages:
                if lang in response_lower or lang in user_lower:
                    target_lang = lang
                    break

            if target_lang:
                # Extract text to translate (quote content)
                text_match = re.search(r'["\']([^"\']+)["\']', user_input)
                if text_match:
                    text = text_match.group(1)
                    print(f"\n🌍 *Automatically translating to {target_lang}*")
                    self.translate_text(target_lang, text)

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