"""
HTML Table Discovery and Parsing Module
Handles extraction and normalization of all tables from 8-K Exhibit 99.1 HTML
"""
import re
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass


@dataclass
class CellData:
    """Individual cell data with provenance"""
    table_id: str
    row_idx: int
    col_idx: int
    original_text: str
    rowspan: int = 1
    colspan: int = 1


@dataclass
class TableMetadata:
    """Table metadata and structure"""
    table_id: str
    caption: str
    dom_path: str
    shape: Tuple[int, int]  # (rows, cols)
    fingerprint: str
    headers: List[str]
    rows: List[List[CellData]]


class HTMLTableExtractor:
    """Extract and normalize all tables from 8-K Exhibit 99.1 HTML"""
    
    def __init__(self):
        self.tables: List[TableMetadata] = []
        
    def extract_all_tables(self, html_content: str) -> List[TableMetadata]:
        """Main entry point - extract all tables from HTML"""
        # Step 1: Pre-clean HTML
        cleaned_html = self._preprocess_html(html_content)
        
        # Step 2: Parse with BeautifulSoup
        soup = BeautifulSoup(cleaned_html, 'html.parser')
        
        # Step 3: Discover all tables
        table_elements = soup.find_all('table')
        
        # Step 4: Process each table
        self.tables = []
        for idx, table_elem in enumerate(table_elements):
            try:
                table_data = self._process_table(table_elem, idx)
                if table_data:
                    self.tables.append(table_data)
            except Exception as e:
                print(f"Warning: Failed to process table {idx}: {e}")
                continue
        
        return self.tables
    
    def _preprocess_html(self, html_content: str) -> str:
        """Clean and normalize HTML content"""
        # Remove unwanted tags
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Strip problematic tags
        for tag in soup.find_all(['script', 'style', 'noscript']):
            tag.decompose()
        
        # Remove sup tags but keep content
        for sup in soup.find_all('sup'):
            sup.unwrap()
        
        html_str = str(soup)
        
        # Normalize whitespace and special characters
        html_str = re.sub(r'\s+', ' ', html_str)  # Collapse whitespace
        html_str = html_str.replace('&nbsp;', ' ')  # Convert nbsp to space
        html_str = html_str.replace('\u2212', '-')  # Unicode minus to regular minus
        html_str = html_str.replace('\u2013', '-')  # En dash to minus
        html_str = html_str.replace('\u2014', '-')  # Em dash to minus
        
        return html_str
    
    def _process_table(self, table_elem: Tag, table_idx: int) -> Optional[TableMetadata]:
        """Process a single table element"""
        table_id = f"table_{table_idx:03d}"
        
        # Extract caption and DOM path
        caption = self._extract_caption(table_elem)
        dom_path = self._get_dom_path(table_elem)
        
        # Extract raw table structure
        raw_grid = self._extract_raw_grid(table_elem)
        if not raw_grid:
            return None
        
        # Expand merged cells (rowspan/colspan)
        expanded_grid = self._expand_merged_cells(raw_grid)
        
        # Trim empty rows/columns
        trimmed_grid = self._trim_empty_rows_cols(expanded_grid)
        if not trimmed_grid:
            return None
        
        # Detect headers
        headers, data_rows = self._detect_headers(trimmed_grid)
        
        # Create cell objects with provenance
        processed_rows = []
        for row_idx, row in enumerate(data_rows):
            processed_row = []
            for col_idx, cell_text in enumerate(row):
                cell = CellData(
                    table_id=table_id,
                    row_idx=row_idx,
                    col_idx=col_idx,
                    original_text=cell_text.strip() if cell_text else ""
                )
                processed_row.append(cell)
            processed_rows.append(processed_row)
        
        # Calculate shape and fingerprint
        shape = (len(processed_rows), len(headers) if headers else 0)
        fingerprint = self._calculate_fingerprint(headers, processed_rows)
        
        return TableMetadata(
            table_id=table_id,
            caption=caption,
            dom_path=dom_path,
            shape=shape,
            fingerprint=fingerprint,
            headers=headers,
            rows=processed_rows
        )
    
    def _extract_caption(self, table_elem: Tag) -> str:
        """Extract table caption from nearby elements"""
        caption_sources = []
        
        # Check for <caption> tag
        caption_tag = table_elem.find('caption')
        if caption_tag:
            caption_sources.append(caption_tag.get_text().strip())
        
        # Check preceding siblings for headings
        prev_sibling = table_elem.find_previous_sibling()
        while prev_sibling and len(caption_sources) < 3:
            if prev_sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
                text = prev_sibling.get_text().strip()
                if text and len(text) < 200:  # Reasonable caption length
                    caption_sources.append(text)
            prev_sibling = prev_sibling.find_previous_sibling()
        
        # Return the most relevant caption
        if caption_sources:
            return caption_sources[0]
        return ""
    
    def _get_dom_path(self, element: Tag) -> str:
        """Generate DOM path for the table element"""
        path_parts = []
        current = element
        
        while current and current.name:
            tag_name = current.name
            # Add index if there are siblings with same tag
            siblings = [s for s in current.parent.children if hasattr(s, 'name') and s.name == tag_name] if current.parent else []
            if len(siblings) > 1:
                idx = siblings.index(current)
                tag_name += f"[{idx}]"
            path_parts.append(tag_name)
            current = current.parent
        
        return " > ".join(reversed(path_parts))
    
    def _extract_raw_grid(self, table_elem: Tag) -> List[List[Dict]]:
        """Extract raw table structure with rowspan/colspan info"""
        rows = []
        
        # Find all row elements (tr, and sometimes direct td/th in malformed tables)
        row_elements = table_elem.find_all(['tr'])
        
        for row_elem in row_elements:
            cells = []
            cell_elements = row_elem.find_all(['td', 'th'])
            
            for cell_elem in cell_elements:
                cell_data = {
                    'text': cell_elem.get_text().strip(),
                    'rowspan': int(cell_elem.get('rowspan', 1)),
                    'colspan': int(cell_elem.get('colspan', 1)),
                    'is_header': cell_elem.name == 'th'
                }
                cells.append(cell_data)
            
            if cells:  # Only add non-empty rows
                rows.append(cells)
        
        return rows
    
    def _expand_merged_cells(self, raw_grid: List[List[Dict]]) -> List[List[str]]:
        """Expand rowspan/colspan into rectangular grid"""
        if not raw_grid:
            return []
        
        # Calculate maximum dimensions needed
        max_cols = 0
        for row in raw_grid:
            col_count = sum(cell['colspan'] for cell in row)
            max_cols = max(max_cols, col_count)
        
        # Create expanded grid
        expanded = []
        
        for row_idx, row in enumerate(raw_grid):
            # Initialize row if needed
            while len(expanded) <= row_idx:
                expanded.append([''] * max_cols)
            
            col_pos = 0
            for cell in row:
                # Find next available position
                while col_pos < len(expanded[row_idx]) and expanded[row_idx][col_pos] != '':
                    col_pos += 1
                
                # Fill the cell and its spans
                for r in range(cell['rowspan']):
                    for c in range(cell['colspan']):
                        target_row = row_idx + r
                        target_col = col_pos + c
                        
                        # Ensure grid is large enough
                        while len(expanded) <= target_row:
                            expanded.append([''] * max_cols)
                        while len(expanded[target_row]) <= target_col:
                            expanded[target_row].extend([''] * (target_col - len(expanded[target_row]) + 1))
                        
                        # Fill with cell text (only in top-left of merged area)
                        if r == 0 and c == 0:
                            expanded[target_row][target_col] = cell['text']
                        else:
                            expanded[target_row][target_col] = ''  # Merged cell continuation
                
                col_pos += cell['colspan']
        
        return expanded
    
    def _trim_empty_rows_cols(self, grid: List[List[str]]) -> List[List[str]]:
        """Remove empty leading/trailing rows and columns"""
        if not grid:
            return []
        
        # Remove empty rows from start and end
        while grid and all(not cell.strip() for cell in grid[0]):
            grid.pop(0)
        while grid and all(not cell.strip() for cell in grid[-1]):
            grid.pop()
        
        if not grid:
            return []
        
        # Remove empty columns from start and end
        max_cols = max(len(row) for row in grid)
        
        # Normalize row lengths
        for row in grid:
            while len(row) < max_cols:
                row.append('')
        
        # Find first and last non-empty columns
        first_col = max_cols
        last_col = -1
        
        for col_idx in range(max_cols):
            if any(row[col_idx].strip() for row in grid):
                first_col = min(first_col, col_idx)
                last_col = max(last_col, col_idx)
        
        if first_col > last_col:
            return []
        
        # Trim columns
        trimmed = []
        for row in grid:
            trimmed_row = row[first_col:last_col + 1]
            trimmed.append(trimmed_row)
        
        return trimmed
    
    def _detect_headers(self, grid: List[List[str]]) -> Tuple[List[str], List[List[str]]]:
        """Detect header row(s) and separate from data"""
        if not grid:
            return [], []
        
        # Find first dense row (≥40% non-empty) as potential header
        header_row_idx = 0
        for idx, row in enumerate(grid):
            non_empty_count = sum(1 for cell in row if cell.strip())
            density = non_empty_count / len(row) if row else 0
            if density >= 0.4:
                header_row_idx = idx
                break
        
        # Check for multi-row headers (concatenate vertically)
        headers = []
        data_start_idx = header_row_idx + 1
        
        # Handle multi-row headers by looking for continuation patterns
        header_rows = [grid[header_row_idx]]
        
        # Look for additional header rows (common in financial tables)
        for next_idx in range(header_row_idx + 1, min(header_row_idx + 3, len(grid))):
            if next_idx < len(grid):
                next_row = grid[next_idx]
                # Check if this looks like a continuation of headers
                if self._looks_like_header_continuation(header_rows[-1], next_row):
                    header_rows.append(next_row)
                    data_start_idx = next_idx + 1
                else:
                    break
        
        # Concatenate multi-row headers
        if header_rows:
            num_cols = max(len(row) for row in header_rows)
            for col_idx in range(num_cols):
                header_parts = []
                for header_row in header_rows:
                    if col_idx < len(header_row) and header_row[col_idx].strip():
                        header_parts.append(header_row[col_idx].strip())
                
                # Join header parts with space
                final_header = ' '.join(header_parts) if header_parts else f"Column_{col_idx}"
                headers.append(final_header)
        
        # Extract data rows
        data_rows = grid[data_start_idx:] if data_start_idx < len(grid) else []
        
        return headers, data_rows
    
    def _looks_like_header_continuation(self, prev_header_row: List[str], candidate_row: List[str]) -> bool:
        """Check if a row looks like a continuation of multi-row headers"""
        # Simple heuristics for header continuation
        non_numeric_count = 0
        total_cells = len(candidate_row)
        
        for cell in candidate_row:
            cell_text = cell.strip()
            if cell_text and not self._looks_like_number(cell_text):
                non_numeric_count += 1
        
        # If most cells are non-numeric text, likely a header continuation
        return (non_numeric_count / total_cells) > 0.6 if total_cells > 0 else False
    
    def _looks_like_number(self, text: str) -> bool:
        """Quick check if text looks like a number"""
        if not text:
            return False
        
        # Remove common formatting
        clean_text = text.replace(',', '').replace('$', '').replace('(', '').replace(')', '').replace('%', '').strip()
        
        try:
            float(clean_text)
            return True
        except ValueError:
            return False
    
    def _calculate_fingerprint(self, headers: List[str], rows: List[List[CellData]]) -> str:
        """Calculate unique fingerprint for table structure"""
        # Combine headers, first column, and shape for fingerprint
        fingerprint_data = []
        
        # Add headers
        fingerprint_data.extend(headers)
        
        # Add first column (up to 5 rows)
        for i, row in enumerate(rows[:5]):
            if row:
                fingerprint_data.append(row[0].original_text)
        
        # Add shape info
        fingerprint_data.append(f"shape_{len(rows)}x{len(headers)}")
        
        # Create hash
        combined_text = '|'.join(fingerprint_data)
        return hashlib.md5(combined_text.encode()).hexdigest()[:12]
