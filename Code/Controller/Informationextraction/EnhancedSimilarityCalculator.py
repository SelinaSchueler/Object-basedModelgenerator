class EnhancedSimilarityCalculator:
    def __init__(self, business_knowledge):
        self.business_knowledge = business_knowledge
        self.weights = {
            'text': 0.3,
            'attributes': 0.3,
            'business_keys': 0.25,
            'temporal': 0.15
        }
    
    def calculate_similarity(self, doc1, doc2):
        """Berechnet die Gesamtähnlichkeit zwischen zwei Dokumenten"""
        similarities = {
            'text': self._calculate_text_similarity(doc1, doc2),
            'attributes': self._calculate_attribute_similarity(doc1, doc2),
            'business_keys': self._calculate_business_key_similarity(doc1, doc2),
            'temporal': self._calculate_temporal_similarity(doc1, doc2)
        }
        
        return sum(self.weights[key] * value for key, value in similarities.items())
    
    def _calculate_business_key_similarity(self, doc1, doc2):
        """Prüft Übereinstimmung der Business Keys mit Gewichtung nach Hierarchie"""
        key_weights = {
            'direkt': 1.0,
            'primär': 0.8,
            'sekundär': 0.5,
            'tertiär': 0.3
        }
        
        total_weight = 0
        matched_weight = 0
        
        for key_type, keys in self.business_knowledge.define_business_keys().items():
            weight = key_weights.get(key_type, 0.1)
            for key in keys:
                total_weight += weight
                if doc1.get(key) and doc1.get(key) == doc2.get(key):
                    matched_weight += weight
                    
        return matched_weight / total_weight if total_weight > 0 else 0
    
    def _calculate_attribute_similarity(self, doc1, doc2):
        """Verbesserte Attributähnlichkeit mit Typ-Berücksichtigung"""
        common_attrs = set(doc1.keys()) & set(doc2.keys())
        if not common_attrs:
            return 0
            
        similarity_score = 0
        for attr in common_attrs:
            val1, val2 = doc1[attr], doc2[attr]
            
            # Typspezifische Vergleiche
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numerische Ähnlichkeit
                max_val = max(abs(val1), abs(val2))
                similarity_score += 1 - (abs(val1 - val2) / max_val) if max_val > 0 else 1
            elif isinstance(val1, str) and isinstance(val2, str):
                # String-Ähnlichkeit mit Levenshtein-Distanz
                similarity_score += self._calculate_string_similarity(val1, val2)
            elif val1 == val2:
                similarity_score += 1
                
        return similarity_score / len(common_attrs)
    
    def _calculate_string_similarity(self, str1, str2):
        """Levenshtein-Distanz für String-Vergleiche"""
        if len(str1) < len(str2):
            str1, str2 = str2, str1
            
        if not str2:
            return 0
            
        previous_row = range(len(str2) + 1)
        for i, c1 in enumerate(str1):
            current_row = [i + 1]
            for j, c2 in enumerate(str2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
            
        return 1 - (previous_row[-1] / max(len(str1), len(str2)))