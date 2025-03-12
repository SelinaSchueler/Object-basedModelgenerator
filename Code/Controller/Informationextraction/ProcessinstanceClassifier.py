from collections import defaultdict
from itertools import combinations
import itertools
import json
import pandas as pd
from datetime import datetime
from statistics import median
from typing import Dict, List, Set, Any, Optional, Tuple
from Model.ProcessInstances.Processinstance import ProcessInstance
from Model.ProcessInstances.BusinessKnowledge import BusinessKnowledge
from scipy.stats import chi2_contingency
import copy
from Controller.Informationextraction.ObjectRelationGenerator import RuleType
from Controller.Informationextraction.ObjecttypeGenerator.NameGenerator import NameGenerator

import networkx as nx

from Controller.PreDataAnalyse.DateTransformer import DateTransformer
from PyQt5.QtCore import pyqtSignal

#TODO: welcher schlüssein in welchem Dokument vorkommt (bisher doc, doc key key), da sortiert, kein zusammenhang zu doc
#TODO: bessere erkennung von prozessinstanzunabhängigen Dokumenten (Proplem: wo ist der Beginn --> mehrmals vorkommen = PI-unabhängig, aber wenn PI-unabhängig, dann erst mehrmas zuordnung)

class ProcessInstanceClassifier:
    """
    Classifies documents into process instances based on structural and content analysis.
    Combines graph-based document correlation with business rules and reference document handling.
    """
    
    def __init__(self, documents_df: pd.DataFrame, key_frequency = 0.8, debug: bool = False, log_signal: pyqtSignal = None):
        self.documents_df = documents_df
        self.datetransformer = DateTransformer()
        self.process_instances = {}
        self.debug = debug
        self.log_signal = log_signal
        self.thresholds = {
            'correlation': {
                'key_frequency': key_frequency,
                'primary_key_coverage': 0.5,
                'secondary_key_coverage': 0.3,
                'value_overlap': 0.3
            }
        }
        
        self.business_knowledge = BusinessKnowledge()
        self.known_keys = self.business_knowledge.define_business_keys()
        self.doc_patterns = self.business_knowledge.define_document_patterns()

    def debug_print(self, message: Any) -> None:
        if self.debug:
            message_str = str(message)
            if self.log_signal:
                self.log_signal.emit(message_str)
            else:
                print(f"[TERMINAL] {message_str}")

    def classify_documents(self) -> Dict[str, ProcessInstance]:
        """
        Main classification pipeline:
        1. Analyze document structures and identify key fields
        2. Build document correlation graph
        3. Find connected components (potential instances)
        4. Create process instances
        5. Distribute reference documents
        6. Validate against business rules
        """
        try:
            renamer = NameGenerator()
        # classifier = NormalDocumentClassifier()
        # # Pfade der Instanzen werden den einzelnen Typen zugeordnet. Liste mit Doctype als Key und Pfaden in Liste.
        # orderedPaths = classifier.clusterPaths(paths)

            ##OpenAI-Name-Generator
            #orderedPaths = renamer.rename_clusters(orderedPaths)

            ##Pathname-NameGenerator
            self.documents_df  = renamer.rename_clusters_by_path(self.documents_df)
            #self.explode_uniform_documents()
            #TODO: structure aufteilen, referenceDocs finden

            
            # 1. Analyze document structures and identify key fields
            #self.analyze_content_correlations()
            #self.analyze_frequency_per_doc_type()
            rules, doc_pairs = self.search_dependencies()

            self.debug_print("Identified rules:")
            # Direkt die einzelnen Tupel aus dem rules Dictionary ausgeben
            for rule_key, rule_tuple in rules.items():
                for rule_type, doc_types, count in rule_tuple:
                    self.debug_print(f"Rule Key: {rule_key}, Rule Type: {rule_type}, Document Types: {doc_types}, Count: {count}")

            self.debug_print("Identified doc_pairs:")
            # Direkt die einzelnen Tupel aus dem rules Dictionary ausgeben
            for docs, rule_tuple in doc_pairs.items():
                for rule_key, rule_type, value, doc_types in rule_tuple:
                    self.debug_print(f"Doc Ids: {docs}, Rule Key: {rule_key}, Rule Type: {rule_type}, value: {value}, Document Types: {doc_types}")

            correlators, correlator_synonyms, indepentend_correlators = self.define_correlators(rules, doc_pairs)
            self.debug_print("Identified correlators:")
            
            for correlator in correlators:
                self.debug_print(correlator)
            for correlator in correlator_synonyms:
                self.debug_print(correlator)

            self.debug_print("Identified independent correlators:")
            for correlator in indepentend_correlators:
                self.debug_print(correlator)

            for correlator in correlators:
                filtered_doc_pairs = defaultdict(list)
                for (doc1, doc2), rules in doc_pairs.items():
                    for rule_key, rule_type, value, doc_types in rules:
                        if (tuple(sorted(rule_key)), tuple(sorted(doc_types))) in correlators or \
                           (tuple(sorted(rule_key)), tuple(sorted(doc_types))) in correlator_synonyms or \
                           (tuple(sorted(rule_key)), tuple(sorted(doc_types))) in indepentend_correlators:
                            filtered_doc_pairs[(doc1, doc2)].append((rule_key, rule_type, value, doc_types))
            
            #self.debug_print(f"Filtered doc pairs for correlator {correlator}: {filtered_doc_pairs}")

            # 2. Build document correlation graph
            # (Placeholder for actual implementation)
            self.debug_print("Building document correlation graph...")            
            graph = self.building_document_correlation_graph(correlators, correlator_synonyms, doc_pairs)
        
            # 3. Find independent pairs
            self.debug_print("Finding independent pairs...")
            indepentend_pairs = self.get_independent_docs(indepentend_correlators, doc_pairs)

            # 3. Find connected components (potential instances)
            self.debug_print("Finding connected components...")
            connected_components = self.find_connected_components(graph, indepentend_pairs)


            # 4. Create process instances
            self.process_instances = self.create_process_instances(connected_components)
            self.debug_print("Creating process instances...")

            for key, value in self.process_instances.items():
                self.debug_print(f"Process instance: {key}, {[i['cluster'] for i in value.process_docs]} mit {[i['partial_content'] for i in value.process_docs]}")

            # 5. Distribute reference documents
            # (Placeholder for actual implementation)
            self.debug_print("Distributing reference documents...")

            # 6. Validate against business rules
            # (Placeholder for actual implementation)
            self.debug_print("Validating against business rules...")

            notused = self.documents_df[self.documents_df['process_instances'].isnull()][['filename', 'content']].to_dict('records')
            self.debug_print(notused)

            doc_pairs = self.search_dependencies_same_types(doc_pairs)

            
            return self.process_instances, doc_pairs, notused
            
        except Exception as e:
            print(f"Classification error: {str(e)}")
            raise

    def search_dependencies_same_types(self, doc_pairs):
        processed_pairs = set()
        
        # Function to compare two objects (documents) and identify potential relations based on predefined rules
        def compare_objects(obj1, obj2,  doc_type1, doc_type2, id1, id2):
            if doc_type1 != doc_type2:
                return
            # Helper function to compare two dictionaries and identify relations
            def compare_dicts(d1, d2):
                if not isinstance(d1, dict) or not isinstance(d2, dict):
                    compare_objects(d1, d2,  doc_type1, doc_type2, id1, id2)  # Recursive call for nested structures
                else:
                    for key, value in d1.items():
                        for key2, value2 in d2.items():
                            # If both values are complex types, recurse into them
                            if isinstance(value, (list, dict)) and isinstance(value2, (list, dict)):
                                compare_objects(value, value2,  doc_type1, doc_type2, id1, id2)
                            elif isinstance(value, (list, dict)):
                                compare_objects(value, d2,  doc_type1, doc_type2, id1, id2)
                            elif isinstance(value2, (list, dict)):
                                compare_objects(d1, value2,  doc_type1, doc_type2, id1, id2)
                            elif value == value2:
                                added = False    
                                rule_key = tuple(sorted((key, key2)))
                                doc_types = tuple(sorted((doc_type1, doc_type2)))
                                # Prüfen, ob das Dokumentpaar für die Regel bereits verarbeitet wurde
                                if (rule_key, RuleType.SAME_KEY_VALUE_PAIR, id1, id2) in processed_pairs:
                                    doc_pairs[(id1, id2)].append((rule_key, RuleType.SAME_KEY_VALUE_PAIR, (value,value2), doc_types))
                                    added = True
                                    return                                
                                if key == key2:
                                    rule_type = RuleType.SAME_KEY_VALUE_PAIR                                    
                                else:
                                    rule_type = RuleType.SAME_VALUE
                                    if str(value).lower() in ['true', 'false', 'none', 'yes', 'no', '1', '0', 'null']:
                                        rule_type = RuleType.SAME_COMMON_VALUE
                                    doc_pairs[(id1, id2)].append((rule_key, rule_type, (value,value2), doc_types))
                                    added = True
                                    if (rule_key, rule_type, id1, id2) in processed_pairs:
                                        return
                                # Dokumentpaar markieren
                                processed_pairs.add((rule_key, rule_type, id1, id2))
                                if not added:
                                    doc_pairs[(id1, id2)].append((rule_key, rule_type, (value,value2), doc_types))
                            elif key == key2:
                                rule_type = RuleType.SAME_KEY
                                rule_key = tuple(sorted((key, key2)))
                                doc_types = tuple(sorted((doc_type1, doc_type2)))
                                doc_pairs[(id1, id2)].append((rule_key, rule_type, (value,value2), doc_types))


            # Entry point for comparing objects, handling different types of structures (dicts or lists)
            if isinstance(obj1, dict) and isinstance(obj2, dict):
                compare_dicts(obj1, obj2)
            elif isinstance(obj1, list) and isinstance(obj2, list):
                for doc in obj1:
                    for doc2 in obj2:
                        compare_objects(doc, doc2, doc_type1, doc_type2,  id1, id2)
            elif isinstance(obj1, dict) and isinstance(obj2, list):
                for doc in obj2:
                    compare_objects(obj1, doc, doc_type1, doc_type2,  id1, id2)
            elif isinstance(obj1, list) and isinstance(obj2, dict):
                for doc in obj1:
                    compare_objects(doc, obj2,  doc_type1, doc_type2, id1, id2)

        # Dokumente paarweise vergleichen
        for (idx1, row1), (idx2, row2) in combinations(self.documents_df.iterrows(), 2):
            if row1['cluster'] != row2['cluster']:
                continue

            common_processID = []
            if isinstance(row1['process_instances'], list) and isinstance(row2['process_instances'], list):
                common_processID = list(set(row1['process_instances']) & set(row2['process_instances']))

            if not common_processID:
                continue
            try:
                content1 = json.loads(row1['content']) if isinstance(row1['content'], str) else row1['content']
                content2 = json.loads(row2['content']) if isinstance(row2['content'], str) else row2['content']
                
                compare_objects(content1, content2, row1['cluster'], row2['cluster'], 
                                idx1, idx2)  # Übergebe die Dokumentindizes
            except Exception as e:
                if self.debug:
                    print(f"Fehler beim Vergleich von {idx1} und {idx2}: {str(e)}")
                continue

        return doc_pairs

    def search_dependencies(self):
        """
        Sucht nach Abhängigkeiten zwischen Dokumenten und deren Werten.
        """
        rules = defaultdict(list)  # {rule_key: [(rule_type, doc_types, count), ...]}
        processed_pairs = set() # Speichere {rule_key: [(rule_type, doc1_index, doc2_index),...]}
        doc_pairs = defaultdict(list)  # {docID, docId: [(key, rule_type, doc_types), ...]}

        def add_or_update_rule(rule_key, rule_type, doc_types):
            """Fügt neue Regel hinzu oder aktualisiert bestehende"""
            # Suche nach existierender Regel
            for i, (existing_type, existing_docs, count) in enumerate(rules[rule_key]):
                if existing_type == rule_type and existing_docs == doc_types:
                    rules[rule_key][i] = (rule_type, doc_types, count + 1)
                    return
            # Keine existierende Regel gefunden, füge neue hinzu
            rules[rule_key].append((rule_type, doc_types, 1))


        # Function to compare two objects (documents) and identify potential relations based on predefined rules
        def compare_objects(obj1, obj2,  doc_type1, doc_type2, id1, id2):
            if doc_type1 == doc_type2:
                return
            # Helper function to compare two dictionaries and identify relations
            def compare_dicts(d1, d2):
                if not isinstance(d1, dict) or not isinstance(d2, dict):
                    compare_objects(d1, d2,  doc_type1, doc_type2, id1, id2)  # Recursive call for nested structures
                else:
                    for key, value in d1.items():
                        for key2, value2 in d2.items():
                            # If both values are complex types, recurse into them
                            if isinstance(value, (list, dict)) and isinstance(value2, (list, dict)):
                                compare_objects(value, value2,  doc_type1, doc_type2, id1, id2)
                            elif isinstance(value, (list, dict)):
                                compare_objects(value, d2,  doc_type1, doc_type2, id1, id2)
                            elif isinstance(value2, (list, dict)):
                                compare_objects(d1, value2,  doc_type1, doc_type2, id1, id2)
                            elif value == value2:
                                added = False    
                                rule_key = tuple(sorted((key, key2)))
                                doc_types = tuple(sorted((doc_type1, doc_type2)))
                                # Prüfen, ob das Dokumentpaar für die Regel bereits verarbeitet wurde
                                if (rule_key, RuleType.SAME_KEY_VALUE_PAIR, id1, id2) in processed_pairs:
                                    doc_pairs[(id1, id2)].append((rule_key, RuleType.SAME_KEY_VALUE_PAIR, (value,value2), doc_types))
                                    added = True
                                    return                                
                                if key == key2:
                                    rule_type = RuleType.SAME_KEY_VALUE_PAIR                                    
                                else:
                                    rule_type = RuleType.SAME_VALUE
                                    if str(value).lower() in ['true', 'false', 'none', 'yes', 'no', '1', '0', 'null']:
                                        rule_type = RuleType.SAME_COMMON_VALUE
                                    doc_pairs[(id1, id2)].append((rule_key, rule_type, (value,value2), doc_types))
                                    added = True
                                    if (rule_key, rule_type, id1, id2) in processed_pairs:
                                        return
                                # Dokumentpaar markieren
                                processed_pairs.add((rule_key, rule_type, id1, id2))
                                add_or_update_rule(rule_key, rule_type, doc_types)
                                if not added:
                                    doc_pairs[(id1, id2)].append((rule_key, rule_type, (value,value2), doc_types))
                            elif key == key2:
                                rule_type = RuleType.SAME_KEY
                                rule_key = tuple(sorted((key, key2)))
                                doc_types = tuple(sorted((doc_type1, doc_type2)))
                                doc_pairs[(id1, id2)].append((rule_key, rule_type, (value,value2), doc_types))


            # Entry point for comparing objects, handling different types of structures (dicts or lists)
            if isinstance(obj1, dict) and isinstance(obj2, dict):
                compare_dicts(obj1, obj2)
            elif isinstance(obj1, list) and isinstance(obj2, list):
                for doc in obj1:
                    for doc2 in obj2:
                        compare_objects(doc, doc2, doc_type1, doc_type2,  id1, id2)
            elif isinstance(obj1, dict) and isinstance(obj2, list):
                for doc in obj2:
                    compare_objects(obj1, doc, doc_type1, doc_type2,  id1, id2)
            elif isinstance(obj1, list) and isinstance(obj2, dict):
                for doc in obj1:
                    compare_objects(doc, obj2,  doc_type1, doc_type2, id1, id2)

        # Dokumente paarweise vergleichen
        for (idx1, row1), (idx2, row2) in combinations(self.documents_df.iterrows(), 2):
            try:
                content1 = json.loads(row1['content']) if isinstance(row1['content'], str) else row1['content']
                content2 = json.loads(row2['content']) if isinstance(row2['content'], str) else row2['content']
                
                compare_objects(content1, content2, row1['cluster'], row2['cluster'], 
                                idx1, idx2)  # Übergebe die Dokumentindizes
            except Exception as e:
                if self.debug:
                    print(f"Fehler beim Vergleich von {idx1} und {idx2}: {str(e)}")
                continue

        return rules, doc_pairs
    
    def define_correlators(self, rules, doc_pairs) -> List[Tuple[str, str]]:
        correlators = set()
        correlator_synonyms = set()
        independent_correlators = set()
        required_frequency = self.thresholds['correlation']['key_frequency']
        
        # Sammle alle `flattened_content`-Einträge von Dokumenten, die `structure_uniform=True` haben
        uniform_contents = " ".join(
            self.documents_df[self.documents_df['process_instance_independent']]['flattened_content'].tolist()
        )
        self.debug_print(f"Uniform contents collected: {uniform_contents}")
        
        # Neues Dictionary für die Ergebnisse
        result = defaultdict(set)
        for ids, doc_tuple in doc_pairs.items():
            for rule_key, rule_type, values, doc_types in doc_tuple:
                if rule_type == RuleType.SAME_KEY_VALUE_PAIR or rule_type == RuleType.SAME_VALUE:
                    doc_types = tuple(sorted(doc_types))
                    rule_key =  tuple(sorted(rule_key))
                    key = (doc_types, rule_key)
                    result[key].add(ids)
                
        # Ausgabe als normales Dictionary
        result_dict = {k: v for k, v in result.items()}

        # Ergebnis anzeigen
        for k, v in result_dict.items():
            self.debug_print(f"Dokumenttypen: {k[0]}, Regel-Schlüssel: {k[1]}, Anzahl - IDs: {len(v)}")
        
        # Finde transitive Beziehungen
        transitive_pairs = self.detect_transitive_correlations(correlators)
        self.debug_print(f"Transitive Pairs")
        # Ergebnis anzeigen
        for n1, n2, key1 in transitive_pairs:
            print(f"Dokumenttypen: {n1} und {n2}, Key: {key1}")
        

        good_correlator = self.compare_id_similarity(result)

        for rule_key, rule_list in rules.items():
            for rule_type, doc_types, count in rule_list:
                doc_type1_array_sum = self.documents_df[self.documents_df['cluster'] == doc_types[0]]['arrays_found'].sum()
                doc_type2_array_sum = self.documents_df[self.documents_df['cluster'] == doc_types[1]]['arrays_found'].sum()
                less_frequent_count = min(doc_type1_array_sum, doc_type2_array_sum)
                if rule_type == RuleType.SAME_KEY_VALUE_PAIR:
                    if count >= required_frequency * less_frequent_count:

                        if self.documents_df[self.documents_df['cluster'] == doc_types[0]]['process_instance_independent'].all() or \
                            self.documents_df[self.documents_df['cluster'] == doc_types[1]]['process_instance_independent'].all():
                            independent_correlators.add((tuple(sorted(rule_key)), tuple(sorted(doc_types))))
                            self.debug_print(f"Adding Independet correlator {rule_key} for doc_types {doc_types} with count {count}")
                        else: 
                            correlators.add((tuple(sorted(rule_key)), tuple(sorted(doc_types))))
                            self.debug_print(f"Adding correlator {rule_key} for doc_types {doc_types} with count {count}")

                elif rule_type == RuleType.SAME_VALUE:
                    if count >= required_frequency * less_frequent_count:
                        if self.documents_df[self.documents_df['cluster'] == doc_types[0]]['process_instance_independent'].all() or \
                            self.documents_df[self.documents_df['cluster'] == doc_types[1]]['process_instance_independent'].all():
                            independent_correlators.add((tuple(sorted(rule_key)), tuple(sorted(doc_types))))
                            self.debug_print(f"Adding Independet correlator {rule_key} for doc_types {doc_types} with count {count}")
                        else: 
                            correlator_synonyms.add((tuple(sorted(rule_key)), tuple(sorted(doc_types))))
                            self.debug_print(f"Adding synonyms correlator {rule_key} for doc_types {doc_types} with count {count}")

        # Nachträgliche Prüfung auf uniform content
        for rule_key, doc_types in list(correlators):
            if rule_key[0] in uniform_contents:
                doc_types1, doc_types2 = doc_types
                doc_type1_in_independent = False
                doc_type2_in_independent = False
                for rule_key2, (doc_type11, doc_type22) in list(independent_correlators):
                    if rule_key[0] in rule_key2:
                        if doc_types1 == doc_type11 or doc_types1 == doc_type22:
                            doc_type1_in_independent = True
                        if doc_types2 == doc_type11 or doc_types2 == doc_type22:
                            doc_type2_in_independent = True 

                if doc_type1_in_independent and doc_type2_in_independent:
                    correlators.discard((rule_key, doc_types))
                    self.debug_print(f"Removed {rule_key} from correlators due to uniform content check")

        for rule_key, doc_types in list(correlator_synonyms):
            for key in rule_key:
                if key in uniform_contents:
                    doc_types1, doc_types2 = doc_types
                    doc_type1_in_independent = False
                    doc_type2_in_independent = False
                    for rule_key2, (doc_type11, doc_type22) in list(independent_correlators):
                        if key in rule_key2:
                            if doc_types1 == doc_type11 or doc_types1 == doc_type22:
                                doc_type1_in_independent = True
                            if doc_types2 == doc_type11 or doc_types2 == doc_type22:
                                doc_type2_in_independent = True 
                    if doc_type1_in_independent and doc_type2_in_independent:
                        correlator_synonyms.discard((rule_key, doc_types))
                        self.debug_print(f"Removed {rule_key} from correlator_synonyms due to uniform content check")
                               
        for rule_key, doc_types in list(correlators):
            if not (rule_key, doc_types) in list(good_correlator):
                correlators.discard((rule_key, doc_types))
                self.debug_print(f"Removed {rule_key} from correlators due to no good correlator")

        for rule_key, doc_types in list(correlator_synonyms):
            if not (rule_key, doc_types) in list(good_correlator):
                correlator_synonyms.discard((rule_key, doc_types))
                self.debug_print(f"Removed {rule_key} from independent_correlators due to no good correlator")
        
        return correlators, correlator_synonyms, independent_correlators
    
    def compare_id_similarity(self, result):
        similarities = {}
        good_correlator = set()
        # Für jedes Paar von Korrelator-Einträgen
        for (doc_types1, rule_key1), ids1 in result.items():
            for (doc_types2, rule_key2), ids2 in result.items():
                if (doc_types1, rule_key1) >= (doc_types2, rule_key2):
                    continue
                    
                # Berechne Jaccard-Ähnlichkeit
                intersection = len(ids1.intersection(ids2))
                union = len(ids1.union(ids2))
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0.5:  # Hohe Überlappung deutet auf Korrelatoren hin
                    similarities[(doc_types1, rule_key1), (doc_types2, rule_key2)] = similarity
                    good_correlator.add((rule_key1, doc_types1)) 
                    good_correlator.add((rule_key2, doc_types2))
        
        def print_similarities():
            for (dt1, rk1), (dt2, rk2) in similarities:
                sim = similarities[((dt1, rk1), (dt2, rk2))]
                self.debug_print(f"\nDoc Types: {dt1} <-> {dt2}")
                self.debug_print(f"Rule Keys: {rk1} <-> {rk2}")  
                self.debug_print(f"Similarity: {sim:.2f}")
                ids1 = result[(dt1, rk1)]
                ids2 = result[(dt2, rk2)]
                self.debug_print(f"IDs 1: {sorted(ids1)}")
                self.debug_print(f"IDs 2: {sorted(ids2)}")
                self.debug_print(f"Shared IDs: {sorted(ids1.intersection(ids2))}")
        print_similarities()           
        return good_correlator
    
    def detect_transitive_correlations(self, correlators):
        # Graph zur Repräsentation der Korrelationsbeziehungen
        G = nx.Graph()
        
        # Füge Kanten für alle Korrelatorpaare hinzu
        for (rule_key, doc_types) in correlators:
            G.add_edge(doc_types[0], doc_types[1], key=rule_key)
        
        # Finde potentiell transitive Korrelationen
        transitive_pairs = []
        for node in G.nodes():
            # Betrachte Nachbarn und deren Nachbarn
            neighbors = list(G.neighbors(node))
            for n1, n2 in itertools.combinations(neighbors, 2):
                # Prüfe ob beide Nachbarn denselben Schlüssel zum Zentrum haben
                key1 = G[node][n1]['key'] 
                key2 = G[node][n2]['key']
                if key1 == key2:
                    # Potentiell transitive Beziehung gefunden
                    transitive_pairs.append((n1, n2, key1))
                    
        return transitive_pairs
        
        #def referenzdata

    def analyze_content_correlations(self):
        """
        Analysiert Zusammenhänge im Content.
        """
        # Assuming 'content' is a JSON string, we need to parse it first
        self.documents_df['parsed_content'] = self.documents_df['content'].apply(json.loads)

        # Perform correlation analysis on the flattened content
        # Here we use a simple example of counting word occurrences
        word_counts = self.documents_df['flattened_content'].str.split(expand=True).stack().value_counts()
        self.debug_print("Wort-Häufigkeiten im Content:")
        self.debug_print(word_counts)

    def analyze_frequency_per_doc_type(self):
        """
        Analysiert die Häufigkeit pro Doc_type.
        """
        if 'cluster' in self.documents_df.columns:
            frequency = self.documents_df['cluster'].value_counts()
            self.debug_print("Häufigkeit je Doc_type:")
            self.debug_print(frequency)
        else:
            self.debug_print("Die Spalte 'cluster' ist im DataFrame nicht vorhanden.")

    def building_document_correlation_graph(self, correlators, correlator_synonyms, doc_pairs):
        """
        Erstellt den Dokumentkorrelationsgraphen.
        """
        G = nx.Graph()

        # Add edges based on correlators and correlator_synonyms
        for (rule_key, doc_types) in correlators:
            self.debug_print(f"Adding edge for correlator: {rule_key} with doc_types: {doc_types}")
            for (doc1, doc2), rules in doc_pairs.items():
                if any((((rk, rt) == (rule_key, RuleType.SAME_KEY_VALUE_PAIR)) and (doc_types == dt)) for rk, rt, value, dt in rules):
                    G.add_edge(doc1, doc2)
                    self.debug_print(f"Added edge between {doc1} and {doc2} for correlator {rule_key}")

        for (rule_key, doc_types) in correlator_synonyms:
            self.debug_print(f"Adding edge for correlator synonym: {rule_key} with doc_types: {doc_types}")
            for (doc1, doc2), rules in doc_pairs.items():
                if any((((rk, rt) == (rule_key, RuleType.SAME_VALUE)) and (doc_types == dt)) for rk, rt, value, dt in rules):
                    G.add_edge(doc1, doc2)
                    self.debug_print(f"Added edge between {doc1} and {doc2} for correlator synonym {rule_key}")

        return G

    def get_independent_docs(self, indepentend_correlators, doc_pairs):
        ind_pairs = set()
        for (rule_key, doc_types) in indepentend_correlators:
            for (doc1, doc2), rules in doc_pairs.items():
                for rk, rt, value, dt in rules:
                    if rk == rule_key and doc_types == dt and (rt == RuleType.SAME_KEY_VALUE_PAIR or rt == RuleType.SAME_VALUE):
                        self.debug_print(f"INDEPENDENT doc1: {doc1}, doc2: {doc2}")
                        ind_pairs.add((doc1, doc2, rk[0], rk[1], value))
        return ind_pairs

    def find_connected_components(self, G: nx.Graph, ind_pairs) -> List[Set[int]]:
        """
        Findet die verbundenen Komponenten im Graphen.
        """
        connected_components = list(nx.connected_components(G))
        uniform_indices = set(self.documents_df[self.documents_df['process_instance_independent'] == True].index)

            # Adding instance-independent documents to the components
        if ind_pairs is not None:
            for component in connected_components:
                for d1, d2, rk1, rk2, value in ind_pairs:
                    if d1 in component and d1 not in uniform_indices:
                        component.add((d2, rk1, rk2, value))
                    if d2 in component and d2 not in uniform_indices:
                        component.add((d1, rk1, rk2, value))

        return connected_components
    
    def find_objects_nested(self, content, rk1, rk2, value):
        """
        Findet alle Objekte in einem Array, die einen bestimmten Key-Value Match haben.
        
        Args:
            content: JSON-Content (bereits geparst)
            rk1, rk2: Die zu suchenden Schlüssel
            value: Der gesuchte Wert (kann ein Tupel sein)
        """
        def get_nested_value(obj, key):
            """Holt verschachtelte Werte mit Punkt-Notation."""
            if not key:
                return None
            if '.' not in key:
                return obj.get(key)
                
            parts = key.split('.')
            current = obj
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            return current

        def compare_values(v1, target_value):
            """Vergleicht zwei Werte, wobei target_value ein Tupel sein kann"""
            if v1 is None:
                return False
                
            # Wenn target_value ein Tupel ist, nehmen wir den ersten Wert
            if isinstance(target_value, tuple):
                target_value = target_value[0]
                
            # Konvertiere beide zu Strings für den Vergleich
            return str(v1).strip() == str(target_value).strip()

        if not isinstance(content, dict):
            return None

        # Hole den Root-Key
        root_key = list(content.keys())[0]
        array_data = content[root_key]
        
        if self.debug:
            self.debug_print(f"Root key: {root_key}")
            self.debug_print(f"Searching for value: {value} (type: {type(value)})")
            self.debug_print(f"In keys: {rk1}, {rk2}")

        # Finde alle passenden Objekte
        matched_objects = []
        for obj in array_data:
            if self.debug:
                self.debug_print(f"Checking object: {obj}")

            value1 = get_nested_value(obj, rk1)
            value2 = get_nested_value(obj, rk2) if rk2 and rk2 != rk1 else None
            
            if self.debug:
                self.debug_print(f"Found values - value1: {value1} (type: {type(value1)}), value2: {value2} (type: {type(value2)})")

            # Vergleiche mit Typkonvertierung
            if compare_values(value1, value) or compare_values(value2, value):
                matched_objects.append(obj)
                if self.debug:
                    self.debug_print(f"Match found!")

        # Gib die Ergebnisse in der ursprünglichen Struktur zurück
        if matched_objects:
            if self.debug:
                self.debug_print(f"Returning {len(matched_objects)} matched objects")
            return {root_key: matched_objects}
            
        if self.debug:
            self.debug_print("No matches found")
        return None
    
    def create_process_instances(self, connected_components) -> Dict[str, ProcessInstance]: 
        """
        Erstellt Prozessinstanzen aus den verbundenen Komponenten.
        """
        process_instances = {}
        
        for i, component in enumerate(connected_components):
            self.debug_print(f"process component: {component}")
            process_instance = ProcessInstance(i)
            cluster_counts = defaultdict(int)  # Dictionary to count documents per cluster
            cluster_counts_without_shared = defaultdict(int)  # Dictionary to count documents per cluster without shared documents
            
            for entry in component:
                if isinstance(entry, tuple):
                    if len(entry) == 4:
                        doc_id, rk1, rk2, value = entry
                    elif len(entry) == 1:
                        doc_id = entry[0]
                        rk1 = rk2 = value = None
                    else:
                        doc_id = entry[0]
                        rk1 = rk2 = value = None

                else:
                    # Falls entry direkt doc_id ist
                    doc_id = entry
                    rk1 = rk2 = value = None

                self.debug_print(f"add doc to process instance: {doc_id}")
                is_partial = self.documents_df.at[doc_id, 'arrays_found']>1
                is_shared = self.documents_df.at[doc_id, 'process_instance_independent']

                if is_partial and (rk1 or rk2):
                    relevant_object = self.find_objects_nested(self.documents_df.at[doc_id, 'content'], rk1, rk2, value)
                    if self.debug:
                        self.debug_print(f"Found partial content: {relevant_object}")
                else:
                    relevant_object = self.documents_df.at[doc_id, 'content']
                
                # Hole die aktuelle Liste
                if 'process_instances' not in self.documents_df.at[doc_id, 'process_instances']:
                    self.documents_df.at[doc_id, 'process_instances'] = []
                self.documents_df.at[doc_id, 'process_instances'].append(i)    

                doc_ref = self._create_doc_ref(doc_id, is_partial, relevant_object)
                process_instance.add_doc(doc_ref, is_partial, is_shared)
                
                # Count documents per cluster
                cluster = self.documents_df.at[doc_id, 'cluster']
                cluster_counts[cluster] += 1
                if not is_shared:
                    cluster_counts_without_shared[cluster] += 1

            # Add cluster counts to process instance
            process_instance.cluster_counts = dict(cluster_counts)
            process_instance.cluster_counts_without_shared = dict(cluster_counts_without_shared)

            process_instances[i] = process_instance
        
        # Define variants
        self.define_variants(process_instances)
        
        # Optional: Debug-Ausgabe
        if self.debug:
            self.debug_print(f"Added {i} to process_instances at doc_id {doc_id}")

        return process_instances

    def define_variants(self, process_instances):
        variant_map = {}
        variant_counts = defaultdict(int)
        
        for pi_id, process_instance in process_instances.items():
            
            variant_key = tuple(sorted(process_instance.cluster_counts_without_shared.items()))

            if variant_key not in variant_map:
                variant_map[variant_key] = len(variant_map) + 1
            process_instance.variant = variant_map[variant_key]
            variant_counts[variant_map[variant_key]] += 1
        
        for pi_id, process_instance in process_instances.items():
            process_instance.variant_count = variant_counts[process_instance.variant]
        
        if self.debug:
            self.debug_print("Defined variants for process instances:")
            for pi_id, process_instance in process_instances.items():
                self.debug_print(f"Process Instance {pi_id}: Variant {process_instance.variant}, Variant Count {process_instance.variant_count}")

    def _create_doc_ref(self, idx, is_partial, relevant_object=None) -> Dict[str, Any]: 
        """Erstellt eine Dokumentreferenz mit verbesserter Fehlerbehandlung"""
        try:
            # Validierung der Eingaben
            if idx not in self.documents_df.index:
                raise ValueError(f"Index {idx} nicht im DataFrame")
            
            self.documents_df.at[idx, 'process_assignments'] += 1
            
            content_timestamps = json.loads(self.documents_df.at[idx, 'content_timestamps'])
            
            meta_timestamps = {
                'creation_time': (self.documents_df['creation_time']),
                'last_access_time': (self.documents_df['last_access_time']),
                'last_modification_time': (self.documents_df['last_modification_time'])
            }
            
            final_timestamp = self.calc_final_timestamp(meta_timestamps, content_timestamps)
            self.documents_df.at[idx, 'final_timestamp'] = final_timestamp

            ref = {
                    'index_dataframe': idx,
                    'doc_type': self.documents_df.at[idx, 'doc_type'],	
                    'cluster': self.documents_df.at[idx, 'cluster'],
                    'content': self.documents_df.at[idx, 'content'],
                    'meta_timestamps': meta_timestamps,
                    'content_timestamps': self.documents_df.at[idx, 'content_timestamps'],
                    'final_timestamp' : final_timestamp,
                    'filename': self.documents_df.at[idx, 'filename'],
                    'partial_content': relevant_object
            }           
            # Debug-Info
            #self.debug_print(f"Created doc_ref for idx={idx}: {ref}")
            
            return ref
        except Exception as e:
            self.debug_print(f"Fehler beim Erstellen der Dokumentreferenz: {str(e)}")
            raise

