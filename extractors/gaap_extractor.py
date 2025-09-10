"""
GAAP reconciliation extractor
"""
import json
import os
import re
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from io import StringIO

load_dotenv()

class GaapExtractor:
    def __init__(self, model=None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or "gpt-4o-mini"
        self.last_token_usage = None
        self._init_gaap_patterns()
    
    def _init_gaap_patterns(self):
        """Initialize advanced GAAP reconciliation patterns"""
        self.reconciliation_headers = [
            r'(?i)reconciliation\s+of\s+(?:gaap|non-gaap)',
            r'(?i)gaap\s+to\s+non-gaap\s+reconciliation',
            r'(?i)non-gaap\s+financial\s+measures',
            r'(?i)supplemental\s+financial\s+information',
            r'(?i)adjusted\s+(?:earnings|income|revenue)',
            r'(?i)reconciliation\s+table'
        ]
        
        self.gaap_line_patterns = [
            r'(?i)(?:net\s+)?(?:income|loss|earnings).*gaap\s+basis',
            r'(?i)gaap\s+(?:net\s+)?(?:income|loss|earnings)',
            r'(?i)(?:gross\s+)?profit.*gaap\s+basis',
            r'(?i)gaap\s+(?:gross\s+)?profit',
            r'(?i)operating\s+(?:income|loss).*gaap\s+basis',
            r'(?i)gaap\s+operating\s+(?:income|loss)',
            r'(?i)revenue.*gaap\s+basis',
            r'(?i)gaap\s+revenue'
        ]
        
        self.adjustment_patterns = [
            r'(?i)stock[\s-]based\s+compensation',
            r'(?i)share[\s-]based\s+compensation',
            r'(?i)amortization\s+of\s+intangible',
            r'(?i)acquisition[\s-]related',
            r'(?i)restructuring\s+(?:costs|charges)',
            r'(?i)impairment\s+(?:charges|losses)',
            r'(?i)litigation\s+(?:costs|settlements)',
            r'(?i)tax\s+(?:effects|adjustments)',
            r'(?i)one[\s-]time\s+(?:charges|items)',
            r'(?i)non[\s-]recurring\s+(?:charges|items)'
        ]
        
        self.non_gaap_patterns = [
            r'(?i)non[\s-]gaap\s+(?:net\s+)?(?:income|loss|earnings)',
            r'(?i)adjusted\s+(?:net\s+)?(?:income|loss|earnings)',
            r'(?i)non[\s-]gaap\s+(?:gross\s+)?profit',
            r'(?i)adjusted\s+(?:gross\s+)?profit',
            r'(?i)non[\s-]gaap\s+operating\s+(?:income|loss)',
            r'(?i)adjusted\s+operating\s+(?:income|loss)',
            r'(?i)non[\s-]gaap\s+revenue',
            r'(?i)adjusted\s+revenue'
        ]
    
    def extract_gaap_reconciliation(self, html_content: str, company_name: str = "") -> Dict:
        """Extract GAAP to Non-GAAP reconciliation data using OpenAI"""
        
        
        # Check if html_content parameter is None first
        if html_content is None:
            raise Exception("html_content parameter is None")
        
        # Use HTML content directly with safe handling
        # Handle potential encoding issues by cleaning the HTML content first
        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8', errors='replace')
        
        # Use the existing cash flow end detection logic
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # Find where cash flow statement ends using the same patterns as financial_parser.py
        cash_flow_patterns = [
            'cash and cash equivalents, end of period',
            'net increase in cash',
            'net decrease in cash',
            'total cash flows'
        ]
        
        last_pos = -1
        for pattern in cash_flow_patterns:
            pos = text.lower().rfind(pattern.lower())
            if pos > last_pos:
                last_pos = pos
        
        if last_pos > -1:
            # Find end of line after the pattern
            line_end = text.find('\n', last_pos)
            if line_end > -1:
                # Use content from end of cash flow to end of document
                content_to_search = html_content[line_end:]
            else:
                content_to_search = html_content[last_pos:]
        else:
            # Fallback to entire document if no cash flow patterns found
            content_to_search = html_content
        
        # Advanced GAAP reconciliation detection and extraction
        reconciliation_sections = self._find_reconciliation_sections(content_to_search)
        
        if not reconciliation_sections:
            return {"periods": [], "data": {}}
        
        # Extract from the best reconciliation section
        best_section = self._select_best_reconciliation_section(reconciliation_sections)
        
        # Try table-based extraction first
        table_result = self._extract_from_reconciliation_tables(best_section, company_name)
        if table_result and table_result.get('data'):
            return table_result
        
        # Fallback to AI-enhanced extraction
        return self._ai_enhanced_reconciliation_extraction(best_section, company_name)
        
        
    def _find_reconciliation_sections(self, html_content: str) -> List[str]:
        """Find all potential GAAP reconciliation sections in the document"""
        soup = BeautifulSoup(html_content, 'html.parser')
        sections = []
        
        # Look for sections with reconciliation headers
        for header_pattern in self.reconciliation_headers:
            matches = soup.find_all(string=re.compile(header_pattern))
            for match in matches:
                # Get the parent element and surrounding content
                parent = match.parent
                while parent and parent.name not in ['table', 'div', 'section']:
                    parent = parent.parent
                
                if parent:
                    # Extract a reasonable section around the match
                    section_text = str(parent)
                    if len(section_text) > 500:  # Only consider substantial sections
                        sections.append(section_text)
        
        # Enhanced table detection for multi-page reconciliations
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text().lower()
            gaap_count = table_text.count('gaap')
            non_gaap_count = table_text.count('non-gaap') + table_text.count('non gaap')
            adjusted_count = table_text.count('adjusted')
            
            # More comprehensive reconciliation detection
            reconciliation_indicators = [
                'reconciliation',
                'loss from operations',
                'income from operations', 
                'operating margin',
                'net loss',
                'net income',
                'earnings per share',
                'loss per share',
                'stock-based compensation',
                'amortization of intangible'
            ]
            
            indicator_count = sum(1 for indicator in reconciliation_indicators if indicator in table_text)
            
            # Include table if it has GAAP content AND reconciliation indicators
            if (gaap_count >= 1 and (non_gaap_count >= 1 or adjusted_count >= 1)) or indicator_count >= 3:
                sections.append(str(table))
        
        # Look for consecutive tables that might be part of multi-page reconciliation
        all_tables = soup.find_all('table')
        for i, table in enumerate(all_tables):
            table_text = table.get_text().lower()
            
            # Check if this table contains reconciliation-like content even without explicit GAAP mentions
            reconciliation_patterns = [
                r'(?i)loss\s+from\s+operations',
                r'(?i)income\s+from\s+operations',
                r'(?i)operating\s+margin',
                r'(?i)net\s+(?:loss|income)',
                r'(?i)(?:loss|earnings)\s+per\s+share',
                r'(?i)stock[\s-]based\s+compensation',
                r'(?i)amortization\s+of\s+intangible',
                r'(?i)acquisition[\s-]related',
                r'(?i)restructuring'
            ]
            
            pattern_matches = sum(1 for pattern in reconciliation_patterns if re.search(pattern, table_text))
            
            # If table has multiple reconciliation patterns, include it
            if pattern_matches >= 2:
                table_str = str(table)
                if table_str not in sections:  # Avoid duplicates
                    sections.append(table_str)
        
        return sections
    
    def _select_best_reconciliation_section(self, sections: List[str]) -> str:
        """Select the most comprehensive reconciliation section"""
        if not sections:
            return ""
        
        best_section = ""
        best_score = 0
        
        for section in sections:
            score = 0
            section_lower = section.lower()
            
            # Score based on reconciliation patterns
            for pattern in self.gaap_line_patterns + self.adjustment_patterns + self.non_gaap_patterns:
                if re.search(pattern, section_lower):
                    score += 1
            
            # Bonus for table structure
            if '<table' in section:
                score += 5
            
            # Bonus for multiple periods
            if section_lower.count('2024') + section_lower.count('2023') + section_lower.count('2025') >= 2:
                score += 3
            
            if score > best_score:
                best_score = score
                best_section = section
        
        return best_section
    
    def _extract_from_reconciliation_tables(self, section_html: str, company_name: str) -> Dict:
        """Extract reconciliation data using table parsing"""
        try:
            soup = BeautifulSoup(section_html, 'html.parser')
            tables = soup.find_all('table')
            
            for table in tables:
                # Check if this table contains reconciliation data
                table_text = table.get_text().lower()
                if 'gaap' in table_text and ('non-gaap' in table_text or 'adjusted' in table_text):
                    try:
                        df_list = pd.read_html(StringIO(str(table)))
                        if df_list:
                            df = df_list[0]
                            return self._parse_reconciliation_dataframe(df)
                    except Exception:
                        continue
            
            return {"periods": [], "data": {}}
        except Exception:
            return {"periods": [], "data": {}}
    
    def _parse_reconciliation_dataframe(self, df: pd.DataFrame) -> Dict:
        """Parse a reconciliation table DataFrame"""
        try:
            # Extract periods from header row
            periods = []
            for col in df.columns[1:]:  # Skip first column (line items)
                if pd.notna(col) and str(col).strip() and not str(col).startswith('Unnamed'):
                    periods.append(str(col).strip())
            
            # Extract data rows
            data = {}
            for _, row in df.iterrows():
                line_item = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                
                # Skip empty or header-like rows
                if not line_item or line_item.lower() in ['nan', 'none', '']:
                    continue
                
                # Check if this looks like a reconciliation line item
                line_lower = line_item.lower()
                is_reconciliation_item = any([
                    'gaap' in line_lower,
                    'non-gaap' in line_lower,
                    'adjusted' in line_lower,
                    any(re.search(pattern, line_lower) for pattern in self.adjustment_patterns)
                ])
                
                if is_reconciliation_item:
                    values = []
                    for i in range(1, min(len(row), len(periods) + 1)):
                        val = row.iloc[i]
                        if pd.notna(val):
                            # Clean numeric values
                            val_str = str(val).replace(',', '').replace('$', '').replace('(', '-').replace(')', '')
                            try:
                                values.append(float(val_str))
                            except:
                                values.append(val_str)
                        else:
                            values.append(None)
                    
                    if values and any(v is not None for v in values):
                        data[line_item] = values
            
            return {'periods': periods, 'data': data}  # Return all periods
        except Exception:
            return {"periods": [], "data": {}}
    
    def _ai_enhanced_reconciliation_extraction(self, section_content: str, company_name: str) -> Dict:
        """Enhanced AI extraction with better prompting and context"""
        # Truncate content intelligently
        truncated_content = self._smart_truncate_reconciliation_content(section_content, 6000)
        
        prompt = f"""
You are a financial expert specializing in GAAP to Non-GAAP reconciliations. Extract reconciliation data from this {company_name} section.

FOCUS ON RECONCILIATION FLOW:
1. Start with GAAP baseline (e.g., "GAAP net loss", "GAAP operating income")
2. Add back adjustments (e.g., "Stock-based compensation", "Amortization of intangibles")
3. Arrive at Non-GAAP result (e.g., "Non-GAAP net income", "Adjusted operating income")

COMMON RECONCILIATION PATTERNS:
- Revenue reconciliations (GAAP → Adjusted)
- Gross profit reconciliations
- Operating income/loss reconciliations  
- Net income/loss reconciliations
- Earnings per share reconciliations

ADJUSTMENT CATEGORIES TO CAPTURE:
- Stock-based compensation expenses
- Amortization of intangible assets
- Acquisition-related costs
- Restructuring charges
- Impairment losses
- Litigation costs
- Tax effects of adjustments
- One-time/non-recurring items

EXTRACT EXACT LINE ITEMS as they appear. Preserve original wording.

Return JSON:
{{
    "periods": ["Period 1", "Period 2", ...],
    "data": {{
        "GAAP net loss": [-50000, -45000],
        "Stock-based compensation": [15000, 12000],
        "Amortization of intangibles": [8000, 7500],
        "Non-GAAP net income": [-27000, -25500],
        "GAAP loss per share, basic and diluted": [-0.25, -0.23],
        "Non-GAAP earnings per share, basic": [-0.14, -0.13]
    }}
}}

Reconciliation Content:
{truncated_content}"""
        
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial expert specializing in GAAP to Non-GAAP reconciliations. Extract reconciliation data with high precision, preserving exact line item names and following the reconciliation flow logic."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            # Track token usage
            if response and hasattr(response, 'usage') and response.usage:
                usage = response.usage
                self.last_token_usage = f"Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}"
            
            # Extract and clean response
            if response and response.choices and len(response.choices) > 0 and response.choices[0].message and response.choices[0].message.content:
                result = response.choices[0].message.content.strip()
            else:
                raise Exception("No response received from OpenAI")
            
            # Clean up the response to ensure it's valid JSON
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "").strip()
            elif result.startswith("```"):
                result = result.replace("```", "").strip()
            
            parsed_result = json.loads(result)
            return parsed_result
            
        except Exception as e:
            error_msg = f"Error extracting GAAP reconciliation: {e}"
            raise Exception(error_msg)
    
    def _smart_truncate_reconciliation_content(self, content: str, max_chars: int) -> str:
        """Intelligently truncate content while preserving reconciliation sections"""
        if len(content) <= max_chars:
            return content
        
        # Try to find and preserve reconciliation tables
        soup = BeautifulSoup(content, 'html.parser')
        tables = soup.find_all('table')
        
        reconciliation_tables = []
        for table in tables:
            table_text = table.get_text().lower()
            if 'gaap' in table_text and ('non-gaap' in table_text or 'adjusted' in table_text):
                reconciliation_tables.append(str(table))
        
        if reconciliation_tables:
            # Prioritize reconciliation tables
            combined_tables = '\n'.join(reconciliation_tables)
            if len(combined_tables) <= max_chars:
                return combined_tables
            else:
                return combined_tables[:max_chars]
        
        # Fallback to simple truncation
        return content[:max_chars]
