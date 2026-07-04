import re
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Strip spaces and convert to uppercase
    return text.strip().upper()

def standardize_vendor(name: str) -> str:
    if not name:
        return ""
    # Uppercase and strip spaces
    cleaned = name.strip().upper()
    # Remove symbols like commas, periods, etc.
    cleaned = re.sub(r'[.,;\-&]', ' ', cleaned)
    # Normalize spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Suffixes to remove
    suffixes = [
        r'\bPVT\s+LTD\b', r'\bPRIVATE\s+LIMITED\b', r'\bLTD\b', r'\bLIMITED\b',
        r'\bINC\b', r'\bINCORPORATED\b', r'\bCORP\b', r'\bCORPORATION\b',
        r'\bCO\b', r'\bCOMPANY\b', r'\bLLC\b'
    ]
    
    for s in suffixes:
        cleaned = re.sub(s, '', cleaned).strip()
        
    # Re-normalize spaces after suffix removal
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def clean_amount(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
        
    s = str(val).strip()
    # Remove currency symbols and formatting commas, keeping period as decimal separator
    # Examples: "$1,250.50" -> "1250.50", "Rs. 450" -> "450"
    # Identify and clean standard European formatting where comma is decimal separator (e.g. "1.250,50")
    if ',' in s and '.' in s:
        # Check which one comes last
        if s.find(',') > s.find('.'):
            # European: dot is thousands, comma is decimal
            s = s.replace('.', '').replace(',', '.')
        else:
            # US: comma is thousands, dot is decimal
            s = s.replace(',', '')
    elif ',' in s:
        # Only comma is present. Is it thousands or decimal?
        # If followed by exactly 2 digits, it is likely a decimal separator.
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
            
    # Extract only numeric parts (+ or - sign, digits, decimal point)
    match = re.search(r'[-+]?\d*\.\d+|\d+', s)
    if match:
        try:
            return float(match.group())
        except ValueError:
            pass
    return 0.0

def clean_date(val) -> date:
    if isinstance(val, (date, datetime)):
        if isinstance(val, datetime):
            return val.date()
        return val
        
    s = str(val).strip()
    # Replace separators with slash or dash for uniform parsing
    s = re.sub(r'[\s\.\\/]', '-', s)
    
    # Try parsing common date formats
    formats = [
        "%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y",
        "%Y-%b-%d", "%d-%b-%Y",  # formats with month names like Jan, Feb
        "%y-%m-%d", "%d-%m-%y", "%m-%d-%y"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
            
    # Fallback to current date on parsing failure
    logger.warning(f"Could not parse date string: {val}. Defaulting to today.")
    return date.today()

def deduplicate_lines(lines: list) -> list:
    # Deduplicate line items list based on matching SKU and descriptions
    seen = set()
    deduped = []
    for line in lines:
        sku = clean_text(line.get("sku", ""))
        desc = clean_text(line.get("description", ""))
        key = (sku, desc)
        if key not in seen:
            seen.add(key)
            deduped.append(line)
    return deduped
