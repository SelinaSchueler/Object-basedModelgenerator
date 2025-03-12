from collections import defaultdict
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple
from itertools import combinations, product
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
import networkx as nx

from Model.ProcessInstances.Processinstance import ProcessInstance

class RelationshipAnalyzer:
    def __init__(self, tolerance: float = 0.01):
        self.tolerance = tolerance
        
    def extract_numeric_paths(self, obj: dict, prefix: str = '') -> Dict[str, float]:
        """Extrahiert numerische Werte mit strukturierten Pfaden"""
        paths = {}
        
        def extract(curr_obj, curr_path):
            if isinstance(curr_obj, dict):
                for k, v in curr_obj.items():
                    root_path = curr_path.split('.')[0] if '.' in curr_path else curr_path
                    if isinstance(v, (int, float)):
                        path_key = f"{root_path}.{k}" if root_path else k
                        paths[path_key] = float(v)
                    elif isinstance(v, (dict, list)):
                        new_path = f"{curr_path}.{k}" if curr_path else k
                        extract(v, new_path)
            elif isinstance(curr_obj, list):
                for i, item in enumerate(curr_obj):
                    if isinstance(item, dict):
                        extract(item, f"{curr_path}[{i}]")
                    elif isinstance(item, (int, float)):
                        paths[f"{curr_path}[{i}]"] = float(item)
        
        extract(obj, prefix)
        return paths

    def create_analysis_df(self, process_instances: Dict[str, ProcessInstance]) -> pd.DataFrame:
        rows = []
        print("\nExtracting data from process instances...")
        
        for proc_id, instance in process_instances.items():
            for doc in instance.process_docs:
                content = doc['content']
                if isinstance(content, str):
                    content = json.loads(content)
                
                root_key = list(content.keys())[0]
                data = content[root_key]
                
                if isinstance(data, list):
                    for i, item in enumerate(data):
                        if isinstance(item, dict):
                            row_data = {f"{root_key}[{i}]_{k}": v 
                                    for k, v in item.items() 
                                    if isinstance(v, (int, float))}
                            row_data.update({
                                'process_id': proc_id,
                                'doc_type': doc['cluster']
                            })
                            rows.append(row_data)
        
        df = pd.DataFrame(rows)
        print(f"Created DataFrame with shape: {df.shape}")
        return df

    def analyze_process_data(self, df: pd.DataFrame) -> Dict:
        print("\nAnalyzing process data...")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col != 'process_id']
        
        process_correlations = {}
        for proc_id in df['process_id'].unique():
            proc_data = df[df['process_id'] == proc_id][numeric_cols]
            if not proc_data.empty:
                process_correlations[proc_id] = proc_data.corr()
        
        grouped_stats = df.groupby(['process_id', 'doc_type'])[numeric_cols].agg([
            'sum', 'mean', 'std'
        ]).round(2)
        
        overall_correlation = df[numeric_cols].corr()
        
        return {
            'process_correlations': process_correlations,
            'grouped_stats': grouped_stats,
            'overall_correlation': overall_correlation
        }

    def find_numeric_combinations(self, values: Dict[str, float], target: float, max_depth: int = 3) -> List[Tuple]:
        """Findet Kombinationen von Werten, die zum Zielwert führen."""
        combinations_found = []
        
        # Test sums
        for depth in range(1, max_depth + 1):
            for combo in combinations(values.items(), depth):
                keys, vals = zip(*combo)
                if abs(sum(vals) - target) < self.tolerance:
                    combinations_found.append(('sum', keys, vals))
                
                # Test products for pairs
                if depth == 2:
                    if abs(vals[0] * vals[1] - target) < self.tolerance:
                        combinations_found.append(('product', keys, vals))
        
        return combinations_found

    def analyze_complex_correlations(self, df: pd.DataFrame) -> List[Dict]:
        relations = []
        print("\nAnalyzing complex correlations...")
        
        for proc_id, group in df.groupby('process_id'):
            doc_values = defaultdict(dict)
            for _, row in group.iterrows():
                doc_type = row['doc_type']
                for col in df.select_dtypes(include=[np.number]).columns:
                    if not pd.isna(row[col]):
                        doc_values[doc_type][col] = row[col]
            
            for doc1, vals1 in doc_values.items():
                for doc2, vals2 in doc_values.items():
                    if doc1 >= doc2:
                        continue
                        
                    print(f"\nAnalyzing {doc1} -> {doc2}")
                    for target_col, target_val in vals2.items():
                        combinations = self.find_numeric_combinations(vals1, target_val)
                        for op_type, source_cols, values in combinations:
                            relations.append({
                                'process_id': proc_id,
                                'source_doc': doc1,
                                'target_doc': doc2,
                                'operation': op_type,
                                'source_fields': source_cols,
                                'target_field': target_col,
                                'source_values': values,
                                'target_value': target_val
                            })
                            print(f"Found {op_type} relation: {source_cols} -> {target_col}")
        
        return relations

    def visualize_analysis(self, results: Dict):
        plt.figure(figsize=(12, 10))
        sns.heatmap(results['overall_correlation'], annot=True, cmap='coolwarm', center=0)
        plt.title('Overall Correlations Across All Process Instances')
        plt.tight_layout()
        plt.show()

    def visualize_complex_relations(self, relations: List[Dict]):
        G = nx.DiGraph()
        
        for rel in relations:
            source = f"{rel['source_doc']}\n{rel['source_fields']}"
            target = f"{rel['target_doc']}\n{rel['target_field']}"
            G.add_edge(source, target, 
                      operation=rel['operation'],
                      values=f"{rel['source_values']} -> {rel['target_value']}")
        
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(G)
        nx.draw(G, pos, with_labels=True, node_color='lightblue', 
                node_size=2000, font_size=8, font_weight='bold')
        nx.draw_networkx_edge_labels(G, pos, 
                                    edge_labels=nx.get_edge_attributes(G, 'operation'))
        plt.title("Complex Value Relations")
        plt.show()

    def analyze_all_relationships(self, process_instances: Dict[str, ProcessInstance]):
        print("Starting comprehensive relationship analysis...")
        df = self.create_analysis_df(process_instances)
        
        # Basic correlations
        results = self.analyze_process_data(df)
        self.visualize_analysis(results)
        
        # Complex relationships
        complex_relations = self.analyze_complex_correlations(df)
        if complex_relations:
            self.visualize_complex_relations(complex_relations)
        
        return results, complex_relations