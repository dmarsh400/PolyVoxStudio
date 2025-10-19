#!/bin/bash
# Clear chapter detection cache for a book
# Run this if you see duplicate or incorrectly split chapters

echo "🧹 Chapter Detection Cache Cleaner"
echo ""
echo "This will clear all cached chapter detections."
echo "After running this, you'll need to re-run chapter detection once on your books."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    cd /home/moderatec/Desktop/VOX_current_working
    
    echo "Clearing cached chapter detections..."
    rm -rf output/booknlp_*
    
    echo "✅ Cache cleared!"
    echo ""
    echo "Next steps:"
    echo "1. Launch PolyVox Studio: ./run_gui.sh"
    echo "2. Load your book"
    echo "3. Run chapter detection ONCE"
    echo "4. Chapters will now be preserved as complete units"
else
    echo "Cancelled."
fi
