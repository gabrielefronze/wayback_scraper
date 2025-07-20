#!/bin/bash

# Wayback Scraper - Split Dataset Run Script (Shared Downloads Version)
# This script splits the input dataset and runs multiple scraper instances
# All instances share the same downloads folder for efficiency

set -e

# Default values
SPLIT_TYPE="rows"
SPLIT_VALUE=10
PARALLEL=false
INPUT_FILE="data.csv"
BASE_OUTPUT_DIR="downloads"
SHARED_DOWNLOADS=false
MIN_DELAY=60   # Increased from 30 to 60 seconds for better anti-ban protection
MAX_DELAY=300  # Increased from 180 to 300 seconds for better anti-ban protection

# Function to display usage
usage() {
    echo "🚀 Wayback Scraper - Split Dataset Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -f, --files NUMBER        Split into NUMBER of files (default: split by rows)"
    echo "  -r, --rows NUMBER         Split into files with NUMBER rows each (default: 10)"
    echo "  -p, --parallel            Run all splits in parallel (default: sequential)"
    echo "  -s, --shared              Use shared downloads folder (default: separate folders)"
    echo "  -i, --input FILE          Input CSV file (default: data.csv)"
    echo "  -o, --output DIR          Base output directory (default: downloads)"
    echo "  --min-delay SECONDS       Minimum delay between parallel starts (default: 30)"
    echo "  --max-delay SECONDS       Maximum delay between parallel starts (default: 180)"
    echo "  -h, --help                Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -r 5 -s                # Split into files with 5 rows, shared downloads"
    echo "  $0 -f 3 -p -s             # Split into 3 files, parallel + shared"
    echo "  $0 -r 10 -p               # Split with separate folders (safer)"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--files)
            SPLIT_TYPE="files"
            SPLIT_VALUE="$2"
            shift 2
            ;;
        -r|--rows)
            SPLIT_TYPE="rows"
            SPLIT_VALUE="$2"
            shift 2
            ;;
        -p|--parallel)
            PARALLEL=true
            shift
            ;;
        -s|--shared)
            SHARED_DOWNLOADS=true
            shift
            ;;
        -i|--input)
            INPUT_FILE="$2"
            shift 2
            ;;
        -o|--output)
            BASE_OUTPUT_DIR="$2"
            shift 2
            ;;
        --min-delay)
            MIN_DELAY="$2"
            shift 2
            ;;
        --max-delay)
            MAX_DELAY="$2"
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

echo "🚀 Wayback Scraper - Split Dataset Runner"
echo "=========================================="
echo ""

# Validate split value
if ! [[ "$SPLIT_VALUE" =~ ^[0-9]+$ ]] || [ "$SPLIT_VALUE" -lt 1 ]; then
    echo "❌ Error: Split value must be a positive integer"
    exit 1
fi

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment from .env file"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if Tor is running (if using Tor proxy)
if [ "$PROXY_URL" = "socks5://127.0.0.1:9050" ]; then
    echo "🔍 Checking Tor connection..."
    if ! curl --socks5 localhost:9050 --socks5-hostname localhost:9050 -s https://check.torproject.org/ | grep -q "Congratulations"; then
        echo "❌ Tor is not running or not working properly"
        echo "Please start Tor: brew services start tor (macOS) or sudo systemctl start tor (Linux)"
        exit 1
    fi
    echo "✅ Tor is running and working!"
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running or not accessible"
    echo "Please start Docker Desktop and try again"
    exit 1
fi

# Check if input CSV file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Error: Input file '$INPUT_FILE' not found!"
    echo ""
    echo "📋 Please create a CSV file with your URLs and deal dates."
    echo "Required format:"
    echo "URL;Deal Date"
    echo "https://example.com;2016-09-30"
    echo ""
    exit 1
fi

# Check if the Docker image exists
if ! docker image inspect wayback-scraper:latest > /dev/null 2>&1; then
    echo "❌ Error: Docker image 'wayback-scraper:latest' not found!"
    echo ""
    echo "📥 Please run the load script first:"
    echo "   ./load_image.sh"
    echo ""
    exit 1
fi

# Create splits directory
SPLITS_DIR="splits"
mkdir -p "$SPLITS_DIR"

# Clean up any existing split files
rm -f "$SPLITS_DIR"/data_split_*.csv

echo "📊 Input file: $INPUT_FILE"
echo "📁 Base output directory: $BASE_OUTPUT_DIR"
echo "🔄 Split type: $SPLIT_TYPE ($SPLIT_VALUE)"
echo "⚡ Parallel execution: $PARALLEL"
echo "🗂️  Shared downloads: $SHARED_DOWNLOADS"
if [ "$PARALLEL" = true ]; then
    echo "🛡️  Anti-ban delays: ${MIN_DELAY}-${MAX_DELAY} seconds between starts"
