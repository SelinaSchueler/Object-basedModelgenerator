from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.preprocessing import LabelEncoder
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json
from PyQt5.QtCore import pyqtSignal

class DecisionPointAnalyzer:
    def __init__(self, debug: bool = False, log_signal: pyqtSignal = None):
        self.debug = debug
        self.log_signal = log_signal  # Add log_signal parameter
        
    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:                
                self.log_signal.emit(message)
            else:
                print(message)

    def analyze_decision_points(self, net, df: pd.DataFrame, content_based_AT: List):
        """
        Hauptmethode zur Analyse der Entscheidungspunkte
        """
        # 1. Identifiziere Entscheidungspunkte und ihre möglichen Pfade
        decision_points = self.identify_decision_points(net, content_based_AT)
        self.debug_print(f"Identifizierte Entscheidungspunkte: {decision_points.keys()}")
        
        # 2. Analysiere die tatsächlichen Prozessflüsse
        flows = self.analyze_process_flows(df, decision_points, content_based_AT)
        
        # 3. Generiere Entscheidungsregeln und bekomme die Figuren
        rules, figures = self.generate_decision_rules(df, flows, content_based_AT)
        
        return rules, figures

    def identify_decision_points(self, net, content_based_AT: List) -> Dict:
        """
        Identifiziert Entscheidungspunkte im Petrinetz und ordnet ihnen Aktivitätstypen zu
        """
        decision_points = {}
        at_map = self.create_activity_type_mapping(content_based_AT)
        
        for place in net.places:
            outgoing_arcs = [arc for arc in net.arcs if arc.source == place]
            if len(outgoing_arcs) > 1:  # Place hat mehrere ausgehende Transitionen
                outgoing_transitions = []
                for arc in outgoing_arcs:
                    trans_name = arc.target.label if arc.target.label else arc.target.name
                    related_ats = at_map.get(self.normalize_transition_name(trans_name), [])
                    outgoing_transitions.append((trans_name, related_ats))
                
                decision_points[place.name] = {
                    'transitions': outgoing_transitions,
                    'type': self.determine_split_type(outgoing_transitions)
                }
                
                self.debug_print(f"Entscheidungspunkt gefunden: {place.name}")
                for trans_name, ats in outgoing_transitions:
                    self.debug_print(f"  - Transition: {trans_name} mit {len(ats)} ATs")
        
        return decision_points

    def create_activity_type_mapping(self, content_based_AT: List) -> Dict:
        """
        Erstellt ein Mapping von normalisierten Transitionsnamen zu Aktivitätstypen
        """
        mapping = defaultdict(list)
        
        for at in content_based_AT:
            name = self.normalize_transition_name(str(at.name))
            mapping[name].append(at)
            
        return mapping

    def normalize_transition_name(self, name: str) -> str:
        """
        Normalisiert einen Transitionsnamen für konsistenten Vergleich
        """
        return str(name).lower().replace(" ", "")

    def determine_split_type(self, transitions) -> str:
        """
        Bestimmt den Typ des Splits (XOR, AND, OR)
        """
        # Für jetzt einfach XOR annehmen - könnte später erweitert werden
        return "XOR"
    
    def analyze_process_flows(self, df: pd.DataFrame, decision_points: Dict, content_based_AT: List) -> Dict:
        """
        Analysiert die tatsächlichen Prozessflüsse für jeden Entscheidungspunkt
        """
        flows = {}
        
        # Get unique process IDs from the DataFrame
        all_process_ids = set()
        for process_list in df['process_instances'].dropna():
            if isinstance(process_list, list):
                all_process_ids.update(process_list)
                
        self.debug_print(f"Found {len(all_process_ids)} unique process instances")
        
        for dp_name, dp_info in decision_points.items():
            dp_flows = defaultdict(lambda: {'instances': set(), 'count': 0})
            
            # Analyze each process instance
            for process_id in all_process_ids:
                # Check each possible transition for this decision point
                for trans_name, ats in dp_info['transitions']:
                    if self.verify_flow(process_id, dp_name, trans_name, df):
                        dp_flows[trans_name]['instances'].add(process_id)
                        dp_flows[trans_name]['count'] += 1
            
            # Calculate relative frequencies
            total_instances = sum(flow['count'] for flow in dp_flows.values())
            if total_instances > 0:
                for trans_name in dp_flows:
                    dp_flows[trans_name]['frequency'] = dp_flows[trans_name]['count'] / total_instances
            
            flows[dp_name] = dict(dp_flows)
            self.debug_print(f"Analysis for {dp_name}: {len(dp_flows)} different flows found")
            
        return flows

    def verify_flow(self, process_id, dp_name: str, transition_name: str, df: pd.DataFrame) -> bool:
        """
        Verifiziert ob eine Prozessinstanz tatsächlich einen bestimmten Fluss genommen hat
        """
        try:
            # Filter documents for this process instance
            instance_mask = df['process_instances'].apply(
                lambda x: isinstance(x, list) and process_id in x
            )
            instance_docs = df[instance_mask].copy()
            
            if instance_docs.empty:
                return False

            # Sort by timestamp
            instance_docs = instance_docs.sort_values('final_timestamp')
            
            # Get document types
            source_type = dp_name
            target_type = self.extract_target_type(transition_name)
            
            # Find relevant documents
            source_docs = instance_docs[instance_docs['doc_type'] == source_type]
            target_docs = instance_docs[instance_docs['doc_type'] == target_type]
            
            if source_docs.empty or target_docs.empty:
                return False
                
            # Check sequence
            source_time = source_docs.iloc[0]['final_timestamp']
            target_time = target_docs.iloc[0]['final_timestamp']
            
            return target_time > source_time
            
        except Exception as e:
            self.debug_print(f"Flow verification error for process {process_id}: {str(e)}")
            return False

    def extract_target_type(self, transition_name: str) -> str:
        """
        Extrahiert den Zieltyp aus einem Transitionsnamen
        """
        try:
            # Handle tuple format
            if isinstance(transition_name, tuple):
                # Take the last element that's not empty or None
                valid_elements = [x for x in transition_name if x and x != 'None']
                return valid_elements[-1] if valid_elements else ''

            # Clean string format
            transition_name = str(transition_name).strip("()' ")
            
            # Split by comma if present
            if ',' in transition_name:
                parts = [p.strip("()' ") for p in transition_name.split(',')]
                valid_parts = [p for p in parts if p and p != 'None']
                return valid_parts[-1] if valid_parts else ''
                
            return transition_name
            
        except Exception as e:
            self.debug_print(f"Error extracting target type from {transition_name}: {str(e)}")
            return ''
    def generate_decision_rules(self, df: pd.DataFrame, flows: Dict, content_based_AT: List) -> Dict:
        """
        Generates decision rules and visualizations using decision trees
        """
        rules = {}
        figures = {}
        
        for dp_name, flow_info in flows.items():
            if len(flow_info) < 2:
                continue
                
            self.debug_print(f"\nAnalyzing decision point: {dp_name}")
            
            # Prepare training data
            features_data = []
            labels = []
            
            # Collect data for each path
            path_instances = {path: info['instances'] for path, info in flow_info.items()}
            all_instances = set().union(*path_instances.values())
            
            for process_id in all_instances:
                taken_path = next(
                    (path for path, instances in path_instances.items() 
                    if process_id in instances),
                    None
                )
                
                if taken_path:
                    features = self.extract_instance_features(process_id, df, content_based_AT)
                    if features:
                        features_data.append(features)
                        labels.append(taken_path)
            
            if not features_data or len(set(labels)) < 2:
                continue
            
            # Convert to DataFrame
            feature_df = pd.DataFrame(features_data)
            
            # Remove constant columns and handle missing values
            constant_cols = [col for col in feature_df.columns if feature_df[col].nunique() <= 1]
            feature_df = feature_df.drop(columns=constant_cols)
            feature_df = feature_df.fillna(feature_df.mean())
            
            if feature_df.empty:
                continue
            
            # Normalize numerical features
            for col in feature_df.select_dtypes(include=['float64', 'int64']).columns:
                if feature_df[col].std() > 0:
                    feature_df[col] = (feature_df[col] - feature_df[col].mean()) / feature_df[col].std()
            
            # Encode categorical variables
            encoders = {}
            for col in feature_df.select_dtypes(include=['object']).columns:
                encoder = LabelEncoder()
                feature_df[col] = encoder.fit_transform(feature_df[col])
                encoders[col] = encoder
            
            # Train decision tree
            clf = DecisionTreeClassifier(
                max_depth=4,
                min_samples_leaf=5,
                class_weight='balanced',
                random_state=42
            )
            
            try:
                clf.fit(feature_df, labels)
                
                # Calculate feature importance
                importance = dict(zip(feature_df.columns, clf.feature_importances_))
                
                # Create visualization
                fig = plt.figure(figsize=(20, 10))
                plot_tree(clf, 
                        feature_names=feature_df.columns,
                        class_names=sorted(set(labels)),
                        filled=True,
                        rounded=True,
                        fontsize=10)
                        
                plt.title(f"Decision Tree for {dp_name}", fontsize=16, pad=20)
                
                # Add feature importance bar plot below the tree
                importance_fig = plt.figure(figsize=(15, 5))
                importance_ax = importance_fig.add_subplot(111)
                
                # Sort importances and plot
                sorted_imp = sorted(importance.items(), key=lambda x: x[1], reverse=True)
                imp_features, imp_values = zip(*sorted_imp)
                
                bars = importance_ax.bar(range(len(imp_features)), imp_values)
                importance_ax.set_xticks(range(len(imp_features)))
                importance_ax.set_xticklabels(imp_features, rotation=45, ha='right')
                importance_ax.set_title(f'Feature Importance for {dp_name}')
                importance_ax.set_ylabel('Importance Score')
                
                # Add value labels on top of bars
                for bar in bars:
                    height = bar.get_height()
                    importance_ax.text(bar.get_x() + bar.get_width()/2., height,
                                    f'{height:.3f}',
                                    ha='center', va='bottom')
                
                plt.tight_layout()
                
                # Store both figures
                figures[f"{dp_name}_tree"] = fig
                figures[f"{dp_name}_importance"] = importance_fig
                
                # Store rules and metadata
                rules[dp_name] = {
                    'importance': importance,
                    'classifier': clf,
                    'feature_names': list(feature_df.columns),
                    'encoders': encoders,
                    'class_distribution': pd.Series(labels).value_counts().to_dict(),
                    'sample_size': len(labels)
                }
                
                # Debug output
                self.debug_print(f"\nRules for {dp_name} (based on {len(labels)} instances):")
                self.debug_print(f"Path distribution: {rules[dp_name]['class_distribution']}")
                self.debug_print("\nFeature importance:")
                for feat, imp in sorted_imp:
                    if imp > 0.01:
                        self.debug_print(f"  {feat}: {imp:.4f}")
                
            except Exception as e:
                self.debug_print(f"Error generating rules for {dp_name}: {str(e)}")
                continue
                
        return rules, figures   
        
    def extract_instance_features(self, process_id: int, df: pd.DataFrame, content_based_AT: List) -> Dict:
        """
        Extracts meaningful features for a process instance
        """
        features = {}
        amounts = []
        prices = []
        quantities = []
        weights = []
        
        try:
            # Get documents for this process instance
            instance_mask = df['process_instances'].apply(
                lambda x: isinstance(x, list) and process_id in x
            )
            instance_docs = df[instance_mask].copy()
            
            if instance_docs.empty:
                return {}
                
            # Sort by timestamp to get sequence information
            instance_docs = instance_docs.sort_values('final_timestamp')

            def extract_numbers(obj, prefix=''):
                """Extract numerical values from nested structure"""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        key_lower = key.lower()
                        if isinstance(value, (int, float)):
                            # Categorize the value based on the key name
                            if 'preis' in key_lower or 'betrag' in key_lower:
                                prices.append(value)
                            elif 'menge' in key_lower or 'anzahl' in key_lower:
                                quantities.append(value)
                            elif 'gewicht' in key_lower:
                                weights.append(value)
                            amounts.append(value)
                        elif isinstance(value, (dict, list)):
                            extract_numbers(value, f'{prefix}{key}_')
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)):
                            extract_numbers(item, prefix)

            # Process each document's content
            for _, doc in instance_docs.iterrows():
                content = doc['content']
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                        
                extract_numbers(content)
            
            # Add statistical features
            if amounts:
                features['max_amount'] = max(amounts)
                features['min_amount'] = min(amounts)
                features['avg_amount'] = sum(amounts) / len(amounts)
                features['amount_range'] = max(amounts) - min(amounts)
            
            if prices:
                features['max_price'] = max(prices)
                features['min_price'] = min(prices)
                features['avg_price'] = sum(prices) / len(prices)
                features['total_value'] = sum(prices)
            
            if quantities:
                features['total_quantity'] = sum(quantities)
                features['max_quantity'] = max(quantities)
                features['avg_quantity'] = sum(quantities) / len(quantities)
                
            if weights:
                features['total_weight'] = sum(weights)
                features['avg_weight'] = sum(weights) / len(weights)
            
            # Temporal features
            timestamps = pd.to_datetime(instance_docs['final_timestamp'])
            if not timestamps.empty:
                first_ts = timestamps.iloc[0]
                last_ts = timestamps.iloc[-1]
                
                features['hour'] = first_ts.hour
                features['day_of_week'] = first_ts.dayofweek
                features['is_weekend'] = int(first_ts.dayofweek >= 5)
                features['process_duration'] = (last_ts - first_ts).total_seconds() / 3600
                features['morning_start'] = int(first_ts.hour < 12)
                features['evening_start'] = int(first_ts.hour >= 18)
                
            # Document features
            doc_types = instance_docs['doc_type'].unique()
            features['total_documents'] = len(instance_docs)
            features['unique_doc_types'] = len(doc_types)
            
            # Document sequence features
            doc_sequence = instance_docs['doc_type'].tolist()
            for i, doc_type in enumerate(doc_sequence[:-1]):
                next_type = doc_sequence[i + 1]
                seq_key = f'seq_{doc_type}_to_{next_type}'
                features[seq_key] = 1
            
            # Activity type features
            for at in content_based_AT:
                if hasattr(at, 'instanceList'):
                    for rule_type, instances in at.instanceList.items():
                        if process_id in instances:
                            at_name = str(at.name).replace(" ", "_").lower()
                            features[f'has_at_{at_name}'] = 1
                            
                            for rule in instances[process_id]:
                                if len(rule) >= 4:
                                    key1, key2, val1, val2 = rule[:4]
                                    if isinstance(val1, (int, float)):
                                        features[f'{at_name}_{key1}'] = val1
                                    if isinstance(val2, (int, float)):
                                        features[f'{at_name}_{key2}'] = val2
            
            # Print the extracted features for debugging
            self.debug_print(f"\nExtracted features for process {process_id}:")
            for key, value in features.items():
                self.debug_print(f"  {key}: {value}")
                
        except Exception as e:
            self.debug_print(f"Error extracting features for process {process_id}: {str(e)}")
            return {}
        
        return features

    def analyze_decision_factors(self, dp_name: str, paths: Dict, df: pd.DataFrame, content_based_AT: List) -> Dict:
        """
        Analysiert die Faktoren die zu verschiedenen Entscheidungen führen
        """
        factors = defaultdict(float)
        total_instances = len(set().union(*paths.values()))
        
        if total_instances == 0:
            return {'importance': {}}
            
        # Analysiere jeden Pfad
        for path, instances in paths.items():
            # Sammle alle relevanten Attribute für diese Instanzen
            path_attributes = self.collect_path_attributes(instances, df, content_based_AT)
            
            # Berechne die Wichtigkeit der Attribute
            for attr, value in path_attributes.items():
                # Einfache Wichtigkeitsberechnung: Häufigkeit * Distinktheit
                frequency = len(instances) / total_instances
                distinctness = len(set(value)) / len(value) if len(value) > 0 else 0
                importance = frequency * distinctness
                factors[attr] = max(factors[attr], importance)
        
        # Normalisiere die Wichtigkeiten
        max_importance = max(factors.values()) if factors else 1
        normalized_factors = {
            attr: value/max_importance 
            for attr, value in factors.items()
        }
        
        return {'importance': normalized_factors}

    def collect_path_attributes(self, instances, df: pd.DataFrame, content_based_AT: List) -> Dict:
        """
        Sammelt alle relevanten Attribute für eine Menge von Prozessinstanzen
        """
        attributes = defaultdict(list)
        
        for instance_id in instances:
            # Finde alle Dokumente dieser Instanz
            instance_docs = df[df['process_instances'].apply(lambda x: isinstance(x, list) and instance_id in x)]
            
            # Sammle Attribute aus den ATs
            for at in content_based_AT:
                if hasattr(at, 'instanceList'):
                    for rule_type, inst_rules in at.instanceList.items():
                        if instance_id in inst_rules:
                            for rule in inst_rules[instance_id]:
                                if len(rule) >= 4:  # Sicherstellen dass genug Elemente vorhanden sind
                                    key1, key2, val1, val2 = rule[:4]
                                    if isinstance(val1, (int, float)):
                                        attributes[f"{key1}"].append(val1)
                                    if isinstance(val2, (int, float)):
                                        attributes[f"{key2}"].append(val2)
        
        return attributes