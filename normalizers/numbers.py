"""
Number and Unit Normalization Module
Handles parsing and normalization of numeric values from financial tables
"""
import re
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class NumericValue:
    """Parsed numeric value with metadata"""
    original_text: str
    number_value: Optional[float]
    scale_hint: Optional[str]  # "millions", "thousands", etc.
    currency_hint: Optional[str]  # "USD", "EUR", etc.
    is_negative: bool = False
    is_percentage: bool = False
    parsing_notes: str = ""


class NumberNormalizer:
    """Normalize numeric values from financial table cells"""
    
    def __init__(self):
        # Scale detection patterns
        self.scale_patterns = {
            'millions': [
                r'(?i)\(in\s+millions?\)',
                r'(?i)\$\s*millions?',
                r'(?i)millions?\s+of\s+dollars?',
                r'(?i)in\s+millions?'
            ],
            'thousands': [
                r'(?i)\(in\s+thousands?\)',
                r'(?i)\$\s*thousands?',
                r'(?i)thousands?\s+of\s+dollars?',
                r'(?i)in\s+thousands?'
            ],
            'billions': [
                r'(?i)\(in\s+billions?\)',
                r'(?i)\$\s*billions?',
                r'(?i)billions?\s+of\s+dollars?',
                r'(?i)in\s+billions?'
            ]
        }
        
        # Currency detection patterns
        self.currency_patterns = {
            'USD': [r'\$', r'(?i)USD', r'(?i)US\s+dollars?', r'(?i)dollars?'],
            'EUR': [r'€', r'(?i)EUR', r'(?i)euros?'],
            'GBP': [r'£', r'(?i)GBP', r'(?i)pounds?'],
            'CAD': [r'(?i)CAD', r'(?i)C\$'],
            'JPY': [r'¥', r'(?i)JPY', r'(?i)yen']
        }
        
        # Number parsing patterns
        self.number_patterns = [
            # Standard formats: 1,234.56, (1,234.56), $1,234.56
            r'[\$€£¥]?\s*\(?\s*([0-9]{1,3}(?:,?[0-9]{3})*(?:\.[0-9]+)?)\s*\)?',
            # Decimal only: .56, (.56)
            r'[\$€£¥]?\s*\(?\s*(\.[0-9]+)\s*\)?',
            # Integer only: 1234, (1234)
            r'[\$€£¥]?\s*\(?\s*([0-9]+)\s*\)?',
            # Scientific notation: 1.23E+06
            r'[\$€£¥]?\s*\(?\s*([0-9]+\.?[0-9]*[eE][+-]?[0-9]+)\s*\)?'
        ]
    
    def normalize_cell_value(self, cell_text: str, table_context: Dict[str, Any] = None) -> NumericValue:
        """Normalize a single cell value"""
        if not cell_text or not cell_text.strip():
            return NumericValue(
                original_text=cell_text,
                number_value=None,
                scale_hint=None,
                currency_hint=None
            )
        
        original_text = cell_text.strip()
        
        # Check for common non-numeric indicators
        if self._is_non_numeric(original_text):
            return NumericValue(
                original_text=original_text,
                number_value=None,
                scale_hint=None,
                currency_hint=None,
                parsing_notes="Non-numeric content"
            )
        
        # Parse the numeric value
        parsed_number, is_negative, parsing_notes = self._parse_number(original_text)
        
        # Detect percentage
        is_percentage = '%' in original_text
        
        # Detect currency (from cell or table context)
        currency_hint = self._detect_currency(original_text, table_context)
        
        # Detect scale (from cell or table context)
        scale_hint = self._detect_scale(original_text, table_context)
        
        return NumericValue(
            original_text=original_text,
            number_value=parsed_number,
            scale_hint=scale_hint,
            currency_hint=currency_hint,
            is_negative=is_negative,
            is_percentage=is_percentage,
            parsing_notes=parsing_notes
        )
    
    def detect_table_scale_hints(self, headers: list, caption: str = "") -> Optional[str]:
        """Detect scale hints from table headers or caption"""
        text_to_search = ' '.join(headers) + ' ' + caption
        
        for scale, patterns in self.scale_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_search):
                    return scale
        
        return None
    
    def detect_table_currency_hints(self, headers: list, caption: str = "") -> Optional[str]:
        """Detect currency hints from table headers or caption"""
        text_to_search = ' '.join(headers) + ' ' + caption
        
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_to_search):
                    return currency
        
        return None
    
    def _is_non_numeric(self, text: str) -> bool:
        """Check if text is clearly non-numeric"""
        text_lower = text.lower().strip()
        
        # Common non-numeric indicators
        non_numeric_indicators = [
            'n/a', 'na', 'not applicable', 'none', 'nil', 'zero', '—', '–', 
            'tbd', 'tba', 'pending', 'see note', 'note', 'footnote',
            'total', 'subtotal', 'sum', 'average', 'mean'
        ]
        
        if text_lower in non_numeric_indicators:
            return True
        
        # Check if it's mostly letters (not a number)
        letter_count = sum(1 for c in text if c.isalpha())
        total_chars = len(text.replace(' ', ''))
        
        if total_chars > 0 and (letter_count / total_chars) > 0.5:
            return True
        
        return False
    
    def _parse_number(self, text: str) -> Tuple[Optional[float], bool, str]:
        """Parse numeric value from text"""
        if not text:
            return None, False, "Empty text"
        
        # Clean the text
        clean_text = text.strip()
        
        # Check for negative indicators
        is_negative = False
        if clean_text.startswith('(') and clean_text.endswith(')'):
            is_negative = True
            clean_text = clean_text[1:-1].strip()
        elif clean_text.startswith('-') or clean_text.startswith('−'):
            is_negative = True
            clean_text = clean_text[1:].strip()
        
        # Handle explicit positive sign
        if clean_text.startswith('+'):
            clean_text = clean_text[1:].strip()
        
        # Handle dashes and blanks (often mean zero or N/A)
        if clean_text in ['—', '–', '-', '']:
            return 0.0, False, "Dash interpreted as zero"
        
        # Try each number pattern
        for pattern in self.number_patterns:
            match = re.search(pattern, clean_text)
            if match:
                number_str = match.group(1)
                try:
                    # Remove commas and parse
                    clean_number = number_str.replace(',', '')
                    parsed_value = float(clean_number)
                    
                    if is_negative:
                        parsed_value = -parsed_value
                    
                    return parsed_value, is_negative, f"Parsed using pattern: {pattern[:20]}..."
                
                except ValueError:
                    continue
        
        # Special handling for percentage-only values
        if '%' in clean_text:
            percent_match = re.search(r'([0-9]+\.?[0-9]*)', clean_text)
            if percent_match:
                try:
                    value = float(percent_match.group(1))
                    if is_negative:
                        value = -value
                    return value, is_negative, "Parsed as percentage"
                except ValueError:
                    pass
        
        return None, is_negative, f"Could not parse: {text}"
    
    def _detect_currency(self, text: str, table_context: Dict[str, Any] = None) -> Optional[str]:
        """Detect currency from text or table context"""
        # First check the cell text itself
        for currency, patterns in self.currency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return currency
        
        # Then check table context if provided
        if table_context:
            headers_text = ' '.join(table_context.get('headers', []))
            caption_text = table_context.get('caption', '')
            context_text = headers_text + ' ' + caption_text
            
            for currency, patterns in self.currency_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, context_text):
                        return currency
        
        return None
    
    def _detect_scale(self, text: str, table_context: Dict[str, Any] = None) -> Optional[str]:
        """Detect scale from text or table context"""
        # First check the cell text itself
        for scale, patterns in self.scale_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    return scale
        
        # Then check table context if provided
        if table_context:
            headers_text = ' '.join(table_context.get('headers', []))
            caption_text = table_context.get('caption', '')
            context_text = headers_text + ' ' + caption_text
            
            for scale, patterns in self.scale_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, context_text):
                        return scale
        
        return None


