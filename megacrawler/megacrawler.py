#!/usr/bin/env python3
"""
Keyword Frequency Analyzer for HTML Files

This script analyzes HTML files in a directory structure to count occurrences
of sustainability-related keywords and generates a comprehensive CSV report.
"""

import os
import re
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, DefaultDict
from collections import defaultdict
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('megacrawler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class Config:
    """Configuration settings for the keyword analyzer."""
    input_dir: str = "combined"
    keywords_file: str = "keys.txt"
    output_file: str = "site_keyword_frequencies.csv"
    max_workers: int = None
    min_occurrence_threshold: int = 1
    case_sensitive: bool = False
    include_file_paths: bool = True
    chunk_size: int = 1000
    show_file_progress: bool = False  # New option to control file progress bars

class KeywordAnalyzer:
    """Main class for analyzing keyword frequencies in HTML files."""
    
    def __init__(self, config: Config):
        self.config = config
        self.keywords = self._load_keywords()
        self.compiled_patterns = self._compile_patterns()
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'keywords_found': 0,
            'total_occurrences': 0
        }
    
    def _load_keywords(self) -> List[str]:
        """Load keywords from file with error handling."""
        try:
            keywords_path = Path(self.config.keywords_file)
            if not keywords_path.exists():
                raise FileNotFoundError(f"Keywords file not found: {keywords_path}")
            
            # Read file as plain text - one keyword per line
            with open(keywords_path, 'r', encoding='utf-8') as f:
                keywords = [line.strip() for line in f if line.strip()]
            
            if not keywords:
                raise ValueError("No keywords found in file")
            
            logger.info(f"Loaded {len(keywords)} keywords from {keywords_path}")
            return keywords
            
        except Exception as e:
            logger.error(f"Failed to load keywords: {e}")
            sys.exit(1)
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for efficient matching."""
        patterns = {}
        for keyword in self.keywords:
            # Escape special regex characters
            escaped_keyword = re.escape(keyword)
            # Create word boundary pattern
            pattern = rf'\b{escaped_keyword}\b'
            flags = 0 if self.config.case_sensitive else re.IGNORECASE
            patterns[keyword] = re.compile(pattern, flags)
        return patterns
    
    def clean_html(self, html_content: str) -> str:
        """Extract clean text from HTML/XML content."""
        try:
            # Filter out the XMLParsedAsHTMLWarning
            from bs4 import XMLParsedAsHTMLWarning
            import warnings
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            
            # Try HTML parser first, fall back to XML if needed
            try:
                soup = BeautifulSoup(html_content, 'html.parser')
            except Exception:
                # If HTML parser fails, try XML parser
                soup = BeautifulSoup(html_content, 'xml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text(separator=' ')
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            return text
            
        except Exception as e:
            logger.warning(f"Failed to parse HTML/XML: {e}")
            return ""
    
    def count_keywords_in_file(self, filepath: Path) -> Tuple[str, Dict[str, int]]:
        """Count keyword occurrences in a single file."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                text = self.clean_html(f.read())
            
            if not text:
                return filepath.name, {}
            
            file_results = {}
            for keyword, pattern in self.compiled_patterns.items():
                count = len(pattern.findall(text))
                if count >= self.config.min_occurrence_threshold:
                    file_results[keyword] = count
            
            self.stats['files_processed'] += 1
            if file_results:
                self.stats['keywords_found'] += len(file_results)
                self.stats['total_occurrences'] += sum(file_results.values())
            
            return filepath.name, file_results
            
        except Exception as e:
            logger.warning(f"Failed to process {filepath}: {e}")
            self.stats['files_failed'] += 1
            return filepath.name, {}
    
    def get_html_files(self, site_path: Path) -> List[Path]:
        """Get all HTML files in a site directory."""
        html_files = []
        try:
            for file_path in site_path.rglob("*.html"):
                if file_path.is_file():
                    html_files.append(file_path)
        except Exception as e:
            logger.error(f"Error scanning {site_path}: {e}")
        
        return html_files
    
    def parse_site_info(self, site_name: str) -> Tuple[str, str]:
        """Parse website URL and date from site folder name."""
        try:
            # Expected format: www_vennli.com_up_to_20160330
            if '_up_to_' in site_name:
                parts = site_name.split('_up_to_')
                if len(parts) == 2:
                    url = parts[0].replace('_', '.')  # Convert www_vennli_com to www.vennli.com
                    date_str = parts[1]
                    
                    # Format date for better readability (YYYY-MM-DD)
                    if len(date_str) == 8:  # YYYYMMDD format
                        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    else:
                        formatted_date = date_str
                    
                    return url, formatted_date
                else:
                    logger.warning(f"Unexpected site name format: {site_name}")
                    return site_name, "Unknown"
            else:
                # Handle cases where the format doesn't match
                logger.warning(f"Site name doesn't contain '_up_to_': {site_name}")
                return site_name, "Unknown"
                
        except Exception as e:
            logger.warning(f"Failed to parse site info for {site_name}: {e}")
            return site_name, "Unknown"
    
    def process_site(self, site_path: Path) -> Tuple[str, str, str, Dict]:
        """Process all HTML files in a site directory."""
        site_name = site_path.name
        url, date = self.parse_site_info(site_name)
        site_results = defaultdict(lambda: {'total': 0, 'files': set()})
        
        html_files = self.get_html_files(site_path)
        logger.info(f"Processing {len(html_files)} files in {site_name}")
        
        # Use tqdm only if show_file_progress is enabled
        file_iterator = tqdm(html_files, desc=f"Processing {site_name}", leave=False) if self.config.show_file_progress else html_files
        
        for filepath in file_iterator:
            filename, file_counts = self.count_keywords_in_file(filepath)
            
            for keyword, count in file_counts.items():
                site_results[keyword]['total'] += count
                if self.config.include_file_paths:
                    relative_path = filepath.relative_to(site_path)
                    site_results[keyword]['files'].add(str(relative_path))
        
        return site_name, url, date, dict(site_results)
    
    def run_analysis(self) -> pd.DataFrame:
        """Run the complete keyword analysis with wide format output."""
        base_dir = Path(self.config.input_dir)
        if not base_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {base_dir}")
        
        site_dirs = [d for d in base_dir.iterdir() if d.is_dir()]
        if not site_dirs:
            raise ValueError(f"No site directories found in {base_dir}")
        
        logger.info(f"Found {len(site_dirs)} site directories")
        
        max_workers = self.config.max_workers or min(os.cpu_count(), len(site_dirs))
        all_results = []
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_site = {
                executor.submit(self.process_site, site_path): site_path 
                for site_path in site_dirs
            }
            
            # Process completed tasks with overall progress bar
            completed_sites = 0
            total_sites = len(site_dirs)
            
            with tqdm(total=total_sites, desc="Processing sites", unit="site") as pbar:
                for future in as_completed(future_to_site):
                    try:
                        site_name, url, date, site_result = future.result()
                        completed_sites += 1
                        
                        # Update progress bar with current site info
                        pbar.set_postfix({
                            'current': site_name,
                            'completed': f"{completed_sites}/{total_sites}",
                            'results': len(all_results)
                        })
                        
                        # Store results for this site
                        all_results.append({
                            'company': site_name,
                            'website': url,
                            'date': date,
                            'keywords_found': set(site_result.keys())
                        })
                        
                        pbar.update(1)
                        logger.info(f"Completed {site_name}: {len(site_result)} keywords found")
                        
                    except Exception as e:
                        site_path = future_to_site[future]
                        logger.error(f"Failed to process {site_path}: {e}")
                        completed_sites += 1
                        pbar.update(1)
        
        logger.info(f"Analysis complete! Processing {len(all_results)} sites")
        
        # Create wide format DataFrame
        if not all_results:
            logger.warning("No results to process")
            return pd.DataFrame()
        
        # Use ALL keywords from the keywords file, not just the ones found
        sorted_keywords = sorted(self.keywords)
        logger.info(f"Creating output with {len(sorted_keywords)} keyword columns")
        
        # Create DataFrame with wide format
        rows = []
        for result in all_results:
            row = {
                'company': result['company'],
                'website': result['website'],
                'date': result['date']
            }
            # Add keyword columns - "1" if keyword found, "0" if not
            for keyword in sorted_keywords:
                row[keyword] = "1" if keyword in result['keywords_found'] else "0"
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Save to CSV
        output_path = Path(self.config.output_file)
        df.to_csv(output_path, index=False)
        logger.info(f"Results saved to {output_path}")
        
        return df
    
    def save_results(self, df: pd.DataFrame) -> None:
        """Save results to CSV file (now handled in run_analysis)."""
        try:
            # Results are already saved during computation
            logger.info(f"Results saved to {self.config.output_file}")
            
            # Print summary statistics
            logger.info(f"Analysis complete:")
            logger.info(f"  - Files processed: {self.stats['files_processed']}")
            logger.info(f"  - Files failed: {self.stats['files_failed']}")
            logger.info(f"  - Keywords found: {self.stats['keywords_found']}")
            logger.info(f"  - Total occurrences: {self.stats['total_occurrences']}")
            
            if not df.empty:
                logger.info(f"  - Sites analyzed: {df['company'].nunique()}")
                logger.info(f"  - Unique keywords found: {df.shape[1] - 3}") # Exclude 'company', 'website', 'date'
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze keyword frequencies in HTML files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python megacrawler.py
  python megacrawler.py --input-dir data --output-file results.csv
  python megacrawler.py --max-workers 4 --min-occurrence 2
  python megacrawler.py --show-file-progress  # Show progress for individual files
        """
    )
    
    parser.add_argument("--input-dir", default="combined",
                       help="Input directory containing site folders (default: combined)")
    parser.add_argument("--keywords-file", default="keys.txt",
                       help="File containing keywords (default: keys.txt)")
    parser.add_argument("--output-file", default="site_keyword_frequencies.csv",
                       help="Output CSV file (default: site_keyword_frequencies.csv)")
    parser.add_argument("--max-workers", type=int, default=None,
                       help="Maximum number of worker processes (default: CPU count)")
    parser.add_argument("--min-occurrence", type=int, default=1,
                       help="Minimum occurrence threshold (default: 1)")
    parser.add_argument("--case-sensitive", action="store_true",
                       help="Case-sensitive keyword matching")
    parser.add_argument("--no-file-paths", action="store_true",
                       help="Exclude file paths from output")
    parser.add_argument("--chunk-size", type=int, default=1000,
                       help="Chunk size for processing (default: 1000)")
    parser.add_argument("--show-file-progress", action="store_true",
                       help="Show progress bars for individual files (default: False)")
    
    args = parser.parse_args()
    
    # Create configuration
    config = Config(
        input_dir=args.input_dir,
        keywords_file=args.keywords_file,
        output_file=args.output_file,
        max_workers=args.max_workers,
        min_occurrence_threshold=args.min_occurrence,
        case_sensitive=args.case_sensitive,
        include_file_paths=not args.no_file_paths,
        chunk_size=args.chunk_size,
        show_file_progress=args.show_file_progress
    )
    
    try:
        # Initialize analyzer
        analyzer = KeywordAnalyzer(config)
        
        # Run analysis
        logger.info("Starting keyword analysis...")
        results_df = analyzer.run_analysis()
        
        # Save results
        analyzer.save_results(results_df)
        
        logger.info("Analysis completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()