from collections import defaultdict
from enum import Enum
import json
from typing import List, Set, Tuple
import numpy as np

import pandas as pd
#from Controller.Informationextraction.ObjecttypeGenerator.NameGenerator import NameGenerator
from Model.ObjectModel.ObjectRelation import RealtationType
from Model.ObjectModel.ObjectRelation import ObjectRelation
from pm4py.objects.log.obj import EventLog, Trace, Event  # PM4Py classes for process mining and event logs
from pm4py.util.xes_constants import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY, DEFAULT_TRACEID_KEY  # Constants for event log attributes
from Controller.Informationextraction.ProcessInstanceCorrelator import RelationshipAnalyzer
import genson as gen
import networkx as nx  # NetworkX library is used for creating, manipulating, and studying complex networks of nodes and edges
from PyQt5.QtCore import pyqtSignal  # Import pyqtSignal

# Constants for event log attributes
DEFAULT_NAME_KEY = 'concept:name'
DEFAULT_TIMESTAMP_KEY = 'time:timestamp'
DEFAULT_TRACEID_KEY = 'concept:case_id'

class RuleType(Enum):
    SAME_KEY_VALUE_PAIR = "gleiche Schlüssel-Wert-Paare"
    SAME_VALUE = "gleiche Werte"
    SAME_COMMON_VALUE = "gleiche Werte,  die jedoch häufig gleich sind"
    SAME_KEY = "gleiche Schlüssel"
    SAME_COMMON_KEY = "gleiche Schlüssel, die jedoch häufig gleich sind"
    CORRELATION = "Korrelation"
    
class ObjectRelationGenerator:
    def __init__(self, debug: bool = False, same_value_threshold: float = 0.8, significant_instance_threshold: float = 0.9, same_common_value_threshold = 1, rule_significance_threshold = 0.9, log_signal: pyqtSignal = None):
        self.debug = debug
        self.same_value_threshold = same_value_threshold
        self.significant_instance_threshold = significant_instance_threshold
        self.same_common_value_threshold = same_common_value_threshold
        self.rule_significance_threshold = rule_significance_threshold
        self.log_signal = log_signal  # Add log_signal parameter

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(f"[TERMINAL] {message}")
   
    # This function takes a list of document types and an initial object model, along with process instances,
