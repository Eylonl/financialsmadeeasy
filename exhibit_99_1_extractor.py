"""
Complete 8-K Exhibit 99.1 Table Extraction Pipeline
Main orchestrator for the robust table extraction system
"""
from typing import Dict, List, Any, Optional
from pathlib import Path

# Flat imports like your working app - no subdirectories
import sys
import os

# Add subdirectories to Python path for deployment
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([
    current_dir,
    os.path.join(current_dir, 'extractors'),
    os.path.join(current_dir, 'normalizers'), 
    os.path.join(current_dir, 'outputs')
])

# Import directly from module names (no subdirectory prefixes)
from html_tables import HTMLTableExtractor
from recon_classifier import ReconciliationClassifier, classify_reconciliation_tables
from normalizers.numbers import normalize_table_numbers
from periods import add_period_info_to_table
from vocab import VocabularyNormalizer
from json_writer import write_extraction_results


class Exhibit99Extractor:
    """Complete pipeline for extracting and processing 8-K Exhibit 99.1 tables"""
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize components
        self.table_extractor = HTMLTableExtractor()
        self.recon_classifier = ReconciliationClassifier()
        self.vocab_normalizer = VocabularyNormalizer()
    
    def extract_all_tables(self, html_content: str, filing_id: str = None) -> Dict[str, Any]:
        """
        Complete extraction pipeline for 8-K Exhibit 99.1
        
        Args:
            html_content: Raw HTML content from Exhibit 99.1
            filing_id: Optional filing identifier
            
        Returns:
            Dictionary with extraction results and file paths
        """
        
        print(f"Starting 8-K Exhibit 99.1 extraction pipeline...")
        
        # Step 1: Extract all tables from HTML
        print("Step 1: Discovering and parsing HTML tables...")
        raw_tables = self.table_extractor.extract_all_tables(html_content)
        print(f"Found {len(raw_tables)} tables")
        
        if not raw_tables:
            return {
                "status": "no_tables_found",
                "tables": [],
                "reconciliation_candidates": [],
                "files": {}
            }
        
        # Step 2: Normalize numbers and units
        print("Step 2: Normalizing numbers and units...")
        tables_with_numbers = []
        for table in raw_tables:
            # Convert table metadata to dict format for processing
            table_dict = self._table_metadata_to_dict(table)
            normalized_table = normalize_table_numbers(table_dict)
            tables_with_numbers.append(normalized_table)
        
        # Step 3: Add period information to headers
        print("Step 3: Parsing period information...")
        tables_with_periods = []
        for table in tables_with_numbers:
            table_with_periods = add_period_info_to_table(table)
            tables_with_periods.append(table_with_periods)
        
        # Step 4: Normalize vocabulary and label matching
        print("Step 4: Normalizing financial vocabulary...")
        fully_normalized_tables = []
        for table in tables_with_periods:
            normalized_table = self.vocab_normalizer.normalize_table_labels(table)
            fully_normalized_tables.append(normalized_table)
        
        # Step 5: Score and classify reconciliation candidates
        print("Step 5: Scoring reconciliation candidates...")
        all_scores, candidate_tables = classify_reconciliation_tables(fully_normalized_tables)
        
        # Add scoring results back to tables
        score_lookup = {score.table_id: score for score in all_scores}
        for table in fully_normalized_tables:
            table_id = table.get('table_id', '')
            score_info = score_lookup.get(table_id)
            if score_info:
                table['recon_candidate'] = score_info.recon_candidate
                table['recon_score'] = score_info.recon_score
                table['recon_rationale'] = score_info.recon_rationale
        
        print(f"Identified {len(candidate_tables)} reconciliation candidates")
        
        # Step 6: Generate JSON outputs
        print("Step 6: Writing JSON outputs...")
        # Convert ReconScore objects to dictionaries for JSON serialization
        serializable_scores = []
        for score in all_scores:
            if hasattr(score, 'to_dict'):
                serializable_scores.append(score.to_dict())
            else:
                serializable_scores.append(score)
        
        json_files = write_extraction_results(
            fully_normalized_tables, 
            serializable_scores, 
            candidate_tables, 
            filing_id, 
            str(self.output_dir)
        )
        
        # Step 7: QA reports generation removed
        
        # Combine all file paths
        all_files = json_files
        
        print(f"Extraction complete! Generated {len(all_files)} output files.")
        
        return {
            "status": "success",
            "total_tables": len(fully_normalized_tables),
            "reconciliation_candidates": len(candidate_tables),
            "tables": fully_normalized_tables,
            "candidate_tables": candidate_tables,
            "scores": all_scores,
            "files": all_files
        }
    
    def _table_metadata_to_dict(self, table_metadata) -> Dict[str, Any]:
        """Convert TableMetadata object to dictionary for processing"""
        
        # Convert headers
        headers = table_metadata.headers if table_metadata.headers else []
        
        # Convert rows with cell data
        rows = []
        for row in table_metadata.rows:
            converted_row = []
            for cell in row:
                # Convert CellData to dict
                cell_dict = {
                    'table_id': cell.table_id,
                    'row_idx': cell.row_idx,
                    'col_idx': cell.col_idx,
                    'original_text': cell.original_text
                }
                converted_row.append(cell_dict)
            rows.append(converted_row)
        
        return {
            'table_id': table_metadata.table_id,
            'caption': table_metadata.caption,
            'dom_path': table_metadata.dom_path,
            'shape': table_metadata.shape,
            'fingerprint': table_metadata.fingerprint,
            'headers': headers,
            'rows': rows
        }
    
    def extract_from_file(self, html_file_path: str, filing_id: str = None) -> Dict[str, Any]:
        """Extract tables from HTML file"""
        
        html_path = Path(html_file_path)
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_file_path}")
        
        # Read HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Use filename as filing_id if not provided
        if not filing_id:
            filing_id = html_path.stem
        
        return self.extract_all_tables(html_content, filing_id)
    
    def get_extraction_summary(self, results: Dict[str, Any]) -> str:
        """Generate a summary of extraction results"""
        
        if results.get('status') != 'success':
            return f"Extraction failed: {results.get('status', 'unknown error')}"
        
        total_tables = results.get('total_tables', 0)
        candidates = results.get('reconciliation_candidates', 0)
        files = results.get('files', {})
        
        summary = f"""
8-K Exhibit 99.1 Extraction Summary
==================================

Tables Discovered: {total_tables}
Reconciliation Candidates: {candidates}
Success Rate: {(candidates/total_tables*100) if total_tables > 0 else 0:.1f}%

Generated Files:
"""
        
        for file_type, file_path in files.items():
            summary += f"- {file_type}: {file_path}\n"
        
        if candidates > 0:
            summary += f"\nTop Reconciliation Candidates:\n"
            scores = results.get('scores', [])
            top_candidates = [s for s in scores if s.recon_candidate][:3]
            
            for i, candidate in enumerate(top_candidates, 1):
                summary += f"{i}. {candidate.table_id} (Score: {candidate.recon_score:.1f})\n"
        
        return summary


