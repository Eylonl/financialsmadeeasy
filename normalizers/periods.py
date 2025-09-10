"""
Period Header Normalization Module
Handles parsing and normalization of period information from table headers
"""
import re
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class PeriodInfo:
    """Parsed period information"""
    original_header: str
    period_end_date: Optional[str]  # ISO format YYYY-MM-DD
    period_type: Optional[str]  # Q, H, Y, TTM, etc.
    is_ytd: bool = False
    fiscal_year: Optional[int] = None
    quarter: Optional[int] = None
    assumption: str = "calendar"  # calendar or fiscal
    parsing_notes: str = ""


class PeriodNormalizer:
    """Normalize period information from table headers"""
    
    def __init__(self):
        # Month name mappings
        self.month_names = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        
        # Quarter end months (calendar year)
        self.quarter_end_months = {1: 3, 2: 6, 3: 9, 4: 12}
        
        # Period type patterns
        self.period_patterns = [
            # Three months ended
            (r'(?i)three\s+months?\s+ended?\s+([a-z]+)\s+(\d{1,2}),?\s*(\d{4})', 'Q'),
            # Six months ended
            (r'(?i)six\s+months?\s+ended?\s+([a-z]+)\s+(\d{1,2}),?\s*(\d{4})', 'H'),
            # Nine months ended
            (r'(?i)nine\s+months?\s+ended?\s+([a-z]+)\s+(\d{1,2}),?\s*(\d{4})', 'Q3_YTD'),
            # Year ended
            (r'(?i)year\s+ended?\s+([a-z]+)\s+(\d{1,2}),?\s*(\d{4})', 'Y'),
            # Twelve months ended
            (r'(?i)twelve\s+months?\s+ended?\s+([a-z]+)\s+(\d{1,2}),?\s*(\d{4})', 'TTM'),
            # Q1 2024, Q2 FY25 formats
            (r'(?i)q([1-4])\s+(?:fy\s*)?(\d{2,4})', 'Q'),
            # FY 2024, Fiscal 2024
            (r'(?i)(?:fy|fiscal\s+year?)\s+(\d{2,4})', 'Y'),
            # 2024, simple year
            (r'^(\d{4})$', 'Y'),
            # TTM formats
            (r'(?i)ttm|trailing\s+twelve\s+months?', 'TTM'),
            # YTD formats
            (r'(?i)ytd|year\s+to\s+date', 'YTD')
        ]
    
    def normalize_period_header(self, header: str) -> PeriodInfo:
        """Normalize a single period header"""
        if not header or not header.strip():
            return PeriodInfo(
                original_header=header,
                period_end_date=None,
                period_type=None,
                parsing_notes="Empty header"
            )
        
        original_header = header.strip()
        
        # Try each pattern
        for pattern, period_type in self.period_patterns:
            match = re.search(pattern, original_header)
            if match:
                try:
                    result = self._parse_match(match, period_type, original_header)
                    if result:
                        return result
                except Exception as e:
                    continue
        
        # If no pattern matches, return with original text
        return PeriodInfo(
            original_header=original_header,
            period_end_date=None,
            period_type=None,
            parsing_notes="No matching pattern found"
        )
    
    def _parse_match(self, match, period_type: str, original_header: str) -> Optional[PeriodInfo]:
        """Parse a regex match into period information"""
        groups = match.groups()
        
        if period_type == 'Q' and len(groups) >= 3:
            # Three months ended format
            month_name, day, year = groups[0], groups[1], groups[2]
            return self._parse_ended_format(month_name, day, year, period_type, original_header)
        
        elif period_type == 'H' and len(groups) >= 3:
            # Six months ended format
            month_name, day, year = groups[0], groups[1], groups[2]
            return self._parse_ended_format(month_name, day, year, period_type, original_header, is_ytd=True)
        
        elif period_type == 'Q3_YTD' and len(groups) >= 3:
            # Nine months ended format
            month_name, day, year = groups[0], groups[1], groups[2]
            return self._parse_ended_format(month_name, day, year, 'Q', original_header, is_ytd=True)
        
        elif period_type == 'Y' and len(groups) >= 3:
            # Year ended format
            month_name, day, year = groups[0], groups[1], groups[2]
            return self._parse_ended_format(month_name, day, year, period_type, original_header)
        
        elif period_type == 'TTM' and len(groups) >= 3:
            # Twelve months ended format
            month_name, day, year = groups[0], groups[1], groups[2]
            return self._parse_ended_format(month_name, day, year, period_type, original_header)
        
        elif period_type == 'Q' and len(groups) >= 2:
            # Q1 2024 format
            quarter, year = groups[0], groups[1]
            return self._parse_quarter_year_format(quarter, year, original_header)
        
        elif period_type == 'Y' and len(groups) >= 1:
            # FY 2024 or simple year format
            year = groups[0]
            return self._parse_year_format(year, original_header)
        
        elif period_type in ['TTM', 'YTD']:
            # TTM or YTD without specific date
            return PeriodInfo(
                original_header=original_header,
                period_end_date=None,
                period_type=period_type,
                parsing_notes=f"Parsed as {period_type} without specific end date"
            )
        
        return None
    
    def _parse_ended_format(self, month_name: str, day: str, year: str, 
                           period_type: str, original_header: str, is_ytd: bool = False) -> PeriodInfo:
        """Parse 'ended' format periods"""
        try:
            # Parse month
            month_num = self._parse_month(month_name)
            if not month_num:
                return None
            
            # Parse day and year
            day_num = int(day)
            year_num = self._parse_year(year)
            
            # Create end date
            end_date = date(year_num, month_num, day_num)
            
            # Determine quarter if applicable
            quarter = None
            if period_type == 'Q':
                quarter = self._get_quarter_from_month(month_num)
            
            # Determine if YTD based on period length or explicit flag
            if period_type == 'H' or is_ytd:
                is_ytd = True
            elif period_type == 'Q' and month_num in [3, 6, 9]:  # Q1, Q2, Q3 are YTD
                is_ytd = quarter < 4
            
            return PeriodInfo(
                original_header=original_header,
                period_end_date=end_date.isoformat(),
                period_type=period_type,
                is_ytd=is_ytd,
                fiscal_year=year_num,
                quarter=quarter,
                parsing_notes=f"Parsed ended format: {month_name} {day}, {year}"
            )
        
        except (ValueError, TypeError):
            return None
    
    def _parse_quarter_year_format(self, quarter: str, year: str, original_header: str) -> PeriodInfo:
        """Parse Q1 2024 format"""
        try:
            quarter_num = int(quarter)
            year_num = self._parse_year(year)
            
            # Calculate end date (assume calendar quarters)
            end_month = self.quarter_end_months[quarter_num]
            
            # Use last day of quarter month
            if end_month == 2:
                # February - handle leap years
                if year_num % 4 == 0 and (year_num % 100 != 0 or year_num % 400 == 0):
                    end_day = 29
                else:
                    end_day = 28
            elif end_month in [4, 6, 9, 11]:
                end_day = 30
            else:
                end_day = 31
            
            end_date = date(year_num, end_month, end_day)
            
            return PeriodInfo(
                original_header=original_header,
                period_end_date=end_date.isoformat(),
                period_type='Q',
                is_ytd=quarter_num < 4,
                fiscal_year=year_num,
                quarter=quarter_num,
                parsing_notes=f"Parsed Q{quarter_num} {year_num} format"
            )
        
        except (ValueError, TypeError):
            return None
    
    def _parse_year_format(self, year: str, original_header: str) -> PeriodInfo:
        """Parse year-only format"""
        try:
            year_num = self._parse_year(year)
            
            # Assume December 31 end date for full year
            end_date = date(year_num, 12, 31)
            
            return PeriodInfo(
                original_header=original_header,
                period_end_date=end_date.isoformat(),
                period_type='Y',
                is_ytd=False,
                fiscal_year=year_num,
                parsing_notes=f"Parsed year format: {year_num}"
            )
        
        except (ValueError, TypeError):
            return None
    
    def _parse_month(self, month_str: str) -> Optional[int]:
        """Parse month name to number"""
        month_lower = month_str.lower().strip()
        return self.month_names.get(month_lower)
    
    def _parse_year(self, year_str: str) -> int:
        """Parse year string to integer"""
        year_num = int(year_str)
        
        # Handle 2-digit years (assume 2000s for now)
        if year_num < 100:
            if year_num < 50:  # 00-49 -> 2000-2049
                year_num += 2000
            else:  # 50-99 -> 1950-1999
                year_num += 1900
        
        return year_num
    
    def _get_quarter_from_month(self, month: int) -> int:
        """Get quarter number from month"""
        if month <= 3:
            return 1
        elif month <= 6:
            return 2
        elif month <= 9:
            return 3
        else:
            return 4
    
    def normalize_table_periods(self, headers: List[str]) -> List[PeriodInfo]:
        """Normalize all period headers in a table"""
        return [self.normalize_period_header(header) for header in headers]


def add_period_info_to_table(table_data: Dict[str, Any]) -> Dict[str, Any]:
    """Add normalized period information to table data"""
    normalizer = PeriodNormalizer()
    
    result = table_data.copy()
    
    if 'headers' in table_data:
        # Normalize period headers
        period_info = normalizer.normalize_table_periods(table_data['headers'])
        
        # Add period info to headers
        enhanced_headers = []
        for i, header in enumerate(table_data['headers']):
            period = period_info[i] if i < len(period_info) else None
            
            enhanced_header = {
                'original_header': header,
                'period_end_date': period.period_end_date if period else None,
                'period_type': period.period_type if period else None,
                'is_ytd': period.is_ytd if period else False,
                'fiscal_year': period.fiscal_year if period else None,
                'quarter': period.quarter if period else None,
                'assumption': period.assumption if period else "calendar",
                'parsing_notes': period.parsing_notes if period else ""
            }
            enhanced_headers.append(enhanced_header)
        
        result['headers'] = enhanced_headers
    
    return result
