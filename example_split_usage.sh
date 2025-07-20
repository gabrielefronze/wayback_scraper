#!/bin/bash

# Example usage of the split functionality

echo "🚀 Wayback Scraper - Split Functionality Examples"
echo "================================================="
echo ""

echo "This script shows examples of how to use the split functionality."
echo "Make sure you have a 'data.csv' file before running these commands."
echo ""

echo "📋 Available commands:"
echo ""

echo "1. Split into files with 5 rows each (sequential):"
echo "   ./run_split.sh -r 5"
echo ""

echo "2. Split into 3 files (sequential):"
echo "   ./run_split.sh -f 3"
echo ""

echo "3. Split into files with 10 rows each (parallel):"
echo "   ./run_split.sh -r 10 -p"
echo ""

echo "4. Split into 4 files (parallel):"
echo "   ./run_split.sh -f 4 -p"
echo ""

echo "5. Use shared downloads folder (recommended for space efficiency):"
echo "   ./run_split.sh -r 5 -s"
echo ""

echo "6. Parallel processing with shared downloads:"
echo "   ./run_split.sh -f 3 -p -s"
echo ""

echo "7. Use custom input file and output directory:"
echo "   ./run_split.sh -i my_data.csv -o my_downloads -r 8"
echo ""

echo "8. After processing with separate folders, combine all results:"
echo "   ./combine_results.sh"
echo ""

echo "9. Combine results from custom directories:"
echo "   ./combine_results.sh -i my_downloads -o final_results"
echo ""

echo "💡 Tips:"
echo ""
echo "   🗂️  SHARED DOWNLOADS (-s flag):"
echo "      • All splits save to the same downloads/ folder"
echo "      • More space efficient - no duplicate structure"
echo "      • Each split has its own state file to avoid conflicts"
echo "      • Logs are separated (logs_split_1/, logs_split_2/, etc.)"
echo "      • Safe because each URL gets its own unique folder"
echo ""
echo "   📁 SEPARATE FOLDERS (default):"
echo "      • Each split saves to downloads/split_1/, downloads/split_2/, etc."
echo "      • Maximum isolation between runs"
echo "      • Use combine_results.sh to merge everything afterwards"
echo "      • Safer for debugging and testing"
echo ""
echo "   ⚡ PARALLEL vs SEQUENTIAL:"
echo "      • Parallel (-p): Faster with multiple CPU cores, higher resource usage"
echo "      • Sequential (default): More stable, better for limited resources"
echo "      • With Tor proxy: Sequential might be more reliable"
echo ""
echo "   📊 SPLIT STRATEGIES:"
echo "      • By rows (-r): Good for consistent workload per split"
echo "      • By files (-f): Good when you know exactly how many parallel jobs you want"
echo "      • Smaller splits work better with limited proxy bandwidth"
echo ""
echo "   🔍 MONITORING:"
echo "      • Each split creates its own log files for debugging"
echo "      • Check individual split logs if something goes wrong"
echo "      • Use 'docker ps' to see running containers"
echo "      • Use 'docker logs wayback-scraper-split-N' for container logs"
echo ""

echo "🔧 Recommended workflows:"
echo ""

echo "   For small datasets (< 50 URLs):"
echo "   ./run_split.sh -r 10 -s"
echo ""

echo "   For medium datasets (50-200 URLs):"
echo "   ./run_split.sh -r 15 -p -s"
echo ""

echo "   For large datasets (200+ URLs):"
echo "   ./run_split.sh -f 8 -p"
echo "   ./combine_results.sh"
echo ""

echo "   For testing/debugging:"
echo "   ./run_split.sh -r 5     # No parallel, separate folders"
echo "" 