"""
Utility functions for handling financial statement periods and avoiding cumulative overlaps
"""
import re
from datetime import datetime
from typing import Set, Optional

def extract_period_end_date(period_string: str) -> Optional[str]:
    """
    Extract the end date from a period string
    
    Examples:
    - "Three Months Ended March 31, 2024" -> "March 31, 2024"
    - "Six Months Ended June 30, 2024" -> "June 30, 2024"
    - "Nine Months Ended September 30, 2024" -> "September 30, 2024"
    """
    if not period_string:
        return None
    
    # Pattern to match "Ended [Date]" or "ended [Date]"
    pattern = r'ended\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})'
    match = re.search(pattern, period_string, re.IGNORECASE)
    
    if match:
        return match.group(1)
    
    # Alternative pattern for different formats
    pattern2 = r'(\w+\s+\d{1,2},\s+\d{4})$'
    match2 = re.search(pattern2, period_string)
    
    if match2:
        return match2.group(1)
    
    return None

def is_cumulative_overlap(period_string: str, seen_end_dates: Set[str]) -> bool:
    """
    Check if this period represents a cumulative overlap with existing periods
    
    Logic:
    - If we have "Three Months Ended March 31, 2024", don't add "Six Months Ended March 31, 2024"
    - If we have "Six Months Ended June 30, 2024", don't add "Nine Months Ended June 30, 2024"
    - Prefer shorter periods over longer cumulative ones
    """
    if not period_string or not seen_end_dates:
        return False
    
    period_end_date = extract_period_end_date(period_string)
    if not period_end_date:
        return False
    
    # Check if we already have data for this end date
    if period_end_date in seen_end_dates:
        return True
    
    # Extract period length (Three, Six, Nine, Twelve months)
    period_lower = period_string.lower()
    
    # If this is a longer cumulative period, check if we have shorter periods for the same year
    if any(keyword in period_lower for keyword in ['six months', 'nine months', 'twelve months']):
        # Extract year from the period
        year_match = re.search(r'\d{4}', period_string)
        if year_match:
            year = year_match.group()
            
            # Check if we have any shorter periods from the same year
            for existing_date in seen_end_dates:
                if year in existing_date:
                    # We already have data from this year, skip longer cumulative periods
                    return True
    
    return False

def get_period_priority(period_string: str) -> int:
    """
    Get priority for period selection (lower number = higher priority)
    Prefer quarterly over cumulative periods
    """
    if not period_string:
        return 999
    
    period_lower = period_string.lower()
    
    if 'three months' in period_lower:
        return 1  # Highest priority - quarterly
    elif 'six months' in period_lower:
        return 2  # Lower priority - semi-annual
    elif 'nine months' in period_lower:
        return 3  # Even lower - nine months
    elif 'twelve months' in period_lower or 'year' in period_lower:
        return 4  # Lowest priority - annual
    else:
        return 5  # Unknown format