def normalize_table_numbers(table_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize all numbers in a table structure"""
    normalizer = NumberNormalizer()
    
    # Extract table context
    table_context = {
        'headers': table_data.get('headers', []),
        'caption': table_data.get('caption', '')
    }
    
    # Detect table-level hints
    table_scale_hint = normalizer.detect_table_scale_hints(
        table_context['headers'], 
        table_context['caption']
    )
    table_currency_hint = normalizer.detect_table_currency_hints(
        table_context['headers'], 
        table_context['caption']
    )
    
    # Add table-level hints to result
    result = table_data.copy()
    result['scale_hint'] = table_scale_hint
    result['currency_hint'] = table_currency_hint
    
    # Normalize each cell
    if 'rows' in table_data:
        normalized_rows = []
        for row in table_data['rows']:
            normalized_row = []
            for cell in row:
                if hasattr(cell, 'original_text'):
                    # Normalize the cell value
                    normalized = normalizer.normalize_cell_value(
                        cell.original_text, 
                        table_context
                    )
                    
                    # Create enhanced cell object
                    enhanced_cell = {
                        'table_id': getattr(cell, 'table_id', ''),
                        'row_idx': getattr(cell, 'row_idx', 0),
                        'col_idx': getattr(cell, 'col_idx', 0),
                        'original_text': cell.original_text,
                        'number_value': normalized.number_value,
                        'scale_hint': normalized.scale_hint or table_scale_hint,
                        'currency_hint': normalized.currency_hint or table_currency_hint,
                        'is_negative': normalized.is_negative,
                        'is_percentage': normalized.is_percentage,
                        'parsing_notes': normalized.parsing_notes
                    }
                    normalized_row.append(enhanced_cell)
                else:
                    normalized_row.append(cell)
            normalized_rows.append(normalized_row)
        
        result['rows'] = normalized_rows
    
    return result
