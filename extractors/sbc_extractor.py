"""
Stock-based compensation extractor
"""
import json
import os
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class SbcExtractor:
    def __init__(self, model=None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or "gpt-4o-mini"
        self.last_token_usage = None
    
    def extract_sbc_breakdown(self, html_content: str, company_name: str = "") -> Dict:
        """Extract stock-based compensation breakdown data using OpenAI"""
        
        prompt = f"""
        Find and extract the stock-based compensation breakdown table from this 8-K earnings release for {company_name}.
        This table typically shows stock-based compensation expense broken down by functional area (Cost of Revenue, Sales & Marketing, R&D, G&A).
        Look for tables with titles like "Stock-based compensation expense", "Share-based compensation", or similar.
        
        Return ONLY a JSON object with this structure:
        {{
            "periods": ["Three Months Ended April 30, 2025", "2024"],
            "data": {{
                "Cost of revenue—subscription": [8395, 6163],
                "Cost of revenue—services": [2894, 2235],
                "Sales and marketing": [39102, 39613],
                "Research and development": [66405, 53774],
                "General and administrative": [14635, 16590],
                "Total stock-based compensation expense": [132431, 120765]
            }}
        }}
        
        CRITICAL REQUIREMENTS:
        - Find the stock-based compensation breakdown table within the 8-K filing
        - Use the EXACT line item names as they appear in the filing (do not standardize or rename)
        - Extract ALL functional area breakdowns shown in the table
        - Include the total if provided
        - If a line item appears in only some periods, include it with null values for missing periods
        - Use the exact period labels from the filing
        - Convert values to numbers (remove commas, $ signs, parentheses for negatives)
        - Use null for missing values
        - Include up to 3 most recent periods
        - Preserve original capitalization and spacing of line item names
        - Look for tables that break down stock compensation by department/function
        - Often appears in footnotes or supplementary tables, not in main financial statements
        
        8-K Filing Content:
        {html_content}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a financial data extraction expert. Extract EXACT numerical values as they appear in the source document. Do not convert between formats (e.g., don't convert 42,154 to 1.76). Extract raw values precisely."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            # Track token usage
            if response and hasattr(response, 'usage') and response.usage:
                usage = response.usage
                self.last_token_usage = f"Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}"
            print(f"DEBUG: Token usage - {self.last_token_usage}")
            
            if not response or not response.choices or len(response.choices) == 0:
                raise Exception("No response received from OpenAI")
            
            if not response.choices[0].message or not response.choices[0].message.content:
                raise Exception("Empty response content from OpenAI")
            
            result = response.choices[0].message.content.strip()
            
            # Clean up the response to ensure it's valid JSON
            if result.startswith("```json"):
                result = result.replace("```json", "").replace("```", "").strip()
            elif result.startswith("```"):
                result = result.replace("```", "").strip()
            
            return json.loads(result)
            
        except Exception as e:
            error_msg = f"Error extracting SBC breakdown: {e}"
            print(error_msg)
            print(f"DEBUG: Full error details: {str(e)}")
            raise Exception(error_msg)
