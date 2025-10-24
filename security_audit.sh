#!/bin/bash
# Security Audit Script for Qwen-Agent
# This script runs comprehensive security checks on dependencies and code

set -e

echo "🔒 Qwen-Agent Security Audit"
echo "============================="
echo "📅 Date: $(date)"
echo "🖥️  Host: $(hostname)"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_status "WARNING" "Activating virtual environment..."
    source venv/bin/activate 2>/dev/null || {
        print_status "ERROR" "Virtual environment not found. Please run 'python3 -m venv venv' first."
        exit 1
    }
fi

echo "🔍 Running Security Analysis..."
echo ""

# 1. Run pip-audit for known vulnerabilities
echo "1. Checking for Known Vulnerabilities (pip-audit)..."
echo "---------------------------------------------------"
if command -v pip-audit &> /dev/null; then
    pip-audit --format=json > audit_results.json 2>/dev/null || {
        pip-audit
        print_status "WARNING" "Could not save audit results to JSON"
    }

    # Count vulnerabilities
    VULN_COUNT=$(pip-audit --format=json 2>/dev/null | jq '.vulnerabilities | length' 2>/dev/null || echo "0")
    if [ "$VULN_COUNT" -eq 0 ]; then
        print_status "OK" "No known vulnerabilities found"
    else
        print_status "WARNING" "Found $VULN_COUNT known vulnerabilities"
        pip-audit --dry-run --fix 2>/dev/null || pip-audit
    fi
else
    print_status "ERROR" "pip-audit not installed. Run: pip install pip-audit"
fi
echo ""

# 2. Run safety check
echo "2. Running Safety Check..."
echo "-------------------------"
if command -v safety &> /dev/null; then
    safety check --json --output safety_report.json 2>/dev/null || {
        safety check
        print_status "WARNING" "Could not save safety report to JSON"
    }

    # Safety exit code 0 means no vulnerabilities
    if safety check --short 2>/dev/null; then
        print_status "OK" "Safety check passed"
    else
        print_status "WARNING" "Safety check found issues"
    fi
else
    print_status "ERROR" "Safety not installed. Run: pip install safety"
fi
echo ""

# 3. Check for sensitive files
echo "3. Checking for Sensitive Files..."
echo "---------------------------------"
SENSITIVE_FILES=(".env" "*.pem" "*.key" ".webui_secret_key" "id_rsa*" "*.p12")
FOUND_SENSITIVE=false

for pattern in "${SENSITIVE_FILES[@]}"; do
    if ls $pattern 2>/dev/null; then
        print_status "WARNING" "Found potentially sensitive file: $pattern"
        FOUND_SENSITIVE=true
    fi
done

if [ "$FOUND_SENSITIVE" = false ]; then
    print_status "OK" "No sensitive files found in repository root"
fi
echo ""

# 4. Check git repository security
echo "4. Git Repository Security Check..."
echo "---------------------------------"

# Check if .gitignore exists and has proper entries
if [ -f ".gitignore" ]; then
    print_status "OK" ".gitignore file exists"

    # Check for common sensitive patterns
    if grep -q ".env" .gitignore; then
        print_status "OK" ".gitignore excludes .env files"
    else
        print_status "WARNING" ".gitignore should exclude .env files"
    fi

    if grep -q "venv" .gitignore; then
        print_status "OK" ".gitignore excludes venv directory"
    else
        print_status "WARNING" ".gitignore should exclude venv directory"
    fi
else
    print_status "ERROR" ".gitignore file not found"
fi

# Check for git secrets configuration
if [ -f ".git/hooks/pre-commit" ]; then
    print_status "OK" "Git pre-commit hook exists"
else
    print_status "INFO" "Consider adding pre-commit hooks for security"
fi
echo ""

# 5. Check Python file security
echo "5. Python Code Security Check..."
echo "-----------------------------"

# Check for hardcoded secrets or API keys
SECRET_PATTERNS=("api_key.*=" "password.*=" "secret.*=" "token.*=" "key.*=")
SECRETS_FOUND=false

for pattern in "${SECRET_PATTERNS[@]}"; do
    if grep -r -i --include="*.py" "$pattern" . --exclude-dir=venv --exclude-dir=.git 2>/dev/null; then
        print_status "WARNING" "Potential hardcoded secret found: $pattern"
        SECRETS_FOUND=true
    fi
done

if [ "$SECRETS_FOUND" = false ]; then
    print_status "OK" "No obvious hardcoded secrets found"
fi
echo ""

# 6. Check dependency versions
echo "6. Dependency Version Analysis..."
echo "--------------------------------"

# Check for outdated packages
if command -v pip-list &> /dev/null; then
    pip list --outdated --format=json > outdated.json 2>/dev/null || {
        print_status "INFO" "Could not generate outdated packages report"
    }

    OUTDATED_COUNT=$(pip list --outdated 2>/dev/null | wc -l)
    if [ "$OUTDATED_COUNT" -gt 1 ]; then
        print_status "WARNING" "Found $(($OUTDATED_COUNT - 1)) outdated packages"
        pip list --outdated
    else
        print_status "OK" "All packages are up to date"
    fi
else
    print_status "INFO" "Skipping outdated package check"
fi
echo ""

# 7. Generate summary report
echo "7. Security Summary Report..."
echo "---------------------------"
echo "📊 Audit completed at: $(date)"
echo "📁 Repository: $(pwd)"
echo "🐍 Python version: $(python --version)"

# Generate a simple security score
SCORE=100

# Deduct points for issues
if [ "$VULN_COUNT" -gt 0 ]; then
    SCORE=$((SCORE - (VULN_COUNT * 10)))
fi

if [ "$FOUND_SENSITIVE" = true ]; then
    SCORE=$((SCORE - 20))
fi

if [ ! -f ".gitignore" ]; then
    SCORE=$((SCORE - 15))
fi

if [ "$SECRETS_FOUND" = true ]; then
    SCORE=$((SCORE - 25))
fi

# Ensure score doesn't go below 0
if [ $SCORE -lt 0 ]; then
    SCORE=0
fi

echo "🔒 Security Score: $SCORE/100"

if [ $SCORE -ge 90 ]; then
    print_status "OK" "Excellent security posture"
elif [ $SCORE -ge 70 ]; then
    print_status "WARNING" "Good security posture with some issues"
elif [ $SCORE -ge 50 ]; then
    print_status "WARNING" "Moderate security concerns"
else
    print_status "ERROR" "Significant security issues need attention"
fi

echo ""
echo "📋 Recommendations:"
echo "   - Regularly update dependencies"
echo "   - Use environment variables for secrets"
echo "   - Enable Dependabot alerts on GitHub"
echo "   - Run this audit weekly"
echo "   - Review and commit security updates promptly"

echo ""
echo "📄 Detailed reports saved to:"
echo "   - audit_results.json (pip-audit)"
echo "   - safety_report.json (safety check)"
echo "   - outdated.json (outdated packages)"

echo ""
echo "✨ Security audit completed! ✨"