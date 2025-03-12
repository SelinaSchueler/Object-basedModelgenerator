from collections import defaultdict
import json
import re
from datetime import datetime
from typing import Any, Dict, Optional, Set, Tuple
import pandas as pd

#from Controller.PreDataAnalyse import DateTransformer


#Prozessinstanzen bestehen aus einer ID und den zugehörigen Daten, deren Typ auch angegeben ist
class ProcessInstance:
    def __init__(self, inst_id):
        self.inst_id = inst_id
        self.process_docs = []
        self.partial_docs = defaultdict(set)  # {doc_idx: set(array_info)}
        self.shared_docs = set()
        self.variante = None #nr der Variante
        self.variant_count = 0 #anzahl der Varianten
        self.cluster_counts = {}  # {cluster_id: count}
        self.cluster_counts_without_shared = {} # {cluster_id: count} (ohne geteilte Dokumente)

    def add_doc(self, doc_refs: Dict, is_partial: bool = False, is_shared: bool = False) -> None:
        """
        Fügt ein Dokument zur Prozessinstanz hinzu.
        
        Args:
            doc_refs: Referenzen zum Dokument
            is_partial: Flag für Teildokumente
            is_shared: Flag für geteilte Dokumente
        """
        try:            
            doc = {
                    'index_dataframe': doc_refs['index_dataframe'],
                    'cluster': doc_refs['cluster'],
                    'doc_type': doc_refs['doc_type'],
                    'content': doc_refs['content'],
                    'meta_timestamps': doc_refs['meta_timestamps'],
                    'content_timestamps': doc_refs['content_timestamps'],
                    'filename': doc_refs['filename'],
                    'final_timestamp': doc_refs['final_timestamp'],
                    'is_partial': is_partial,
                    'partial_content': doc_refs['partial_content'],
                    'is_shared': is_shared,
                    'variantID': 0,
                    'variants': False,
                    'multiple': False
            }


            self.process_docs.append(doc)
            
            # # Verarbeite Teildokumente und geteilte Dokumente
            # df, idx, _ = doc_refs['doc_type']
            # if is_partial and 'array_path' in doc_refs and 'entry_index' in doc_refs:
            #     # Konvertiere array_path zu einem String für das Set
            #     array_path_str = '.'.join(doc_refs['array_path']) if isinstance(doc_refs['array_path'], list) else doc_refs['array_path']
            #     self.partial_docs[idx].add((array_path_str, doc_refs['entry_index']))


                
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Dokuments: {str(e)}")

    def get_value_from_ref(self, ref: Tuple) -> Any:
        """Hilfsmethode zum Auslesen einer Referenz"""
        df, idx, column = ref
        return df.at[idx, column]

    def get_all_partial_docs(self) -> Dict[int, Set[Tuple[str, int]]]:
        """
        Gibt alle Teildokumente zurück.
        
        Returns:
            Dictionary mit Dokument-IDs als Schlüssel und Sets von (array_path, entry_idx) Tupeln
        """
        return dict(self.partial_docs)

    def get_array_content(self, doc_id: int, array_info: Tuple[str, int]) -> Optional[Dict]:
        """
        Holt den Inhalt eines spezifischen Array-Elements.
        
        Args:
            doc_id: ID des Dokuments
            array_info: Tupel aus (array_path, entry_idx)
            
        Returns:
            Inhalt des Array-Elements oder None bei Fehler
        """
        try:
            for doc in self.process_docs:
                df, idx, _ = doc['refs']['doc_type']
                if idx == doc_id:
                    content = json.loads(self.get_value_from_ref(doc['refs']['content']))
                    array_path, entry_idx = array_info
                    
                    # Navigation durch den Array-Pfad
                    temp_content = content
                    for key in array_path.split('.'):
                        temp_content = temp_content[key]
                    
                    return temp_content[entry_idx]
                    
        except Exception as e:
            print(f"Fehler beim Zugriff auf Array-Element: {str(e)}")
            return None

    def get_doc_statistics(self) -> Dict[str, Any]:
        """Erweiterte Statistiken über die Dokumente"""
        try:
            stats = {
                'total_docs': len(self.process_docs),
                'partial_docs': len(self.partial_docs),
                'shared_docs': len(self.shared_docs),
                'doc_types': set()
            }
            
            # Sammle Dokumenttypen
            for doc in self.process_docs:
                try:
                    doc_type = self.get_value_from_ref(doc['refs']['doc_type'])
                    stats['doc_types'].add(doc_type)
                except Exception:
                    continue
            
            # Füge Zeitstatistiken hinzu
            timestamps = [doc['final_timestamp'] for doc in self.process_docs 
                        if doc['final_timestamp'] is not None]
            if timestamps:
                stats.update({
                    'earliest_doc': min(timestamps),
                    'latest_doc': max(timestamps),
                    'date_range': (max(timestamps) - min(timestamps)).days
                })
                
            return stats
            
        except Exception as e:
            print(f"Fehler bei der Statistikberechnung: {str(e)}")
            return {}