def extract_exhibit_99_1(html_content: str, filing_id: str = None, 
                         output_dir: str = "outputs") -> Dict[str, Any]:
    """
    Convenience function for complete 8-K Exhibit 99.1 extraction
    
    Args:
        html_content: Raw HTML content from EDGAR
        filing_id: Optional filing identifier  
        output_dir: Output directory for results
        
    Returns:
        Complete extraction results with file paths
    """
    
    extractor = Exhibit99Extractor(output_dir)
    return extractor.extract_all_tables(html_content, filing_id)


def extract_from_file(html_file_path: str, filing_id: str = None, 
                     output_dir: str = "outputs") -> Dict[str, Any]:
    """
    Convenience function to extract from HTML file
    
    Args:
        html_file_path: Path to HTML file
        filing_id: Optional filing identifier
        output_dir: Output directory for results
        
    Returns:
        Complete extraction results with file paths
    """
    
    extractor = Exhibit99Extractor(output_dir)
    return extractor.extract_from_file(html_file_path, filing_id)


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python exhibit_99_1_extractor.py <html_file_path> [filing_id]")
        sys.exit(1)
    
    html_file = sys.argv[1]
    filing_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        results = extract_from_file(html_file, filing_id)
        
        extractor = Exhibit99Extractor()
        summary = extractor.get_extraction_summary(results)
        print(summary)
        
    except Exception as e:
        print(f"Extraction failed: {e}")
        sys.exit(1)
