"""
JSON output writer for financial extraction results
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


def write_extraction_results(
    normalized_tables: List[Dict[str, Any]], 
    scores: List[Dict[str, Any]], 
    candidate_tables: List[Dict[str, Any]], 
    filing_id: str = None,
    output_dir: str = "outputs"
) -> Dict[str, str]:
    """
    Write extraction results to JSON files
    
    Args:
        normalized_tables: List of normalized table data
        scores: List of table scores and classifications
        candidate_tables: List of candidate tables found
        filing_id: Filing identifier for output naming
        output_dir: Output directory path
        
    Returns:
        Dictionary with paths to created JSON files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = filing_id or f"extraction_{timestamp}"
    
    json_files = {}
    
    # Write normalized tables
    tables_file = output_path / f"tables_{base_name}.json"
    with open(tables_file, 'w', encoding='utf-8') as f:
        json.dump({
            "filing_id": filing_id,
            "extraction_timestamp": timestamp,
            "normalized_tables": normalized_tables
        }, f, indent=2, ensure_ascii=False)
    json_files['tables'] = str(tables_file)
    
    # Write reconciliation candidates and scores
    recon_file = output_path / f"recon_candidates_{base_name}.json"
    with open(recon_file, 'w', encoding='utf-8') as f:
        json.dump({
            "filing_id": filing_id,
            "extraction_timestamp": timestamp,
            "candidate_tables": candidate_tables,
            "scores": scores
        }, f, indent=2, ensure_ascii=False)
    json_files['reconciliation'] = str(recon_file)
    
    return json_files


def generate_qa_reports(extraction_data: Dict[str, Any], output_dir: str = "outputs") -> str:
    """
    Generate QA reports for extraction results
    
    Args:
        extraction_data: Extracted financial data
        output_dir: Output directory path
        
    Returns:
        Path to generated QA report
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    qa_file = output_path / f"qa_report_{timestamp}.json"
    
    # Generate basic QA metrics
    qa_data = {
        "timestamp": timestamp,
        "extraction_summary": {
            "total_tables": len(extraction_data.get('normalized_tables', [])),
            "total_candidates": len(extraction_data.get('candidate_tables', [])),
            "high_confidence_tables": len([
                t for t in extraction_data.get('scores', []) 
                if t.get('confidence_score', 0) > 0.8
            ])
        },
        "data_quality_checks": {
            "tables_with_periods": len([
                t for t in extraction_data.get('normalized_tables', [])
                if t.get('periods')
            ]),
            "tables_with_line_items": len([
                t for t in extraction_data.get('normalized_tables', [])
                if t.get('line_items')
            ])
        }
    }
    
    with open(qa_file, 'w', encoding='utf-8') as f:
        json.dump(qa_data, f, indent=2, ensure_ascii=False)
    
    return str(qa_file)
