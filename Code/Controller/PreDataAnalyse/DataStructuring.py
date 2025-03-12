from collections import defaultdict
from itertools import combinations
import json
import pandas as pd
from datetime import datetime
from Model.ProcessInstances.Processinstance import ProcessInstance
from Model.ProcessInstances.BusinessKnowledge import BusinessKnowledge
from PyQt5.QtCore import pyqtSignal


class ProcessInstanceClassifier:
    def __init__(self, documents_df, debug=False, log_signal: pyqtSignal = None):
        self.documents_df = documents_df
        self.documents_df['process_assignments'] = 0
        self.documents_df['suspicious'] = False
        self.documents_df['suspicious_reason'] = None
        self.process_instances = {}
        self.debug = debug
        self.log_signal = log_signal

        self.thresholds = {
            'similarity': {'structure': 0.9}
        }
    
    def debug_print(self, message) -> None:
        if self.debug:
            message_str = str(message)
            if self.log_signal:
                self.log_signal.emit(message_str)
            else:
                print(f"[TERMINAL] {message_str}")

    def _create_process_instances(self, connected_components, document_parts):
        """Erstellt Prozessinstanzen aus den gefundenen Komponenten mit verbesserter Array-Verarbeitung"""
        for component_idx, component in enumerate(connected_components):
            try:
                process_instance = ProcessInstance(f"proc_{component_idx}")
                
               # Create instance with explicit error handling
                try:
                    process_instance = ProcessInstance(f"proc_{component_idx}")
                except TypeError as te:
                    self.debug_print(f"TypeError beim Erstellen: {str(te)}")
                    raise
                except Exception as e:
                    self.debug_print(f"Andere Exception beim Erstellen: {str(e)}")
                    raise

                # Gruppiere nach Dokumenten-IDs und behalte Array-Informationen
                doc_groups = defaultdict(list)
                for doc_key in component:
                    idx, array_path, entry_idx = doc_key
                    
                    # Debug-Informationen für Array-Strukturen
                    if array_path or entry_idx is not None:
                        self.debug_print(f"Array-Dokument gefunden: ID={idx}, Pfad={array_path}, Index={entry_idx}")
                    
                    doc_groups[idx].append((array_path, entry_idx))
                
                self.debug_print(f"\nErstelle Prozessinstanz {component_idx}")
                self.debug_print(f"Enthält {len(doc_groups)} Dokumente")
                
                # Füge Dokumente zur Prozessinstanz hinzu
                for idx, parts in doc_groups.items():
                    for array_path, entry_idx in parts:
                        try:
                            doc_ref = self._create_doc_ref(idx, array_path, entry_idx)
                            is_partial = array_path is not None and entry_idx is not None
                            
                            # Debug vor dem Hinzufügen des Dokuments
                            # self.debug_print(f"Adding document: idx={idx}, path={array_path}, entry={entry_idx}")
                            # self.debug_print(f"Document reference: {doc_ref}")
                            
                            process_instance.add_doc(doc_ref, is_partial=is_partial)
                            self.documents_df.at[idx, 'process_assignments'] += 1                   
                        
                        except Exception as e:
                            self.debug_print(f"Fehler bei Dokument {idx}: {str(e)}")
                            continue
                
                self.process_instances[f"proc_{component_idx}"] = process_instance
                
            except Exception as e:
                print(f"Fehler beim Erstellen der Prozessinstanz {component_idx}: {str(e)}")
                self.debug_print(f"Component: {component}")
                self.debug_print(f"Document parts: {document_parts}")
                import traceback
                self.debug_print(f"Stacktrace:\n{traceback.format_exc()}")
                continue

    def _create_doc_ref(self, idx, array_path=None, entry_idx=None):
        """Erstellt eine Dokumentreferenz mit verbesserter Fehlerbehandlung"""
        try:
            # Validierung der Eingaben
            if idx not in self.documents_df.index:
                raise ValueError(f"Index {idx} nicht im DataFrame")
            
            ref = {
                'doc_type': (self.documents_df, idx, 'doc_type'),
                'content': (self.documents_df, idx, 'content'),
                'creation_time': (self.documents_df, idx, 'creation_time'),
                'last_access_time': (self.documents_df, idx, 'last_access_time'),
                'last_modification_time': (self.documents_df, idx, 'last_modification_time'),
                'content_timestamps': (self.documents_df, idx, 'content_timestamps'),
                'filename': (self.documents_df, idx, 'filename')
            }
            
            if array_path is not None:
                if isinstance(array_path, str):
                    ref['array_path'] = array_path.split('.')
                else:
                    ref['array_path'] = array_path
                    
            if entry_idx is not None:
                ref['entry_index'] = entry_idx
            
            # Debug-Info
            self.debug_print(f"Created doc_ref for idx={idx}: {ref}")
            
            return ref
        except Exception as e:
            self.debug_print(f"Fehler beim Erstellen der Dokumentreferenz: {str(e)}")
            raise

    def classify_documents(self):
        """Hauptmethode mit verbesserter Referenzdokument-Behandlung"""
        try:
            self.debug_print("Starte Dokument-Klassifizierung...")
            
            # 2. Finde korrelierende Keys und deren Werte
            correlators = self.find_correlating_keys(self.documents_df)
            
            # 3. Erstelle den Dokumentengraph
            graph, document_parts, multiple_assignments = self.build_document_graph(self.documents_df, correlators)
            
            # 4. Finde Komponenten mit den erweiterten Korrelatoren
            components = self.find_connected_components(graph, correlators)
            
            # 5. Erstelle Prozessinstanzen
            self._create_process_instances(components, document_parts)
            
            # 6. Analysiere Ähnlichkeiten zwischen Instanzen
            self._analyze_instance_similarity(self.process_instances)
            
            return self.process_instances
            
        except Exception as e:
            print(f"Fehler bei der Klassifizierung: {str(e)}")
            raise

    def _find_array_values(self, content, array_paths=None):
        """Findet Werte in Array-Strukturen"""
        if array_paths is None:
            array_paths = []
            
        values = defaultdict(set)
        
        def extract_values(obj, current_path=[]):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_path = current_path + [key]
                    path_str = '.'.join(map(str, new_path))
                    
                    if isinstance(value, (dict, list)):
                        extract_values(value, new_path)
                    else:
                        values[path_str].add(value)
                        
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        extract_values(item, current_path + [i])
        
        extract_values(content)
        return values
   
    def _check_correlation(self, obj1, obj2, correlators):
        """Prüft Korrelation zwischen zwei Objekten basierend auf extrahierten Keys"""
        
        # Primäre Keys prüfen
        for key in correlators['primär']:
            val1 = self._find_value_recursive(obj1, key)
            val2 = self._find_value_recursive(obj2, key)
            if val1 and val2 and val1 == val2:
                return True

        # Sekundäre Keys prüfen
        for key in correlators['sekundär']:
            val1 = self._find_value_recursive(obj1, key)
            val2 = self._find_value_recursive(obj2, key)
            if val1 and val2 and val1 == val2:
                return True
                
        return False
    
    def find_correlating_keys(self, documents_df):
        """Korrelierende Keys identifizieren"""
        key_occurrences = defaultdict(int)
        key_values = defaultdict(lambda: defaultdict(set))
        
        # Sammle Keys und markiere Referenzdokumente
        for idx in documents_df.index:
            content = json.loads(documents_df.at[idx, 'content'])
            arrays = self._find_arrays(content)
            
            # Prüfe jedes Array auf Referenzcharakter
            for array_path, array_entries in arrays:
                if self._is_reference_array(array_entries):
                    self.documents_df.at[idx, 'suspicious'] = True 
                    self.documents_df.at[idx, 'suspicious_reason'] = f"Referenzarray gefunden: {array_path}"
                    continue
                    
                # Sammle Keys/Werte nur von Nicht-Referenz-Dokumenten 
                self._collect_keys_and_values(content, idx, key_occurrences, key_values)
        
        # Klassifiziere Keys
        correlators = {'primär': [], 'sekundär': []}
        doc_count = sum(1 for idx in documents_df.index if not documents_df.at[idx, 'suspicious'])
        
        for key, count in key_occurrences.items():
            if count < 2:  # Ignoriere einmalige Keys
                continue
                
            # Berechne Überschneidungsgrad zwischen Dokumenten
            overlap_ratio = self._calculate_value_overlap(key_values[key])
            
            if count >= doc_count * 0.5 and overlap_ratio > 0.3:
                correlators['primär'].append(key)
            elif count >= doc_count * 0.3:
                correlators['sekundär'].append(key)
                
        return correlators

    def _extract_keys_recursive(self, obj, key_occurrences, key_values, path=''):
        """Extrahiert Keys und Werte rekursiv"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                if isinstance(value, (str, int, float)) and value not in (None, "", 0):
                    key_occurrences[current_path] += 1
                    key_values[current_path].add(value)
                    
                elif isinstance(value, (dict, list)):
                    self._extract_keys_recursive(value, key_occurrences, key_values, current_path)
                    
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    self._extract_keys_recursive(item, key_occurrences, key_values, path)

    def _add_graph_edge(self, graph, idx1, idx2, path1, path2, entry1, entry2, 
                        document_parts, multiple_assignments):
        """Fügt eine Kante zum Graphen hinzu"""
        # Erstelle Node-Keys
        key1 = (idx1, path1, entry1)
        key2 = (idx2, path2, entry2)
        
        # Initialisiere Graph-Struktur
        for key in [key1, key2]:
            if key not in graph:
                graph[key] = {
                    'connections': set(),
                    'correlations': []
                }
        
        # Füge Verbindungen hinzu
        graph[key1]['connections'].add(key2)
        graph[key2]['connections'].add(key1)
        
        # Tracke Mehrfachzuordnungen
        multiple_assignments[idx1].add(idx2)
        multiple_assignments[idx2].add(idx1)
        
        # Speichere Array-Teile
        if path1 and entry1 is not None:
            document_parts[idx1].add((path1, entry1))
        if path2 and entry2 is not None:
            document_parts[idx2].add((path2, entry2))
    
    def set_threshold(self, category, name, value):
        """Erlaubt das Anpassen einzelner Schwellenwerte"""
        if category in self.thresholds and name in self.thresholds[category]:
            self.thresholds[category][name] = value
        else:
            raise ValueError(f"Ungültiger Schwellenwert: {category}.{name}")

    def _find_value_recursive(self, obj, target_key):
        """
        Sucht rekursiv nach einem Wert in verschachtelten Strukturen.
        
        Args:
            obj: Das zu durchsuchende Objekt (dict, list)
            target_key: Der gesuchte Schlüssel
            
        Returns:
            Der gefundene Wert oder None
        """
        if isinstance(obj, dict):
            # Direkter Schlüssel-Match
            if target_key in obj:
                return obj[target_key]
            
            # Normalisiere Schlüssel für Vergleich
            normalized_target = target_key.lower().replace('_', '').replace('-', '')
            
            # Prüfe auch normalisierte Schlüssel
            for key, value in obj.items():
                normalized_key = key.lower().replace('_', '').replace('-', '')
                
                # Direkter Match mit normalisiertem Schlüssel
                if normalized_key == normalized_target:
                    return value
                    
                # Rekursiv in verschachtelten Strukturen suchen
                if isinstance(value, (dict, list)):
                    result = self._find_value_recursive(value, target_key)
                    if result is not None:
                        return result
                        
        elif isinstance(obj, list):
            # Liste durchsuchen
            for item in obj:
                if isinstance(item, (dict, list)):
                    result = self._find_value_recursive(item, target_key)
                    if result is not None:
                        return result
                        
        return None

    def build_document_graph(self, documents_df, correlators):
        """Baut den Dokumentgraph mit Referenzhandling"""
        graph = {}
        document_parts = defaultdict(set)
        multiple_assignments = defaultdict(set)

        # Verarbeite erst Nicht-Referenz-Dokumente
        for idx1, idx2 in combinations(documents_df.index, 2):
            if documents_df.at[idx1, 'suspicious'] or documents_df.at[idx2, 'suspicious']:
                continue
                
            content1 = json.loads(documents_df.at[idx1, 'content'])
            content2 = json.loads(documents_df.at[idx2, 'content'])
            
            arrays1 = self._find_arrays(content1)
            arrays2 = self._find_arrays(content2)

            # Prüfe Array-Korrelationen
            for array_path1, entries1 in arrays1:
                for i1, entry1 in enumerate(entries1):
                    for array_path2, entries2 in arrays2:
                        for i2, entry2 in enumerate(entries2):
                            if self._check_correlation(entry1, entry2, correlators):
                                self._add_graph_edge(graph, idx1, idx2, array_path1, array_path2,
                                                    i1, i2, document_parts, multiple_assignments)

            # Prüfe Hauptdokument-Korrelation
            if self._check_correlation(content1, content2, correlators):
                self._add_graph_edge(graph, idx1, idx2, None, None, 
                                    None, None, document_parts, multiple_assignments)

        return graph, document_parts, multiple_assignments        

    def _check_uniform_structure(self, entries):
        """
        Prüft ob alle Einträge eine ähnliche Struktur haben (mind. 90% Übereinstimmung der Keys)
        
        Args:
            entries: Liste von Dictionary-Einträgen
            
        Returns:
            bool: True wenn Struktur ähnlich genug ist
        """
        """Prüft ob alle Einträge eine ähnliche Struktur haben"""
        if not entries or len(entries) < 2:
            return False
            
        base_keys = set(entries[0].keys())
        required_similarity = self.thresholds['similarity']['structure']
        
        for entry in entries[1:]:
            current_keys = set(entry.keys())
            intersection = len(base_keys.intersection(current_keys))
            union = len(base_keys.union(current_keys))
            similarity = intersection / union if union > 0 else 0
            
            if similarity < required_similarity:
                return False
                
        return True    
            
    def find_connected_components(self, graph, correlators):
        """Findet zusammenhängende Komponenten ohne Referenzdokumente"""
        visited = set()
        components = []
        
        def dfs(node, component):
            visited.add(node)
            idx = node[0]
            
            if not self.documents_df.at[idx, 'suspicious']:
                component.add(node)
                
                if node in graph:
                    for neighbor in graph[node]['connections']:
                        if neighbor not in visited and not self.documents_df.at[neighbor[0], 'suspicious']:
                            dfs(neighbor, component)

        # Finde Basis-Komponenten ohne Referenzdokumente
        for node in graph:
            if node not in visited and not self.documents_df.at[node[0], 'suspicious']:
                component = set()
                dfs(node, component)
                if component:
                    components.append(component)

        # Weise Referenzdokumente zu
        self._distribute_reference_docs(components, graph)
        return components

    def _are_values_consistent(self, values):
        """Überprüft, ob die Werte in einer Liste konsistent sind"""
        if not values:
            return True
        
        first_value = values[0]
        for value in values:
            if value != first_value:
                return False
        return True
    def _distribute_reference_docs(self, components, graph):
        """Verteilt Referenzdokumente auf passende Komponenten"""
        for node in graph:
            idx = node[0]
            if not self.documents_df.at[idx, 'suspicious']:
                continue

            ref_content = json.loads(self.documents_df.at[idx, 'content'])
            ref_arrays = self._find_arrays(ref_content)
            
            for array_path, entries in ref_arrays:
                for i, entry in enumerate(entries):
                    for component in components:
                        if self._entry_matches_component(entry, component):
                            component.add((idx, array_path, i))
    
    def _find_arrays(self, content, doc_idx=None):
        arrays = []
        array_values = defaultdict(set)
        
        def find_arrays_recursive(obj, path=[]):
            if isinstance(obj, dict):
                if len(obj) == 1:  # Hauptarray
                    for key, value in obj.items():
                        if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
                            if self._check_uniform_structure(value):
                                array_path = key
                                arrays.append((array_path, value))
                                
                                # Sammle distinkte Werte aus dem Array
                                for entry in value:
                                    for k,v in entry.items():
                                        if isinstance(v, (str, int, float)) and v not in (None, "", 0):
                                            array_values[k].add(v)
                                
                                # Markiere als Referenz wenn:
                                # 1. Array hat uniforme Struktur
                                # 2. Einzelne Werte tauchen in mehreren Einträgen auf
                                if doc_idx is not None:
                                    repeated_values = any(
                                        len(values) < len(value) # Werte wiederholen sich
                                        for values in array_values.values()
                                    )
                                    if repeated_values:
                                        self.documents_df.at[doc_idx, 'suspicious'] = True 
                                        self.documents_df.at[doc_idx, 'suspicious_reason'] = f"Referenzarray gefunden: {array_path}"
                
                for key, value in obj.items():
                    current_path = path + [key]
                    if isinstance(value, (dict, list)):
                        find_arrays_recursive(value, current_path)
                        
        find_arrays_recursive(content)
        return arrays
    
    def _is_reference_array(self, array_entries):
        """Erkennt Referenzarrays durch Wertwiederholungen"""
        if len(array_entries) < 2:
            return False
            
        # Extrahiere alle Werte je Key
        key_values = defaultdict(set)
        for entry in array_entries:
            for key, value in self._extract_significant_attributes(entry).items():
                if value not in (None, "", 0):
                    key_values[key].add(value)
                    
        # Referenzcharakter wenn Werte häufig wiederverwendet werden
        return any(len(values) < len(array_entries)/2 
                    for values in key_values.values() 
                    if len(values) > 1)

    def _collect_keys_and_values(self, content, doc_idx, key_occurrences, key_values):
        """Sammelt Keys und deren Werte aus einem Dokument"""
        def collect_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (str, int, float)) and value not in (None, "", 0):
                        key_occurrences[key] += 1
                        key_values[key][doc_idx].add(value)
                    elif isinstance(value, (dict, list)):
                        collect_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        collect_recursive(item)
                        
        collect_recursive(content)

    def _calculate_value_overlap(self, doc_values):
        """Berechnet Überschneidungsgrad der Werte zwischen Dokumenten"""
        overlaps = 0
        comparisons = 0
        
        docs = list(doc_values.keys())
        for i, doc1 in enumerate(docs):
            for doc2 in docs[i+1:]:
                values1 = doc_values[doc1]
                values2 = doc_values[doc2]
                
                if values1 and values2:
                    overlap = len(values1.intersection(values2)) / min(len(values1), len(values2))
                    overlaps += overlap
                    comparisons += 1
                    
        return overlaps / comparisons if comparisons else 0
    
    def _extract_significant_attributes(self, content):
        """Extrahiert wichtige Attribute aus dem Content"""
        attributes = {}
        
        def extract_recursive(obj, prefix=''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, (dict, list)):
                        extract_recursive(value, current_path)
                    else:
                        attributes[current_path] = value
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_recursive(item, f"{prefix}[{i}]")
                    
        extract_recursive(content)
        return attributes

    def _get_sorted_docs(self, proc_inst):
        """Sortiert Dokumente nach Erstellungszeit"""
        return sorted(
            proc_inst.process_docs,
            key=lambda x: pd.to_datetime(self._get_value_from_ref(x['refs']['creation_time']))
        )

    def _get_value_from_ref(self, ref):
        """Hilfsmethode zum Auslesen einer Referenz"""
        df, idx, column = ref
        return df.at[idx, column]
    
    def get_doc_content(self, doc_ref):
        """Holt den Inhalt eines Dokuments aus seiner Referenz"""
        return json.loads(self._get_value_from_ref(doc_ref['content']))

    def view_process_instances(self, detail_level='normal'):
        """
        Zeigt Prozessinstanzen mit wählbarem Detailgrad.
        
        Args:
            detail_level: 'minimal', 'normal' oder 'full'
        """
        if detail_level == 'minimal':
            self._show_minimal_info()
        elif detail_level == 'normal':
            self._print_process_instance_contents()
        else:  # 'full'
            self._print_process_instance_contents()
            #self._analyze_process_instances()

    def _show_minimal_info(self):
        """Zeigt minimale Prozessinstanz-Informationen"""
        for proc_id, instance in self.process_instances.items():
            print(f"\nProzessinstanz {proc_id}:")
            print(f"  Dokumente: {len(instance.process_docs)}")
            doc_types = set(self._get_value_from_ref(doc['refs']['doc_type']) 
                          for doc in instance.process_docs)
            print(f"  Typen: {', '.join(doc_types)}")

    def _print_process_instance_contents(self, indent=2):
        """Druckt detaillierte Prozessinstanz-Inhalte"""
        for proc_id, instance in self.process_instances.items():
            print(f"\n{'='*80}")
            print(f"Prozessinstanz: {proc_id}")
            print(f"Dokumente: {len(instance.process_docs)}")
            print('='*80)
            
            sorted_docs = self._get_sorted_docs(instance)
            for i, doc in enumerate(sorted_docs, 1):
                self._print_document_info(doc, i, indent)

    def _print_document_info(self, doc, index, indent):
        """Druckt Informationen zu einem einzelnen Dokument"""
        refs = doc['refs']
        print(f"\n--- Dokument {index} ---")
        print(f"Typ: {self._get_value_from_ref(refs['doc_type'])}")
        print(f"Datei: {self._get_value_from_ref(refs['filename'])}")
        print(f"Erstellt: {self._get_value_from_ref(refs['creation_time'])}")
        
        content = doc.get('entry_index') is not None \
            and self.get_doc_content(refs) \
            or json.loads(self._get_value_from_ref(refs['content']))
        # Content mit Array-Handling laden
        content = self.process_instances[list(self.process_instances.keys())[0]].get_document_content(refs)
     
        print("Inhalt:")
        print(json.dumps(content, indent=indent, ensure_ascii=False))
        
        # Korrekte Referenz verwenden
        df, idx, _ = refs['doc_type']
        try:
            assignments = self._get_value_from_ref((df, idx, 'process_assignments'))
            suspicious = self._get_value_from_ref((df, idx, 'suspicious'))
            suspicious_reason = self._get_value_from_ref((df, idx, 'suspicious_reason'))
            
            print(f"Zuordnungen: {assignments}")
            if suspicious:
                print(f"⚠️  Verdächtig: {suspicious_reason}")
        except Exception as e:
            print("Fehler beim Zugriff auf Dokumentinformationen")


    def _analyze_instance_similarity(self, process_instances):
        """
        Analysiert die Ähnlichkeit zwischen Prozessinstanzen basierend auf ihren Dokumenten.
        """
        similarity_groups = defaultdict(list)
        
        # Gruppiere Instanzen nach Dokumenttypen
        for inst_id, instance in process_instances.items():
            doc_signature = self._get_instance_signature(instance)
            similarity_groups[doc_signature].append(inst_id)
        
        # Identifiziere ähnliche Instanzen
        for signature, instances in similarity_groups.items():
            if len(instances) > 1:
                self.debug_print(f"Ähnliche Instanzen gefunden: {instances}")
                self._check_shared_references(instances)

    def _get_instance_signature(self, instance):
        """
        Erstellt eine Signatur für eine Prozessinstanz basierend auf ihren Dokumenttypen.
        """
        doc_types = set()
        for doc in instance.process_docs:
            doc_type = self._get_value_from_ref(doc['refs']['doc_type'])
            if doc_type:
                doc_types.add(doc_type)
        return frozenset(doc_types)

    def _check_shared_references(self, instance_ids):
        """
        Überprüft, ob Prozessinstanzen gemeinsame Referenzdokumente teilen.
        """
        shared_refs = defaultdict(set)
        
        for inst_id in instance_ids:
            instance = self.process_instances[inst_id]
            for doc in instance.process_docs:
                df, idx, _ = doc['refs']['doc_type']
                if self.documents_df.at[idx, 'suspicious']:
                    shared_refs[idx].add(inst_id)
        
        # Analysiere geteilte Referenzen
        for ref_idx, sharing_instances in shared_refs.items():
            if len(sharing_instances) > 1:
                self.debug_print(f"Referenzdokument {ref_idx} wird von Instanzen {sharing_instances} geteilt")
                self._validate_reference_sharing(ref_idx, sharing_instances)

    def _validate_reference_sharing(self, ref_idx, sharing_instances):
        """
        Validiert, ob das Teilen eines Referenzdokuments legitim ist.
        """
        try:
            content = json.loads(self.documents_df.at[ref_idx, 'content'])
            arrays = self._find_arrays(content)
            
            for array_path, entries in arrays:
                entry_assignments = defaultdict(set)
                
                # Prüfe, welche Array-Einträge zu welchen Instanzen gehören
                for entry_idx, entry in enumerate(entries):
                    for inst_id in sharing_instances:
                        instance = self.process_instances[inst_id]
                        if self._entry_belongs_to_instance(entry, instance):
                            entry_assignments[entry_idx].add(inst_id)
            
            # Analysiere die Zuordnungen
            problematic_entries = {idx: insts for idx, insts in entry_assignments.items() 
                                 if len(insts) > 1}
            
            if problematic_entries:
                self.debug_print(f"Warnung: Mehrdeutige Zuordnungen in Referenzdokument {ref_idx}:")
                for entry_idx, conflicting_instances in problematic_entries.items():
                    self.debug_print(f"  Entry {entry_idx} wird von {conflicting_instances} beansprucht")
        
        except Exception as e:
            self.debug_print(f"Fehler bei der Validierung von Referenzdokument {ref_idx}: {str(e)}")

    def _entry_belongs_to_instance(self, entry, instance):
        """
        Prüft, ob ein Array-Eintrag eines Referenzdokuments zu einer Prozessinstanz gehört.
        
        Args:
            entry: Ein Eintrag aus einem Referenzdokument (z.B. ein Kunde oder Produkt)
            instance: Eine Prozessinstanz
            
        Returns:
            bool: True wenn der Eintrag zur Instanz gehört
        """
        # Hole alle relevanten Werte aus dem Entry
        entry_values = {}
        for key, value in entry.items():
            if isinstance(value, (str, int, float)) and value not in (None, "", 0):
                entry_values[key] = value
        
        # Prüfe jedes Dokument in der Instanz
        for doc in instance.process_docs:
            try:
                # Überspringe Referenzdokumente
                df_idx = doc['refs']['doc_type'][1]
                if self.documents_df.at[df_idx, 'suspicious']:
                    continue
                    
                # Hole den Dokumentinhalt
                content = instance.get_document_content(doc['refs'])
                
                # Suche nach übereinstimmenden Werten
                for key, value in entry_values.items():
                    found_value = self._find_value_recursive(content, key)
                    if found_value == value:
                        self.debug_print(f"Match gefunden: {key}={value} in Dokument {df_idx}")
                        return True
                        
                # Prüfe auch in verschachtelten Arrays (z.B. Produkte in Bestellung)
                arrays = self._find_array_values(content)
                for array_values in arrays.values():
                    for array_value in array_values:
                        if any(str(array_value) == str(value) for value in entry_values.values()):
                            self.debug_print(f"Match in Array gefunden: {array_value} in Dokument {df_idx}")
                            return True
                            
            except Exception as e:
                self.debug_print(f"Fehler beim Prüfen von Dokument: {str(e)}")
                continue
                
        return False

#TODO Zusammenhänge von Werten analysieren, da hier noch alle Werte vorhanden, Functional Dependencies? 

#TODO Namen vereinheitlichen