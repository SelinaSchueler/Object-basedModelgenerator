import pandas as pd
import json
import os
from datetime import datetime
from typing import List, Dict, Set, Any, Optional
from dataclasses import dataclass
from Controller.PreDataAnalyse.DateTransformer import DateTransformer
from Controller.PreDataAnalyse.FileConverter import FileConverter
from PyQt5.QtCore import pyqtSignal

@dataclass
class Metadata:
    """Strukturierte Speicherung von Metadaten"""
    creation_time: Optional[str] = None
    last_access_time: Optional[str] = None
    last_modification_time: Optional[str] = None

class PreInstanceGenerator:
    def __init__(self, debug: bool = False, log_signal: pyqtSignal = None):
        self.debug = debug
        self.log_signal = log_signal
        self.datetransformer = DateTransformer()
        self.file_converter = FileConverter(debug=debug, log_signal=log_signal)

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(f"[TERMINAL] {message}")

    def generateinstances(self, file_paths: List[str]) -> pd.DataFrame:
        """
        Generiert Dokumentinstanzen aus verschiedenen Dateiformaten.
        
        Args:
            file_paths: Liste der zu verarbeitenden Dateipfade
        
        Returns:
            DataFrame mit verarbeiteten Dokumenten
        """
        documents = []
        total_files = len(file_paths)
        
        self.debug_print(f"Verarbeite {total_files} Dokumente...")
        
        for index, file_path in enumerate(file_paths, 1):
            try:
                document = self.process_single_document(file_path)
                if document:
                    documents.append(document)
                self.debug_print(f"Fortschritt: {index}/{total_files} ({(index/total_files)*100:.1f}%)")
            except Exception as e:
                self.debug_print(f"Fehler bei Dokument {file_path}: {str(e)}")
                continue
        
        if not documents:
            self.debug_print("Warnung: Keine Dokumente konnten verarbeitet werden!")
            return pd.DataFrame()
        
        documents_df = pd.DataFrame(documents)
        self.debug_print(f"Erfolgreich verarbeitet: {len(documents_df)} Dokumente")

        # Füge die Spalten mit leeren Listen hinzu
        num_rows = len(documents_df)
        documents_df['process_assignments'] = 0
        documents_df['suspicious'] = False
        documents_df['suspicious_reason'] = None
        documents_df['process_instance_independent'] = False
        documents_df['arrays_found'] = 1
        documents_df['structure_uniform'] = None
        documents_df['structure_base_keys'] = [[] for _ in range(num_rows)]  # Leere Liste pro Zeile
        documents_df['structure_similarities'] = [[] for _ in range(num_rows)]  # Leere Liste pro Zeile
        documents_df['structure_missing_keys'] = [[] for _ in range(num_rows)]  # Leere Liste pro Zeile
        documents_df['structure_extra_keys'] = [[] for _ in range(num_rows)]  # Leere Liste pro Zeile
        documents_df['process_instances'] = [[] for _ in range(num_rows)]  # Leeres Dict pro Zeile
        documents_df['final_timestamp'] = None
        documents_df['variantID'] = 0
        documents_df['variants'] = False
        documents_df['multiple'] = False
        return documents_df

    def process_single_document(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Verarbeitet ein einzelnes Dokument mit verbesserter Fehlerbehandlung.
        """
        try:
            data = self.file_converter.convert_file(file_path)
            if not data:
                return None
            
            # Nutze die globale datetransformer Instanz
            data = self.datetransformer.find_and_parse_Date(data)
            
            # Flachen Content erstellen
            flattened_content = " ".join(str(k) for k in self.flatten_keys(data))
            
            # Metadaten und Timestamps
            metadata = self.read_metadata(file_path)
            timestamps_dict = self.datetransformer.get_content_timestamps(data)
            
            return {
                "filename": file_path,
                "title": data.get("title", ""), # Falls kein Titel vorhanden ist, leere Zeichenkette
                "content": data,
                "content_string": json.dumps(data),
                "flattened_content": flattened_content,
                "creation_time": metadata.creation_time,
                "last_access_time": metadata.last_access_time,
                "last_modification_time": metadata.last_modification_time,
                "content_timestamps": json.dumps(timestamps_dict),
                "doc_type": ""
            }
        except Exception as e:
            self.debug_print(f"Fehler bei der Verarbeitung von {file_path}: {str(e)}")
            return None

    def read_metadata(self, file_path: str) -> Metadata:
        """
        Liest Metadaten einer Datei mit verbesserter Fehlerbehandlung.
        """
        try:
            file_stats = os.stat(file_path)
            
            # Nutze die globale datetransformer Instanz
            creation_time = self.datetransformer.format_date(
                datetime.fromtimestamp(file_stats.st_ctime)
            )
            last_access_time = self.datetransformer.format_date(
                datetime.fromtimestamp(file_stats.st_atime)
            )
            last_modification_time = self.datetransformer.format_date(
                datetime.fromtimestamp(file_stats.st_mtime)
            )
            
            return Metadata(
                creation_time=creation_time,
                last_access_time=last_access_time,
                last_modification_time=last_modification_time
            )
            
        except FileNotFoundError:
            self.debug_print(f'Die Datei {file_path} wurde nicht gefunden.')
            return Metadata()
        except Exception as e:
            self.debug_print(f'Fehler beim Lesen der Metadaten der Datei {file_path}: {str(e)}')
            return Metadata()

    def flatten_keys(self, d: Dict) -> Set[str]:
        """
        Extrahiert alle Schlüssel aus verschachtelten Strukturen.
        
        Args:
            d: Zu verarbeitendes Dictionary
        """
        keys = set()

        def extract_keys(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    keys.add(str(key))
                    extract_keys(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_keys(item)

        extract_keys(d)
        return keys

# Example usage:
# generator = PreInstanceGenerator(debug=True)
# df = generator.generateinstances(["path/to/file1.json", "path/to/file2.xml", "path/to/file3.txt"])