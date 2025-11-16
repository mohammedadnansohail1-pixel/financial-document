"""
Utility helper functions
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)


def generate_id(*args) -> str:
    """
    Generate unique ID from arguments
    """
    content = "_".join(str(arg) for arg in args)
    return hashlib.md5(content.encode()).hexdigest()


def clean_text(text: str) -> str:
    """
    Clean and normalize text
    """
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove special characters (keep alphanumeric and common punctuation)
    text = re.sub(r'[^\w\s.,!?;:()\-\'\"$%]', '', text)

    return text.strip()


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string in various formats
    """
    formats = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ'
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    return None


def format_currency(amount: float, currency: str = 'USD') -> str:
    """
    Format amount as currency
    """
    if abs(amount) >= 1e9:
        return f"${amount/1e9:.2f}B"
    elif abs(amount) >= 1e6:
        return f"${amount/1e6:.2f}M"
    elif abs(amount) >= 1e3:
        return f"${amount/1e3:.2f}K"
    else:
        return f"${amount:.2f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format value as percentage
    """
    return f"{value*100:.{decimals}f}%"


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safe division with default value
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def safe_get(dictionary: Dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary values
    """
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result


def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator with exponential backoff
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1

                    if attempts >= max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise

                    logger.warning(f"Attempt {attempts} failed: {e}. Retrying in {current_delay}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff

            return None
        return wrapper
    return decorator


def benchmark(func):
    """
    Benchmark decorator
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = (time.time() - start) * 1000

        logger.info(f"{func.__name__} took {elapsed:.2f}ms")

        return result
    return wrapper


def validate_email(email: str) -> bool:
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_cik(cik: str) -> bool:
    """
    Validate SEC CIK number
    """
    # CIK should be 10 digits
    pattern = r'^\d{10}$'
    return re.match(pattern, cik) is not None


def normalize_ticker(ticker: str) -> str:
    """
    Normalize stock ticker symbol
    """
    return ticker.upper().strip()


def extract_numbers(text: str) -> List[float]:
    """
    Extract all numbers from text
    """
    pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def batch_process(
    items: List[Any],
    process_func,
    batch_size: int = 100,
    show_progress: bool = False
) -> List[Any]:
    """
    Process items in batches
    """
    results = []
    batches = chunk_list(items, batch_size)

    for i, batch in enumerate(batches):
        batch_results = [process_func(item) for item in batch]
        results.extend(batch_results)

        if show_progress:
            progress = (i + 1) / len(batches) * 100
            logger.info(f"Progress: {progress:.1f}% ({i+1}/{len(batches)} batches)")

    return results


def merge_dicts(*dicts: Dict) -> Dict:
    """
    Merge multiple dictionaries
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    Flatten nested dictionary
    """
    items = []

    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change
    """
    if old_value == 0:
        return 0.0

    return ((new_value - old_value) / abs(old_value)) * 100


def is_business_day(date: datetime) -> bool:
    """
    Check if date is a business day (Monday-Friday)
    """
    return date.weekday() < 5


def get_quarter(date: datetime) -> Tuple[int, int]:
    """
    Get quarter and year from date
    """
    quarter = (date.month - 1) // 3 + 1
    return quarter, date.year


def quarter_to_dates(quarter: int, year: int) -> Tuple[datetime, datetime]:
    """
    Get start and end dates for a quarter
    """
    start_month = (quarter - 1) * 3 + 1
    start_date = datetime(year, start_month, 1)

    if quarter == 4:
        end_date = datetime(year, 12, 31)
    else:
        end_month = quarter * 3
        # Last day of the month
        if end_month in [1, 3, 5, 7, 8, 10, 12]:
            end_day = 31
        elif end_month in [4, 6, 9, 11]:
            end_day = 30
        else:  # February
            end_day = 29 if year % 4 == 0 else 28

        end_date = datetime(year, end_month, end_day)

    return start_date, end_date


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove invalid characters
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        name = name[:max_length - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name

    return filename


def format_json(data: Any, indent: int = 2) -> str:
    """
    Format data as pretty-printed JSON
    """
    return json.dumps(data, indent=indent, default=str)


def parse_json_safe(json_str: str, default: Any = None) -> Any:
    """
    Safely parse JSON string
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse JSON: {json_str[:100]}")
        return default


class Timer:
    """Context manager for timing code blocks"""

    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed = (time.time() - self.start_time) * 1000
        logger.info(f"{self.name} took {self.elapsed:.2f}ms")


class RateLimiter:
    """Simple rate limiter"""

    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []

    def is_allowed(self) -> bool:
        """Check if call is allowed"""
        now = time.time()

        # Remove old calls
        self.calls = [t for t in self.calls if now - t < self.time_window]

        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True

        return False

    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        while not self.is_allowed():
            time.sleep(0.1)