# and generates a complete object model by adding object types and relations derived from the documents.
    def generateObjectRelations(self, dataframe, processInstances, process_pairs):
        # analyzer = RelationshipAnalyzer()
        # results, complex_relations = analyzer.analyze_all_relationships(processInstances)
        # rules, cluster_map = self.correlation_to_relations(dataframe, results['overall_correlation'])

        #analyzer.visualize_analysis(results)

        mapping = dataframe.groupby('cluster')['doc_type'].agg(lambda x: x.value_counts().index[0]).to_dict()

        # print("\nRules:")
        # print("\nDetailed Rule Analysis:")
        # for rule in rules:
        #     rule_type, keys, doc_type1, doc_type2, process_ids = rule
        #     print(f"\nRule: {doc_type1} -> {doc_type2}")
            
        #     # Numerische Werte analysieren
        #     for proc_id, values in process_ids.items():
        #         print(f"\nProcess Instance {proc_id}:")
        #         for key1, key2, val1, val2 in values:
        #             print(f"  {key1}: {val1}")
        #             print(f"  {key2}: {val2}")
                    
        #             # Beziehungen prüfen
        #             if abs(val1 * val2 - val2) < 0.01:  # Multiplikation
        #                 print(f"  Found multiplication: {val1} × {val2}")
        #             elif abs(val1 + val2 - val2) < 0.01:  # Addition
        #                 print(f"  Found addition: {val1} + {val2}")
        final_content_based_objectrelations = {}
        # Initialize a list to store potential relations identified from instances
        possibleRelations_instances = {}
        # Initialize a dictionary to store potential relations identified from types
        possibleRelations_types = {}
        # Set to store unique rules identified during comparison
        rules = set()
        
        # Function to update a dictionary with a new key-value pair or append to an existing key's value
        def update_dict(d, key, value):
            if key in d:
                d[key].extend(value)  # If key exists, append the value
            else:
                d[key] = value  # If key does not exist, create a new entry
            return d
       

        # Function to find an existing relation in the list of possible relations
        def find_existing_relation(kind1, key1, id1, id2):
            for i, (kind, keys, id1rule, id2rule, processIDs) in enumerate(possibleRelations_instances):
                # Check if the current relation matches the specified criteria
                if kind1 == kind and ((id1 == id1rule and id2 == id2rule) or (id2 == id1rule and id1 == id2rule)):
                    return i  # Return the index of the matching relation
            return None  # Return None if no matching relation is found
        
        # Function to assign variants and handle multiple documents of the same type within a process instance
        def assign_variants_and_multiples(processInstances):
            for processID, processinstance in processInstances.items():
                cluster_count = defaultdict(int)
                for doc in processinstance.process_docs:
                    if not doc['is_shared'] and not doc['is_partial']:
                        cluster_count[doc['cluster']] += 1

                for cluster, count in cluster_count.items():
                    if count > 1:
                        docs_of_same_cluster = [doc for doc in processinstance.process_docs if doc['cluster'] == cluster]
                        timestamps = [doc['final_timestamp'] for doc in docs_of_same_cluster]
                        unique_timestamps = len(docs_of_same_cluster) == len(timestamps)

                        if unique_timestamps:
                            for idx, doc in enumerate(docs_of_same_cluster):
                                self.debug_print(f"Docs in different variants")
                                doc['variantID'] = idx
                                doc['variants'] = True
                                dataframe.loc[doc['index_dataframe'], 'variants'] = True
                                dataframe.loc[doc['index_dataframe'], 'variantID'] = idx

                        else:
                            for doc in docs_of_same_cluster:
                                self.debug_print(f"Multiple Docs without different variants")
                                doc['multiple'] = True
                                dataframe.loc[doc['index_dataframe'], 'multiple'] = True

        assign_variants_and_multiples(processInstances)

        # Main loop to iterate through each process instance and its documents to find relations
        for processID, processinstance in processInstances.items():
            # Iterate through each document in the process instance

            for i, doc1 in enumerate(processinstance.process_docs):
                id1 = doc1['index_dataframe']
                if 'cluster' in doc1 and 'partial_content' in doc1:
                    doc_type1 = doc1['cluster']
                    json_obj1 = doc1['partial_content']
                    timestamp1 = doc1['final_timestamp']
                    is_independent1 = doc1['is_shared']
                    variant1 = doc1['variantID']
                elif 'cluster' in doc1 and 'content' in doc1:
                    doc_type1 = doc1['cluster']
                    json_obj1 = doc1['content']
                    timestamp1 = doc1['final_timestamp']
                    is_independent1 = doc1['is_shared']
                    variant1 = doc1['variantID']
                for j, doc2 in enumerate(processinstance.process_docs):
                    id2 = doc2['index_dataframe']
                    if i >= j:  # Avoid comparing a document with itself or re-comparing pairs
                        continue
                    if 'cluster' in doc2 and 'partial_content' in doc2:
                        doc_type2 = doc2['cluster']
                        json_obj2 = doc2['partial_content']
                        timestamp2 = doc2['final_timestamp']
                        is_independent2 = doc2['is_shared']
                        variant2 = doc2['variantID']

                    elif 'cluster' in doc2 and 'content' in doc2:
                        doc_type2 = doc2['cluster']
                        json_obj2 = doc2['content']
                        timestamp2 = doc2['final_timestamp']
                        is_independent2 = doc2['is_shared']
                        variant2 = doc2['variantID']

                    else:
                        continue


                    # Compare the two documents to identify potential relations based on the rules
                    docs_key = tuple(sorted((id1, id2)))
                    calculate_input1= 0
                    if not is_independent2 and not is_independent1:
                        if doc_type1 == doc_type2:
                            if variant2 > variant1:
                                calculate_input1 = -1
                            else:
                                calculate_input1 = 1
                        else:
                            if timestamp1 < timestamp2:
                                calculate_input1 = -1
                            else:
                                calculate_input1 = 1
                    elif is_independent1 and not is_independent2:
                        calculate_input1 = -1
                    elif not is_independent1 and is_independent2:
                        calculate_input1 = 1
                    else:
                        calculate_input1 = 0
                
                    objectlist1 = (doc_type1, calculate_input1, doc1.get('variantID', 0))
                    objectlist2 = (doc_type2, 0 - calculate_input1, doc2.get('variantID', 0))
                    for key_in_pairs, ruleitem in process_pairs.items():
                        #key_in_pairs_sorted = tuple(sorted((key_in_pairs[0], key_in_pairs[0])))
                        # if doc_type1 == doc_type2 and not is_independent1:
                            # print('check: ')
                            # print(doc_type2, doc_type1, key_in_pairs, docs_key)
                        if set(key_in_pairs) == set(docs_key):
                            for rule_key, rule_type, (value1, value2), doc_types in ruleitem: #doctypes sind die Cluster
                                #self.debug_print(f"{rule_key}, {rule_type}, {value1}, {value2}, {doc_types}")
                                rules.add((rule_type, (rule_key[0], rule_key[1], value1, value2, objectlist1, objectlist2, docs_key), (doc1.get('variantID', 0), doc2.get('variantID', 0), doc_type1, doc_type2)))
                   
            # Process identified rules to update or create new relation instances
            if rules:
                for rule_type, key1, (variant1, variant2, clusterid1, clusterid2) in rules:
                    clusterid1key = (clusterid1, variant1)
                    clusteridkey = (clusterid2, variant2)
                    doc_pair = tuple(sorted((clusterid1key, clusteridkey)))
                    
                    # Initialisiere das Dictionary falls noch nicht vorhanden
                    if doc_pair not in possibleRelations_instances:
                        possibleRelations_instances[doc_pair] = {}

                    # Erstelle einen eindeutigen Schlüssel für rule_type und keys
                    rule_key = (rule_type, tuple(sorted((key1[0], key1[1]))))
                    
                    # Initialisiere das innere Dictionary falls noch nicht vorhanden
                    if rule_key not in possibleRelations_instances[doc_pair]:
                        possibleRelations_instances[doc_pair][rule_key] = {}

                    # Füge die Prozessinstanz hinzu oder aktualisiere sie
                    if processID in possibleRelations_instances[doc_pair][rule_key]:
                        possibleRelations_instances[doc_pair][rule_key][processID].append(key1)
                    else:
                        possibleRelations_instances[doc_pair][rule_key][processID] = [key1]
            rules.clear()  # Clear the rules set for the next iteration

        # Initialize an empty list to store object relations

        objectrelations = []

        # TODO Anzahl PI grenze abhängig von PI-Variant --> Mapping funktion
        # TODO wenn PI mehrmals drin mit unterschiedlichen doc IDs dann auseinandeerziehen (ggf. später zusammenführen)
        # doc ids in PI = keys mit: (rule_key[0], rule_key[1], value1, value2, objectlist1, objectlist2, docs_key)

        
        # Iterate through each possible relation instance identified earlier
        for (id1, id2), rules in list(possibleRelations_instances.items()):
            objecttyps = tuple(sorted((id1, id2)))
            objectlist = {id1: 0, id2: 0}
            processinstanceindependentid1 = dataframe[dataframe['cluster'] == id1[0]]['process_instance_independent'].iloc[0]
            processinstanceindependentid2 = dataframe[dataframe['cluster'] == id2[0]]['process_instance_independent'].iloc[0]
            # Calculate the sum of arrays_found for the respective clusters
            sum_arrays_found_id1 = dataframe[dataframe['cluster'] == id1[0]]['arrays_found'].sum()
            sum_arrays_found_id2 = dataframe[dataframe['cluster'] == id2[0]]['arrays_found'].sum()
            thresholdid1 = self.significant_instance_threshold * sum_arrays_found_id1
            thresholdid2 = self.significant_instance_threshold * sum_arrays_found_id2

            name = (mapping[id1[0]], mapping[id2[0]])
            noObjectRelation = ObjectRelation(name, name, objectlist)
            noObjectRelation_used = False
            objectRelation = ObjectRelation(name, name, objectlist)
            objectRelation_used = False

            

            for (rule_type, keys), processIDs in list(rules.items()):
                variants = []
                variant_count = 0

                for key, value in processIDs.items():
                    processInstance = processInstances[key]
                    if processInstance.variante not in variants:
                        variants.append(processInstance.variante)
                        variant_count += processInstance.variant_count

                same_value_condition = len(processIDs) > (self.same_value_threshold * variant_count)
                same_common_value_condition = len(processIDs) > (self.same_common_value_threshold * variant_count)
                key0_condition = (not processinstanceindependentid1 and len(processIDs) > thresholdid1)
                key1_condition = (not processinstanceindependentid2 and len(processIDs) > thresholdid2)

                counter = min(thresholdid1, thresholdid2) if 1 >= min(thresholdid1, thresholdid2) else max(thresholdid1, thresholdid2)
                deleted = False

                # if len(processIDs) < counter:
                #     self.debug_print(f"Rule {rule_type} with keys {keys} is not significant enough")

                #     del rules[(rule_type, keys)]
                #     deleted = True


                # Check for duplicate attributes in different rules
                keys_to_delete = []
                for (other_rule_type, other_keys), other_processIDs in rules.items():
                    if (other_rule_type, other_keys) == (rule_type, keys) and not self.same_docs(other_processIDs, processIDs):
                        for key, value in other_processIDs.items():
                            if key in processIDs:
                                if not value in processIDs[key]:
                                    processIDs[key].append(value)
                            else:
                                processIDs[key] = value
                        rules[(rule_type, keys)] = processIDs
                        #self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {name} because of {rule_type} with keys {keys}")
                        keys_to_delete.append((other_rule_type, other_keys, other_processIDs))
                        continue
                    if other_keys != keys and (keys[0] in other_keys or keys[1] in other_keys) \
                        and (rule_type == RuleType.SAME_VALUE or rule_type == RuleType.SAME_COMMON_VALUE or rule_type == RuleType.SAME_KEY_VALUE_PAIR) \
                            and (other_rule_type == RuleType.SAME_VALUE or other_rule_type == RuleType.SAME_COMMON_VALUE or other_rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                        
                        if len(processIDs)*self.same_common_value_threshold > len(rules[(other_rule_type, other_keys)]):
                            #self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {name} because of {rule_type} with keys {keys}")
                            keys_to_delete.append((other_rule_type, other_keys, other_processIDs))
                        elif len(processIDs) < len(rules[(other_rule_type, other_keys)])*self.same_common_value_threshold:
                            #self.debug_print(f"Removing less significant rule by same used attributs {rule_type} with keys {keys} for {name} because of {other_rule_type} with keys {other_keys}")
                            keys_to_delete.append((rule_type, keys, processIDs))
                            deleted = True
                            break
                        else: 
                            if (other_rule_type != RuleType.SAME_KEY_VALUE_PAIR and rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                                #self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {name} because of {rule_type} with keys {keys}")
                                keys_to_delete.append((other_rule_type, other_keys, other_processIDs))
                            elif (rule_type != RuleType.SAME_KEY_VALUE_PAIR and other_rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                                #self.debug_print(f"Removing less significant rule by same used attributs {rule_type} with keys {keys} for {name} because of {rule_type} with keys {keys}")
                                keys_to_delete.append((rule_type, keys, processIDs))
                                deleted = True
                                break
                            elif (rule_type != RuleType.SAME_VALUE and other_rule_type == RuleType.SAME_VALUE):
                                #self.debug_print(f"Removing less significant rule by same used attributs {rule_type} with keys {keys} for {name} because of {other_rule_type} with keys {other_keys}")
                                keys_to_delete.append((rule_type, keys, processIDs))
                                deleted = True
                                break
                            elif (other_rule_type != RuleType.SAME_VALUE and rule_type == RuleType.SAME_VALUE):
                                #self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {name} because of {rule_type} with keys {keys}")
                                keys_to_delete.append((other_rule_type, other_keys, other_processIDs))
                
                for (other_rule_type, other_keys), other_processIDs in rules.items():
                    if deleted:
                        break
                    if (other_rule_type, other_keys, other_processIDs) in keys_to_delete:
                        #self.debug_print(f"Skipping rule for {name} ({other_rule_type} with keys {other_keys}  and {rule_type} with keys {keys})")
                        continue
                           
                    if (rule_type == RuleType.SAME_VALUE or rule_type == RuleType.SAME_COMMON_VALUE or rule_type == RuleType.SAME_KEY_VALUE_PAIR) \
                                and (other_rule_type == RuleType.SAME_VALUE or other_rule_type == RuleType.SAME_COMMON_VALUE or other_rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                        if len(other_processIDs)*self.rule_significance_threshold > len(processIDs):
                            #self.debug_print(f"Removing less significant rule by processIDs {rule_type} with keys {keys} and PI-length {len(processIDs)} for {name} because of {other_rule_type} with keys {other_keys} and PI-length {len(other_processIDs)}")
                            keys_to_delete.append((rule_type, keys, processIDs))
                            deleted = True
                            break
                        elif len(other_processIDs) < len(processIDs)*self.rule_significance_threshold:
                            #self.debug_print(f"Removing less significant rule by processIDs {other_rule_type} with keys {other_keys} and PI-length {len(other_processIDs)} for {name} because of {rule_type} with keys {keys} and PI-length {len(processIDs)}")
                            keys_to_delete.append((other_rule_type, other_keys, other_processIDs))
                    
                # Delete collected keys
                for del_rule_type, del_keys, del_processIDs in keys_to_delete:
                    noObjectRelation.add_rule((del_rule_type, del_keys))
                    noObjectRelation.add_processinstance((del_rule_type, del_keys), del_processIDs)
                    noObjectRelation_used = True
                    if (del_rule_type, del_keys) in rules:
                        del rules[(del_rule_type, del_keys)]
                        self.debug_print(f"Removing less significant rule by processIDs or by same used attributs{del_rule_type} with keys {del_keys} for {name}")
                
                if deleted:
                    continue

                # Create an ObjectRelation instance with the identified information
                # Handle relations based on the rule type
                if rule_type == RuleType.SAME_KEY:
                    noObjectRelation.add_rule((rule_type, keys))
                    noObjectRelation.add_processinstance((rule_type, keys), processIDs)
                    noObjectRelation_used = True
                elif rule_type == RuleType.SAME_VALUE:
                    if same_value_condition or key0_condition or key1_condition:
                        objectRelation.add_rule((rule_type, keys))
                        objectRelation.add_processinstance((rule_type, keys), processIDs)
                        objectRelation_used = True
                    else:
                        noObjectRelation.add_rule((rule_type, keys))
                        noObjectRelation.add_processinstance((rule_type, keys), processIDs)
                        noObjectRelation_used = True
                    # Add the relation to the model based on the evaluation
                elif rule_type == RuleType.SAME_COMMON_VALUE:
                    if same_common_value_condition or key0_condition or key1_condition:
                        objectRelation.add_rule((rule_type, keys))
                        objectRelation.add_processinstance((rule_type, keys), processIDs)
                        objectRelation_used = True
                    else:
                        noObjectRelation.add_rule((rule_type, keys))
                        noObjectRelation.add_processinstance((rule_type, keys), processIDs)
                        noObjectRelation_used = True
                    # Add the relation to the model based on the evaluation      
                elif same_value_condition or key0_condition or key1_condition:
                    # If the relation is significant across a majority of process instances, add it to the model
                    objectRelation.add_rule((rule_type, keys))
                    objectRelation.add_processinstance((rule_type, keys), processIDs)
                    objectRelation_used = True

                else:
                    # For all other cases, add the relation as a NoneObjectRelation
                    noObjectRelation.add_rule((rule_type, keys))
                    noObjectRelation.add_processinstance((rule_type, keys), processIDs)
                    noObjectRelation_used = True
                
            if noObjectRelation_used:
                final_content_based_objectrelations = update_dict(final_content_based_objectrelations, objecttyps, [(RealtationType.NO_RELATION, noObjectRelation)])

            if objectRelation_used:
                objectrelations.append(objectRelation)
      
        for i, relation in enumerate(objectrelations):
            objecttypes =  tuple(sorted(relation.objects.keys()))
            final_content_based_objectrelations = update_dict(final_content_based_objectrelations, objecttypes, [(RealtationType.CONTENT_BASED_RELATION, relation)])


        final_time_based_objectrelations = self.generate_final_time_based_objectrelations(dataframe)

        self.debug_print("Content-based ObjectRelationships.....:")
        for key, objectrelation in final_content_based_objectrelations.items():
            for relation in objectrelation:
                if relation[0] == RealtationType.CONTENT_BASED_RELATION:
                    self.debug_print(f"Name: {relation[1].name}")
                    self.debug_print(f"Objekte: {relation[1].objects}")
                    self.debug_print(f"Regeln: {relation[1].rules}")
                    self.debug_print(f"Prozessinstanzen: {relation[1].processinstances}")
        # self.debug_print("NO Content-based ObjectRelationships.....:")
        # for key, objectrelation in final_content_based_objectrelations.items():
        #     for relation in objectrelation:
        #         if relation[0] == RealtationType.NO_RELATION:
        #             self.debug_print(f"Name: {relation[1].name}")
        #             self.debug_print(f"Objekte: {relation[1].objects}")
        #             self.debug_print(f"Regeln: {relation[1].rules}")
        #             self.debug_print(f"Prozessinstanzen: {relation[1].processinstances}")
        # Return the updated object model
        self.debug_print("Time-based ObjectRelationships.....:")
        for key, relation in final_time_based_objectrelations.items():
            if relation[0] == RealtationType.TIME_BASED_RELATION:
                self.debug_print(f"Name: {relation[1].name}")
                self.debug_print(f"Objekte: {relation[1].objects}")
                self.debug_print(f"Prozessinstanzen: {relation[1].processinstances}")
        return final_content_based_objectrelations, final_time_based_objectrelations
    
    def same_docs(self, other_processIds, processIds) -> bool:
        used_docs_id1 = set()
        used_docs_id2 = set()

        # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
        for pi, value in other_processIds.items():
            self.debug_print(f"ProcessIDs: {value}")
            for (_, _, _, _, _, _, (docid1, docid2)) in value:
                if not docid1 in used_docs_id1:
                    used_docs_id1.add(docid1)
                if not docid2 in used_docs_id1:
                    used_docs_id1.add(docid2)
        for pi2, value2 in processIds.items():
            for (_, _, _, _, _, _, (docid21, docid22)) in value2:
                if not docid21 in used_docs_id2:
                    used_docs_id2.add(docid21)  # Add obj1 ID
                if not docid22 in used_docs_id2:
                    used_docs_id2.add(docid22)  # Add obj1 ID

        # wenn die docids zu 80 % übereinstimmen, dann sollte eine Regel gelöscht werden, sonst nicht
        overlap_count = len(used_docs_id1 & used_docs_id2)
        total_count = len(used_docs_id1 | used_docs_id2)
        if total_count > 0:
            if(overlap_count / total_count) >= 0.8:
                return True
        
        return False



    def generate_final_time_based_objectrelations(self, df: pd.DataFrame) -> dict:
        final_time_based_objectrelations = {}        
        df['case_ids'] = df['process_instances'].apply(lambda x: x if isinstance(x, list) else [])
        df_exploded = df.explode('case_ids')  

        for case_id, case_docs in df_exploded.groupby('case_ids'):
            activities = case_docs[
                ~case_docs['process_instance_independent'] & 
                case_docs['final_timestamp'].notna()
            ]
                        
            activities_sorted = activities.sort_values('final_timestamp')
            activities_list = list(activities_sorted.iterrows())

            for i in range(len(activities_list) - 1):
                objecttyps = (activities_list[i][1]['cluster'], activities_list[i + 1][1]['cluster'])
                name = (activities_list[i][1]['doc_type'], activities_list[i + 1][1]['doc_type'])
                objectlist = {(activities_list[i][1]['cluster'], activities_list[i][1]['variantID']) : -1, (activities_list[i + 1][1]['cluster'], activities_list[i+1][1]['variantID']) :+1}
                instancelist = (case_id, (activities_list[i][1]['cluster'], activities_list[i][1]['variantID']), (activities_list[i + 1][1]['cluster'], activities_list[i+1][1]['variantID']))
                if objecttyps in final_time_based_objectrelations.keys():
                    relationtype, objectRelation = final_time_based_objectrelations[(objecttyps)]                
                    objectRelation.add_object(objectlist)                                                                 
                    objectRelation.add_processinstance_timebased(instancelist)
                    final_time_based_objectrelations[(objecttyps)] = (RealtationType.TIME_BASED_RELATION, objectRelation)
                    self.debug_print(f"Add objectrelationshiptype from {activities_list[i][1]['doc_type']} to {activities_list[i + 1][1]['doc_type']}")

                else:
                    objectRelation = ObjectRelation(name, name, objectlist, None)
                    objectRelation.add_processinstance_timebased(instancelist)
                    final_time_based_objectrelations[(objecttyps)] = (RealtationType.TIME_BASED_RELATION, objectRelation)
                    self.debug_print(f"Creating objectrelationshiptype from {activities_list[i][1]['doc_type']} to {activities_list[i + 1][1]['doc_type']}")                

        return final_time_based_objectrelations
    
    # Function to calculate the weight of a relation
    def calculate_relation_weight(self, relations, attribute_weights):
        weight = 0
        # Iterate through each relation
        for key in relations:
            # Sum the weights of the attributes involved in the relation
            # Default weight is 1 if the attribute is not explicitly weighted
            weight += attribute_weights.get(key[0], 1) + attribute_weights.get(key[1], 1)
        return weight

    # Function to derive the minimal set of overlapping relations
    def derive_minimal_relations(self, object_relations, attribute_weights):
        object_types = {}

        # Create a list with all passed attributes to ensure their inclusion later
        for (obj1, obj2), relations in object_relations.items():
            for (attr1, attr2) in relations:
                # Ensure each object type has a set of its attributes
                object_types.setdefault(obj1, set()).add(attr1)
                object_types.setdefault(obj2, set()).add(attr2)

        # Create a directed graph
        G = nx.DiGraph()
        # Add nodes for each object type
        G.add_nodes_from(object_types.keys())
        
        # Add nodes and weighted edges to the graph
        for (obj1, obj2), relations in object_relations.items():
            weight = self.calculate_relation_weight(relations, attribute_weights)
            # Add an edge with the calculated weight and the relations it represents
            G.add_edge(obj1, obj2, weight=weight, relations=relations)
        
        # Initialize the minimal relations graph
        minimal_relations = nx.Graph()
        minimal_relations.add_nodes_from(G.nodes)
        
        # Function to check if all attributes of a node are covered
        def node_attributes_covered(node, minimal_relations, object_types):
            required_attributes = object_types[node]
            covered_attributes = set()
            # Collect attributes covered by existing relations
            for neighbor in minimal_relations.neighbors(node):
                covered_attributes.update(attr1 for attr1, attr2 in minimal_relations[node][neighbor]['relations'])
            # Check if all required attributes are covered
            return required_attributes <= covered_attributes

        # Sort edges by weight in descending order to prioritize important relations
        edges_sorted = sorted(G.edges(data=True), key=lambda x: x[2]['weight'], reverse=True)

        # Add edges until all attributes for each node are covered
        for obj1, obj2, data in edges_sorted:
            new_relations = set(data['relations'])
            
            # Check if new attributes are already covered by other neighbors of obj1
            obj1_covered_attrs = set()
            for neighbor in minimal_relations.neighbors(obj1):
                obj1_covered_attrs.update(attr1 for attr1, attr2 in minimal_relations[obj1][neighbor]['relations'])
            
            # Check if new attributes are already covered by other neighbors of obj2
            obj2_covered_attrs = set()
            for neighbor in minimal_relations.neighbors(obj2):
                obj2_covered_attrs.update(attr2 for attr1, attr2 in minimal_relations[obj2][neighbor]['relations'])

            # Filter new relations to add only those attributes that are not yet covered
            filtered_relations = {(attr1, attr2) for attr1, attr2 in new_relations if attr1 not in obj1_covered_attrs or attr2 not in obj2_covered_attrs}

            if filtered_relations:
                # Add the filtered relations to the minimal relations graph
                if not minimal_relations.has_edge(obj1, obj2):
                    minimal_relations.add_edge(obj1, obj2, relations=filtered_relations)
                else:
                    minimal_relations[obj1][obj2]['relations'].update(filtered_relations)

            # Break the loop if all attributes for each node are covered
            if all(node_attributes_covered(node, minimal_relations, object_types) for node in G.nodes):
                break

        # Convert sets to lists for output
        for u, v, data in minimal_relations.edges(data=True):
            data['relations'] = list(data['relations'])

        return minimal_relations

    def correlation_to_relations(self, df: pd.DataFrame, correlation_matrix: pd.DataFrame) -> List:
        possibleRelations_instances = []
        
        # Erstelle das Mapping direkt aus den doc_types
        cluster_map = {}
        for idx, row in df.iterrows():
            if row['doc_type'] not in cluster_map:
                cluster_map[row['doc_type']] = row['doc_type']
                
        print(f"\nCluster mapping: {cluster_map}")
        
        # Normalisiere Spaltennamen
        renamed_cols = {}
        for col in correlation_matrix.columns:
            if '[' in col:
                parts = col.replace(']', '').split('[')
                doc_type = parts[0]
                field = parts[1].split('_')[-1]
                renamed_cols[col] = f"{doc_type}_{field}"
        
        correlation_matrix = correlation_matrix.rename(columns=renamed_cols, index=renamed_cols)
        df = df.rename(columns=renamed_cols)
        
        print(f"\nDataFrame shape: {df.shape}")
        print(f"Correlation matrix shape: {correlation_matrix.shape}")
        
        corr_pairs = np.where(np.abs(correlation_matrix) > 0.9)
        
        for i, j in zip(*corr_pairs):
            if i >= j:
                continue
                
            col1, col2 = correlation_matrix.index[i], correlation_matrix.index[j]
            corr_value = correlation_matrix.iloc[i,j]
            
            doc_type1 = col1.split('_')[0]
            doc_type2 = col2.split('_')[0]
            key1 = col1.split('_')[-1]
            key2 = col2.split('_')[-1]
            
            if col1 in df.columns and col2 in df.columns:
                values = []
                df_filtered = df.dropna(subset=[col1, col2])
                
                for _, row in df_filtered.iterrows():
                    values.append((str(row['process_id']), row[col1], row[col2]))
                
                if values:
                    process_ids = {proc_id: [(key1, key2, float(v1), float(v2))] 
                                for proc_id, v1, v2 in values}
                    
                    possibleRelations_instances.append([
                        RuleType.SAME_KEY_VALUE_PAIR if abs(corr_value) > 0.99 else RuleType.SAME_VALUE,
                        [(key1, key2)],
                        doc_type1,
                        doc_type2,
                        process_ids
                    ])
        
        return possibleRelations_instances, cluster_map
    

    # def analyze_and_establish_relations(self, content_based_relation, dataframe):

    #     def analyze_attribute_importance():
    #         """Calculate dynamic weights for attributes based on their usage patterns"""
    #         attribute_frequency = defaultdict(int)
    #         doc_type_usage = defaultdict(int)
    #         total_relations = 0
            
    #         # Collect usage statistics
    #         for key, relations in content_based_relation.items():
    #             doc_type_usage[key[0]] += 1
    #             doc_type_usage[key[1]] += 1
                
    #             for relation_type, relation in relations:
    #                 if relation_type != RealtationType.CONTENT_BASED_RELATION:
    #                     continue
                        
    #                 total_relations += 1
    #                 for (rule_type, keys), processIDs in relation.processinstances.items():
    #                     for key in keys:
    #                         attribute_frequency[key] += 1

    #         # Calculate dynamic weights
    #         weights = {}
    #         for attr, freq in attribute_frequency.items():
    #             ratio = freq / total_relations
    #             # Higher weight for less common attributes (more discriminative)
    #             if ratio < 0.2:
    #                 weights[attr] = 3.0  # Highly discriminative
    #             elif ratio < 0.5:
    #                 weights[attr] = 2.0  # Moderately discriminative
    #             else:
    #                 weights[attr] = 1.0  # Common attribute
                    
    #         return weights, doc_type_usage

    #     def separate_independent_objects(df):
    #         """Identify and separate process-independent objects"""
    #         independent_objects = set(df[df['process_instance_independent']]['cluster'])
    #         dependent_objects = set(df[~df['process_instance_independent']]['cluster'])
    #         return independent_objects, dependent_objects

    #     def build_relation_graph(content_relations, attribute_weights):
    #         """Build weighted graph of relations"""
    #         G = nx.Graph()
            
    #         for key, relations in content_relations.items():
    #             obj1, obj2 = key
    #             edge_weight = 0
                
    #             for relation_type, relation in relations:
    #                 if relation_type != RealtationType.CONTENT_BASED_RELATION:
    #                     continue
                        
    #                 for (rule_type, keys), processIDs in relation.processinstances.items():
    #                     # Calculate weight based on attribute importance and process coverage
    #                     weight = sum(attribute_weights.get(k, 1.0) for k in keys)
    #                     coverage_factor = len(processIDs) / max_instances
    #                     edge_weight += weight * coverage_factor
                
    #             if edge_weight > 0:
    #                 G.add_edge(obj1, obj2, weight=edge_weight, relations=relations)
                    
    #         return G

    #     def find_minimal_spanning_tree(G, independent_objects):
    #         """Find minimal spanning tree while prioritizing connections to independent objects"""
    #         # Start with independent objects
    #         T = nx.Graph()
    #         T.add_nodes_from(G.nodes())
            
    #         # Connect independent objects first
    #         for ind_obj in independent_objects:
    #             if ind_obj not in G:
    #                 continue
    #             edges = sorted(G.edges(ind_obj, data=True), 
    #                         key=lambda x: x[2]['weight'], 
    #                         reverse=True)
    #             if edges:
    #                 u, v, data = edges[0]
    #                 T.add_edge(u, v, **data)
            
    #         # Complete the spanning tree
    #         remaining_edges = sorted(G.edges(data=True), 
    #                             key=lambda x: x[2]['weight'], 
    #                             reverse=True)
            
    #         for u, v, data in remaining_edges:
    #             if not nx.has_path(T, u, v):
    #                 T.add_edge(u, v, **data)
                    
    #         return T

    #     # Main execution flow
    #     independent_objects, dependent_objects = separate_independent_objects(dataframe)
    #     attribute_weights, doc_type_usage = analyze_attribute_importance()
    #     max_instances = max(len(relation.processinstances) 
    #                     for _, relations in content_based_relation.items()
    #                     for _, relation in relations)
        
    #     # Build and analyze relation graph
    #     G = build_relation_graph(content_based_relation, attribute_weights)
    #     minimal_tree = find_minimal_spanning_tree(G, independent_objects)
        
    #     # Create final optimized relations
    #     optimized_relations = {}
    #     for u, v, data in minimal_tree.edges(data=True):
    #         key = tuple(sorted([u, v]))
    #         optimized_relations[key] = data['relations']
        
    #     # Ensure all independent objects are connected
    #     for ind_obj in independent_objects:
    #         if not any(ind_obj in key for key in optimized_relations):
    #             # Find best possible connection for unconnected independent object
    #             best_edge = max(
    #                 (edge for edge in G.edges(ind_obj, data=True)),
    #                 key=lambda x: x[2]['weight'],
    #                 default=None
    #             )
    #             if best_edge:
    #                 u, v, data = best_edge
    #                 key = tuple(sorted([u, v]))
    #                 optimized_relations[key] = data['relations']
        
    #     return optimized_relations