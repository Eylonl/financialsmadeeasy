"""
Smart Financial Data Extractor - Advanced hybrid approach with caching and adaptive strategies
"""
import json
import re
import os
import hashlib
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import pickle
from datetime import datetime, timedelta

load_dotenv()

class SmartExtractor:
    def __init__(self, model="gpt-4o-mini"):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model
        # Initialize pattern matching capabilities
        self._init_patterns()
        self.last_token_usage = None
        self.cache_dir = "extraction_cache"
        self.cache_ttl_hours = 24  # Cache for 24 hours
        
        # Create cache directory
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Company-specific extraction patterns learned from previous extractions
        self.company_patterns = {}
        
        # Load cached patterns
        self._load_company_patterns()
        
    def _init_patterns(self):
        """Initialize common financial statement patterns"""
        self.income_patterns = [
            r'(?i)(?:total\s+)?(?:net\s+)?revenues?\s*(?:and\s+sales)?',
            r'(?i)(?:total\s+)?(?:net\s+)?sales?',
            r'(?i)cost\s+of\s+(?:goods\s+sold|revenue|sales)',
            r'(?i)gross\s+(?:profit|margin|income)',
            r'(?i)operating\s+(?:income|profit|loss)',
            r'(?i)net\s+(?:income|profit|loss|earnings)',
            r'(?i)research\s+(?:and|&)\s+development',
            r'(?i)sales\s+(?:and|&)\s+marketing',
            r'(?i)general\s+(?:and|&)\s+administrative'
        ]
        
        self.balance_patterns = [
            r'(?i)(?:total\s+)?(?:current\s+)?assets',
            r'(?i)cash\s+(?:and\s+)?(?:cash\s+)?equivalents',
            r'(?i)(?:total\s+)?(?:current\s+)?liabilities',
            r'(?i)(?:total\s+)?(?:stockholders?|shareholders?)\s+equity',
            r'(?i)accounts\s+receivable',
            r'(?i)accounts\s+payable'
        ]
        
        self.cash_flow_patterns = [
            r'(?i)(?:net\s+)?cash\s+(?:provided\s+by|from)\s+operating\s+activities',
            r'(?i)(?:net\s+)?cash\s+(?:used\s+in|for)\s+investing\s+activities',
            r'(?i)(?:net\s+)?cash\s+(?:used\s+in|from)\s+financing\s+activities',
            r'(?i)net\s+(?:increase|decrease)\s+in\s+cash'
        ]
    
    def _pattern_based_extraction(self, html_content: str, statement_type: str) -> Dict:
        """Extract financial data using pattern matching and table parsing"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all tables
            tables = soup.find_all('table')
            if not tables:
                return {'periods': [], 'data': {}}
            
            # Get patterns for this statement type
            if statement_type == 'income_statement':
                patterns = self.income_patterns
            elif statement_type == 'balance_sheet':
                patterns = self.balance_patterns
            elif statement_type == 'cash_flow_statement':
                patterns = self.cash_flow_patterns
            else:
                patterns = self.income_patterns  # Default
            
            best_table = None
            max_matches = 0
            
            # Find table with most pattern matches
            for table in tables:
                table_text = table.get_text()
                matches = sum(1 for pattern in patterns if re.search(pattern, table_text))
                if matches > max_matches:
                    max_matches = matches
                    best_table = table
            
            if not best_table or max_matches == 0:
                return {'periods': [], 'data': {}}
            
            # Parse the best table using pandas
            try:
                table_html = str(best_table)
                df_list = pd.read_html(StringIO(table_html))
                if not df_list:
                    return {'periods': [], 'data': {}}
                
                df = df_list[0]
                
                # Extract periods from header row
                periods = []
                for col in df.columns[1:]:  # Skip first column (line items)
                    if pd.notna(col) and str(col).strip():
                        periods.append(str(col).strip())
                
                # Extract data
                data = {}
                for _, row in df.iterrows():
                    line_item = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
                    if line_item and line_item != 'nan':
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
                
            except Exception as e:
                return {'periods': [], 'data': {}}
                
        except Exception as e:
            return {'periods': [], 'data': {}}
    
    def _load_company_patterns(self):
        """Load cached company patterns"""
        patterns_file = os.path.join(self.cache_dir, "company_patterns.json")
        if os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r') as f:
                    self.company_patterns = json.load(f)
            except Exception:
                self.company_patterns = {}

    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content caching"""
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cache_path(self, content_hash: str, statement_type: str) -> str:
        """Get cache file path"""
        return os.path.join(self.cache_dir, f"{content_hash}_{statement_type}.pkl")

    def _is_cache_valid(self, cache_path: str) -> bool:
        """Check if cache is still valid"""
        if not os.path.exists(cache_path):
            return False
        
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        return datetime.now() - cache_time < timedelta(hours=self.cache_ttl_hours)

    def _save_to_cache(self, content_hash: str, statement_type: str, data: Dict):
        """Save extraction result to cache"""
        cache_path = self._get_cache_path(content_hash, statement_type)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            pass  # Fail silently if caching doesn't work

    def _load_from_cache(self, content_hash: str, statement_type: str) -> Optional[Dict]:
        """Load extraction result from cache"""
        cache_path = self._get_cache_path(content_hash, statement_type)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            return None

    def _load_company_patterns(self):
        """Load learned company-specific patterns"""
        patterns_file = os.path.join(self.cache_dir, "company_patterns.json")
        if os.path.exists(patterns_file):
            try:
                with open(patterns_file, 'r') as f:
                    self.company_patterns = json.load(f)
            except Exception as e:
                self.company_patterns = {}

    def _save_company_patterns(self):
        """Save learned company-specific patterns"""
        patterns_file = os.path.join(self.cache_dir, "company_patterns.json")
        try:
            with open(patterns_file, 'w') as f:
                json.dump(self.company_patterns, f, indent=2)
        except Exception as e:
            pass

    def _learn_from_extraction(self, company_name: str, statement_type: str, extracted_data: Dict):
        """Learn patterns from successful extractions"""
        if not company_name or not extracted_data.get('data'):
            return
        
        company_key = company_name.upper().strip()
        if company_key not in self.company_patterns:
            self.company_patterns[company_key] = {}
        
        if statement_type not in self.company_patterns[company_key]:
            self.company_patterns[company_key][statement_type] = {
                'common_line_items': [],
                'period_formats': [],
                'extraction_count': 0
            }
        
        patterns = self.company_patterns[company_key][statement_type]
        
        # Learn common line items
        for line_item in extracted_data['data'].keys():
            if line_item not in patterns['common_line_items']:
                patterns['common_line_items'].append(line_item)
        
        # Learn period formats
        for period in extracted_data.get('periods', []):
            if period not in patterns['period_formats']:
                patterns['period_formats'].append(period)
        
        patterns['extraction_count'] += 1
        
        # Keep only the most recent 10 line items and periods to avoid bloat
        patterns['common_line_items'] = patterns['common_line_items'][-10:]
        patterns['period_formats'] = patterns['period_formats'][-5:]
        
        self._save_company_patterns()

    def _get_company_context(self, company_name: str, statement_type: str) -> str:
        """Get learned context for a company"""
        if not company_name:
            return ""
        
        company_key = company_name.upper().strip()
        if company_key not in self.company_patterns:
            return ""
        
        patterns = self.company_patterns[company_key].get(statement_type, {})
        if not patterns:
            return ""
        
        context = f"\nLEARNED PATTERNS FOR {company_name}:\n"
        
        if patterns.get('common_line_items'):
            context += f"Common line items: {', '.join(patterns['common_line_items'][:5])}\n"
        
        if patterns.get('period_formats'):
            context += f"Period formats: {', '.join(patterns['period_formats'][:3])}\n"
        
        context += f"Previous extractions: {patterns.get('extraction_count', 0)}\n"
        
        return context

    def _adaptive_extraction_strategy(self, html_content: str, statement_type: str, company_name: str) -> Dict:
        """Choose extraction strategy based on content characteristics"""
        
        # Analyze content characteristics
        content_length = len(html_content)
        table_count = html_content.lower().count('<table')
        numeric_density = len(re.findall(r'\d+[,.]?\d*', html_content)) / max(content_length, 1) * 1000
        
        # Strategy selection logic
        if table_count >= 3 and numeric_density > 5:
            # Rich tabular content - use hybrid approach
            return self._hybrid_extraction_with_context(html_content, statement_type, company_name)
        elif table_count >= 1 and numeric_density > 2:
            # Moderate tabular content - pattern first, then AI if needed
            pattern_result = self._pattern_based_extraction(html_content, statement_type)
            if len(pattern_result.get('data', {})) >= 5:  # Good pattern extraction
                return pattern_result
            else:
                return self._targeted_ai_extraction(html_content, statement_type, company_name)
        else:
            # Poor structure - use AI with company context
            return self._targeted_ai_extraction(html_content, statement_type, company_name)

    def _hybrid_extraction_with_context(self, html_content: str, statement_type: str, company_name: str) -> Dict:
        """Hybrid extraction enhanced with company-specific context"""
        
        # Get company context
        company_context = self._get_company_context(company_name, statement_type)
        
        # Use pattern-based extraction
        result = self._pattern_based_extraction(html_content, statement_type)
        
        # If hybrid extraction was successful, enhance with context
        if result.get('data') and len(result['data']) >= 3:
            if company_context:
                # Use AI to validate and enhance based on learned patterns
                enhanced_result = self._context_aware_enhancement(result, html_content, statement_type, company_name, company_context)
                return enhanced_result
            return result
        else:
            # Use AI extraction with context (no fallback, this IS the method)
            return self._targeted_ai_extraction(html_content, statement_type, company_name)

    def _targeted_ai_extraction(self, html_content: str, statement_type: str, company_name: str) -> Dict:
        """Targeted AI extraction with company context and token optimization"""
        
        company_context = self._get_company_context(company_name, statement_type)
        
        # Truncate content intelligently - keep table sections
        truncated_content = self._smart_content_truncation(html_content, 4000)
        
        prompt = f"""
Extract {statement_type} data from this financial document for {company_name}.

{company_context}

Return ONLY a JSON object:
{{
    "periods": ["Period 1", "Period 2", ...],
    "data": {{
        "Line Item Name": [value1, value2, ...]
    }}
}}

REQUIREMENTS:
- Use exact line item names from document
- Convert to numbers (remove $, commas, parentheses=negative)
- null for missing values
- Up to 3 most recent periods
- Focus on main financial table

Document:
{truncated_content}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1200
            )
            
            # Track token usage
            if hasattr(response, 'usage'):
                usage = response.usage
                self.last_token_usage = f"Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}"
            
            result = response.choices[0].message.content.strip()
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "").strip()
            
            return json.loads(result)
            
        except Exception as e:
            return {"periods": [], "data": {}}

    def _context_aware_enhancement(self, base_result: Dict, html_content: str, statement_type: str, company_name: str, company_context: str) -> Dict:
        """Enhance extraction using learned company patterns"""
        
        enhancement_prompt = f"""
