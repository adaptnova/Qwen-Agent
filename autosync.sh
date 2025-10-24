#!/bin/bash
# Auto-sync script for Qwen3 repository

echo "🔄 Auto-syncing Qwen3 repository..."
echo "=================================="

# Pull latest changes
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# Check if there are any local changes to push
if [[ -n $(git status --porcelain) ]]; then
    echo "📤 Local changes detected, pushing to GitHub..."

    # Add all changes
    git add .

    # Commit with timestamp
    git commit -m "Auto-sync: $(date '+%Y-%m-%d %H:%M:%S')"

    # Push to GitHub
    git push origin main

    if [ $? -eq 0 ]; then
        echo "✅ Auto-sync completed successfully!"
    else
        echo "❌ Auto-sync failed!"
        exit 1
    fi
else
    echo "✅ Repository is up to date!"
fi

echo ""
echo "🚀 Qwen3 repository sync complete!"