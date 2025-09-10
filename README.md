# Financial Statements Extractor

A Streamlit application that extracts Income Statement, Balance Sheet, and Cash Flow Statement data from SEC 8-K earnings releases using AI-powered parsing.

## Features

- **SEC 8-K Integration**: Automatically fetch 8-K earnings releases from SEC EDGAR database
- **AI-Powered Extraction**: Use OpenAI GPT to intelligently extract financial statement data
- **Multi-Statement Support**: Extract all three core financial statements
- **Excel Export**: Generate formatted Excel files with separate sheets for each statement
- **Flexible Timeframes**: Support for "last quarter", "last year", "last 4 quarters", etc.

## Technology Stack

- **Frontend**: Streamlit
- **Data Source**: SEC EDGAR database
- **AI**: OpenAI GPT models
- **Export**: Excel (openpyxl)

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Copy `.env.template` to `.env` and fill in your values:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SEC_USER_AGENT=FinancialExtractor/1.0 (+your_email@domain.com)
   ```

3. **Run Locally**
   ```bash
   streamlit run streamlit_app.py
   ```

## Usage

1. Enter a stock ticker (e.g., AAPL, MSFT, GOOGL)
2. Select timeframe (Last Year, Last 2 Years, Last 4 Quarters)
3. Click "Extract Financial Statements"
4. Download the generated Excel file

## Output Format

The Excel file contains four sheets:
- **Income Statement**: Revenue, expenses, net income data
- **Balance Sheet**: Assets, liabilities, equity data  
- **Cash Flow Statement**: Operating, investing, financing cash flows
- **Summary**: Key metrics and ratios

## Requirements

- Python 3.8+
- OpenAI API key
- Internet connection for SEC EDGAR access
