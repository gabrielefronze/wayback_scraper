#!/bin/bash

# Wayback Scraper - Combine Split Results
# This script combines the results from multiple split runs

set -e

# Default values
BASE_OUTPUT_DIR="downloads"
COMBINED_DIR="downloads_combined"

# Function to display usage
usage() {
    echo "🔗 Wayback Scraper - Combine Split Results"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -i, --input DIR           Base input directory containing splits (default: downloads)"
    echo "  -o, --output DIR          Combined output directory (default: downloads_combined)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                        # Combine results from downloads/ to downloads_combined/"
    echo "  $0 -i my_downloads        # Combine from my_downloads/ directory"
    echo "  $0 -o final_results       # Output to final_results/ directory"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--input)
            BASE_OUTPUT_DIR="$2"
            shift 2
            ;;
        -o|--output)
            COMBINED_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

echo "🔗 Wayback Scraper - Combine Split Results"
echo "==========================================="
echo ""

# Check if input directory exists
if [ ! -d "$BASE_OUTPUT_DIR" ]; then
    echo "❌ Error: Input directory '$BASE_OUTPUT_DIR' not found!"
    exit 1
fi

# Find all split directories
SPLIT_DIRS=($(find "$BASE_OUTPUT_DIR" -maxdepth 1 -type d -name "split_*" | sort -V))

if [ ${#SPLIT_DIRS[@]} -eq 0 ]; then
    echo "❌ Error: No split directories found in '$BASE_OUTPUT_DIR'"
    echo "Expected directories like: split_1, split_2, etc."
    exit 1
fi

echo "📂 Found ${#SPLIT_DIRS[@]} split directories:"
for dir in "${SPLIT_DIRS[@]}"; do
    echo "   📁 $(basename "$dir")"
done
echo ""

# Create combined directory
mkdir -p "$COMBINED_DIR"

echo "🔄 Combining results..."
echo "📁 Output directory: $COMBINED_DIR"
echo ""

# Combine all splits
TOTAL_SITES=0
TOTAL_DOWNLOADS=0

for split_dir in "${SPLIT_DIRS[@]}"; do
    split_name=$(basename "$split_dir")
    echo "▶️  Processing $split_name..."
    
    # Count sites and downloads in this split
    SITES_IN_SPLIT=0
    DOWNLOADS_IN_SPLIT=0
    
    if [ -d "$split_dir" ]; then
        # Count directories (each site creates 2 directories - before and after)
        DOWNLOADS_IN_SPLIT=$(find "$split_dir" -maxdepth 1 -type d ! -path "$split_dir" ! -name "logs" | wc -l | tr -d ' ')
        SITES_IN_SPLIT=$((DOWNLOADS_IN_SPLIT / 2))
        
        # Copy all content to combined directory
        if [ $DOWNLOADS_IN_SPLIT -gt 0 ]; then
            cp -r "$split_dir"/* "$COMBINED_DIR/" 2>/dev/null || true
            echo "   ✅ Copied $DOWNLOADS_IN_SPLIT download directories ($SITES_IN_SPLIT sites)"
        else
            echo "   ⚠️  No download directories found"
        fi
        
        TOTAL_SITES=$((TOTAL_SITES + SITES_IN_SPLIT))
        TOTAL_DOWNLOADS=$((TOTAL_DOWNLOADS + DOWNLOADS_IN_SPLIT))
    else
        echo "   ⚠️  Directory not found: $split_dir"
    fi
done

echo ""
echo "🔄 Combining log files..."

# Combine all log files
LOGS_DIR="$COMBINED_DIR/logs"
mkdir -p "$LOGS_DIR"

# Combine main log files
MAIN_LOG_COMBINED="$LOGS_DIR/wayback_scraper_combined.log"
echo "# Combined log file created on $(date)" > "$MAIN_LOG_COMBINED"
echo "# Combined from split results" >> "$MAIN_LOG_COMBINED"
echo "" >> "$MAIN_LOG_COMBINED"

for split_dir in "${SPLIT_DIRS[@]}"; do
    split_name=$(basename "$split_dir")
    SPLIT_LOG="$split_dir/logs/wayback_scraper.log"
    
    if [ -f "$SPLIT_LOG" ]; then
        echo "# ========== $split_name ==========" >> "$MAIN_LOG_COMBINED"
        cat "$SPLIT_LOG" >> "$MAIN_LOG_COMBINED"
        echo "" >> "$MAIN_LOG_COMBINED"
    fi
done

echo "✅ Log files combined"

echo ""
echo "🎉 Results successfully combined!"
echo ""
echo "📊 Summary:"
echo "   Total sites processed: $TOTAL_SITES"
echo "   Total download directories: $TOTAL_DOWNLOADS"
echo "   Combined results location: $COMBINED_DIR/"
echo "   Combined log file: $MAIN_LOG_COMBINED"
echo ""
echo "📁 You can now find all results in the '$COMBINED_DIR' directory" 