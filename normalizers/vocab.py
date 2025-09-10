"""
Controlled Vocabulary and Row Grouping Module
Handles standardization of financial line item names using fuzzy matching
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class LabelMatch:
    """Result of label matching"""
    original_label: str
    label_group: Optional[str]
    label_match_reason: str
    confidence_score: float


class VocabularyNormalizer:
    """Normalize financial line item labels using controlled vocabulary"""
    
    def __init__(self):
        # Define controlled vocabulary with synonym sets
        self.vocabulary = {
            # GAAP Baselines
            'GAAP_NET_INCOME': [
                'gaap net income', 'net income gaap basis', 'gaap net earnings',
                'net income on a gaap basis', 'gaap net loss', 'net loss gaap basis',
                'net loss on a gaap basis', 'gaap net earnings loss'
            ],
            'GAAP_OPERATING_INCOME': [
                'gaap operating income', 'operating income gaap basis', 
                'gaap operating loss', 'operating loss gaap basis',
                'gaap loss from operations', 'loss from operations gaap basis',
                'gaap income from operations', 'income from operations gaap basis'
            ],
            'GAAP_GROSS_PROFIT': [
                'gaap gross profit', 'gross profit gaap basis',
                'gaap gross margin', 'gross margin gaap basis'
            ],
            'GAAP_REVENUE': [
                'gaap revenue', 'revenue gaap basis', 'gaap total revenue',
                'total revenue gaap basis'
            ],
            
            # Non-GAAP Results
            'NON_GAAP_NET_INCOME': [
                'non-gaap net income', 'adjusted net income', 'non gaap net income',
                'non-gaap net earnings', 'adjusted net earnings', 'non gaap net earnings',
                'non-gaap net loss', 'adjusted net loss', 'non gaap net loss'
            ],
            'NON_GAAP_OPERATING_INCOME': [
                'non-gaap operating income', 'adjusted operating income',
                'non gaap operating income', 'non-gaap income from operations',
                'adjusted income from operations', 'non-gaap operating loss',
                'adjusted operating loss', 'non gaap operating loss'
            ],
            'NON_GAAP_GROSS_PROFIT': [
                'non-gaap gross profit', 'adjusted gross profit', 'non gaap gross profit',
                'non-gaap gross margin', 'adjusted gross margin'
            ],
            'NON_GAAP_REVENUE': [
                'non-gaap revenue', 'adjusted revenue', 'non gaap revenue',
                'non-gaap total revenue', 'adjusted total revenue'
            ],
            
            # Common Adjustments
            'SBC': [
                'stock-based compensation', 'stock based compensation',
                'share-based compensation', 'share based compensation',
                'equity compensation', 'stock compensation expense',
                'share-based payment', 'stock option expense'
            ],
            'AMORTIZATION_INTANGIBLES': [
                'amortization of intangible assets', 'amortization of intangibles',
                'intangible asset amortization', 'intangible amortization',
                'amortization intangible assets', 'amortization - intangible assets'
            ],
            'RESTRUCTURING': [
                'restructuring charges', 'restructuring costs', 'restructuring expenses',
                'restructuring and other charges', 'restructuring activities',
                'workforce reduction costs', 'facility consolidation costs'
            ],
            'ACQ_RELATED': [
                'acquisition-related costs', 'acquisition related costs',
                'acquisition expenses', 'merger and acquisition costs',
                'transaction costs', 'deal costs', 'acquisition integration costs'
            ],
            'TAX_EFFECT': [
                'tax effects', 'tax effect of adjustments', 'income tax effects',
                'tax impact', 'tax benefit', 'tax provision adjustments'
            ],
            'OTHER_ADJUSTMENTS': [
                'other adjustments', 'other charges', 'other expenses',
                'one-time charges', 'one time charges', 'non-recurring items',
                'non recurring items', 'special items', 'unusual items'
            ],
            'IMPAIRMENT': [
                'impairment charges', 'impairment losses', 'asset impairment',
                'goodwill impairment', 'intangible impairment'
            ],
            'LITIGATION': [
                'litigation costs', 'litigation expenses', 'legal settlements',
                'legal costs', 'settlement costs'
            ]
        }
        
        # Deny-list patterns (exclude these from matching)
        self.deny_patterns = [
            r'(?i)per\s+share', r'(?i)eps', r'(?i)earnings\s+per\s+share',
            r'(?i)margin', r'(?i)%', r'(?i)percentage', r'(?i)ratio',
            r'(?i)shares\s+outstanding', r'(?i)weighted\s+average',
            r'(?i)diluted', r'(?i)basic'
        ]
        
        # Minimum similarity threshold for fuzzy matching
        self.similarity_threshold = 0.75
    
    def normalize_label(self, label: str) -> LabelMatch:
        """Normalize a single financial line item label"""
        if not label or not label.strip():
            return LabelMatch(
                original_label=label,
                label_group=None,
                label_match_reason="Empty label",
                confidence_score=0.0
            )
        
        original_label = label.strip()
        
        # Check deny-list first
        if self._is_denied_label(original_label):
            return LabelMatch(
                original_label=original_label,
                label_group=None,
                label_match_reason="Excluded by deny-list",
                confidence_score=0.0
            )
        
        # Try exact matching first
        exact_match = self._find_exact_match(original_label)
        if exact_match:
            return LabelMatch(
                original_label=original_label,
                label_group=exact_match,
                label_match_reason="Exact match",
                confidence_score=1.0
            )
        
        # Try fuzzy matching
        fuzzy_match, confidence = self._find_fuzzy_match(original_label)
        if fuzzy_match and confidence >= self.similarity_threshold:
            return LabelMatch(
                original_label=original_label,
                label_group=fuzzy_match,
                label_match_reason=f"Fuzzy match (confidence: {confidence:.2f})",
                confidence_score=confidence
            )
        
        # No match found
        return LabelMatch(
            original_label=original_label,
            label_group=None,
            label_match_reason="No match found",
            confidence_score=0.0
        )
    
    def _is_denied_label(self, label: str) -> bool:
        """Check if label matches deny-list patterns"""
        for pattern in self.deny_patterns:
            if re.search(pattern, label):
                return True
        return False
    
    def _find_exact_match(self, label: str) -> Optional[str]:
        """Find exact match in vocabulary"""
        normalized_label = self._normalize_for_matching(label)
        
        for group, synonyms in self.vocabulary.items():
            for synonym in synonyms:
                normalized_synonym = self._normalize_for_matching(synonym)
                if normalized_label == normalized_synonym:
                    return group
        
        return None
    
    def _find_fuzzy_match(self, label: str) -> Tuple[Optional[str], float]:
        """Find best fuzzy match in vocabulary"""
        normalized_label = self._normalize_for_matching(label)
        
        best_match = None
        best_score = 0.0
        
        for group, synonyms in self.vocabulary.items():
            for synonym in synonyms:
                normalized_synonym = self._normalize_for_matching(synonym)
                
                # Calculate similarity using multiple methods
                similarity = self._calculate_similarity(normalized_label, normalized_synonym)
                
                if similarity > best_score:
                    best_score = similarity
                    best_match = group
        
        return best_match, best_score
    
    def _normalize_for_matching(self, text: str) -> str:
        """Normalize text for matching (case, punctuation, etc.)"""
        # Convert to lowercase
        normalized = text.lower()
        
        # Remove common punctuation and normalize spacing
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        # Remove common filler words
        filler_words = ['the', 'of', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'with']
        words = normalized.split()
        filtered_words = [w for w in words if w not in filler_words]
        
        return ' '.join(filtered_words)
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two normalized texts"""
        # Use sequence matcher for basic similarity
        seq_similarity = SequenceMatcher(None, text1, text2).ratio()
        
        # Bonus for word overlap
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if words1 and words2:
            word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
        else:
            word_overlap = 0.0
        
        # Combine similarities with weights
        combined_similarity = (seq_similarity * 0.7) + (word_overlap * 0.3)
        
        return combined_similarity
    
    def normalize_table_labels(self, table_data: Dict) -> Dict:
        """Normalize all row labels in a table"""
        result = table_data.copy()
        
        if 'rows' in table_data:
            enhanced_rows = []
            
            for row in table_data['rows']:
                if row and len(row) > 0:
                    # Get the first cell as the label
                    first_cell = row[0]
                    if hasattr(first_cell, 'original_text'):
                        label_text = first_cell.original_text
                    elif isinstance(first_cell, dict):
                        label_text = first_cell.get('original_text', '')
                    else:
                        label_text = str(first_cell)
                    
                    # Normalize the label
                    label_match = self.normalize_label(label_text)
                    
                    # Create enhanced row with label info
                    enhanced_row = []
                    for i, cell in enumerate(row):
                        if i == 0:  # First cell gets label info
                            if isinstance(cell, dict):
                                enhanced_cell = cell.copy()
                            else:
                                enhanced_cell = {
                                    'original_text': getattr(cell, 'original_text', str(cell)),
                                    'table_id': getattr(cell, 'table_id', ''),
                                    'row_idx': getattr(cell, 'row_idx', 0),
                                    'col_idx': getattr(cell, 'col_idx', 0)
                                }
                            
                            # Add label normalization info
                            enhanced_cell.update({
                                'label_group': label_match.label_group,
                                'label_match_reason': label_match.label_match_reason,
                                'confidence_score': label_match.confidence_score
                            })
                            enhanced_row.append(enhanced_cell)
                        else:
                            enhanced_row.append(cell)
                    
                    enhanced_rows.append(enhanced_row)
                else:
                    enhanced_rows.append(row)
            
            result['rows'] = enhanced_rows
        
        return result


def get_vocabulary_stats() -> Dict[str, int]:
    """Get statistics about the controlled vocabulary"""
    normalizer = VocabularyNormalizer()
    
    stats = {
        'total_groups': len(normalizer.vocabulary),
        'total_synonyms': sum(len(synonyms) for synonyms in normalizer.vocabulary.values()),
        'deny_patterns': len(normalizer.deny_patterns)
    }
    
    # Group counts by category
    gaap_groups = [k for k in normalizer.vocabulary.keys() if k.startswith('GAAP_')]
    non_gaap_groups = [k for k in normalizer.vocabulary.keys() if k.startswith('NON_GAAP_')]
    adjustment_groups = [k for k in normalizer.vocabulary.keys() 
                        if not k.startswith('GAAP_') and not k.startswith('NON_GAAP_')]
    
    stats.update({
        'gaap_baseline_groups': len(gaap_groups),
        'non_gaap_groups': len(non_gaap_groups),
        'adjustment_groups': len(adjustment_groups)
    })
    
    return stats