Enhance this {statement_type} extraction for {company_name} using learned patterns.

CURRENT EXTRACTION:
{json.dumps(base_result, indent=2)}

{company_context}

ENHANCEMENT TASKS:
1. Check for missing expected line items based on learned patterns
2. Validate period formats match company's typical format
3. Suggest any standardization needed

Return JSON with:
{{
    "enhanced_data": {{"line_item": [val1, val2, ...]}},
    "corrections": {{"old_name": "new_name"}},
    "confidence_score": 0.85
}}

Document excerpt:
{html_content[:1500]}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial data analyst. Return only valid JSON."},
                    {"role": "user", "content": enhancement_prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            result = response.choices[0].message.content.strip()
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "").strip()
            
            enhancement = json.loads(result)
            
            # Apply enhancements
            enhanced_result = base_result.copy()
            
            if enhancement.get('enhanced_data'):
                enhanced_result['data'].update(enhancement['enhanced_data'])
            
            if enhancement.get('corrections'):
                for old_name, new_name in enhancement['corrections'].items():
                    if old_name in enhanced_result['data']:
                        enhanced_result['data'][new_name] = enhanced_result['data'].pop(old_name)
            
            return enhanced_result
            
        except Exception as e:
            return base_result

    def _smart_content_truncation(self, html_content: str, max_chars: int) -> str:
        """Intelligently truncate content to preserve important sections"""
        
        if len(html_content) <= max_chars:
            return html_content
        
        # Priority sections to preserve
        important_patterns = [
            r'<table[^>]*>.*?</table>',
            r'consolidated.*?statement',
            r'income.*?statement',
            r'balance.*?sheet',
            r'cash.*?flow'
        ]
        
        preserved_sections = []
        remaining_content = html_content
        
        for pattern in important_patterns:
            matches = re.finditer(pattern, remaining_content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                section = match.group()
                if len(section) < max_chars // 2:  # Don't take more than half the budget
                    preserved_sections.append(section)
                    remaining_content = remaining_content.replace(section, '', 1)
        
        # Combine preserved sections with remaining content
        preserved_text = '\n'.join(preserved_sections)
        remaining_budget = max_chars - len(preserved_text)
        
        if remaining_budget > 0:
            preserved_text += '\n' + remaining_content[:remaining_budget]
        
        return preserved_text

    def extract_financial_statement(self, html_content: str, statement_type: str, company_name: str = "") -> Dict:
        """
        Main smart extraction method with caching and adaptive strategies
        """
        
        # Check cache first
        content_hash = self._get_content_hash(html_content)
        cached_result = self._load_from_cache(content_hash, statement_type)
        
        if cached_result:
            return cached_result
        
        # Perform extraction using adaptive strategy
        result = self._adaptive_extraction_strategy(html_content, statement_type, company_name)
        
        # Learn from successful extraction
        if result.get('data') and len(result['data']) >= 3:
            self._learn_from_extraction(company_name, statement_type, result)
        
        # Cache the result
        self._save_to_cache(content_hash, statement_type, result)
        
        return result

    def extract_income_statement(self, html_content: str, company_name: str = "") -> Dict:
        """Extract income statement using smart approach"""
        return self.extract_financial_statement(html_content, "income_statement", company_name)
    
    def extract_balance_sheet(self, html_content: str, company_name: str = "") -> Dict:
        """Extract balance sheet using smart approach"""
        return self.extract_financial_statement(html_content, "balance_sheet", company_name)
    
    def extract_cash_flow_statement(self, html_content: str, company_name: str = "") -> Dict:
        """Extract cash flow statement using smart approach"""
        return self.extract_financial_statement(html_content, "cash_flow", company_name)

    def get_extraction_stats(self) -> Dict:
        """Get comprehensive extraction statistics"""
        return {
            "last_token_usage": self.last_token_usage,
            "model_used": self.model,
            "extraction_method": "smart_adaptive",
            "companies_learned": len(self.company_patterns),
            "cache_dir": self.cache_dir
        }

    def clear_cache(self):
        """Clear extraction cache"""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.company_patterns = {}
