"""
Reconciliation Candidate Classifier Module
Scores and identifies likely GAAP ↔ Non-GAAP reconciliation tables
"""
import re
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class ReconScore:
    """Reconciliation scoring result"""
    table_id: str
    recon_score: float
    recon_candidate: bool
    recon_rationale: List[str]


class ReconciliationClassifier:
    """Classify tables as reconciliation candidates using heuristics"""
    
    def __init__(self):
        # Keyword scoring weights
        self.keyword_weights = {
            # High-value reconciliation keywords
            'reconciliation': 10,
            'gaap': 8,
            'non-gaap': 8,
            'non gaap': 8,
            'adjusted': 6,
            
            # Reconciliation phrases
            'reconciliation of': 15,
            'gaap to non-gaap': 15,
            'non-gaap reconciliation': 12,
            'reconciliation table': 10,
            
            # Financial line items common in reconciliations
            'stock-based compensation': 5,
            'stock based compensation': 5,
            'share-based compensation': 5,
            'amortization of intangible': 5,
            'amortization of intangibles': 5,
            'acquisition-related': 4,
            'acquisition related': 4,
            'restructuring': 4,
            'impairment': 3,
            'litigation': 3,
            'tax effects': 4,
            'tax effect': 4,
            'one-time': 3,
            'one time': 3,
            'non-recurring': 3,
            'non recurring': 3,
            
            # Operating metrics in reconciliations
            'operating income': 3,
            'operating loss': 3,
            'net income': 3,
            'net loss': 3,
            'gross profit': 2,
            'earnings per share': 2,
            'loss per share': 2
        }
        
        # Shape constraints for reconciliation tables
        self.min_cols = 3
        self.max_cols = 12
        self.min_rows = 5
        self.max_rows = 80
        
        # Reconciliation candidate threshold
        self.recon_threshold = 25.0
        
        # Maximum candidates to return
        self.max_candidates = 8
    
    def score_table(self, table_data: Dict[str, Any]) -> ReconScore:
        """Score a single table for reconciliation likelihood"""
        table_id = table_data.get('table_id', 'unknown')
        
        score = 0.0
        rationale = []
        
        # Extract text content for analysis
        caption = table_data.get('caption', '')
        headers = self._extract_header_text(table_data.get('headers', []))
        first_column = self._extract_first_column_text(table_data.get('rows', []))
        
        # Combine all text for keyword analysis
        all_text = f"{caption} {' '.join(headers)} {' '.join(first_column)}"
        
        # 1. Keyword scoring
        keyword_score, keyword_rationale = self._score_keywords(all_text)
        score += keyword_score
        rationale.extend(keyword_rationale)
        
        # 2. Shape scoring
        shape_score, shape_rationale = self._score_shape(table_data)
        score += shape_score
        rationale.extend(shape_rationale)
        
        # 3. Reconciliation phrase detection
        phrase_score, phrase_rationale = self._score_reconciliation_phrases(all_text)
        score += phrase_score
        rationale.extend(phrase_rationale)
        
        # 4. GAAP/Non-GAAP balance scoring
        balance_score, balance_rationale = self._score_gaap_balance(all_text)
        score += balance_score
        rationale.extend(balance_rationale)
        
        # 5. Financial line item density
        density_score, density_rationale = self._score_financial_density(first_column)
        score += density_score
        rationale.extend(density_rationale)
        
        # Determine if this is a reconciliation candidate
        is_candidate = score >= self.recon_threshold
        
        return ReconScore(
            table_id=table_id,
            recon_score=round(score, 2),
            recon_candidate=is_candidate,
            recon_rationale=rationale
        )
    
    def score_all_tables(self, tables: List[Dict[str, Any]]) -> List[ReconScore]:
        """Score all tables and return sorted by reconciliation likelihood"""
        scores = []
        
        for table in tables:
            try:
                score = self.score_table(table)
                scores.append(score)
            except Exception as e:
                # Create a failed score entry
                table_id = table.get('table_id', 'unknown')
                scores.append(ReconScore(
                    table_id=table_id,
                    recon_score=0.0,
                    recon_candidate=False,
                    recon_rationale=[f"Scoring failed: {str(e)}"]
                ))
        
        # Sort by score (highest first)
        scores.sort(key=lambda x: x.recon_score, reverse=True)
        
        return scores
    
    def get_top_candidates(self, tables: List[Dict[str, Any]]) -> List[ReconScore]:
        """Get top reconciliation candidates"""
        all_scores = self.score_all_tables(tables)
        
        # Filter candidates and limit to max count
        candidates = [s for s in all_scores if s.recon_candidate]
        return candidates[:self.max_candidates]
    
    def _extract_header_text(self, headers: List) -> List[str]:
        """Extract text from headers (handle both string and dict formats)"""
        text_headers = []
        
        for header in headers:
            if isinstance(header, str):
                text_headers.append(header)
            elif isinstance(header, dict):
                text_headers.append(header.get('original_header', ''))
            else:
                text_headers.append(str(header))
        
        return text_headers
    
    def _extract_first_column_text(self, rows: List) -> List[str]:
        """Extract text from first column of all rows"""
        first_column = []
        
        for row in rows:
            if row and len(row) > 0:
                first_cell = row[0]
                if isinstance(first_cell, dict):
                    text = first_cell.get('original_text', '')
                elif hasattr(first_cell, 'original_text'):
                    text = first_cell.original_text
                else:
                    text = str(first_cell)
                
                if text.strip():
                    first_column.append(text.strip())
        
        return first_column
    
    def _score_keywords(self, text: str) -> Tuple[float, List[str]]:
        """Score based on reconciliation keywords"""
        text_lower = text.lower()
        score = 0.0
        rationale = []
        
        for keyword, weight in self.keyword_weights.items():
            count = text_lower.count(keyword.lower())
            if count > 0:
                keyword_score = weight * count
                score += keyword_score
                rationale.append(f"Keyword '{keyword}': {count}x (score: +{keyword_score})")
        
        return score, rationale
    
    def _score_shape(self, table_data: Dict[str, Any]) -> Tuple[float, List[str]]:
        """Score based on table shape (reasonable reconciliation table size)"""
        shape = table_data.get('shape', (0, 0))
        rows, cols = shape
        
        score = 0.0
        rationale = []
        
        # Check column count
        if self.min_cols <= cols <= self.max_cols:
            score += 5.0
            rationale.append(f"Good column count: {cols} (score: +5)")
        else:
            rationale.append(f"Poor column count: {cols} (score: 0)")
        
        # Check row count
        if self.min_rows <= rows <= self.max_rows:
            score += 3.0
            rationale.append(f"Good row count: {rows} (score: +3)")
        else:
            rationale.append(f"Poor row count: {rows} (score: 0)")
        
        # Bonus for typical reconciliation dimensions
        if 5 <= rows <= 25 and 3 <= cols <= 6:
            score += 2.0
            rationale.append(f"Typical reconciliation size: {rows}x{cols} (score: +2)")
        
        return score, rationale
    
    def _score_reconciliation_phrases(self, text: str) -> Tuple[float, List[str]]:
        """Score based on specific reconciliation phrases"""
        text_lower = text.lower()
        score = 0.0
        rationale = []
        
        # High-value reconciliation phrases
        recon_phrases = [
            (r'reconciliation\s+of\s+gaap', 25),
            (r'gaap\s+to\s+non[- ]?gaap', 22),
            (r'non[- ]?gaap\s+reconciliation', 20),
            (r'reconciliation\s+of.*(?:net\s+income|operating\s+income)', 18),
            (r'adjusted.*reconciliation', 15),
            (r'reconciliation\s+table', 12)
        ]
        
        # Negative phrases that indicate full statements (not reconciliations)
        statement_phrases = [
            (r'consolidated\s+statements?\s+of\s+operations', -15),
            (r'consolidated\s+statements?\s+of\s+income', -15),
            (r'consolidated\s+statements?\s+of\s+cash\s+flows?', -15),
            (r'statements?\s+of\s+operations', -12),
            (r'statements?\s+of\s+income', -12),
            (r'income\s+statements?', -10),
            (r'cash\s+flow\s+statements?', -10)
        ]
        
        # Score positive reconciliation phrases
        for pattern, points in recon_phrases:
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                phrase_score = points * matches
                score += phrase_score
                rationale.append(f"Reconciliation phrase '{pattern}': {matches}x (score: +{phrase_score})")
        
        # Score negative statement phrases
        for pattern, points in statement_phrases:
            matches = len(re.findall(pattern, text_lower))
            if matches > 0:
                phrase_score = points * matches  # points is already negative
                score += phrase_score
                rationale.append(f"Statement phrase '{pattern}': {matches}x (score: {phrase_score})")
        
        return score, rationale
    
    def _score_gaap_balance(self, text: str) -> Tuple[float, List[str]]:
        """Score based on balance of GAAP vs Non-GAAP mentions"""
        text_lower = text.lower()
        
        gaap_count = text_lower.count('gaap')
        non_gaap_count = text_lower.count('non-gaap') + text_lower.count('non gaap')
        adjusted_count = text_lower.count('adjusted')
        
        score = 0.0
        rationale = []
        
        # Both GAAP and Non-GAAP should be present
        if gaap_count > 0 and (non_gaap_count > 0 or adjusted_count > 0):
            balance_score = min(gaap_count, non_gaap_count + adjusted_count) * 2
            score += balance_score
            rationale.append(f"GAAP/Non-GAAP balance: {gaap_count} GAAP, {non_gaap_count + adjusted_count} Non-GAAP/Adjusted (score: +{balance_score})")
        
        # Bonus for multiple GAAP mentions (indicates reconciliation flow)
        if gaap_count >= 3:
            score += 3.0
            rationale.append(f"Multiple GAAP mentions: {gaap_count} (score: +3)")
        
        return score, rationale
    
    def _score_financial_density(self, first_column: List[str]) -> Tuple[float, List[str]]:
        """Score based on density of financial line items in first column"""
        if not first_column:
            return 0.0, ["No first column data"]
        
        # Patterns that indicate reconciliation adjustments (not full statements)
        reconciliation_patterns = [
            r'(?i)stock[- ]?based\s+compensation',
            r'(?i)share[- ]?based\s+compensation',
            r'(?i)amortization\s+of\s+intangible',
            r'(?i)acquisition[- ]?related',
            r'(?i)restructuring',
            r'(?i)impairment',
            r'(?i)tax\s+effect',
            r'(?i)adjustment',
            r'(?i)one[- ]?time',
            r'(?i)non[- ]?recurring',
            r'(?i)litigation'
        ]
        
        # Patterns that indicate full financial statements (penalize these)
        statement_patterns = [
            r'(?i)^total\s+revenue$',
            r'(?i)^revenue$',
            r'(?i)^cost\s+of\s+revenue$',
            r'(?i)^gross\s+profit$',
            r'(?i)^operating\s+expenses$',
            r'(?i)^research\s+and\s+development$',
            r'(?i)^sales\s+and\s+marketing$',
            r'(?i)^general\s+and\s+administrative$',
            r'(?i)^subscription$',
            r'(?i)^services$'
        ]
        
        reconciliation_matches = 0
        statement_matches = 0
        total_items = len(first_column)
        
        for item in first_column:
            # Check for reconciliation adjustment patterns
            for pattern in reconciliation_patterns:
                if re.search(pattern, item):
                    reconciliation_matches += 1
                    break
            
            # Check for full statement patterns (penalty)
            for pattern in statement_patterns:
                if re.search(pattern, item):
                    statement_matches += 1
                    break
        
        if total_items > 0:
            recon_density = reconciliation_matches / total_items
            statement_density = statement_matches / total_items
            
            # Positive score for reconciliation items, negative for statement items
            score = (recon_density * 15) - (statement_density * 10)
            
            rationale = [f"Reconciliation items: {reconciliation_matches}/{total_items} = {recon_density:.2f} (+{recon_density * 15:.1f})"]
            if statement_matches > 0:
                rationale.append(f"Statement items: {statement_matches}/{total_items} = {statement_density:.2f} (-{statement_density * 10:.1f})")
            rationale.append(f"Net density score: {score:.1f}")
        else:
            score = 0.0
            rationale = ["No items in first column"]
        
        return score, rationale


def classify_reconciliation_tables(tables: List[Dict[str, Any]]) -> Tuple[List[ReconScore], List[Dict[str, Any]]]:
    """Classify all tables and return scores + top candidates"""
    classifier = ReconciliationClassifier()
    
    # Score all tables
    all_scores = classifier.score_all_tables(tables)
    
    # Get top candidates
    top_candidates = classifier.get_top_candidates(tables)
    
    # Extract candidate table data
    candidate_tables = []
    candidate_ids = {score.table_id for score in top_candidates}
    
    for table in tables:
        if table.get('table_id') in candidate_ids:
            candidate_tables.append(table)
    
    return all_scores, candidate_tables