#TODO an anderer Stelle? wenn man alle PI hat?
    def calc_final_timestamp(self, meta_timestamps: Dict[str, str], 
                        content_timestamps: Dict[str, str]) -> Optional[datetime]:
        try:
            timestamps = []
            
            # Meta-Timestamps verarbeiten
            for ts in meta_timestamps.values():
                if isinstance(ts, str) and ts:  # Prüfe ob es ein nicht-leerer String ist
                    try:
                        timestamps.append(pd.to_datetime(ts, format='%d.%m.%Y %H:%M:%S', dayfirst=True))
                    except ValueError:
                        print(f"Ungültiges Datumsformat in Meta-Timestamp: {ts}")
            
            # Content-Timestamps verarbeiten
            if isinstance(content_timestamps, dict):  # Prüfe ob es ein Dictionary ist
                for ts in content_timestamps.values():
                    if isinstance(ts, str) and ts:
                        try:
                            timestamps.append(pd.to_datetime(ts, format='%d.%m.%Y %H:%M:%S', dayfirst=True))
                        except ValueError:
                            print(f"Ungültiges Datumsformat in Content-Timestamp: {ts}")
            
            # Prüfe ob die Liste nicht leer ist
            if timestamps:
                # Konvertiere Liste in pandas Series und berechne Median
                ts_series = pd.Series(timestamps)
                return ts_series.median()
            return None
                
        except Exception as e:
            print(f"Fehler bei der Zeitstempelberechnung: {str(e)}")
            return None

    def explode_uniform_documents(self):
        """
        Explode the DataFrame to include individual array entries if structure_uniform is true.
        """
        exploded_rows = []
        
        for idx, row in self.documents_df.iterrows():
            if row['process_instance_independent']:
                content = json.loads(row['content']) if isinstance(row['content'], str) else row['content']
                root_key = list(content.keys())[0]
                array_data = content[root_key]
                
                for entry in array_data:
                    new_row = row.copy()
                    new_row['content'] = json.dumps({root_key: [entry]})
                    exploded_rows.append(new_row)
            else:
                exploded_rows.append(row)
        
        self.documents_df = pd.DataFrame(exploded_rows)


