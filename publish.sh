#!/bin/bash

# Simple GitHub Publisher
cd "$(dirname "$0")"

echo "🎭 Publishing PolyVox Studio to GitHub"
echo "======================================"
echo ""

# Initialize git if needed
if [ ! -d ".git" ]; then
    git init
    git remote add origin https://github.com/dmarsh400/PolyVoxStudio.git
fi

# Add all files
git add .

# Commit
git commit -m "PolyVox Studio v1.0.0

AI-powered audiobook generation with character-specific voice cloning.
Automatic character detection, voice synthesis, and full editorial control."

# Set branch and push
git branch -M main
git push -f origin main

echo ""
echo "✅ Published to: https://github.com/dmarsh400/PolyVoxStudio"
