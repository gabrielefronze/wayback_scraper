# Wayback Scraper - Split Processing Guide

This guide covers the new split processing functionality that allows you to divide your dataset and run multiple scraper instances.

## Overview

The split functionality solves several key challenges:
- **Performance**: Run multiple scrapers in parallel for faster processing
- **Resource Management**: Control system load by splitting large datasets
- **Fault Tolerance**: If one split fails, others continue independently
- **Proxy Efficiency**: Better bandwidth utilization with multiple connections

## Quick Start

```bash
# Basic usage - split into files with 10 rows each
./run_split.sh -r 10

# Parallel processing with shared downloads folder (recommended)
./run_split.sh -r 10 -p -s

# View all examples and tips
./example_split_usage.sh
```

## Scripts

### 1. `run_split.sh` - Main Split Runner

**Purpose**: Splits your CSV file and runs multiple scraper instances

**Basic Syntax**:
```bash
./run_split.sh [OPTIONS]
```

**Key Options**:
- `-f NUMBER` - Split into exactly NUMBER files
- `-r NUMBER` - Split into files with NUMBER rows each
- `-p` - Run splits in parallel (default: sequential)
- `-s` - Use shared downloads folder (default: separate folders)
- `-i FILE` - Input CSV file (default: data.csv)
- `-o DIR` - Output directory (default: downloads)

### 2. `combine_results.sh` - Results Combiner

**Purpose**: Combines results from separate split runs

**Basic Syntax**:
```bash
./combine_results.sh [OPTIONS]
```

**Options**:
- `-i DIR` - Input directory with splits (default: downloads)
- `-o DIR` - Combined output directory (default: downloads_combined)

## Shared vs Separate Downloads

### Shared Downloads (`-s` flag) - **RECOMMENDED**

**How it works**:
- All splits save to the same `downloads/` folder
- Each split uses a unique state file: `wayback_scraper_state_split_N.json`
- Logs are separated: `logs_split_1/`, `logs_split_2/`, etc.
- Website folders are shared (no conflicts since URLs are unique)

**Benefits**:
✅ Space efficient - no duplicate directory structure  
✅ All results in one place  
✅ No conflicts between splits  
✅ Easy to manage  

**When to use**: Almost always, unless you need maximum isolation

### Separate Folders (default)

**How it works**:
- Each split creates its own folder: `downloads/split_1/`, `downloads/split_2/`, etc.
- Each split has its own complete environment
- Use `combine_results.sh` to merge afterwards

**Benefits**:
✅ Maximum isolation between runs  
✅ Easier debugging  
✅ Safer for testing  

**When to use**: Testing, debugging, or when you want complete separation

## Usage Examples

### Small Dataset (< 50 URLs)
```bash
# Simple parallel processing with shared folder
./run_split.sh -r 10 -p -s
```

### Medium Dataset (50-200 URLs)
```bash
# More parallel workers with shared folder
./run_split.sh -r 15 -p -s
```

### Large Dataset (200+ URLs)
```bash
# Maximum parallelism with separate folders, then combine
./run_split.sh -f 8 -p
./combine_results.sh
```

### Testing/Debugging
```bash
# Sequential processing with separate folders
./run_split.sh -r 5
```

## Advanced Usage

### Custom Input and Output
```bash
./run_split.sh -i my_data.csv -o my_results -r 12 -p -s
```

### Monitoring Progress
```bash
# Check running containers
docker ps

# View logs for specific split
docker logs wayback-scraper-split-1

# Monitor shared state files
ls downloads/wayback_scraper_state_split_*.json
```

### Resume Failed Runs
The scraper automatically resumes from where it left off using state files:
- Shared mode: `wayback_scraper_state_split_N.json`
- Separate mode: `split_N/wayback_scraper_state.json`

## Directory Structure

### Shared Downloads Mode (`-s`)
```
downloads/
├── example_com_up_to_20160331/     # Website downloads
├── another_site_up_to_20170630/
├── wayback_scraper_state_split_1.json  # State files
├── wayback_scraper_state_split_2.json
├── logs_split_1/                   # Separate log directories
│   ├── wayback_scraper.log
│   └── download_*.log
└── logs_split_2/
    ├── wayback_scraper.log
    └── download_*.log
```

### Separate Folders Mode (default)
```
downloads/
├── split_1/
│   ├── example_com_up_to_20160331/
│   ├── wayback_scraper_state.json
│   └── logs/
├── split_2/
│   ├── another_site_up_to_20170630/
│   ├── wayback_scraper_state.json
│   └── logs/
└── split_3/
    └── ...
```

## Tips and Best Practices

### Resource Management
- **CPU**: Use `-p` for parallel processing if you have multiple cores
- **Memory**: Smaller splits (5-15 rows) use less memory per container
- **Disk**: Use `-s` to save space with shared downloads
- **Network**: With Tor proxy, sequential might be more reliable

### Split Strategies
- **By rows (`-r`)**: Good for consistent workload per split
- **By files (`-f`)**: Good when you know exactly how many parallel jobs you want
- **Smaller splits**: Better for limited proxy bandwidth
- **Larger splits**: More efficient for powerful systems

### Troubleshooting
1. **Container conflicts**: Each split uses a unique container name
2. **State file issues**: Check permissions on state files
3. **Log analysis**: Look at split-specific logs for debugging
4. **Resume issues**: Delete state files to start fresh
5. **Resource limits**: Reduce parallel splits if system is overwhelmed

### Proxy Considerations
- **Tor**: Sequential processing might be more stable
- **HTTP Proxy**: Parallel processing usually works well
- **Rate Limiting**: Smaller splits help avoid rate limits
- **IP Rotation**: Each split can potentially get different IPs

## Migration from Original Script

The original `run.sh` script continues to work unchanged. The split functionality is completely separate:

```bash
# Original single-threaded approach
./run.sh

# New split approach
./run_split.sh -r 10 -s
```

Both scripts use the same Docker image and configuration, so you can switch between them as needed. 