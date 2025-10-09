#!/usr/bin/env python3
"""
ASCII Sanity Check - CI Smoke Test for Model Output Corruption

Detects model corruption by checking for multilingual gibberish in simple math responses.
Fails fast if "2+2" returns hieroglyphics instead of clean English.
"""

import requests
import json
import re
import sys
import os
from typing import Dict, Any, Tuple

class ModelCorruptionDetector:
    def __init__(self, base_url: str = "http://127.0.0.1:18000/v1"):
        self.base_url = base_url
        self.test_cases = [
            {"prompt": "What is 2+2? Give just the number.", "expected": ["4", "four"]},
            {"prompt": "What is 1+1? Give just the number.", "expected": ["2", "two"]},
            {"prompt": "What is 3+3? Give just the number.", "expected": ["6", "six"]},
        ]

    def check_ascii_ratio(self, text: str) -> Tuple[float, bool]:
        """Check ASCII character ratio in response"""
        if not text:
            return 0.0, False

        total_chars = len(text.strip())
        if total_chars == 0:
            return 0.0, False

        ascii_chars = sum(1 for c in text.strip() if ord(c) < 128)
        ascii_ratio = ascii_chars / total_chars

        # Fail if less than 90% ASCII
        is_healthy = ascii_ratio >= 0.9
        return ascii_ratio, is_healthy

    def detect_cjk_rtl_contamination(self, text: str) -> bool:
        """Detect CJK or RTL character contamination"""
        cjk_pattern = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uff00-\uffef]')
        rtl_pattern = re.compile(r'[\u0590-\u05ff\u0600-\u06ff\u0750-\u077f\ufb50-\ufdff\ufe70-\ufeff]')

        return bool(cjk_pattern.search(text) or rtl_pattern.search(text))

    def detect_garbage_patterns(self, text: str) -> bool:
        """Detect common corruption patterns from our tests"""
        garbage_patterns = [
            r'\[\.\.\.\]',  # [...]
            r'[…]+',      # Multiple ellipsis
            r'﹡',         # Specific corruption character
            r'_\^-',      # Corruption pattern
            r'topic.*找找找',  # Chinese corruption pattern
            r'أهد',       # Arabic contamination
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in garbage_patterns)

    def make_request(self, prompt: str, model: str = None) -> Dict[str, Any]:
        """Make a single request to the model"""
        payload = {
            "model": model or "Qwen/Qwen3-30B-A3B-Instruct-2507",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 20,
            "temperature": 0,
            "presence_penalty": 0  # As recommended for health checks
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer sk-EMPTY"
                },
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "content": ""
                }

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            return {
                "success": True,
                "content": content.strip(),
                "model": data.get("model"),
                "usage": data.get("usage", {})
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }

    def evaluate_response(self, test_case: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate if response is healthy"""
        if not response["success"]:
            return {
                "passed": False,
                "error": response["error"],
                "details": "Request failed"
            }

        content = response["content"].lower()

        # Check if expected answer is present
        has_expected = any(exp in content for exp in test_case["expected"])

        # ASCII ratio check
        ascii_ratio, ascii_healthy = self.check_ascii_ratio(content)

        # CJK/RTL contamination check
        has_cjk_rtl = self.detect_cjk_rtl_contamination(content)

        # Garbage pattern detection
        has_garbage = self.detect_garbage_patterns(content)

        # Overall health assessment
        is_healthy = (
            has_expected and
            ascii_healthy and
            not has_cjk_rtl and
            not has_garbage and
            len(content) < 100  # Should be concise for math questions
        )

        return {
            "passed": is_healthy,
            "has_expected": has_expected,
            "ascii_ratio": ascii_ratio,
            "ascii_healthy": ascii_healthy,
            "has_cjk_rtl": has_cjk_rtl,
            "has_garbage": has_garbage,
            "content": response["content"],
            "details": {
                "expected_answer": has_expected,
                "ascii_ratio": f"{ascii_ratio:.2%}",
                "cjk_rtl_detected": has_cjk_rtl,
                "garbage_patterns": has_garbage,
                "content_length": len(content)
            }
        }

    def run_sanity_check(self) -> Dict[str, Any]:
        """Run the complete sanity check suite"""
        print("🔍 Running Model Corruption Sanity Check")
        print(f"Target: {self.base_url}")
        print("=" * 50)

        results = []
        passed_count = 0

        for i, test_case in enumerate(self.test_cases, 1):
            print(f"Test {i}: {test_case['prompt']}")

            response = self.make_request(test_case["prompt"])
            evaluation = self.evaluate_response(test_case, response)

            results.append({
                "test_id": i,
                "prompt": test_case["prompt"],
                "response": response,
                "evaluation": evaluation
            })

            if evaluation["passed"]:
                print(f"  ✅ PASS - {evaluation['content']}")
                passed_count += 1
            else:
                print(f"  ❌ FAIL - {evaluation['content']}")
                print(f"     Details: {evaluation['details']}")
                if not response["success"]:
                    print(f"     Error: {evaluation['error']}")

            print()

        # Overall assessment
        total_tests = len(self.test_cases)
        success_rate = (passed_count / total_tests) * 100

        print("=" * 50)
        print(f"📊 Results: {passed_count}/{total_tests} passed ({success_rate:.1f}%)")

        if success_rate == 100:
            print("🎉 Model is HEALTHY - No corruption detected")
            return {"success": True, "results": results, "success_rate": success_rate}
        elif success_rate >= 66:
            print("⚠️  Model has ISSUES - Partial corruption detected")
            return {"success": False, "results": results, "success_rate": success_rate}
        else:
            print("🚨 Model is CORRUPTED - Critical failure detected")
            return {"success": False, "results": results, "success_rate": success_rate}

def main():
    """Main entry point for CI/CD integration"""
    # Get base URL from environment or use default
    base_url = os.getenv('MODEL_API_URL', 'http://127.0.0.1:18000/v1')

    detector = ModelCorruptionDetector(base_url)
    result = detector.run_sanity_check()

    # Exit codes for CI/CD
    if result["success"]:
        print("\n✅ Sanity check PASSED - Model is healthy")
        sys.exit(0)
    else:
        print("\n❌ Sanity check FAILED - Model corruption detected")
        # Save detailed results for debugging
        results_file = f"/tmp/model_sanity_check_{int(__import__('time').time())}.json"
        with open(results_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"📄 Detailed results saved to: {results_file}")

        # Different exit codes for different failure levels
        if result["success_rate"] == 0:
            sys.exit(2)  # Critical failure - complete corruption
        else:
            sys.exit(1)  # Partial failure

if __name__ == "__main__":
    main()