fi
echo ""

# Count total rows (excluding header)
TOTAL_ROWS=$(tail -n +2 "$INPUT_FILE" | wc -l | tr -d ' ')
echo "📈 Total data rows: $TOTAL_ROWS"

# Extract header
HEADER=$(head -n 1 "$INPUT_FILE")

# Split the file
if [ "$SPLIT_TYPE" = "files" ]; then
    # Split into specified number of files
    ROWS_PER_FILE=$((($TOTAL_ROWS + $SPLIT_VALUE - 1) / $SPLIT_VALUE))
    ACTUAL_FILES=$SPLIT_VALUE
    echo "📄 Splitting into $SPLIT_VALUE files (~$ROWS_PER_FILE rows each)"
    
    # Use split command to divide the data (excluding header)
    tail -n +2 "$INPUT_FILE" | split -l "$ROWS_PER_FILE" - "$SPLITS_DIR/data_split_"
    
    # Add headers and rename files
    SPLIT_COUNT=0
    for file in "$SPLITS_DIR"/data_split_*; do
        if [ -f "$file" ]; then
            SPLIT_COUNT=$((SPLIT_COUNT + 1))
            mv "$file" "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv.tmp"
            echo "$HEADER" > "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv"
            cat "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv.tmp" >> "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv"
            rm "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv.tmp"
        fi
    done
else
    # Split by rows per file
    ROWS_PER_FILE=$SPLIT_VALUE
    ACTUAL_FILES=$((($TOTAL_ROWS + $ROWS_PER_FILE - 1) / $ROWS_PER_FILE))
    echo "📄 Splitting into files with $ROWS_PER_FILE rows each (~$ACTUAL_FILES files)"
    
    # Use split command to divide the data
    tail -n +2 "$INPUT_FILE" | split -l "$ROWS_PER_FILE" - "$SPLITS_DIR/data_split_"
    
    # Add headers and rename files
    SPLIT_COUNT=0
    for file in "$SPLITS_DIR"/data_split_*; do
        if [ -f "$file" ]; then
            SPLIT_COUNT=$((SPLIT_COUNT + 1))
            mv "$file" "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv.tmp"
            echo "$HEADER" > "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv"
            cat "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv.tmp" >> "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv"
            rm "$SPLITS_DIR/data_split_${SPLIT_COUNT}.csv.tmp"
        fi
    done
fi

echo "✅ Created $SPLIT_COUNT split files"
echo ""

# Display split information
for i in $(seq 1 $SPLIT_COUNT); do
    SPLIT_ROWS=$(tail -n +2 "$SPLITS_DIR/data_split_${i}.csv" | wc -l | tr -d ' ')
    echo "   📄 data_split_${i}.csv: $SPLIT_ROWS rows"
done
echo ""

# Set up output directories
if [ "$SHARED_DOWNLOADS" = true ]; then
    echo "🗂️  Using shared downloads folder: $BASE_OUTPUT_DIR"
    mkdir -p "$BASE_OUTPUT_DIR"
    OUTPUT_MODE="shared"
else
    echo "📁 Using separate folders for each split"
    OUTPUT_MODE="separate"
fi

# Proxy configuration check and display
if [ -n "$PROXY_URL" ]; then
    echo "🔗 Proxy Configuration:"
    echo "   URL: $PROXY_URL"
    if [ "$PROXY_URL" = "socks5://127.0.0.1:9050" ]; then
        echo "   Type: Tor (SOCKS5)"
    fi
    if [ -n "$PROXY_USER" ]; then
        echo "   User: $PROXY_USER"
    fi
    if [ -n "$PROXY_PASS" ]; then
        echo "   Password: [HIDDEN]"
    fi
    echo ""
else
    echo "🌐 Using direct connection (no proxy)"
    echo " To use Tor, create a .env file with: PROXY_URL=socks5://127.0.0.1:9050"
    echo ""
fi

