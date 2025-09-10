"""
SEC EDGAR API integration for fetching 8-K earnings releases
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

class SECEdgar:
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.headers = {
            "User-Agent": os.getenv("SEC_USER_AGENT", "FinancialExtractor/1.0 contact@example.com"),
            "Accept-Encoding": "gzip, deflate"
        }
    
    def get_company_cik(self, ticker: str) -> Optional[str]:
        """Get CIK number for a given ticker symbol"""
        try:
            # Get company tickers JSON - use SEC's direct URL
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            
            # Search for ticker using the same logic as working app
            for entry in data.values():
                if entry["ticker"].upper() == ticker.upper():
                    return str(entry["cik_str"]).zfill(10)
            
            return None
        except Exception as e:
            print(f"Error getting CIK for {ticker}: {e}")
            return None
    
    def get_fiscal_year_end(self, ticker: str, cik: str) -> tuple:
        """Get the fiscal year end month for a company from SEC data"""
        try:
            url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            resp = requests.get(url, headers=self.headers)
            resp.raise_for_status()
            data = resp.json()
            if 'fiscalYearEnd' in data:
                fiscal_year_end = data['fiscalYearEnd']
                if len(fiscal_year_end) == 4:
                    month = int(fiscal_year_end[:2])
                    day = int(fiscal_year_end[2:])
                    month_name = datetime(2000, month, 1).strftime('%B')
                    print(f"Retrieved fiscal year end for {ticker}: {month_name} {day}")
                    return month, day
            print(f"Could not determine fiscal year end for {ticker} from SEC data. Using December 31 (calendar year).")
            return 12, 31
        except Exception as e:
            print(f"Error retrieving fiscal year end: {str(e)}. Using December 31 (calendar year).")
            return 12, 31

    def generate_fiscal_quarters(self, fiscal_year_end_month: int) -> dict:
        """Dynamically generate fiscal quarters based on the fiscal year end month"""
        fiscal_year_start_month = (fiscal_year_end_month % 12) + 1
        quarters = {}
        current_month = fiscal_year_start_month
        for q in range(1, 5):
            start_month = current_month
            end_month = (start_month + 2) % 12
            if end_month == 0:
                end_month = 12
            quarters[q] = {'start_month': start_month, 'end_month': end_month}
            current_month = (end_month % 12) + 1
        return quarters

    def get_fiscal_dates(self, ticker: str, quarter_num: int, year_num: int, fiscal_year_end_month: int, fiscal_year_end_day: int) -> dict:
        """Calculate the appropriate date range for a fiscal quarter"""
        quarters = self.generate_fiscal_quarters(fiscal_year_end_month)
        if quarter_num < 1 or quarter_num > 4:
            print(f"Invalid quarter number: {quarter_num}. Must be 1-4.")
            return None
        quarter_info = quarters[quarter_num]
        start_month = quarter_info['start_month']
        end_month = quarter_info['end_month']
        spans_calendar_years = end_month < start_month
        if fiscal_year_end_month == 12:
            start_calendar_year = year_num
        else:
            fiscal_year_start_month = (fiscal_year_end_month % 12) + 1
            if start_month >= fiscal_year_start_month:
                start_calendar_year = year_num - 1
            else:
                start_calendar_year = year_num
        end_calendar_year = start_calendar_year
        if spans_calendar_years:
            end_calendar_year = start_calendar_year + 1
        start_date = datetime(start_calendar_year, start_month, 1)
        if end_month == 2:
            if (end_calendar_year % 4 == 0 and end_calendar_year % 100 != 0) or (end_calendar_year % 400 == 0):
                end_day = 29
            else:
                end_day = 28
        elif end_month in [4, 6, 9, 11]:
            end_day = 30
        else:
            end_day = 31
        end_date = datetime(end_calendar_year, end_month, end_day)
        report_start = end_date + timedelta(days=15)
        report_end = report_start + timedelta(days=45)
        quarter_period = f"Q{quarter_num} FY{year_num}"
        period_description = f"{start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}"
        expected_report = f"~{report_start.strftime('%B %d, %Y')} to {report_end.strftime('%B %d, %Y')}"
        print(f"Fiscal year ends in {datetime(2000, fiscal_year_end_month, 1).strftime('%B')} {fiscal_year_end_day}")
        print(f"Quarter {quarter_num} spans: {datetime(2000, start_month, 1).strftime('%B')}-{datetime(2000, end_month, 1).strftime('%B')}")
        print("All quarters for this fiscal pattern:")
        for q, q_info in quarters.items():
            print(f"Q{q}: {datetime(2000, q_info['start_month'], 1).strftime('%B')}-{datetime(2000, q_info['end_month'], 1).strftime('%B')}")
        return {
            'quarter_period': quarter_period,
            'start_date': start_date,
            'end_date': end_date,
            'report_start': report_start,
            'report_end': report_end,
            'period_description': period_description,
            'expected_report': expected_report
        }

    def get_accessions(self, cik: str, ticker: str, years_back: int = None, specific_quarter: str = None) -> List[tuple]:
        """General function for finding filings"""
        print(f"\n=== DEBUG: get_accessions called ===")
        print(f"CIK: {cik}")
        print(f"Ticker: {ticker}")
        print(f"Years back: {years_back}")
        print(f"Specific quarter: {specific_quarter}")
        
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        data = resp.json()
        filings = data["filings"]["recent"]
        accessions = []
        fiscal_year_end_month, fiscal_year_end_day = self.get_fiscal_year_end(ticker, cik)
        
        print(f"Fiscal year end: {fiscal_year_end_month}/{fiscal_year_end_day}")
        print(f"Total 8-K filings available: {sum(1 for form in filings['form'] if form == '8-K')}")
        
        if years_back:
            cutoff = datetime.today() - timedelta(days=(365 * years_back) + 91.25)
            print(f"Looking for filings from the past {years_back} years plus 1 quarter (from {cutoff.strftime('%Y-%m-%d')} to present)")
            for form, date_str, accession in zip(filings["form"], filings["filingDate"], filings["accessionNumber"]):
                if form == "8-K":
                    date = datetime.strptime(date_str, "%Y-%m-%d")
                    if date >= cutoff:
                        accessions.append((accession, date_str))
        elif specific_quarter:
            print(f"Processing specific quarter: {specific_quarter}")
            match = re.search(r'(?:Q?(\d)Q?|Q(\d))(?:\s*FY\s*|\s*)?(\d{2}|\d{4})', specific_quarter.upper())
            if match:
                quarter = match.group(1) or match.group(2)
                year = match.group(3)
                if len(year) == 2:
                    year = '20' + year
                try:
                    quarter_num = int(quarter)
                    year_num = int(year)
                    print(f"Parsed quarter: Q{quarter_num} FY{year_num}")
                except (ValueError, OSError) as e:
                    print(f"Error parsing quarter/year values: quarter='{quarter}', year='{year}', error={e}")
                    return []
                
                fiscal_info = self.get_fiscal_dates(ticker, quarter_num, year_num, fiscal_year_end_month, fiscal_year_end_day)
                if not fiscal_info:
                    print("ERROR: Could not get fiscal dates")
                    return []
                print(f"Looking for {ticker} {fiscal_info['quarter_period']} filings")
                print(f"Fiscal quarter period: {fiscal_info['period_description']}")
                print(f"Expected earnings reporting window: {fiscal_info['expected_report']}")
                start_date = fiscal_info['report_start'] - timedelta(days=15)
                end_date = fiscal_info['report_end'] + timedelta(days=15)
                print(f"Searching for filings between: {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
                
                # Debug: Show all 8-K filings for comparison
                all_8k_dates = []
                for form, date_str, accession in zip(filings["form"], filings["filingDate"], filings["accessionNumber"]):
                    if form == "8-K":
                        all_8k_dates.append(date_str)
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        if start_date <= date <= end_date:
                            accessions.append((accession, date_str))
                            print(f"[FOUND] Found filing from {date_str}: {accession}")
                
                print(f"All available 8-K dates for {ticker}:")
                for date in sorted(all_8k_dates, reverse=True)[:10]:
                    print(f"  - {date}")
            else:
                print(f"ERROR: Could not parse quarter format: {specific_quarter}")
        else:
            # Default: auto-detect most recent quarter and search for that specific quarter's earnings
            current_date = datetime.today()
            
            # Determine the most recent completed quarter based on fiscal year end
            if fiscal_year_end_month <= 3:  # Jan-Mar fiscal year end
                if current_date.month <= fiscal_year_end_month:
                    # We're in the fiscal year, determine quarter
                    quarter_num = ((current_date.month - fiscal_year_end_month - 1) % 12) // 3 + 1
                    year_num = current_date.year
                else:
                    # We're past fiscal year end, so last quarter was Q4 of previous fiscal year
                    quarter_num = 4
                    year_num = current_date.year
            else:  # Apr-Dec fiscal year end
                if current_date.month > fiscal_year_end_month:
                    # We're past fiscal year end, so last quarter was Q4
                    quarter_num = 4
                    year_num = current_date.year
                else:
                    # We're in the fiscal year
                    months_into_fy = (current_date.month - fiscal_year_end_month - 1) % 12
                    quarter_num = months_into_fy // 3 + 1
                    year_num = current_date.year
            
            # Adjust for the most recent completed quarter (subtract 1 quarter)
            quarter_num -= 1
            if quarter_num <= 0:
                quarter_num = 4
                year_num -= 1
            
            print(f"Auto-detecting most recent quarter: Q{quarter_num} {year_num}")
            
            # Use the quarter-based search logic
            fiscal_info = self.get_fiscal_dates(ticker, quarter_num, year_num, fiscal_year_end_month, fiscal_year_end_day)
            if fiscal_info:
                print(f"Looking for {ticker} {fiscal_info['quarter_period']} filings")
                print(f"Expected earnings reporting window: {fiscal_info['expected_report']}")
                start_date = fiscal_info['report_start'] - timedelta(days=15)
                end_date = fiscal_info['report_end'] + timedelta(days=15)
                print(f"Searching for filings between: {start_date.strftime('%Y-%m-%d')} and {end_date.strftime('%Y-%m-%d')}")
                for form, date_str, accession in zip(filings["form"], filings["filingDate"], filings["accessionNumber"]):
                    if form == "8-K":
                        date = datetime.strptime(date_str, "%Y-%m-%d")
                        if start_date <= date <= end_date:
                            accessions.append((accession, date_str))
                            print(f"Found filing from {date_str}: {accession}")
        
        if accessions:
            print(f"Found {len(accessions)} relevant 8-K filings")
        else:
            available_dates = []
            for form, date_str in zip(filings["form"], filings["filingDate"]):
                if form == "8-K":
                    available_dates.append(date_str)
            if available_dates:
                available_dates.sort(reverse=True)
                print("All available 8-K filing dates:")
                for date in available_dates[:15]:
                    print(f"- {date}")
                if len(available_dates) > 15:
                    print(f"... and {len(available_dates) - 15} more")
        return accessions
    
    def get_ex99_1_links(self, cik: str, accessions: List[tuple]) -> List[tuple]:
        """Enhanced function to find exhibit 99.1 files with better searching and earnings validation"""
        try:
            print(f"\n=== DEBUG: get_ex99_1_links called ===")
            print(f"CIK: {cik}")
            print(f"Number of accessions to process: {len(accessions)}")
        except OSError:
            # Handle console output issues on Windows
            print("DEBUG: get_ex99_1_links called")
            print(f"CIK: {str(cik)}")
            print(f"Number of accessions to process: {str(len(accessions))}")
        
        links = []
        for i, (accession, date_str) in enumerate(accessions):
            try:
                print(f"\n--- Processing accession {i+1}/{len(accessions)}: {accession} ({date_str}) ---")
            except OSError:
                # Handle invalid characters in date_str that cause print issues on Windows
                safe_date = str(date_str).replace(':', '-').replace('/', '-')
                print(f"\n--- Processing accession {i+1}/{len(accessions)}: {accession} ({safe_date}) ---")
            accession_no_dashes = accession.replace('-', '')
            base_folder = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_no_dashes}/"
            index_url = base_folder + f"{accession}-index.htm"
            # Handle special characters in URL for Windows printing
            safe_url = str(index_url).encode('ascii', 'ignore').decode('ascii')
            print(f"Index URL: {safe_url}")
            
            try:
                res = requests.get(index_url, headers=self.headers, timeout=30)
                if res.status_code != 200:
                    print(f"❌ Failed to get index page: HTTP {res.status_code}")
                    continue
                soup = BeautifulSoup(res.text, "html.parser")
                found_exhibit = False
                
                # First, look for explicit 99.1 exhibits
                for row in soup.find_all("tr"):
                    row_text = row.get_text().lower()
                    if "99.1" in row_text or "99.01" in row_text:
                        tds = row.find_all("td")
                        if len(tds) >= 3:
                            filename = tds[2].text.strip()
                            exhibit_url = base_folder + filename
                            
                            # Validate it's an earnings release
                            if self.is_earnings_release(exhibit_url):
                                print(f"[VALID] Validated earnings release: {exhibit_url}")
                                links.append((date_str, accession, exhibit_url))
                                found_exhibit = True
                                break
                            else:
                                print(f"[SKIP] Skipped non-earnings 8-K: {exhibit_url}")
                
                # If no explicit 99.1, look for other exhibit files
                if not found_exhibit:
                    for row in soup.find_all("tr"):
                        tds = row.find_all("td")
                        if len(tds) >= 3:
                            filename = tds[2].text.strip()
                            if filename.endswith('.htm') and ('ex' in filename.lower() or 'exhibit' in filename.lower()):
                                exhibit_url = base_folder + filename
                                
                                # Validate it's an earnings release
                                if self.is_earnings_release(exhibit_url):
                                    print(f"[VALID] Validated earnings release: {exhibit_url}")
                                    links.append((date_str, accession, exhibit_url))
                                    found_exhibit = True
                                    break
                                else:
                                    print(f"[SKIP] Skipped non-earnings 8-K: {exhibit_url}")
                
                # Try common patterns as fallback
                if not found_exhibit:
                    date_no_dash = date_str.replace('-', '')
                    common_patterns = [
                        f"ex-991x{date_no_dash}x8k.htm",
                        f"ex991x{date_no_dash}x8k.htm",
                        f"ex-99_1x{date_no_dash}x8k.htm",
                        f"ex991{date_no_dash}.htm", 
                        f"exhibit991.htm",
                        f"ex99-1.htm",
                        f"ex991.htm",
                        f"ex-99.1.htm",
                        f"exhibit99_1.htm"
                    ]
                    for pattern in common_patterns:
                        test_url = base_folder + pattern
                        try:
                            test_res = requests.head(test_url, headers=self.headers, timeout=10)
                            if test_res.status_code == 200:
                                # Validate it's an earnings release
                                if self.is_earnings_release(test_url):
                                    print(f"[VALID] Validated earnings release: {test_url}")
                                    links.append((date_str, accession, test_url))
                                    found_exhibit = True
                                    break
                                else:
                                    print(f"[SKIP] Skipped non-earnings 8-K: {test_url}")
                        except:
                            continue
            except Exception as e:
                print(f"Error processing accession {accession}: {str(e)}")
                continue
        return links
    
    def is_earnings_release(self, url: str) -> bool:
        """Validate that a document is actually an earnings release"""
        try:
            # Skip iXBRL files that cause redirect issues
            if 'ixbrl' in url.lower():
                print(f"Skipped iXBRL file: {url}")
                return False
                
            # Get a sample of the document content with redirect handling
            res = requests.get(url, headers=self.headers, timeout=30, allow_redirects=False)
            
            # Handle redirects manually to avoid infinite loops
            if res.status_code in [301, 302, 303, 307, 308]:
                print(f"Skipped redirected URL: {url}")
                return False
                
            if res.status_code != 200:
                return False
            
            content = res.text.lower()
            
            # Check for earnings-related keywords
            earnings_keywords = [
                'earnings', 'quarterly results', 'financial results', 
                'revenue', 'net income', 'earnings per share', 'eps',
                'quarterly earnings', 'fiscal quarter', 'q1', 'q2', 'q3', 'q4',
                'first quarter', 'second quarter', 'third quarter', 'fourth quarter'
            ]
            
            # Must have at least 3 earnings keywords
            keyword_count = sum(1 for keyword in earnings_keywords if keyword in content)
            
            # Strong exclusion indicators (these are likely NOT earnings releases)
            strong_exclusions = [
                'dividend declaration only', 'stock split announcement', 
                'director appointment', 'officer appointment',
                'merger agreement', 'acquisition agreement'
            ]
            
            # Check for strong exclusions that indicate non-earnings documents
            has_strong_exclusions = any(exclusion in content for exclusion in strong_exclusions)
            
            # Additional check: if it has many earnings keywords, it's likely an earnings release
            # even if it mentions some business activities
            is_likely_earnings = keyword_count >= 5
            
            # Must have earnings keywords and either be clearly earnings-focused or not have strong exclusions
            return keyword_count >= 3 and (is_likely_earnings or not has_strong_exclusions)
            
        except Exception as e:
            print(f"Error validating earnings release {url}: {str(e)}")
            return False

    def extract_financial_tables(self, html_content: str) -> Dict[str, str]:
        """Extract financial statement tables from HTML content"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Common patterns for financial statements
            patterns = {
                'income_statement': [
                    'consolidated statements of operations',
                    'consolidated statements of income',
                    'statements of operations',
                    'income statement',
                    'profit and loss'
                ],
                'balance_sheet': [
                    'consolidated balance sheets',
                    'balance sheets',
                    'consolidated statements of financial position',
                    'statements of financial position'
                ],
                'cash_flow': [
                    'consolidated statements of cash flows',
                    'statements of cash flows',
                    'cash flow statements'
                ],
                'sbc_breakdown': [
                    'stock-based compensation expense',
                    'stock based compensation expense',
                    'share-based compensation expense',
                    'share based compensation expense',
                    'stock compensation expense',
                    'equity compensation expense',
                    'includes stock-based compensation expense as follows',
                    'stock-based compensation',
                    'share-based compensation'
                ],
                'gaap_reconciliation': [
                    'reconciliation of gaap to non-gaap',
                    'gaap to non-gaap reconciliation',
                    'reconciliation of non-gaap',
                    'adjusted earnings reconciliation',
                    'non-gaap financial measures',
                    'reconciliation table'
                ]
            }
            
            results = {}
            
            # Find tables by looking for headers
            for statement_type, search_terms in patterns.items():
                for term in search_terms:
                    # Look for text containing the term
                    elements = soup.find_all(text=re.compile(term, re.IGNORECASE))
                    
                    for element in elements:
                        # Find the parent table or div
                        parent = element.parent
                        while parent and parent.name not in ['table', 'div']:
                            parent = parent.parent
                        
                        if parent:
                            # Start with the header element - clean text only
                            content_parts = [parent.get_text(strip=True)]
                            
                            # Get all following siblings that contain table data
                            current = parent
                            for _ in range(10):  # Look ahead up to 10 siblings
                                next_sibling = current.find_next_sibling()
                                if next_sibling:
                                    sibling_text = next_sibling.get_text().lower()
                                    # Include if it contains table-like content or financial data
                                    if (next_sibling.name in ['table', 'div'] and 
                                        (len(sibling_text) > 50 or 
                                         any(keyword in sibling_text for keyword in 
                                             ['revenue', 'income', 'expense', 'total', 'assets', 'liabilities', 
                                              'cash', 'operations', '$', 'thousand', 'million']))):
                                        
                                        # Extract clean table structure
                                        clean_content = self.extract_clean_table_content(next_sibling)
                                        if clean_content:
                                            content_parts.append(clean_content)
                                        current = next_sibling
                                    else:
                                        # Stop if we hit a different section
                                        if any(stop_word in sibling_text for stop_word in 
                                               ['consolidated balance', 'cash flows', 'stockholders', 'notes to']):
                                            break
                                        current = next_sibling
                                else:
                                    break
                            
                            results[statement_type] = '\n\n'.join(content_parts)
                            break
                    
                    if statement_type in results:
                        break
            
            return results
            
        except Exception as e:
            print(f"Error extracting financial tables: {e}")
            return {}
    
    def extract_clean_table_content(self, element) -> str:
        """Extract clean table content without HTML styling metadata"""
        try:
            if element.name == 'table':
                # Extract table rows and cells with clean text
                rows = []
                for tr in element.find_all('tr'):
                    cells = []
                    for td in tr.find_all(['td', 'th']):
                        # Get clean text, preserve numbers and basic formatting
                        cell_text = td.get_text(strip=True)
                        if cell_text:  # Only include non-empty cells
                            cells.append(cell_text)
                    if cells:  # Only include non-empty rows
                        rows.append('\t'.join(cells))
                return '\n'.join(rows)
            else:
                # For div elements, just get clean text
                return element.get_text(strip=True)
        except Exception as e:
            print(f"Error cleaning table content: {e}")
            return ""
    
    def get_filings_by_timeframe(self, ticker: str, year_input: str = "", quarter_input: str = "") -> List[Dict]:
        """Get 8-K earnings releases based on timeframe specification"""
        cik = self.get_company_cik(ticker)
        if not cik:
            return []
        
        # Parse timeframe for 8-K earnings releases
        if quarter_input.strip():
            accessions = self.get_accessions(cik, ticker, specific_quarter=quarter_input.strip())
        elif year_input.strip():
            try:
                years_back = int(year_input.strip())
                accessions = self.get_accessions(cik, ticker, years_back=years_back)
            except ValueError:
                print("Invalid year input. Must be a number.")
                accessions = []
        else:
            accessions = self.get_accessions(cik, ticker)
        
        # Get exhibit 99.1 links (earnings releases)
        earnings_links = self.get_ex99_1_links(cik, accessions)
        
        # Convert to filing format and add content
        filings = []
        for date_str, accession, exhibit_url in earnings_links:
            try:
                # Get the earnings release content
                response = requests.get(exhibit_url, headers=self.headers, timeout=30)
                if response.status_code == 200:
                    content = response.text
                    filing = {
                        'form': '8-K',
                        'accession_number': accession,
                        'filing_date': date_str,
                        'report_date': date_str,
                        'cik': cik,
                        'content': content,
                        'exhibit_url': exhibit_url,
                        'financial_tables': self.extract_financial_tables(content)
                    }
                    filings.append(filing)
            except Exception as e:
                print(f"Error getting content for {exhibit_url}: {e}")
                continue
        
        return filings
