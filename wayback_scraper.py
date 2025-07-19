#!/usr/bin/env python3
"""
Wayback Machine Scraper
Scrapes websites from the Wayback Machine using wayback-machine-downloader
for two different dates specified in a CSV file.
"""

import argparse
import os
import subprocess
import sys
import json
import logging
import time
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random

# CSV Column Constants - Modify these to match your CSV column names
WEBSITE_URL_COLUMN = 'URL'
DEAL_DATE_COLUMN = 'Deal Date'

# Time period parameters (in months)
MONTHS_BEFORE_DEAL = 6
MONTHS_AFTER_DEAL = 12

# State file name
STATE_FILE_NAME = 'wayback_scraper_state.json'

# Logging configuration
MAIN_LOG_FILE = 'wayback_scraper.log'

# Timeout in seconds
TIMEOUT = 900  # 15 minutes


def setup_logging(output_dir):
    """
    Setup logging configuration for both console and file output.
    """
    # Create logs directory
    logs_dir = os.path.join(output_dir, 'logs')
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    
    # Main log file path
    main_log_path = os.path.join(logs_dir, MAIN_LOG_FILE)
    
    # Configure logging for main script only
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler (main script logs only)
            logging.FileHandler(main_log_path, mode='a', encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Main log file: {main_log_path}")
    return logger


def create_download_logger(download_folder, url, date):
    """
    Create a logger specific to a download operation.
    """
    # Create download-specific log file
    log_filename = f"download_{date}.log"
    log_file = os.path.join(download_folder, log_filename)
    
    # Create logger for this download
    download_logger = logging.getLogger(f"download_{url}_{date}")
    download_logger.setLevel(logging.INFO)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Add handler to logger
    download_logger.addHandler(file_handler)
    
    return download_logger, log_file


def load_state(state_file_path):
    """
    Load the state from the state file.
    """
    if os.path.exists(state_file_path):
        try:
            with open(state_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not load state file {state_file_path}: {e}")
            return {}
    return {}


def save_state(state, state_file_path):
    """
    Save the state to the state file.
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(state_file_path), exist_ok=True)
        
        with open(state_file_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Could not save state file {state_file_path}: {e}")


def is_download_completed(state, website_url, date, folder_name):
    """
    Check if a download has already been completed.
    """
    if 'downloads' not in state:
        return False
    
    download_key = f"{website_url}_{date}_{folder_name}"
    return download_key in state['downloads']


def mark_download_completed(state, website_url, date, folder_name, success=True):
    """
    Mark a download as completed in the state.
    """
    if 'downloads' not in state:
        state['downloads'] = {}
    
    download_key = f"{website_url}_{date}_{folder_name}"
    state['downloads'][download_key] = {
        'completed_at': datetime.now().isoformat(),
        'success': success,
        'folder': folder_name
    }


def get_resume_stats(state, df):
    """
    Get statistics about resume progress.
    """
    if 'downloads' not in state:
        return 0, len(df) * 2  # 2 downloads per row
    
    completed = 0
    total = len(df) * 2  # 2 downloads per row
    
    for row_num, (index, row) in enumerate(df.iterrows(), 1):
        website_url = str(row[WEBSITE_URL_COLUMN]).strip()
        deal_date = str(row[DEAL_DATE_COLUMN]).strip()
        
        first_date, second_date = calculate_download_dates(deal_date)
        if first_date is None or second_date is None:
            continue
        
        sanitized_name = sanitize_folder_name(website_url)
        
        # Check first date download
        if is_download_completed(state, website_url, first_date, f"{sanitized_name}_up_to_{first_date}"):
            completed += 1
        
        # Check second date download
        if is_download_completed(state, website_url, second_date, f"{sanitized_name}_up_to_{second_date}"):
            completed += 1
    
    return completed, total


def sanitize_folder_name(url):
    """
    Create a safe folder name from a URL.
    """
    # Remove protocol
    if url.startswith(('http://', 'https://')):
        url = url.split('://', 1)[1]
    
    # Remove trailing slash
    url = url.rstrip('/')
    
    # Replace invalid characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        url = url.replace(char, '_')
    
    # Replace dots with underscores (except for file extensions)
    parts = url.split('.')
    if len(parts) > 1:
        # Keep the last part as extension if it looks like one
        if len(parts[-1]) <= 4 and parts[-1].isalpha():
            domain = '.'.join(parts[:-1])
            extension = parts[-1]
            domain = domain.replace('.', '_')
            url = f"{domain}.{extension}"
        else:
            url = url.replace('.', '_')
    else:
        url = url.replace('.', '_')
    
    return url


def parse_deal_date(deal_date_str):
    """
    Parse deal date string to datetime object.
    Handles format like "2016-09-30 00:00:00"
    """
    try:
        # Remove time part if present and parse date
        date_part = deal_date_str.split()[0]
        return datetime.strptime(date_part, '%Y-%m-%d')
    except (ValueError, AttributeError) as e:
        logging.warning(f"Could not parse deal date '{deal_date_str}': {e}")
        return None


def calculate_download_dates(deal_date_str):
    """
    Calculate the two download dates based on the deal date.
    """
    deal_date = parse_deal_date(deal_date_str)
    if deal_date is None:
        return None, None
    
    # Calculate dates
    first_date = deal_date - relativedelta(months=MONTHS_BEFORE_DEAL)
    second_date = deal_date + relativedelta(months=MONTHS_AFTER_DEAL)
    
    # Format as YYYYMMDD
    return first_date.strftime('%Y%m%d'), second_date.strftime('%Y%m%d')


def run_wayback_downloader(url, date, output_folder, state, state_file_path, proxy_config=None):
    """
    Run wayback-machine-downloader with specified parameters.
    """
    folder_name = os.path.basename(output_folder)
    
    # Check if already completed
    if is_download_completed(state, url, date, folder_name):
        logging.info(f"Skipping {url} (up to {date}) - already completed")
        return True
    
    logging.info(f"Downloading {url} up to {date} into {output_folder}")
    
    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Create download-specific logger
    download_logger, log_file = create_download_logger(output_folder, url, date)
    
    # Prepare wayback-machine-downloader command
    cmd = [
        "/build/bin/wayback_machine_downloader",
        url,
        "--to", date,
        "--directory", output_folder,
        "-o", r"/(\.(html|htm)$|\/[^\.]*\/?$)/",
        "-c", "2",  # Reduce from 8 to 2
    ]
    
    # Add proxy options if provided
    if proxy_config:
        if proxy_config.get('url'):
            cmd.extend(["--proxy", proxy_config['url']])
        if proxy_config.get('user'):
            cmd.extend(["--proxy-user", proxy_config['user']])
        if proxy_config.get('password'):
            cmd.extend(["--proxy-pass", proxy_config['password']])
    
    success = False
    start_time = time.time()
    
    try:
        # Log the command that will be run
        download_logger.info(f"Starting download for {url} up to {date}")
        download_logger.info(f"Command: {' '.join(cmd)}")
        download_logger.info(f"Output folder: {output_folder}")
        download_logger.info(f"Log file: {log_file}")
        if proxy_config:
            download_logger.info(f"Using proxy: {proxy_config.get('url', 'N/A')}")
        download_logger.info("-" * 80)
        
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=TIMEOUT
        )

        # Log successful completion
        download_logger.info("Download completed successfully")
        if result.stdout:
            download_logger.info(f"Command output:\n{result.stdout}")
        
        success = True
            
    except subprocess.CalledProcessError as e:
        error_msg = f"Error downloading {url} (up to {date}): {e}"
        download_logger.error(error_msg)
        if e.stderr:
            download_logger.error(f"Error details:\n{e.stderr}")
        if e.stdout:
            download_logger.info(f"Command output:\n{e.stdout}")
        logging.error(error_msg)
        
    except subprocess.TimeoutExpired:
        error_msg = f"Timeout downloading {url} (up to {date})"
        download_logger.error(error_msg)
        logging.error(error_msg)
        
    except Exception as e:
        error_msg = f"Unexpected error downloading {url} (up to {date}): {e}"
        download_logger.error(error_msg)
        logging.error(error_msg)
    
    finally:
        # Calculate and log timing information
        end_time = time.time()
        duration = end_time - start_time
        duration_minutes = duration / 60
        duration_seconds = duration % 60
        
        # Log timing to main log
        if success:
            logging.info(f"Successfully downloaded {url} (up to {date})")
        else:
            logging.error(f"Failed to download {url} (up to {date})")
        
        logging.info(f"Duration: {int(duration_minutes)}m {duration_seconds:.1f}s")
        logging.info(f"Download log saved to: {log_file}")
        
        # Always log completion status to download logger
        download_logger.info(f"Download process finished for {url} (up to {date})")
        download_logger.info(f"Success: {success}")
        download_logger.info(f"Duration: {int(duration_minutes)}m {duration_seconds:.1f}s")
        download_logger.info("-" * 80)
        
        # Remove the download logger handler to avoid memory leaks
        for handler in download_logger.handlers[:]:
            handler.close()
            download_logger.removeHandler(handler)
    
    # Mark as completed (or failed) and save state
    mark_download_completed(state, url, date, folder_name, success)
    save_state(state, state_file_path)
    
    return success


def run_wayback_downloader_with_retry(url, date, output_folder, state, state_file_path, proxy_config=None, max_retries=3):
    """
    Run wayback downloader with retry logic and exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            success = run_wayback_downloader(url, date, output_folder, state, state_file_path, proxy_config)
            if success:
                return True
            
            # If failed, wait before retry
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 60  # 1, 2, 4 minutes
                logging.info(f"Download failed, retrying in {wait_time} seconds... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                
        except Exception as e:
            logging.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 60
                time.sleep(wait_time)
    
    return False


def process_csv(csv_file, output_base_dir, state_file_path, proxy_config=None):
    """
    Process the CSV file and download websites for each row.
    """
    logging.info(f"Processing CSV file: {csv_file}")
    
    # Always load existing state (resume mode is default)
    state = load_state(state_file_path)
    
    try:
        # Read CSV file with semicolon delimiter
        df = pd.read_csv(csv_file, sep=';')
        
        # Check if CSV has the expected columns
        required_columns = [WEBSITE_URL_COLUMN, DEAL_DATE_COLUMN]
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logging.error(f"Error: CSV file is missing required columns: {missing_columns}")
            logging.error(f"Expected columns: {required_columns}")
            logging.error(f"Found columns: {list(df.columns)}")
            return False
        
        logging.info(f"Found {len(df)} websites to process")
        
        # Show resume statistics if state exists
        if state:
            completed, total = get_resume_stats(state, df)
            logging.info(f"Resume statistics: {completed}/{total} downloads already completed")
            logging.info(f"Remaining: {total - completed} downloads")
        else:
            logging.info(f"Starting fresh - no previous state found")
        
        # Process each row
        for row_num, (index, row) in enumerate(df.iterrows(), 1):
            website_url = str(row[WEBSITE_URL_COLUMN]).strip()
            deal_date = str(row[DEAL_DATE_COLUMN]).strip()
            
            # Calculate download dates
            first_date, second_date = calculate_download_dates(deal_date)
            if first_date is None or second_date is None:
                logging.warning(f"Skipping row {row_num} - invalid deal date: {deal_date}")
                continue
            
            logging.info(f"\n--- Processing row {row_num}/{len(df)} ---")
            logging.info(f"Website: {website_url}")
            logging.info(f"Deal date: {deal_date}")
            logging.info(f"First date ({MONTHS_BEFORE_DEAL} months before): {first_date}")
            logging.info(f"Second date ({MONTHS_AFTER_DEAL} months after): {second_date}")
            
            # Create sanitized folder name
            sanitized_name = sanitize_folder_name(website_url)
            
            # Create output folders
            first_date_folder = os.path.join(output_base_dir, f"{sanitized_name}_up_to_{first_date}")
            second_date_folder = os.path.join(output_base_dir, f"{sanitized_name}_up_to_{second_date}")
            
            # Download for first date
            run_wayback_downloader_with_retry(website_url, first_date, first_date_folder, state, state_file_path, proxy_config)
            
            # Add random delay between downloads (30-90 seconds)
            delay = random.uniform(30, 90)
            logging.info(f"Waiting {delay:.1f} seconds before next download...")
            time.sleep(delay)
            
            # Download for second date
            run_wayback_downloader_with_retry(website_url, second_date, second_date_folder, state, state_file_path, proxy_config)
            
            # Add delay between different websites (60-180 seconds)
            if row_num < len(df):
                delay = random.uniform(60, 180)
                logging.info(f"Waiting {delay:.1f} seconds before next website...")
                time.sleep(delay)
            
        logging.info(f"\n Finished processing all {len(df)} websites")
        
        # Final state save
        save_state(state, state_file_path)
        return True
        
    except FileNotFoundError:
        logging.error(f"Error: CSV file '{csv_file}' not found")
        return False
    except pd.errors.EmptyDataError:
        logging.error(f"Error: CSV file '{csv_file}' is empty")
        return False
    except Exception as e:
        logging.error(f"Error processing CSV file: {e}")
        return False


def main():
    """
    Main function to parse arguments and start the scraping process.
    """
    parser = argparse.ArgumentParser(
        description="Scrape websites from Wayback Machine for two different dates"
    )
    parser.add_argument(
        "csv_file",
        help="Path to CSV file with columns: URL, Deal Date (semicolon-separated)"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="downloads",
        help="Output directory for downloaded websites (default: downloads)"
    )
    parser.add_argument(
        "--state-file",
        "-s",
        help="Path to state file (default: <output_dir>/wayback_scraper_state.json)"
    )
    
    # Add proxy options
    parser.add_argument(
        "--proxy",
        help="Proxy URL (e.g., http://proxy.example.com:8080)"
    )
    parser.add_argument(
        "--proxy-user",
        help="Proxy username for authentication"
    )
    parser.add_argument(
        "--proxy-pass",
        help="Proxy password for authentication"
    )
    
    args = parser.parse_args()
    
    # Check if CSV file exists
    if not os.path.exists(args.csv_file):
        print(f"Error: CSV file '{args.csv_file}' does not exist")
        sys.exit(1)
    
    # Create output directory
    output_dir = os.path.abspath(args.output)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Set state file path
    state_file_path = args.state_file or os.path.join(output_dir, STATE_FILE_NAME)
    
    # Setup proxy configuration - check both command line args and environment variables
    proxy_config = None
    
    # First check command line arguments
    if args.proxy:
        proxy_config = {
            'url': args.proxy,
            'user': args.proxy_user,
            'password': args.proxy_pass
        }
    # If no command line proxy, check environment variables
    elif os.environ.get('PROXY_URL'):
        proxy_config = {
            'url': os.environ.get('PROXY_URL'),
            'user': os.environ.get('PROXY_USER'),
            'password': os.environ.get('PROXY_PASS')
        }
    
    # Setup logging
    logger = setup_logging(output_dir)
    
    logger.info("=" * 50)
    logger.info("Wayback Machine Scraper")
    logger.info(f"CSV file: {args.csv_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"State file: {state_file_path}")
    logger.info(f"Time periods: {MONTHS_BEFORE_DEAL} months before, {MONTHS_AFTER_DEAL} months after deal date")
    logger.info(f"Resume mode: ALWAYS ON (automatic)")
    if proxy_config:
        logger.info(f"Proxy: {proxy_config['url']}")
        if proxy_config.get('user'):
            logger.info(f"Proxy user: {proxy_config['user']}")
    else:
        logger.info("Proxy: None (direct connection)")
    logger.info("=" * 50)
    
    # Process the CSV file
    success = process_csv(args.csv_file, output_dir, state_file_path, proxy_config)
    
    if success:
        logger.info("✅ Scraping completed successfully!")
        logger.info(f"📁 Check the downloads in: {output_dir}")
    else:
        logger.error("❌ Scraping failed!")
        sys.exit(1)


if __name__ == "__main__":
    main() 