# Function to run scraper for a single split
run_split() {
    local split_num=$1
    local split_file="$SPLITS_DIR/data_split_${split_num}.csv"
    local container_name="wayback-scraper-split-${split_num}"
    
    if [ "$SHARED_DOWNLOADS" = true ]; then
        local output_dir="$BASE_OUTPUT_DIR"
        local state_file_name="wayback_scraper_state_split_${split_num}.json"
        local log_dir="$BASE_OUTPUT_DIR/logs_split_${split_num}"
    else
        local output_dir="${BASE_OUTPUT_DIR}/split_${split_num}"
        local state_file_name="wayback_scraper_state.json"
        local log_dir="$output_dir/logs"
    fi
    
    echo "🔄 Starting scraper for split $split_num..."
    
    # Create output directory
    mkdir -p "$output_dir"
    mkdir -p "$log_dir"
    
    # Create a temporary docker-compose file for this split
    local compose_file="docker-compose-split-${split_num}.yml"
    
    cat > "$compose_file" << EOF
version: '3.8'

services:
  wayback-scraper-split-${split_num}:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ${container_name}
    network_mode: host
    volumes:
      # Mount the split CSV file from the host
      - ./${split_file}:/app/data.csv:ro
      # Mount the downloads folder for persistent storage
      - ./${output_dir}:/app/downloads
    working_dir: /app
    command: ["python3", "wayback_scraper.py", "data.csv", "--output", "downloads", "--state-file", "downloads/${state_file_name}"]
    environment:
      # Set Python to not buffer output for better logging
      - PYTHONUNBUFFERED=1
      # Proxy configuration (optional)
      - PROXY_URL=\${PROXY_URL:-socks5://127.0.0.1:9050}
      - PROXY_USER=\${PROXY_USER:-}
      - PROXY_PASS=\${PROXY_PASS:-}
      - TOR_NEW_CIRCUIT_PER_REQUEST=true
      # Add connection pool limits for better anti-ban protection
      - CONNECTION_POOL_SIZE=5
      - RATE_LIMIT=0.5
    restart: unless-stopped
    # Keep container running for debugging if needed
    tty: true
    stdin_open: true
EOF
    
    # Run the scraper
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$compose_file" up --build
    else
        docker compose -f "$compose_file" up --build
    fi
    
    # Clean up the temporary compose file
    rm -f "$compose_file"
    
    echo "✅ Split $split_num completed!"
    if [ "$SHARED_DOWNLOADS" = true ]; then
        echo "📁 Results saved to shared folder: $output_dir"
        echo "📋 State file: $output_dir/$state_file_name"
        echo "📝 Logs: $log_dir/"
    else
        echo "📁 Results saved to: $output_dir"
    fi
    echo ""
}

# Start the scraping process
echo "🚀 Starting scraper processes..."
echo ""

if [ "$PARALLEL" = true ]; then
    echo "⚡ Running splits in parallel with random delays..."
    
    # Array to store background process PIDs
    PIDS=()
    
    # Calculate random delays to avoid getting banned
    echo "🛡️  Anti-ban protection: Random delays between ${MIN_DELAY}-${MAX_DELAY} seconds"
    echo ""
    
    # Start all splits in background with random delays
    for i in $(seq 1 $SPLIT_COUNT); do
        if [ $i -gt 1 ]; then
            # Generate random delay between MIN_DELAY and MAX_DELAY seconds
            DELAY=$((RANDOM % (MAX_DELAY - MIN_DELAY + 1) + MIN_DELAY))
            echo "⏳ Waiting $DELAY seconds before starting split $i (anti-ban protection)..."
            sleep $DELAY
        fi
        
        echo "🔄 Starting split $i in background..."
        run_split "$i" &
        PIDS+=($!)
        
        # Small additional delay to avoid overwhelming the system
        sleep 5
    done
    
    echo "⏳ Waiting for all splits to complete..."
    
    # Wait for all background processes to complete
    for pid in "${PIDS[@]}"; do
        wait $pid
        if [ $? -eq 0 ]; then
            echo "✅ One split completed successfully"
        else
            echo "❌ One split failed"
        fi
    done
    
else
    echo "🔄 Running splits sequentially..."
    
    # Run splits one by one
    for i in $(seq 1 $SPLIT_COUNT); do
        echo "▶️  Processing split $i of $SPLIT_COUNT"
        run_split "$i"
        
        if [ $i -lt $SPLIT_COUNT ]; then
            echo "⏸️  Brief pause before next split..."
            sleep 5
        fi
    done
fi

echo ""
echo "🎉 All splits completed!"
echo ""
echo "📊 Summary:"
echo "   Total splits processed: $SPLIT_COUNT"
echo "   Total rows processed: $TOTAL_ROWS"
if [ "$SHARED_DOWNLOADS" = true ]; then
    echo "   Shared results location: $BASE_OUTPUT_DIR/"
    echo "   State files: wayback_scraper_state_split_*.json"
    echo "   Log directories: logs_split_*/"
else
    echo "   Results location: $BASE_OUTPUT_DIR/"
    echo "📁 Individual split results:"
    for i in $(seq 1 $SPLIT_COUNT); do
        echo "   📂 Split $i: ${BASE_OUTPUT_DIR}/split_${i}/"
    done
fi
echo ""
echo "🧹 Cleaning up split files..."
rm -rf "$SPLITS_DIR"
echo "✅ Cleanup completed!" 