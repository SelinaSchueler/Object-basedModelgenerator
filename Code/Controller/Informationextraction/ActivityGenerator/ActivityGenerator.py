# Importing necessary modules and classes
from collections import defaultdict
from typing import List, Set
from matplotlib import pyplot as plt
import pandas as pd
import pm4py

from pm4py.objects.log.obj import EventLog, Trace, Event  # PM4Py classes for process mining and event logs
from pm4py.util.xes_constants import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY, DEFAULT_TRACEID_KEY  # Constants for event log attributes
from pm4py.algo.discovery.alpha import algorithm as alpha_miner  # Heuristic process discovery algorithm
from pm4py.algo.discovery.footprints import algorithm as footprints_discovery
from pm4py.visualization.footprints import visualizer as fp_visualizer
from pm4py.visualization.petri_net import visualizer as vis_factory  # Visualization tools for Petri nets
from PIL import Image  # Python Imaging Library for image processing
from datetime import datetime  # Standard library for handling dates and times
from dateutil.relativedelta import relativedelta
import networkx as nx
import numpy as np
from Model.Activity.ActivityType import ActivityType # Custom class for defining activity types
from Model.Activity.ActivityType import ActivityRelationType # Enum for activity relation types 
from Model.ObjectModel.ObjectRelation import RealtationType
from Controller.Transformation.PNGenerator import EventlogPNGenerator
from Controller.Informationextraction.ObjectRelationGenerator import RuleType  # Dateutil library for more complex date manipulations
from PyQt5.QtCore import pyqtSignal

# TODO: Implement arithmetic operators for multidimensional relationships: addition, subtraction, etc.
# TODO: Define activation conditions: occurrence of objects, changes depending on specific objects, attributes, values

# Object model: Object types and their relations
# Process instances: Each process instance with its associated documents, derive further relationships from these

# # Main steps outlined for the activity generation process:
# 1. Create an activity for each relation,
# 2. In each process instance, check if it exists and evaluate the probability of input/output,
# 3. In each process instance, check if rules apply - sum, etc., and create activity,
# 4. Apply machine learning to recognize relationships, check if these are already covered by steps 1 or 3,
# 5. Generate activities according to timestamps, check if they already exist.

# Constants for event log attributes

class ActivityGenerator:
    def __init__(self, dataframe, debug: bool = False, early_position_bonus: float = 1.5, late_position_penalty: float = 0.5, reference_weight: float = 2.0, reference_position_factor: float = 2.0, sequence_weight: float = 1.5, attribute_weight: float = 1.2, temporal_weight: float = 2.0, variant_weight: float = 0.5, parallel_object_penalty: float = 6.0, each_attribute_by_object: bool = False, min_score = 2.0, loop_weight = -1.0, log_signal: pyqtSignal = None):
        self.debug = debug
        self.footprint = None
        self.object_traces = None
        self.dataframe = dataframe
        self.maping = None
        self.scored_content_AT = None
        self.early_position_bonus = early_position_bonus
        self.late_position_penalty = late_position_penalty
        self.reference_weight = reference_weight
        self.reference_position_factor = reference_position_factor
        self.sequence_weight = sequence_weight
        self.attribute_weight = attribute_weight
        self.temporal_weight = temporal_weight
        self.variant_weight = variant_weight
        self.parallel_object_penalty = parallel_object_penalty
        self.each_attribute_by_object = each_attribute_by_object
        self.min_score = min_score
        self.loop_weight = loop_weight
        self.log_signal = log_signal  # Add log_signal parameter

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(f"[TERMINAL] {message}")

    def generate_content_activities(self, content_based_relation, process_instances: dict) -> None:
        self.debug_print("Starting content-based activity generation")
        self.mapping = self.dataframe.groupby('cluster')['doc_type'].agg(lambda x: x.value_counts().index[0]).to_dict()
        content_based_AT = []
        unclearAT = []
        for key, relations in content_based_relation.items():
            for relation_type, relation in relations:
                if relation_type == RealtationType.CONTENT_BASED_RELATION:
                    #self.debug_print(f"Processing relation: {relation.name} with type: {relation_type}")
                    calculated_weights = {obj: [] for obj in relation.objects.keys()}

                    # Process instances now contain the correct format of data
                    for (rule_type, keys), processIDs in relation.processinstances.items():
                        for process_id, rules_list in processIDs.items():
                            for (rule_key1, rule_key2, value1, value2, obj1, obj2, docs_key) in rules_list:
                            # obj1 and obj2 are tuples of (doc_type, weight)
                                doc_type1, weight1, variant1 = obj1
                                doc_type2, weight2, variant2 = obj2
                                calculated_weights[(doc_type1, variant1)].append(weight1)
                                calculated_weights[(doc_type2, variant2)].append(weight2)
                                #self.debug_print(f"Updated weights for {doc_type1}: {calculated_weights[doc_type1]} and {doc_type2}: {calculated_weights[doc_type2]}")

                    # Update relation weights with averages
                    for obj, weights in calculated_weights.items():
                        if weights:
                            relation.objects[obj] = sum(weights) / len(weights)
                            #self.debug_print(f"Calculated average weight for {obj}: {relation.objects[obj]}")
                    if len(calculated_weights) < 2:
                        input_list = [obj for obj, weight in relation.objects.items()]
                        output_list = [obj for obj, weight in relation.objects.items()]
                        for obj, weight in relation.objects.items():
                            relation.objects[obj] = 0
                    else:
                        input_list = [obj for obj, weight in relation.objects.items() if weight <= 0]
                        output_list = [obj for obj, weight in relation.objects.items() if weight > 0]
                    
                    name = (tuple(self.mapping[x[0]] for x in input_list), tuple(self.mapping[x[0]] for x in output_list))
                    name = str(name).replace(",)", ")")
                
                    # Create activity
                    activity = ActivityType(relation.inst_id, name, ActivityRelationType.CONTENT_BASED, relation.individualScore)
                    activity.add_rule(relation.rules)
                    # Set input/output based on calculated weights
                    addedInput = False
                    addedOutput = False
                    for obj, weight in relation.objects.items():
                        if len(relation.objects)<2:
                            activity.add_input_object_type(obj)
                            activity.add_output_object_type(obj)                            
                            addedInput = True
                            addedOutput = True
                        elif weight < -0.2:
                            addedInput = True
                            activity.add_input_object_type(obj)
                            self.debug_print(f"Added {obj} as input object type with weight {weight}")
                        elif weight > 0.2:
                            addedOutput = True
                            activity.add_output_object_type(obj)                            
                            self.debug_print(f"Added {obj} as output object type with weight {weight}")
                    if addedInput and addedOutput:
                        activity.add_relation_instance(relation.processinstances)
                        content_based_AT.append(activity)
                    else:
                        unclearAT.append((activity,relation))
                        self.debug_print(f"Added {obj} as unclear object type with weight {weight}")

                    self.debug_print(f"Created activity: {activity.name} with inputs: {activity.input_object_types} and outputs: {activity.output_object_types}, Prozessinstanzen: {activity.instanceList.keys()}")
    
        for activity, relation in unclearAT:
            activity.input_object_types.clear()
            activity.output_object_types.clear()
            objects = {unclearobj: weight for unclearobj, weight in relation.objects.items()}
            for unclearobj, weight in objects.items():
                for activityAT in content_based_AT:
                    input_list = [obj for obj in activityAT.input_object_types]
                    output_list = [obj for obj in activityAT.output_object_types]
                    if unclearobj in input_list:
                        relation.objects[unclearobj] =+ 0.15
                    elif unclearobj in output_list:
                        relation.objects[unclearobj] =- 0.15

        for activity, relation in unclearAT:
            input_list = [obj for obj, weight in relation.objects.items() if weight <= -0.1]
            output_list = [obj for obj, weight in relation.objects.items() if weight > 0.1]
            name = (tuple(self.mapping[x[0]] for x in input_list), tuple(self.mapping[x[0]] for x in output_list))
            name = str(name).replace(",)", ")")
            activity.name = name
            for obj, weight in relation.objects.items():
                if weight < -0.1:
                    activity.add_input_object_type(obj)
                    #self.debug_print(f"Added {obj} as input object type with weight {weight}")
                elif weight > 0.1:
                    activity.add_output_object_type(obj)
                #self.debug_print(f"Added {obj} as output object type with weight {weight}")
            if len(activity.input_object_types) > 0 and len(activity.output_object_types) > 0:
                activity.add_relation_instance(relation.processinstances)
                content_based_AT.append(activity)
                self.debug_print(f"Created unclear activity: {activity.name} with inputs: {activity.input_object_types} and outputs: {activity.output_object_types}, Prozessinstanzen: {activity.instanceList.keys()}")
        
        optimized_relations = self.optimize_activity_types(content_based_AT)
        self.debug_print("Inhaltsbasierte bewertete Aktivitätstypen:")
        for activity in optimized_relations:
            self.debug_print(f"Name: {activity.name}")

        optimized_relations = self.find_and_merge_overlapping_activities(optimized_relations)

        optimized_relations = self.optimize_merged_activity_types(optimized_relations)

        self.debug_print("Inhaltsbasierte zusammengeführte Aktivitätstypen:")
        for activity in optimized_relations:
            self.debug_print(f"Name: {activity.name}")
            self.debug_print(f"Objekte: inputs: {activity.input_object_types} and outputs: {activity.output_object_types}")
            self.debug_print(f"Regeln: {activity.rules}")
            self.debug_print(f"Prozessinstanzen: {activity.instanceList}")

        for activity in content_based_AT:
            activity.named_all_object_types(self.mapping)

        return optimized_relations

    def generate_activities(self, time_based_relation, process_instances: dict) -> None:
        self.debug_print("Starting time-based activity generation")
        dataframe = self.dataframe  # Use the class attribute
        self.mapping = dataframe.groupby('cluster')['doc_type'].agg(lambda x: x.value_counts().index[0]).to_dict()
        time_based_AT = []
        aggregated_activities, time_based_relation_updated, fig_footprint = self.analyze_footprints(time_based_relation)
        for key, relation in time_based_relation_updated.items():
            if relation[0] == RealtationType.TIME_BASED_RELATION:
                activity = ActivityType(relation[1].inst_id, relation[1].name, ActivityRelationType.TIME_BASED)
                for obj, value in relation[1].objects.items():
                    if value == -1:
                        activity.add_input_object_type(obj)
                    elif value == 1:
                        activity.add_output_object_type(obj)
                activity.add_instance(relation[1].processinstances)
                activity.add_rule(relation[1].rules)
                time_based_AT.append(activity)
        for key, relationlist in aggregated_activities.items():

            inputs = set()
            outputs = set()
            and_split_in = set()
            and_split_out = set()
            and_join_in = set()
            and_join_out = set()        
            and_join_process_instancesAT = {}
            and_split_process_instancesAT = {}
            for relation in relationlist:
                if len(relation.objects) >= 2:
                    key1v, key2v = list(relation.objects.keys())[:2]
                if key1v[0] in key and key2v[0] in key:
                    continue

                self.debug_print(f"creating time aggregated Activity: {relation.name}, objects: {relation.objects}, Instances: {relation.processinstances}")
                for k, value in relation.objects.items():
                    if value == -1:
                        if k[0] not in key:
                            and_split_in.add(k)
                            for keys, item in relation.processinstances.items():
                                if keys in and_split_process_instancesAT:
                                    continue
                                else:
                                    and_split_process_instancesAT[keys] = "timebased"
                        else:
                            and_join_in.add(k)
                            for keys, item in relation.processinstances.items():
                                if keys in and_join_process_instancesAT:
                                    continue
                                else:
                                    and_join_process_instancesAT[keys] = "timebased"
                    elif value == 1:
                        if k[0] not in key:
                            and_join_out.add(k)
                        else:
                            and_split_out.add(k)
                # activity.add_rule(relation.rules)
            if len(and_join_in) > 0 and len(and_join_out) > 0:

                # Convert sets to sorted lists for consistent ordering
                input_list = sorted(list(and_join_in))
                output_list = sorted(list(and_join_out))
                
                # Get the first input and output type names
                name = (tuple(set(self.mapping[x[0]] for x in input_list)), tuple(set(self.mapping[x[0]] for x in output_list)))
                name = str(name).replace(",)", ")")
                self.debug_print(f"creating and join time aggregated Activity: {name}, objects: {input_list}, {output_list}")

                activity = ActivityType(name, str(name), ActivityRelationType.AGGREGATED_TIME_BASED)
                for input in and_join_in:
                    activity.add_input_object_type(input)
                for output in and_join_out:
                    activity.add_output_object_type(output)
                activity.add_instance(and_join_process_instancesAT)
                time_based_AT.append(activity)

            if len(and_split_in) > 0 and len(and_split_out) > 0:
                # Convert sets to sorted lists for consistent ordering
                input_list = sorted(list(and_split_in))
                output_list = sorted(list(and_split_out))
                
                # Get the first input and output type names
                name = (tuple(set(self.mapping[x[0]] for x in input_list)), tuple(set(self.mapping[x[0]] for x in output_list)))
                name = str(name).replace(",)", ")")
                self.debug_print(f"creating and split time aggregated Activity: {name}, objects: {input_list}, Instances: {output_list}")

                activity = ActivityType(name, str(name), ActivityRelationType.AGGREGATED_TIME_BASED)
                for input in and_split_in:
                    activity.add_input_object_type(input)
                for output in and_split_out:
                    activity.add_output_object_type(output)
                activity.add_instance(and_split_process_instancesAT)
                time_based_AT.append(activity)

        for activity in time_based_AT:
            self.debug_print(f"Activity: {activity.name}, Inputs: {activity.input_object_types}, Outputs: {activity.output_object_types}, Instances: {activity.instanceList}")
            activity.named_all_object_types(self.mapping)
        return time_based_AT, {'Footprint-Matrix': fig_footprint}

    def aggregate_time_based_activity_types(self, time_based_relation, agAT):
        self.debug_print(f"Aggregating time-based activity types for {agAT}")
        dataframe = self.dataframe  # Use the class attribute
        """
        Aggregates activity types based on the parallel relationship between object types OA and OB.
        """
        deleted_relations = []
        updated_relation = []

        possible_aggregated_activities = {}

        def update_dict(d, key, value):
            if key in d:
                d[key].extend(value)  # If key exists, append the value
            else:
                d[key] = value if isinstance(value, list) else [value]  # If key does not exist, create a new entry with a list
            return d

        for oa_cluster, ob_cluster in agAT:
            possible_aggregated_activities_oa_input = {}
            possible_aggregated_activities_ob_input = {}
            possible_aggregated_activities_oa_output = {}
            possible_aggregated_activities_ob_output = {}
            for key, (kind, relation) in time_based_relation.items():
               
                if len(relation.objects) >= 2:
                    key1v, key2v = list(relation.objects.keys())[:2]
                else:
                    break
                key1 = key[0]  # cluster
                key2 = key[1]  # cluster

                self.debug_print(f"Relation: {key1} -> {key2}, oa_cluster: {oa_cluster}, ob_cluster: {ob_cluster} + relation: {relation.name}")
                if (oa_cluster == key1 and ob_cluster == key2) or (oa_cluster == key2 and ob_cluster == key1):
                    sorted_key = tuple(sorted((key1, key2)))
                    possible_aggregated_activities = update_dict(possible_aggregated_activities, sorted_key, [relation])
                    deleted_relations.append(key)
                elif oa_cluster == key1 or ob_cluster == key2 or oa_cluster == key2 or ob_cluster == key1:
                    input = key1v[0] if relation.objects[key1v] == -1 else key2v
                    output = key2v[0] if relation.objects[key2v] == 1 else key1v
                    if input == oa_cluster:
                        possible_aggregated_activities_oa_input = update_dict(possible_aggregated_activities_oa_input, key, [relation])
                    elif input == ob_cluster:
                        possible_aggregated_activities_ob_input = update_dict(possible_aggregated_activities_ob_input, key, [relation])
                    elif output == oa_cluster:
                        possible_aggregated_activities_oa_output = update_dict(possible_aggregated_activities_oa_output, key, [relation])
                    elif output == ob_cluster:
                        possible_aggregated_activities_ob_output = update_dict(possible_aggregated_activities_ob_output, key, [relation])

            if len(possible_aggregated_activities_oa_input) > 0 and len(possible_aggregated_activities_ob_input) > 0:
                for (input_oa, output_oa), relation_oa in possible_aggregated_activities_oa_input.items():
                    for (input_ob, output_ob), relation_ob in possible_aggregated_activities_ob_input.items():
                        if output_oa == output_ob:
                        # Check if output_oa is in any tuple in the list agAT
                            if not any(output_oa in tup for tup in agAT):
                                keytupel = tuple(sorted((input_oa, input_ob)))
                                deleted_relations.append((input_oa, output_oa))
                                deleted_relations.append((input_ob, output_ob))
                                possible_aggregated_activities = update_dict(possible_aggregated_activities, keytupel, relation_oa)
                                possible_aggregated_activities = update_dict(possible_aggregated_activities, keytupel, relation_ob)
                                self.debug_print(f"Aggregated activities for input: {input_oa}, {input_ob} and output: {output_oa}")
                            else:
                                updated_relation.append(((relation_oa, input_oa, output_oa ), (relation_ob, input_ob, output_ob)))
                                self.debug_print(f"Updated relation for input: {input_oa}, {input_ob} and output: {output_oa}")

            if len(possible_aggregated_activities_oa_output) > 0 and len(possible_aggregated_activities_ob_output) > 0:
                for (input_oa, output_oa), relation_oa in possible_aggregated_activities_oa_output.items():
                    for (input_ob, output_ob), relation_ob in possible_aggregated_activities_ob_output.items():
                        if input_oa == input_ob:
                            if not any(input_oa in tup for tup in agAT):
                                keytupel = tuple(sorted((output_oa, output_ob)))
                                deleted_relations.append((input_oa, output_oa))
                                deleted_relations.append((input_ob, output_ob))
                                possible_aggregated_activities = update_dict(possible_aggregated_activities, keytupel, relation_oa)
                                possible_aggregated_activities = update_dict(possible_aggregated_activities, keytupel, relation_ob)
                                self.debug_print(f"Aggregated activities for input: {input_oa} and output: {output_oa}, {output_ob}")
                            else:
                                updated_relation.append(((relation_oa, input_oa, output_oa ), (relation_ob, input_ob, output_ob)))
                                self.debug_print(f"Updated relation for input: {input_oa} and output: {output_oa}, {output_ob}")
                        
        updating_result = []
        instances1 = {}
        pi_1 = []
        pi_2 = []
        instances2 = {}
        instaces1upandel = []
        instaces1upande2 = []

        for ((relation_oa, input_oa, output_oa ), (relation_ob, input_ob, output_ob)) in updated_relation:
            for input in relation_oa[0].objects:
                if input_oa in input:
                    input_oa_v = input[1]
            for input in relation_ob[0].objects:
                if input_ob in input:
                    input_ob_v = input[1]
            
            for output in relation_oa[0].objects:
                if output_oa in output:
                    output_oa_v = output[1]
            for output in relation_ob[0].objects:
                if output_ob in output:
                    output_ob_v = output[1]
           
            if not any(input_oa == t[0] for t in instances1.keys()) and not any(output_oa == t[1] for t in instances1.keys()):
                instances1[(input_oa, output_oa)] = len(relation_oa[0].processinstances)
                for piob, indocob, outdocob in relation_ob[0].processinstances.keys():
                    if (piob, (input_oa, input_oa_v), (output_oa, output_oa_v)) not in pi_1:
                        pi_1.append((piob, (input_oa, input_oa_v), (output_oa, output_oa_v)))
                instaces1upandel.append(((relation_oa, input_oa, output_oa ), (relation_ob, input_ob, output_ob)))
                self.debug_print(f"Instance 1 updated for input: {input_oa} and output: {output_oa} for Relation {relation_oa[0].name}")

            elif not any(input_oa == t[0] for t in instances2.keys()) and not any(output_oa == t[1] for t in instances2.keys()):
                instances2[(input_oa, output_oa)] = len(relation_oa[0].processinstances)
                for pioa, indocoa, outdocoa in relation_oa[0].processinstances.keys():
                    if (pioa, (input_ob, input_ob_v), (output_ob, output_ob_v)) not in pi_2:
                        pi_2.append((pioa, (input_ob, input_ob_v), (output_ob, output_ob_v)))
                instaces1upande2.append(((relation_oa, input_oa, output_oa ), (relation_ob, input_ob, output_ob)))
                self.debug_print(f"Instance 2 updated for input: {input_oa} and output: {output_oa} for Relation {relation_oa[0].name}")
                        
            if not any(input_ob == t[0] for t in instances2.keys()) and not any(output_ob == t[1] for t in instances2.keys()):
                instances2[(input_ob, output_ob)] = len(relation_ob[0].processinstances)
                for pioa, indocoa, outdocoa in relation_oa[0].processinstances.keys():
                    if (pioa, (input_ob, input_ob_v), (output_ob, output_ob_v)) not in pi_2:
                        pi_2.append((pioa, (input_ob, input_ob_v), (output_ob, output_ob_v)))
                instaces1upande2.append(((relation_ob, input_ob, output_ob), (relation_oa, input_oa, output_oa)))
                self.debug_print(f"Instance 2 updated for input: {input_ob} and output: {output_ob} for Relation {relation_ob[0].name}")

            elif not any(input_ob == t[0] for t in instances1.keys()) and not any(output_ob == t[1] for t in instances1.keys()):
                instances1[(input_ob, output_ob)] = len(relation_ob[0].processinstances)
                #TODO: pi richtig aktualisieren mit neuen docs...
                for piob, indocob, outdocob in relation_ob[0].processinstances.keys():
                    if (piob, (input_oa, input_oa_v), (output_oa, output_oa_v)) not in pi_1:
                        pi_1.append((piob, (input_oa, input_oa_v), (output_oa, output_oa_v)))
                instaces1upandel.append(((relation_ob, input_ob, output_ob), (relation_oa, input_oa, output_oa)))
                self.debug_print(f"Instance 1 updated for input: {input_ob} and output: {output_ob} for Relation {relation_ob[0].name}")

        sum1 = sum(instances1.values())
        sum2 = sum(instances2.values())
        self.debug_print(f"Sum of instances1: {sum1}, Sum of instances2: {sum2}")
        if sum1 > 0 or sum2 > 0:
            if sum1 < sum2:
                for ((relation_ob, input_ob, output_ob), (relation_oa, input_oa, output_oa)) in instaces1upande2:
                    for i in pi_2:
                        relation_ob[0].add_processinstance_timebased(i)

                    relation_ob[0].add_related_processinstances(relation_oa[0].processinstances)
                    updating_result.append((input_ob, output_ob, relation_ob[0]))
                    deleted_relations.append((input_oa, output_oa))
                    self.debug_print(f"Updated relation_ob for input: {input_ob} and output: {output_ob}")
            else:
                for ((relation_ob, input_ob, output_ob), (relation_oa, input_oa, output_oa)) in instaces1upandel:
                    for i in pi_1:
                        relation_ob[0].add_processinstance_timebased(i)
                    relation_ob[0].add_related_processinstances(relation_oa[0].processinstances)
                    updating_result.append((input_ob, output_ob, relation_ob[0]))
                    deleted_relations.append((input_oa, output_oa))
                    self.debug_print(f"Updated relation_ob for input: {input_ob} and output: {output_ob}")
            
        for key in deleted_relations :
            if key in time_based_relation and not any(key == (t[0],t[1]) for t in updating_result):
                kind, relation = time_based_relation[key]
                time_based_relation[key] = (RealtationType.USED_TIME_BASED_RELATION, relation)
                self.debug_print(f"Marked relation as used for key: {key}")
        
        for input, output, relation in updating_result:    
            if (input, output) in time_based_relation:       
                kind, relation_old = time_based_relation[(input, output)]
                time_based_relation[(input, output)] = (kind, relation)
                self.debug_print(f"Updated time_based_relation for input: {input} and output: {output}")
            else:
                self.debug_print(f"Not updated time_based_relation for input: {input} and output: {output}")



        for key, relations in possible_aggregated_activities.items():
            for relation in relations:
                self.debug_print(f"Aggregated activity for objects {key}: {relation.name}")

        return possible_aggregated_activities, time_based_relation

    def analyze_footprints(self, time_based_relation):
        self.debug_print("Analyzing footprints")
        dataframe = self.dataframe  # Use the class attribute
        object_log = self.create_object_event_log()
        #process_tree = pm4py.discover_process_tree_inductive(object_log, noise_threshold=0.1)
        self.footprint = footprints_discovery.apply(object_log, variant=footprints_discovery.Variants.ENTIRE_EVENT_LOG)
        
        #fp_model = footprints_discovery.apply(process_tree, variant=footprints_discovery.Variants.PROCESS_TREE)
        gviz = fp_visualizer.apply(self.footprint)
        #fp_visualizer.view(gviz)
        #vis_factory.save(gviz, "foodprint.png")

        fig_footprint = EventlogPNGenerator.convert_gviz_to_matplotlib(EventlogPNGenerator, gviz)
        plt.close(fig_footprint)


        aggregated_activities = {} # List of new aggregated activity types and old activity types
        arc_analyzed = [] # List of analyzed arcs
        mapping = dataframe.groupby('doc_type')['cluster'].agg(lambda x: x.value_counts().index[0]).to_dict()

        self.debug_print("\nDirectly-Follows Relationships:")
        for (act1, act2) in self.footprint['sequence']:
            self.debug_print(f"{act1} -> {act2}")
        
        aggregating_AT = []
        self.debug_print("\nParallel Relationships:")
        for (act1, act2) in self.footprint['parallel']:            
            self.debug_print(f"{act1} || {act2}")
            if (act1, act2) in arc_analyzed or (act2, act1) in arc_analyzed:
                continue
            act1_back = act1.split('_')[0]
            act2_back = act2.split('_')[0]
            aggregating_AT.append((mapping[act1_back], mapping[act2_back]))
            #aggregating_AT.append((act1, act2))
            arc_analyzed.append((act1, act2))

        ag, time_based_relation= self.aggregate_time_based_activity_types(time_based_relation, aggregating_AT)
        aggregated_activities.update(ag)
            
            #event[DEFAULT_NAME_KEY] = f"{doc['doc_type']}"
            
        self.debug_print("\nStart Activities:")
        for act in self.footprint['start_activities']:
            self.debug_print(f"Start: {act}")
            
        self.debug_print("\nEnd Activities:")
        for act in self.footprint['end_activities']:
            self.debug_print(f"End: {act}")
        
        return aggregated_activities, time_based_relation, fig_footprint
    
    def create_object_event_log(self) -> EventLog:
        self.debug_print("Creating object event log")
        dataframe = self.dataframe  # Use the class attribute
        """
        Erstellt ein EventLog aus dem DataFrame.
        """
        log = EventLog()
        traces = self.create_object_traces_from_df()
        
        # Sicherheitsprüfung
        if traces:
            for trace in traces:
                log.append(trace)
        else:
            self.debug_print("Warnung: Keine Traces generiert")
        self.object_traces = log
        return log
    
    def create_object_traces_from_df(self) -> List[Trace]:
        self.debug_print(f"Starting trace creation with DataFrame of shape: {self.dataframe.shape}")
        df = self.dataframe  # Use the class attribute
        self.debug_print(f"Starting trace creation with DataFrame of shape: {df.shape}")
        
        df['case_ids'] = df['process_instances'].apply(lambda x: x if isinstance(x, list) else [])
        df_exploded = df.explode('case_ids')
        self.debug_print(f"After explode, DataFrame shape: {df_exploded.shape}")

        object_traces = []
        for case_id, case_docs in df_exploded.groupby('case_ids'):
            self.debug_print(f"\nProcessing case_id: {case_id}")
            self.debug_print(f"Number of documents in case: {len(case_docs)}")
            
            activities = case_docs[
                ~case_docs['process_instance_independent'] & 
                case_docs['final_timestamp'].notna()
            ]
            self.debug_print(f"After filtering, number of documents: {len(activities)}")
            
            activities_sorted = activities.sort_values('final_timestamp')
            self.debug_print(f"Sorted timestamps: {activities_sorted['final_timestamp'].tolist()}")

             # Erstelle Trace
            object_trace = Trace()
            object_trace.attributes[DEFAULT_TRACEID_KEY] = case_id
            
            activities_list = list(activities_sorted.iterrows())
            self.debug_print(f"Number of documents to process: {len(activities_list)}")
            
            # Füge Events hinzu
            for _, doc in activities_sorted.iterrows():
                event = Event()

                # Create event with attributes dictionary
                event = Event()
                event[DEFAULT_NAME_KEY] = f"{doc['doc_type']}_{doc['variantID']}"
                event[DEFAULT_TIMESTAMP_KEY] = doc['final_timestamp']
                
                object_trace.append(event)
            
            if len(object_trace) > 0:
                self.debug_print(f"Adding trace with {len(object_trace)} events")
                object_traces.append(object_trace)
            else:
                self.debug_print("No events in trace, skipping")

        self.debug_print(f"\nTotal traces created: {len(object_traces)}")
        return object_traces

    def check_process_instances(self, activity_list, process_instances):
        self.debug_print("Checking process instances")
        return activity_list

    def evaluate_object_probabilities(self, object_relations: dict) -> dict:
        self.debug_print("Evaluating object probabilities")
        dataframe = self.dataframe  # Use the class attribute
        """
        Evaluates the probabilities of objects being inputs or outputs based on various criteria.
        """
        probabilities = {}

        for key, relation in object_relations.items():
            obj1, obj2 = key
            obj1_prob = 0.5
            obj2_prob = 0.5

            # Check if dates are present in object instances
            if 'date' in dataframe.columns:
                if dataframe.loc[dataframe['cluster'] == obj1, 'date'].notna().any():
                    obj1_prob += 0.1
                if dataframe.loc[dataframe['cluster'] == obj2, 'date'].notna().any():
                    obj2_prob += 0.1

            # Check if objects are classified as process instance independent
            if 'process_instance_independent' in dataframe.columns:
                if dataframe.loc[dataframe['cluster'] == obj1, 'process_instance_independent'].any():
                    obj1_prob += 0.1
                if dataframe.loc[dataframe['cluster'] == obj2, 'process_instance_independent'].any():
                    obj2_prob += 0.1

            # Check if objects are involved in multiple relations
            if obj1 in [rel[0] for rel in object_relations.keys()] and obj1 in [rel[1] for rel in object_relations.keys()]:
                obj1_prob += 0.1
            if obj2 in [rel[0] for rel in object_relations.keys()] and obj2 in [rel[1] for rel in object_relations.keys()]:
                obj2_prob += 0.1

            # Check for multiple relationships (e.g., addition of prices)
            if 'price' in dataframe.columns:
                if dataframe.loc[dataframe['cluster'] == obj1, 'price'].sum() > 0:
                    obj1_prob += 0.1
                if dataframe.loc[dataframe['cluster'] == obj2, 'price'].sum() > 0:
                    obj2_prob += 0.1

            probabilities[key] = (obj1_prob, obj2_prob)

        return probabilities

    def find_and_merge_overlapping_activities(self, activity_list: List[ActivityType]) -> List[ActivityType]:
        self.debug_print("Starting to find and merge overlapping activities")
        # First pass: Merge activities with identical inputs and outputs
        merged_identical = self.merge_identical_activities(activity_list)
        
        # Second pass: Merge activities with shared input/output types
        final_merged = self.merge_shared_io_activities(merged_identical)
        
        return final_merged

    def merge_shared_io_activities(self, activity_list: List[ActivityType]) -> List[ActivityType]:
        self.debug_print("Starting to merge activities with shared input/output types")
        merged_activities = []
        activity_map = defaultdict(list)
        visited = set()

        # Map activities by both their inputs and outputs
        for activity in activity_list:
            for input_obj in activity.input_object_types:
                activity_map[('input', input_obj)].append(activity)
            for output_obj in activity.output_object_types:
                activity_map[('output', output_obj)].append(activity)

        # First pass: merge activities with same input and parallel outputs
        for activity in activity_list:
            if activity in visited:
                continue
                
            same_input_candidates = self.find_input_merge_candidates(activity, activity_map)
            
            if same_input_candidates:
                valid_candidates = set()
                for candidate in same_input_candidates:
                    if candidate not in visited and self.can_merge_activities(activity, candidate, activity_list):                        
                        valid_candidates.add(candidate)
                
                if valid_candidates:
                    self.debug_print(f"Merging activities with same input and parallel outputs: {activity.name} with {', '.join([c.name for c in valid_candidates])}")
                    additional_saved_activities = []
                    for candidate in valid_candidates:
                        additional_saved_activities.extend(self.not_complete_merge(activity, candidate))
                        if len(additional_saved_activities) > 0:
                            for activity_saved in additional_saved_activities:
                                merged_activities.append(activity_saved)
                                self.debug_print(f"Saved activities based on other relationships: {activity_saved.name}")

                    merged = self.merge_activities([activity] + list(valid_candidates))
                    if merged:
                        self.debug_print(f"  Merged into: {merged.name}")
                        merged_activities.append(merged)
                        visited.update(valid_candidates)
                        visited.add(activity)
                        continue
            
            # Only add to second pass if no parallel merging occurred
            if activity not in visited:
                merged_activities.append(activity)
                visited.add(activity)

        # Second pass: merge remaining activities based on other relationships
        # BUT only if they weren't involved in parallel merges
        second_pass_results = []
        visited_second_pass = set()
        
        for activity in merged_activities:
            if activity in visited_second_pass:
                continue
                
            # Skip activities that have parallel outputs
            database_candidates = self.find_input_database_candidates(activity, activity_map)
            valid_candidates = set()
            
            for candidate in database_candidates:
                if (candidate not in visited_second_pass and 
                    self.can_merge_activities(activity, candidate, activity_list)):
                    valid_candidates.add(candidate)
            
            if valid_candidates:
                self.debug_print(f"Merging activities based on other relationships: {activity.name} with {', '.join([c.name for c in valid_candidates])}")
                additional_saved_activities = []
                for candidate in valid_candidates:
                    additional_saved_activities.extend(self.not_complete_merge(activity, candidate))
                if len(additional_saved_activities) > 0:
                    for activity_saved in additional_saved_activities:
                        second_pass_results.append(activity_saved)
                        self.debug_print(f"Saved activities based on other relationships: {activity_saved.name}")

                
                merged = self.merge_activities([activity] + list(valid_candidates))
                if merged:
                    self.debug_print(f"  Merged into: {merged.name}")
                    second_pass_results.append(merged)
                    visited_second_pass.update(valid_candidates)
                    visited_second_pass.add(activity)
                else:
                    second_pass_results.append(activity)
                    visited_second_pass.add(activity)
            else:
                second_pass_results.append(activity)
                visited_second_pass.add(activity)
        
        third_pass_results = []
        visited_third_pass = set()
        
        for activity in second_pass_results:
            if activity in visited_third_pass:
                continue
                
            # Skip activities that have parallel outputs
            other_candidates = self.find_merge_candidates(activity, activity_map)
            valid_candidates = set()
            
            for candidate in other_candidates:
                self.debug_print(f"check other candidate {candidate.name} for merge with: {activity.name}")
                if (candidate not in visited_third_pass):
                    if self.can_merge_activities(activity, candidate, activity_list):
                        valid_candidates.add(candidate)
                else:
                    self.debug_print(f"candidate {candidate.name} was already visited")

            
            if valid_candidates:
                self.debug_print(f"Merging activities based on other relationships: {activity.name} with {', '.join([c.name for c in valid_candidates])}")
                additional_saved_activities = []
                for candidate in other_candidates:
                    additional_saved_activities.extend(self.not_complete_merge(activity, candidate))
                if len(additional_saved_activities) > 0:
                    for activity_saved in additional_saved_activities:
                        third_pass_results.append(activity_saved)
                        self.debug_print(f"Saved activities based on other relationships: {activity_saved.name}")

                merged = self.merge_activities([activity] + list(valid_candidates))
                if merged:
                    self.debug_print(f"  Merged into: {merged.name}")
                    third_pass_results.append(merged)
                    visited_third_pass.update(valid_candidates)
                    visited_third_pass.add(activity)
                else:
                    third_pass_results.append(activity)
                    visited_third_pass.add(activity)
            else:
                third_pass_results.append(activity)
                visited_third_pass.add(activity)

        return third_pass_results
    
    def merge_activities(self, activities: List[ActivityType]) -> ActivityType:
        self.debug_print(f"Merging activities: {[activity.name for activity in activities]}")
        """
        Merges a list of activities into a single activity.
        """
        # TODO wenn merge, dann aktivität entfernen die gleichen fluss behandeln (Lieferschein und Rechnung Output, dann Lieferschein - Rechnung entfernen)
        if not activities:
            return None
            
        merged_activity = activities[0]
        
        # Combine all input and output object types
        all_inputs = set()
        all_outputs = set()
        all_instances = {}
        all_rules = []
        
        for activity in activities:
            all_inputs.update(activity.input_object_types)
            all_outputs.update(activity.output_object_types)
          
            for key, pis in activity.instanceList.items():
                for pi, values in pis.items():
                    if key in all_instances:
                        if pi in all_instances[key]:
                            for value in values:
                                if value in all_instances[key][pi] or value == None:
                                    continue
                                else:
                                    all_instances[key][pi].append(value)
                        else:
                            all_instances[key][pi] = values
                    else:
                        all_instances[key] = {pi: values}
 
            all_rules.extend(activity.rules)
        # Create new name for merged activity
        name = (tuple(set(self.mapping[x[0]] for x in all_inputs)), tuple(set(self.mapping[x[0]] for x in all_outputs)))
        merged_name = str(name).replace(",)", ")")

        self.debug_print(f"Merging activities into: {merged_name}")

        # Create new merged activity
        merged_activity.name = merged_name
        merged_activity.input_object_types.clear()
        merged_activity.output_object_types.clear()
        merged_activity.instanceList.clear()
        merged_activity.rules.clear()
        
        # Add combined elements
        for input_type in all_inputs:
            merged_activity.add_input_object_type(input_type)
        for output_type in all_outputs:
            merged_activity.add_output_object_type(output_type)
        merged_activity.add_instance(all_instances)
    
        for rule in all_rules:
            merged_activity.add_rule([rule])
        
        self.debug_print(f"Merged activity: {merged_activity.name}")
        return merged_activity

    def find_input_database_candidates(self, activity: ActivityType, activity_map: dict) -> tuple[set, set]:
        self.debug_print(f"Finding merge candidates for activity with database input: {activity.name}")
        """
        Finds suitable candidates for merging with the given activity.
        Requires ALL outputs to be parallel for merging.
        """
        database_input_output_candidates = set()

        # Get parallel pairs from footprint
        parallel_pairs = set((act1, act2) for act1, act2 in self.footprint.get('parallel', []))
        footprint_activities = {act for pair in parallel_pairs for act in pair}
        # First check for sequential output relationships
        for output_obj in activity.output_object_types:
            for related in activity_map[('output', output_obj)]:
                if related != activity:
                    if set(related.output_object_types) == set(activity.output_object_types):
                        if len(set(related.input_object_types)) == 1:
                            input_doc_type = f"{self.mapping[related.input_object_types[0][0]]}_{related.input_object_types[0][1]}"                            
                            if input_doc_type not in footprint_activities:
                                database_input_output_candidates.add(related)
                                self.debug_print(f"Added to other candidates (database input and same output): {activity.name} and {related.name}")
                        if len(set(activity.input_object_types)) == 1:
                            input_doc_type = f"{self.mapping[activity.input_object_types[0][0]]}_{activity.input_object_types[0][1]}"  
                            if input_doc_type not in footprint_activities:
                                database_input_output_candidates.add(related)
                                self.debug_print(f"Added to other candidates (database input and same output): {activity.name} and {related.name}")
        
        return database_input_output_candidates


    def find_input_merge_candidates(self, activity: ActivityType, activity_map: dict) -> tuple[set, set]:
        self.debug_print(f"Finding merge candidates for activity: {activity.name}")
        """
        Finds suitable candidates for merging with the given activity.
        Requires ALL outputs to be parallel for merging.
        """
        same_input_parallel_output_candidates = set()
        
        # Get parallel pairs from footprint
        parallel_pairs = set((act1, act2) for act1, act2 in self.footprint.get('parallel', []))
        
        # First find all activities with the exact same inputs
        same_input_activities = set()
        for input_obj in activity.input_object_types:
            for related in activity_map[('input', input_obj)]:
                if related != activity:
                    if set(related.input_object_types) == set(activity.input_object_types):
                        same_input_activities.add((input_obj, related))
                        self.debug_print(f"Found same input activity: {related.name}")           

        possible_pairs1= {}
        for rule, processinstances in activity.instanceList.items():
            for pi, value in processinstances.items():
                if pi[1] not in possible_pairs1:
                    possible_pairs1[pi[1]] = [pi[2]]
                else: 
                    possible_pairs1[pi[1]].append(pi[2])
                if pi[2] not in possible_pairs1:
                    possible_pairs1[pi[2]] = [pi[1]]
                else: 
                    possible_pairs1[pi[2]].append(pi[1])
                            
        

        # Among same-input activities, check for parallel outputs
        if same_input_activities:
            parallel_output = 0.0
            for (input, related) in same_input_activities:
                                
                possible_pairs2 = {}
                for rule, processinstances in related.instanceList.items():
                    for pi, value in processinstances.items():
                        if pi[1] not in possible_pairs2:
                            possible_pairs2[pi[1]] = [pi[2]]
                        else: 
                            possible_pairs2[pi[1]].append(pi[2])
                        if pi[2] not in possible_pairs2:
                            possible_pairs2[pi[2]] = [pi[1]]
                        else: 
                            possible_pairs2[pi[2]].append(pi[1])

                if input in possible_pairs1:
                    output1_set = set(possible_pairs1[input])
                if input in possible_pairs2:
                    output2_set = set(possible_pairs2[input])

                # Check if any output from activity and related are in parallel relationship
                for output1 in activity.output_object_types:                              
                    if output1 in output1_set:
                        output1_doc_type = f"{self.mapping[output1[0]]}_{output1[1]}"
                    else:
                        self.debug_print(f"Outputs {output1} not related to {input}")
                        continue

                    for output2 in related.output_object_types:
                        if output2 in output2_set:
                            output2_doc_type = f"{self.mapping[output2[0]]}_{output2[1]}"                            
                            if not ((output1_doc_type, output2_doc_type) in parallel_pairs or 
                                (output2_doc_type, output1_doc_type) in parallel_pairs):

                                self.debug_print(f"Outputs {output1_doc_type} and {output2_doc_type} are not parallel")
                                parallel_output -= 1
                            else:
                                parallel_output += 1
                            
                        else:
                            self.debug_print(f"Outputs {output2} not related to {input}")
                            
                if parallel_output > 0:
                    same_input_parallel_output_candidates.add(related)
                    self.debug_print(f"Added to same input parallel output candidates: {related.name}")
       
        return same_input_parallel_output_candidates  

    def find_merge_candidates(self, activity: ActivityType, activity_map: dict) -> tuple[set, set]:
        self.debug_print(f"Finding merge candidates for activity: {activity.name}")
        """
        Finds suitable candidates for merging with the given activity.
        Requires ALL outputs to be parallel for merging.
        """
        other_candidates = set()

        # First check for sequential output relationships
        for output_obj in activity.output_object_types:
            for related in activity_map[('output', output_obj)]:
                if related != activity:
                    if self.can_merge_objects(output_obj, output_obj, activity, related, 'output'):
                        other_candidates.add(related)
                        self.debug_print(f"Added to other candidates (can merge objects): {related.name}")
        for input_obj in activity.input_object_types:
            for related in activity_map[('input', input_obj)]:
                if related != activity:
                    if self.can_merge_objects(input_obj, input_obj, activity, related, 'input'):
                        other_candidates.add(related)
                        self.debug_print(f"Found same input activity: {related.name}, added to other candidates.")

        return other_candidates
    
    def merge_identical_activities(self, activity_list: List[ActivityType]) -> List[ActivityType]:
        self.debug_print("Merging identical activities")
        """
        Merges activities that have exactly the same input and output object types,
        with additional validation.
        """
        merged_activities = []
        groups = {}
        
        for activity in activity_list:
            signature = (
                tuple(sorted(input[0] for input in activity.input_object_types)),
                tuple(sorted(output[0] for output in activity.output_object_types))
            )
            
            if signature in groups:
                if self.are_objects_used_uniquely(activity, groups[signature], activity_list, 'input') and self.are_objects_used_uniquely(activity, groups[signature], activity_list, 'output'):
                    self.debug_print("Merging identical activities because of objects used uniquely")

                    groups[signature].append(activity)
                # Validate before adding to group
                else:
                    groups[signature].append(activity)
                    self.debug_print(f"Check Deleting identical activities because of objects not used uniquely: {activity.name}")
                    activities = self.delete_identical_activitie(groups[signature], activity_list)

                    del groups[signature]
                    groups[signature] = activities

                    
            else:
                groups[signature] = [activity]
        
        # Merge activities in each valid group
        for activities in groups.values():
            if len(activities) == 1:
                merged_activities.append(activities[0])
            else:
                merged = self.merge_activities(activities)
                if merged:
                    merged_activities.append(merged)
                    
        return merged_activities

    def are_objects_used_uniquely(self, activity1: ActivityType, list, activity_list, object_type) -> bool:
        self.debug_print(f"Checking if objects from {activity1.name} are used uniquely")
        """
        Checks if the given objects are used uniquely and not shared with other activities.
        
        Args:
            obj1, obj2: Objects to check
            activity1, activity2: Activities containing these objects
        """
        # Collect all activities that use these objects
        activities_using_obj1 = set()
        activities_using_obj2 = set()
        if object_type == 'output':
            for activity in activity_list:
                if activity == activity1 or activity in list:
                    continue
                for obj in activity1.output_object_types:    
                    if obj in activity.output_object_types:
                        self.debug_print(f"objects {obj} are used in {activity.name} as output")
                        activities_using_obj1.add(activity)
        elif object_type == 'input':
            for activity in activity_list:
                if activity == activity1 or activity in list:
                    continue 
                for obj in activity1.input_object_types:                    
                    if obj in activity.input_object_types:
                        self.debug_print(f"objects {obj} are used in {activity.name} as input")
                        activities_using_obj1.add(activity)
        
        # Objects should not be used by other activities
        return len(activities_using_obj1) == 0 and len(activities_using_obj2) == 0

    def has_temporal_contradictions(self, activity1: ActivityType, activity2: ActivityType) -> bool:
        self.debug_print(f"Checking for temporal contradictions between activities: {activity1.name} and {activity2.name}")
        """
        Checks if there are temporal contradictions between the activities based on object traces.
        Returns True if contradictions found.
        """
        possible_pairs1 = {}
        possible_pairs2 = {}

        for rule, processinstances in activity1.instanceList.items():
            for pi, value in processinstances.items():
                if pi[1] not in possible_pairs1:
                    possible_pairs1[pi[1]] = [pi[2]]
                else: 
                    possible_pairs1[pi[1]].append(pi[2])
                if pi[2] not in possible_pairs1:
                    possible_pairs1[pi[2]] = [pi[1]]
                else: 
                    possible_pairs1[pi[2]].append(pi[1])

        for rule, processinstances in activity2.instanceList.items():
            for pi, value in processinstances.items():
                if pi[1] not in possible_pairs2:
                    possible_pairs2[pi[1]] = [pi[2]]
                else: 
                    possible_pairs2[pi[1]].append(pi[2])
                if pi[2] not in possible_pairs2:
                    possible_pairs2[pi[2]] = [pi[1]]
                else: 
                    possible_pairs2[pi[2]].append(pi[1])

    
        # Collect all input-output relationships that need to be checked
        relationships_to_check = []
        for input_obj in activity1.input_object_types:
            for output_obj in activity1.output_object_types:
                if output_obj in possible_pairs1[input_obj]:
                    relationships_to_check.append((input_obj, output_obj))

        for input_obj in activity2.input_object_types:
            for output_obj in activity2.output_object_types:
                if output_obj in possible_pairs2[input_obj]:
                    relationships_to_check.append((input_obj, output_obj))
        
        # Check each relationship against object traces
        for trace in self.object_traces:
            events = [(event[DEFAULT_NAME_KEY], event[DEFAULT_TIMESTAMP_KEY]) 
                    for event in trace]
            
            # Create timestamp lookup for each object type
            timestamps = defaultdict(list)
            for obj_type, timestamp in events:
                timestamps[obj_type].append(timestamp)
            
            # Check each relationship
            for input_obj, output_obj in relationships_to_check:
                input = f"{self.mapping[input_obj[0]]}_{input_obj[1]}"
                output = f"{self.mapping[output_obj[0]]}_{output_obj[1]}"
                input_timestamps = timestamps.get(input, [])
                output_timestamps = timestamps.get(output, [])
                
                # Check for temporal violations
                temporal_violations = []
                for input_ts in input_timestamps:
                    for output_ts in output_timestamps:
                        if input_ts > output_ts:  # Input happens after output
                            self.debug_print(f"Temporal violation: {input_obj}({input_ts}) -> {output_obj}({output_ts})")
                            temporal_violations.append(True)
                        else:
                            temporal_violations.append(False)
                if True in temporal_violations and not False in temporal_violations:
                    return True              
        return False
    
    def delete_identical_activitie(self, activity_list_identical, activity_list: List[ActivityType]) -> bool:
        self.debug_print(f"Validating if identical activities can be merged: {activity_list_identical}")
        newlist = activity_list_identical
        # wenn output variante und wo anders in einer aktivität ebenfalls verwendet dann nicht. dann eher varianten aktivität löschen
        visited_out = set()
        same_output_activities = []
        for activity in activity_list:
            if activity not in visited_out:                
                visited_out.add(activity)
                for related in activity_list_identical:
                    if related not in visited_out and related != activity:
                        visited_out.add(related)
                        if set(t[0] for t in  related.output_object_types) & set(t[0] for t in  activity.output_object_types):
                            types_in1 = set(t[0] for t in activity.output_object_types)
                            types_out1 = set(t[0] for t in activity.output_object_types)
                            types_in2 = set(t[0] for t in related.output_object_types)
                            types_out2 = set(t[0] for t in related.output_object_types)
                            types_in = types_in1 & types_in2
                            types_out = types_out1 & types_out2
                            if (self.used_same_docs2(activity, related, types_in)>0.7 and self.used_same_docs2(activity, related, types_out)>0.7):
                                self.debug_print(f"Found same input activity: {related.name} and {activity.name} with same used docs")
                                added=False
                                for type in types_in:
                                    if(self.dataframe.loc[self.dataframe['cluster'] == type, 'process_instance_independent'].any()):
                                        #related.add_output_object_type(type)
                                        #activity.add_output_object_type(type)
                                        added = True
                                    else:
                                        added = False
                                if not added:
                                    self.debug_print(f"Delete: {related.name}")
                                    newlist.remove(related)

                            else: 
                                newlist = activity_list_identical
        return newlist

    def not_complete_merge(self, activity1: ActivityType, activity2: ActivityType):
        self.debug_print(f"Validating if activities can completly be merged: {activity1.name} and {activity2.name}")
        
        # Check if activities belong to only different process instances (alternatives)
        instances1 = set()
        instances2 = set()
        aditional_activity = []
        for rule_type, keys in activity1.instanceList.items():
            for process_id in keys:
                instances1.add(process_id[0])
        
        for rule_type, keys in activity2.instanceList.items():
            for process_id in keys:
                instances2.add(process_id[0])
        
         # Calculate instance overlap ratio
        overlap = len(instances1.intersection(instances2))
        total = len(instances1.union(instances2))
        overlap_ratio = overlap / total if total > 0 else 0        
        
        if overlap_ratio < 0.9:
            self.debug_print(f"Sufficient process instance overlap: {overlap_ratio:.2f}, but additional activity needed")
            common_instances = instances1.intersection(instances2)
            if len(instances1 - instances2) > 0:
                for instance in common_instances:
                    if instance in activity1.instanceList:
                        del activity1.instanceList[instance]
                        aditional_activity.append(activity1)
                self.debug_print(f"Instances1 without instances2 is greater than 0")
            if len(instances2 - instances1) > 0:
                for instance in common_instances:
                    if instance in activity2.instanceList:
                        del activity2.instanceList[instance]
                        aditional_activity.append(activity2)
                self.debug_print(f"Instances1 without instances2 is greater than 0")

        return aditional_activity

    def can_merge_activities(self, activity1: ActivityType, activity2: ActivityType, activity_list: List[ActivityType]) -> bool:
        self.debug_print(f"Validating if activities can be merged: {activity1.name} and {activity2.name}")
        """
        Validates if two activities can be merged by checking:
        1. No contradicting relationships in other activities
        2. No temporal contradictions in object traces
        3. Activities do not belong to only different process instances (alternatives)
        
        Args:
            activity1, activity2: Activities to validate for merging
            activity_list: List of all activities to check for contradictions
        """
        # Check for contradicting relationships
        if self.has_contradicting_relations(activity1, activity2, activity_list):
            self.debug_print(f"Found contradicting relations between activities: {activity1.name} and {activity2.name}")
            return False
        
        # Check if activities belong to only different process instances (alternatives)
        instances1 = set()
        instances2 = set()
        instances1id = set()
        instances2id = set()
        
        for rule_type, keys in activity1.instanceList.items():
            for process_id in keys:
                instances1id.add(process_id[0])                
                instances1.add(process_id)

        
        for rule_type, keys in activity2.instanceList.items():
            for process_id in keys:
                instances2id.add(process_id[0])
                instances2.add(process_id)

        
        if instances1id.isdisjoint(instances2id):
            self.debug_print(f"Activities {activity1.name} and {activity2.name} are alternatives with different process instances")
            return False
        
         # Calculate instance overlap ratio
        overlap = len(instances1id.intersection(instances2id))
        total = len(instances1id.union(instances2id))
        overlap_ratio = overlap / total if total > 0 else 0

        overlap2 = len(instances1.intersection(instances2))
        total2 = len(instances1.union(instances2))
        overlap_ratio2 = overlap2 / total2 if total2 > 0 else 0

        aditional_activity = None
        # Only merge if there's significant overlap (at least 60%)
        if overlap_ratio < 0.8:
            self.debug_print(f"Insufficient process instance overlap: {overlap_ratio:.2f}")
            return False
        
        


        # Check for temporal contradictions
        if self.has_temporal_contradictions(activity1, activity2):
            self.debug_print(f"Found temporal contradictions between activities: {activity1.name} and {activity2.name}")
            return False
        
        # Check for compatible docs
        if self.have_not_compatible_docs(activity1, activity2):
            self.debug_print(f"Found not compatible docs between activities: {activity1.name} and {activity2.name}")
            return False
                
        return True
    
    def have_not_compatible_docs(self, activity1: ActivityType, activity2: ActivityType) -> bool:
        """
        Checks document compatibility with stricter criteria
        """
        used_instances_objecttype_input1 = defaultdict(set)
        used_instances_objecttype_output1 = defaultdict(set)
        used_instances_objecttype_input2 = defaultdict(set)
        used_instances_objecttype_output2 = defaultdict(set)
        # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
        for activity, docs_in, docs_out in [(activity1, used_instances_objecttype_input1, used_instances_objecttype_output1), 
                                        (activity2, used_instances_objecttype_input2, used_instances_objecttype_output2)]:
            for rule, processinstances in activity.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.input_object_types):
                            docs_in[self.dataframe.at[docid1, 'cluster']].add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.input_object_types):
                            docs_in[self.dataframe.at[docid2, 'cluster']].add(docid2)
                            
                        if self.dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.output_object_types):
                            docs_out[self.dataframe.at[docid1, 'cluster']].add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.output_object_types):
                            docs_out[self.dataframe.at[docid2, 'cluster']].add(docid2)
            
            # Usage:
            overlap_in = self.calculate_overlap_score(used_instances_objecttype_input1, used_instances_objecttype_input2)
            overlap_out = self.calculate_overlap_score(used_instances_objecttype_output1, used_instances_objecttype_output2) 

            if overlap_in < 0.8 or overlap_out < 0.8:
                return True
            return False
      
    def calculate_overlap_score(self, dict1, dict2):
        self.debug_print("Calculating overlap score")
        total_overlap_score = 0
        total_pairs = 0
        
        for key in set(dict1.keys()) | set(dict2.keys()):
            set1 = dict1.get(key, set())
            set2 = dict2.get(key, set())
            
            if not set1 or not set2:
                continue

            overlap = len(set1 & set2)
            total = len(set1 | set2)
            
            self.debug_print(f"Key: {key}, Overlap: {overlap}, Total: {total}")
            
            if total > 0:
                total_overlap_score += overlap / total
                total_pairs += 1
        
        overlap_score = total_overlap_score / total_pairs if total_pairs > 0 else 1

        self.debug_print(f"Total overlap score: {overlap_score}")
        return overlap_score

    def can_merge_objects(self, obj1, obj2, activity1: ActivityType, activity2: ActivityType, obj_type: str) -> bool:
        self.debug_print(f"Checking if objects {obj1} from {activity1.name} and {obj2} from {activity2.name} can be merged")
        """
        Determines if two objects can be merged based on footprint relationships.
        """
        sequence_pairs = set((act1, act2) for act1, act2 in self.footprint['sequence'])
        parallel_pairs = set((act1, act2) for act1, act2 in self.footprint.get('parallel', []))
        possible_pairs1= {}
        possible_pairs2 = {}

        for rule, processinstances in activity1.instanceList.items():
            for pi, value in processinstances.items():
                if pi[1] not in possible_pairs1:
                    possible_pairs1[pi[1]] = [pi[2]]
                else: 
                    possible_pairs1[pi[1]].append(pi[2])
                if pi[2] not in possible_pairs1:
                    possible_pairs1[pi[2]] = [pi[1]]
                else: 
                    possible_pairs1[pi[2]].append(pi[1])

        for rule, processinstances in activity2.instanceList.items():
            for pi, value in processinstances.items():
                if pi[1] not in possible_pairs2:
                    possible_pairs2[pi[1]] = [pi[2]]
                else: 
                    possible_pairs2[pi[1]].append(pi[2])
                if pi[2] not in possible_pairs2:
                    possible_pairs2[pi[2]] = [pi[1]]
                else: 
                    possible_pairs2[pi[2]].append(pi[1])

            
        # For objects in footprint
        doc_type1 = f"{self.mapping[obj1[0]]}_{obj1[1]}"                            
        doc_type2 = f"{self.mapping[obj2[0]]}_{obj2[1]}"                            
        # First check for parallel relationship
        if obj_type == 'input':
            sequence_or_parallel = 0.0
            for output in activity1.output_object_types:
                if output in possible_pairs1:
                        input1 = set(possible_pairs1[output])
                for output2 in activity2.output_object_types:                    
                    if output2 in possible_pairs2:
                        input2 = set(possible_pairs2[output2])
                    if input1 & input2:
                        # For objects in footprint
                        doc_type1 = f"{self.mapping[output[0]]}_{output[1]}"                            
                        doc_type2 = f"{self.mapping[output2[0]]}_{output2[1]}"
                        if not ((doc_type1, doc_type2) in parallel_pairs or (doc_type2, doc_type1) in parallel_pairs \
                                or (doc_type1, doc_type2) in sequence_pairs or (doc_type2, doc_type1) in sequence_pairs):
                            self.debug_print(f"Checked that output objects {output} and {output2} not parallel or sequentiel")
                            sequence_or_parallel -=1
                        else:
                            sequence_or_parallel += 1

        elif obj_type == 'output':
            sequence_or_parallel = True
            for output in activity1.input_object_types:
                if output in possible_pairs1:
                        input1 = set(possible_pairs1[output])
                for output2 in activity2.input_object_types:                    
                        if output2 in possible_pairs2:
                            input2 = set(possible_pairs2[output2])
                        if input1 & input2:
                            # For objects in footprint
                            doc_type1 = f"{self.mapping[output[0]]}_{output[1]}"                            
                            doc_type2 = f"{self.mapping[output2[0]]}_{output2[1]}"
                            if not ((doc_type1, doc_type2) in parallel_pairs or (doc_type2, doc_type1) in parallel_pairs \
                                    or (doc_type1, doc_type2) in sequence_pairs or (doc_type2, doc_type1) in sequence_pairs):
                                self.debug_print(f"Checked that input objects {output} and {output2} not parallel or sequentiel")
                                sequence_or_parallel -= 1
                            else:
                                sequence_or_parallel += 1                     
            # return self.are_objects_used_uniquely(obj1, obj2, activity1, activity2, obj_type)
        if sequence_or_parallel > 0:
            self.debug_print(f"Checked that input objects {activity1.name} and {activity2.name} have parallel or sequentiel objects (Faktor: {sequence_or_parallel})")
            
        return sequence_or_parallel>0
    
    def has_contradicting_relations(self, activity1: ActivityType, activity2: ActivityType, 
                                activity_list: List[ActivityType]) -> bool:
        self.debug_print(f"Checking for contradicting relations between activities: {activity1.name} and {activity2.name}")
        """
        Checks if there are contradicting relationships between the activities.
        Returns True if contradictions found.
        """
        # Collect all input-output relationships from both activities

        proposed_relationships = set()
        for activity in [activity1, activity2]:
            for input_obj in activity.input_object_types:
                for output_obj in activity.output_object_types:
                    proposed_relationships.add((input_obj, output_obj))
        
        # Check for reverse relationships in other activities
        for activity in activity_list:
            if activity == activity1 or activity == activity2:
                continue
            
            # Look for direct reverse relationships
            for input_obj in activity.input_object_types:
                for output_obj in activity.output_object_types:
                    current_rel = (input_obj, output_obj)
                    # Check if this creates a contradiction with any proposed relationship
                    for prop_input, prop_output in proposed_relationships:
                        if output_obj == prop_input and input_obj == prop_output:
                            contracting = False
                            if self.contradicting_relations_with_same_docs(activity1, activity): 
                                self.debug_print(f"Found contradicting relationship without compatible docs: {activity1.name} and {activity.name}")
                                contracting = True
                            if self.contradicting_relations_with_same_docs(activity2, activity):
                                self.debug_print(f"Found contradicting relationship without compatible docs: {activity1.name} and {activity.name}")
                                contracting = True    

                            return contracting
        return False

    def contradicting_relations_with_same_docs(self, activity1: ActivityType, activity2: ActivityType) -> bool:
        self.debug_print(f"Checking for contradicting relations with same docs between activities: {activity1.name} and {activity2.name}")
        used_instances_objecttype_input1 = defaultdict(set)
        used_instances_objecttype_output1 = defaultdict(set)
        used_instances_objecttype_input2 = defaultdict(set)
        used_instances_objecttype_output2 = defaultdict(set)
        # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
        for activity, docs_in, docs_out in [(activity1, used_instances_objecttype_input1, used_instances_objecttype_output1), 
                                        (activity2, used_instances_objecttype_input2, used_instances_objecttype_output2)]:
            for rule, processinstances in activity.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.input_object_types):
                            docs_in[self.dataframe.at[docid1, 'cluster']].add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.input_object_types):
                            docs_in[self.dataframe.at[docid2, 'cluster']].add(docid2)
                            
                        if self.dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.output_object_types):
                            docs_out[self.dataframe.at[docid1, 'cluster']].add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.output_object_types):
                            docs_out[self.dataframe.at[docid2, 'cluster']].add(docid2)
            
            # Usage:
            overlap_in = self.calculate_overlap_score(used_instances_objecttype_input1, used_instances_objecttype_output2)
            overlap_out = self.calculate_overlap_score(used_instances_objecttype_output1, used_instances_objecttype_input2 ) 

            if overlap_in > 0.6 or overlap_out > 0.6:
                return True
            return False
        
    def have_compatible_rules(self, activity1: ActivityType, activity2: ActivityType) -> bool:
        self.debug_print(f"Checking if activities have compatible rules: {activity1.name} and {activity2.name}")
        """
        Checks if two activities have compatible rules that suggest they should be merged.
        """
        if not hasattr(activity1, 'rules') or not hasattr(activity2, 'rules'):
            return False
            
        # Extract rule types and keys
        rules1 = set((rule_type, tuple(sorted(keys))) for rule_type, keys in activity1.rules)
        rules2 = set((rule_type, tuple(sorted(keys))) for rule_type, keys in activity2.rules)
        
        # Check for rule overlap
        shared_rules = rules1 & rules2
        
        # TODO manche shared rules ok, aber auch neue attribute oder andere instanzen
        # If there are shared rules, activities might be complementary parts of the same process
        # if shared_rules:
        #     return True
            
        # If rules operate on the same attributes but in different ways, might be complementary
        attrs1 = {key for _, keys in activity1.rules for key in keys}
        attrs2 = {key for _, keys in activity2.rules for key in keys}
        if attrs1 & attrs2 and not shared_rules:
            return True
            
        return False

    def optimize_activity_types(self, content_based_AT):
        self.debug_print("Optimizing activity types")
        dataframe = self.dataframe  # Use the class attribute
        """
        Optimiert Aktivitätstypen basierend auf generischen Prozessmustern:
        1. Referenzdaten -> Hauptprozess
        2. Sequenzielle Hauptprozessschritte
        3. Parallele und optionale Prozessschritte
        """
        startdocs = set()
        enddocs = set()
        enddocs_types = set()

        def identify_process_layers():
            """Identifiziert Prozessschichten basierend auf Dokumenteigenschaften"""
            layers = {
                'reference': set(),  # Referenzdaten (prozessinstanzunabhängig)
                'main': set(),      # Hauptprozess
                'exception': set()    # exception/optionale Prozesse
            }
            
            # Klassifiziere Dokumenttypen basierend auf Eigenschaften
            for doc_type in dataframe['cluster'].unique():
                mask = dataframe['cluster'] == doc_type
                if dataframe[mask]['process_instance_independent'].any():
                    self.debug_print(f"Reference data: {doc_type}")
                    layers['reference'].add(doc_type)
                else:
                    # Prüfe Verwendungshäufigkeit und Timing
                    doc_count = len(dataframe[mask])
                    total_instances = len(dataframe['process_instances'].explode().unique())
                    usage_ratio = doc_count / total_instances
                    
                    if usage_ratio > 0.8:  # Häufig verwendet -> Hauptprozess
                        layers['main'].add(doc_type)
                    else:  # Seltener verwendet -> exception/Optional
                        layers['exception'].add(doc_type)
            
            return layers

        def build_sequence_graph():
            """Erstellt einen Graphen der typischen Dokumentsequenzen"""
            G = nx.DiGraph()
            
            # Expandiere die case_ids und erstelle Sequenzen pro Prozessinstanz
            df_proc = dataframe[~dataframe['process_instance_independent']].copy()
            
            # Erstelle eine explodierte Version des DataFrames mit einzelnen case_ids
            df_exploded = df_proc.assign(
                case_id=df_proc['process_instances'].apply(lambda x: x if isinstance(x, list) else [])
            ).explode('case_id')
            
            # Sortiere nach case_id und Timestamp
            df_exploded = df_exploded.sort_values(['case_id', 'final_timestamp'])

            for case_id, group in df_exploded.groupby('case_id'):
                prev_type = None
                startdocs.add(group.index[0])
                lastdoc = group.index[-1]  # Index der ersten Zeile in der Gruppe
                enddocs.add(group.index[-1])              
                enddocs_types.add((group.at[lastdoc, 'cluster'], group.at[lastdoc, 'variantID'])) #
                # Erstelle Kanten basierend auf der Sequenz
                for idx, row in group.iterrows():
                    clusterid1 = row['cluster']
                    variant1 = row['variantID']
                    curr_type = (clusterid1, variant1)
                    if prev_type is not None:
                        if not G.has_edge(prev_type, curr_type):
                            G.add_edge(prev_type, curr_type, weight=0)
                        G[prev_type][curr_type]['weight'] += 1
                    prev_type = curr_type
            
            return G
        
        def calculate_temporal_proximity(activity):
            temporal_scores = []
            doc_pairs = []
            for tuplekey, values in activity.instanceList.items():
                for pi, value in values.items():
                    for _, _, _, _, _, _, (id1, id2) in value:
                        doc_pairs.append((id1, id2)) 
                                            
                # Calculate time diff for each pair
                for doc1_id, doc2_id in doc_pairs:
                    doc1 = self.dataframe.loc[doc1_id]
                    doc2 = self.dataframe.loc[doc2_id]
                    
                    if (not doc1['process_instance_independent'] and not doc2['process_instance_independent'] 
                        and pd.notna(doc1['final_timestamp']) and pd.notna(doc2['final_timestamp'])):
                        
                        # Time diff for this pair
                        pair_time_diff = abs((doc1['final_timestamp'] - doc2['final_timestamp']).total_seconds())
                        
                        # Get process instance duration
                        instance_docs = self.dataframe[
                            (~self.dataframe['process_instance_independent']) & 
                            (self.dataframe['process_instances'].apply(lambda x: pi[0] in x if isinstance(x, list) else False))
                        ]
                        instance_timestamps = instance_docs['final_timestamp'].dropna()
                        
                        if not instance_timestamps.empty:
                            total_time_diff = (instance_timestamps.max() - instance_timestamps.min()).total_seconds()
                            if total_time_diff > 0:
                                temporal_scores.append(np.exp(-pair_time_diff / total_time_diff))
            
            return np.mean(temporal_scores) if temporal_scores else 0.0

        def calculate_activity_score(activity, layers, sequence_graph, node_distances, attr_weights):
            score = activity.individualScore
            input_types = activity.input_object_types 
            output_types = activity.output_object_types

            avg_distance = sum(node_distances.values()) / len(node_distances) if node_distances else 0
            position_bonus = sum(self.early_position_bonus if node_distances.get(t[0], avg_distance) < avg_distance 
                                else self.late_position_penalty for t in input_types + output_types)
            score += position_bonus

            if any(t[0] in layers['reference'] for t in input_types):
                ref_score = sum(self.reference_weight / (node_distances.get(out_type) + 1 if out_type in node_distances else 1.0) 
                                for out_type in output_types)
                score += ref_score * self.reference_position_factor

            for in_type in input_types:
                for out_type in output_types:
                    if sequence_graph.has_edge(in_type, out_type):
                        freq = sequence_graph[in_type][out_type]['weight']
                        score += freq * self.sequence_weight

                    input_doc_type = f"{self.mapping[in_type[0]]}_{in_type[1]}"
                    output_doc_type = f"{self.mapping[out_type[0]]}_{out_type[1]}"
                    if (input_doc_type, output_doc_type) in self.footprint['parallel'] or (output_doc_type, input_doc_type) in self.footprint['parallel']:
                        self.debug_print(f"Reducing score for activity {activity.name} due to parallel relationship between {input_doc_type} and {output_doc_type}")
                        score -= 3.0* self.parallel_object_penalty 

            if activity.rules:
                attr_scores = [attr_weights.get(key, 1.0) for _, keys in activity.rules for key in keys]
                score += (sum(attr_scores) / len(attr_scores)) * self.attribute_weight

            if set(t[0] for t in activity.input_object_types) == set(t[0] for t in activity.output_object_types):
                score += self.loop_weight #TODO Schleifen wunsch faktor


            temporal_proximity = calculate_temporal_proximity(activity)
            score += temporal_proximity * self.temporal_weight

            variant_count = sum(1 for t in input_types + output_types if t[1] < 1)
            score += variant_count * self.variant_weight
            return score

        def get_attribute_weights():
            """Berechnet Attributgewichte basierend auf Verwendungshäufigkeit"""
            weights = defaultdict(float)            
            for activity in content_based_AT:
                for rule_type, keys in activity.rules:
                    if rule_type == RuleType.SAME_KEY_VALUE_PAIR:
                        weights[keys[0]] += 1
                    elif rule_type == RuleType.SAME_VALUE:
                        for key in keys:
                            weights[key] += 1
            
            # Normalisiere Gewichte
            max_weight = max(weights.values()) if weights else 1
            return {k: (1-v/max_weight) for k, v in weights.items()}

        def optimize_paths():
            """Optimiert die Aktivitätspfade"""
            layers = identify_process_layers()
            sequence_graph = build_sequence_graph()
            attr_weights = get_attribute_weights()
                # Berechne für jeden Knoten die minimale Pfadlänge vom Start
            node_distances = {}
            start_nodes = {node for node in sequence_graph.nodes() 
                        if sequence_graph.in_degree(node) == 0}
            for node in sequence_graph.nodes():
                min_distance = float('inf')
                for start in start_nodes:
                    try:
                        dist = nx.shortest_path_length(sequence_graph, start, node)
                        min_distance = min(min_distance, dist)
                    except nx.NetworkXNoPath:
                        continue
                node_distances[node] = min_distance if min_distance != float('inf') else 0

            # Bewerte und sortiere Aktivitäten
            scored_activities = []
            for activity in content_based_AT:
                score = calculate_activity_score(
                    activity, layers, sequence_graph, node_distances, attr_weights
                )
                #has_independent = any(t in layers['reference'] for t in activity.input_object_types)
                scored_activities.append((
                    #has_independent,
                    score,
                    activity.name,  # Für stabile Sortierung
                    activity
                ))

            for i, (score1, id, activity1) in enumerate(scored_activities):
                for score2, id, activity2 in scored_activities:
                    if activity1 == activity2:
                        continue
                    if set(t[0] for t in activity1.input_object_types) == set(t[0] for t in activity2.input_object_types) and set(t[0] for t in activity1.output_object_types) == set(t[0] for t in activity2.output_object_types):
                        for output_type in activity1.output_object_types:
                            for other_output_type in activity2.output_object_types:
                                for input_type in activity1.input_object_types:
                                    for other_input_type in activity2.input_object_types:
                                        if output_type[0] == other_output_type[0] and output_type[1] != other_output_type[1] \
                                                and input_type[0] == other_input_type[0] and input_type[1] != other_input_type[1]:
                                            score1 += 2
                                            scored_activities[i] = (score1, id, activity1)
                                        elif output_type[0] == other_output_type[0] and other_output_type[1] < output_type[1] \
                                                and input_type[0] == other_input_type[0] and other_input_type[1] == input_type[1]:
                                            score1 -= score2*2
                                            scored_activities[i] = (score1, id, activity1)
                                            self.debug_print(f"Reduced score for activity {activity1.name} due to existing activity type with same input/output type but different output variant {output_type}")                        
                                        elif output_type[0] == other_output_type[0] and other_output_type[1] == output_type[1] \
                                                and input_type[0] == other_input_type[0] and other_input_type[1] > input_type[1]:
                                            score1 += score2/2
                                            scored_activities[i] = (score1, id, activity1)
                                            self.debug_print(f"Added score for activity {activity1.name} due to existing activity type with same input/output type but different input variant {input_type}")


            # Optimiere Pfade
            optimized = []
            covered_paths = set()
            covered_objects = set()

            covered_attributes_in = defaultdict(set)
            covered_attributs_all = set()
            independent_objects_used = set()  # Tracking für verwendete unabhängige Objekte
            # Erste Runde: Füge Aktivitäten mit unabhängigen Objekten hinzu
            remaining_activities = []
            covered_instances_objecttype_input = defaultdict(set)
            covered_instances_objecttype_output = defaultdict(set)
            second_activities = []

            # Sortiere nach has_independent (True zuerst), dann base_score, dann temporal_score
            scored_activities.sort(key=lambda x: x[0], reverse=True)

            self.scored_content_AT = scored_activities
            for score, _, activity in scored_activities:
                self.debug_print(f"Aktivitätstyp: {activity.name} Bewertung: {score}")
            
            self.debug_print(f"end object: {enddocs}")
           
            for score, _, activity in scored_activities:
                if score < self.min_score: # TODO Limt Faktors

                    break
                add_activity=False

                path = (frozenset(activity.input_object_types), 
                    frozenset(activity.output_object_types))
                independent_inputs = {obj for obj in activity.input_object_types 
                            if obj[0] in layers['reference']}
                new_objects = set()
                new_objects.update(
                    ('input', obj) for obj in activity.input_object_types
                    if ('input', obj) not in covered_objects
                    )
                new_objects.update(
                    ('output', obj) for obj in activity.output_object_types
                    if ('output', obj) not in covered_objects
                    )
                end_object = set()
                end_object = set(enddocs_types) & set(activity.input_object_types)

                # Prüfe ob der Pfad neue Attribute überträgt
                new_attributes = set()
                new_attributs_all = set()
                input_set = set((input[0] for input in activity.input_object_types))
                output_set = set((output[0] for output in activity.output_object_types))
                if input_set != output_set:
                    for rule_type, keys in activity.rules: 
                        if rule_type in [RuleType.SAME_KEY_VALUE_PAIR, RuleType.SAME_VALUE]:                        
                            if (keys[0] not in covered_attributs_all and keys[1] not in covered_attributs_all):
                                new_attributs_all.update(
                                    key for key in keys 
                                    if key not in covered_attributs_all
                                )  
                            # Prüfe für jedes Output-Objekt, ob es das Attribut schon hat
                            for output_obj in activity.output_object_types:
                                if (keys[0] not in covered_attributes_in[output_obj] and keys[1] not in covered_attributes_in[output_obj]):
                                    new_attributes.update(
                                        key for key in keys 
                                        if key not in covered_attributes_in[output_obj]
                                    )                
                
                new_covered_instances_objecttype_input = defaultdict(set)
                new_covered_instances_objecttype_output = defaultdict(set)
                # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
                for rule, processinstances in activity.instanceList.items():
                    for pi, value in processinstances.items():
                        for (_, _, _, _, _, _, (docid1, docid2)) in value:
                            if dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.input_object_types):
                                if end_object:
                                    if docid1 in enddocs and end_object in new_objects:
                                        self.debug_print(f"Remove new objects found (objects: {end_object}) because it is an endobject")
                                        new_objects.remove(end_object)
                                if not docid1 in covered_instances_objecttype_input[dataframe.at[docid1, 'cluster']] and docid1 not in enddocs:
                                    new_covered_instances_objecttype_input[dataframe.at[docid1, 'cluster']].add(docid1)
                               
                            if dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.input_object_types):
                                if docid2 in enddocs and end_object in new_objects:
                                    self.debug_print(f"Remove new objects found (objects: {end_object}) because it is an endobject")
                                    new_objects.remove(end_object)
                                if not docid2 in covered_instances_objecttype_input[dataframe.at[docid2, 'cluster']] and docid2 not in enddocs:
                                    new_covered_instances_objecttype_input[dataframe.at[docid2, 'cluster']].add(docid2)
                                
                            if dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.output_object_types):
                                if not docid1 in covered_instances_objecttype_output[dataframe.at[docid1, 'cluster']]:
                                    new_covered_instances_objecttype_output[dataframe.at[docid1, 'cluster']].add(docid1)
                                
                            if dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.output_object_types):
                                if not docid2 in covered_instances_objecttype_output[dataframe.at[docid2, 'cluster']]:
                                    new_covered_instances_objecttype_output[dataframe.at[docid2, 'cluster']].add(docid2)

                if independent_inputs and (new_objects or new_attributes): 
                    if independent_inputs & independent_objects_used:
                        remaining_activities.append((
                            #has_independent,
                            score,
                            activity.name,  # Für stabile Sortierung
                            activity
                        ))
                    else:
                        self.debug_print(f"Independent objects not used yet, add activity in first pass: {activity.name}")
                        independent_objects_used.update(independent_inputs)    
                        add_activity=True
                elif new_objects:
                    self.debug_print(f"New objects found (objects: {new_objects}) for activity in first pass: {activity.name}")
                    add_activity=True

                elif (new_attributes and self.each_attribute_by_object) or (new_attributs_all and not self.each_attribute_by_object):
                    self.debug_print(f"New attributes found (attributs: {new_attributes}) for activity in first pass: {activity.name}")
                    add_activity=True
                
                # elif new_covered_instances_objecttype_output or new_covered_instances_objecttype_input:
                #     self.debug_print(f"New docs found for activity: {activity.name}")
                #     add_activity=True
                
                else:
                    self.debug_print(f"Attributs and Objects already used: {activity.name}")
                    # 4. Variantenbewertung der docs
                    for output_type in activity.output_object_types:
                        if output_type[1] > 0:
                            score += 1.0
                    for input_typ in activity.input_object_types:
                        if input_typ[1] > 0:
                            score += 1.0

                    second_activities.append((
                        #has_independent,
                        score,
                        activity.name,  # Für stabile Sortierung
                        activity
                    ))

                if add_activity:
                    optimized.append(activity)
                    for key, values in new_covered_instances_objecttype_input.items():
                        covered_instances_objecttype_input[key].update(values)
                    for key, values in new_covered_instances_objecttype_output.items():
                        covered_instances_objecttype_output[key].update(values)              
                    covered_paths.add(path)
                    covered_objects.update(new_objects)
                    covered_attributs_all.update(new_attributs_all)
                    # Aktualisiere für jedes Output-Objekt seine empfangenen Attribute
                    for output_obj in activity.output_object_types:
                        covered_attributes_in[output_obj].update(new_attributes)
                    
                
            # Sortiere nach has_independent (True zuerst), dann base_score, dann temporal_score
            remaining_activities.sort(key=lambda x: x[0], reverse=True)
            # Zweite Runde: Füge verbleibende Aktivitäten hinzu
            for score, _, activity in remaining_activities:
                if score < self.min_score:
                    break
                add_activity= False
                path = (frozenset(activity.input_object_types), 
                    frozenset(activity.output_object_types))
                
                new_attributes = set()
                new_attributs_all = set()
                input_set = set((input[0] for input in activity.input_object_types))
                output_set = set((output[0] for output in activity.output_object_types))
                if input_set != output_set:
                    for rule_type, keys in activity.rules:
                        if rule_type in [RuleType.SAME_KEY_VALUE_PAIR, RuleType.SAME_VALUE]:
                            if (keys[0] not in covered_attributs_all and keys[1] not in covered_attributs_all):
                                new_attributs_all.update(
                                    key for key in keys 
                                    if key not in covered_attributs_all
                                ) 
                            # Prüfe für jedes Output-Objekt, ob es das Attribut schon hat
                            for output_obj in activity.output_object_types:
                                if (keys[0] not in covered_attributes_in[output_obj] and keys[1] not in covered_attributes_in[output_obj]):
                                    new_attributes.update(
                                        key for key in keys 
                                        if key not in covered_attributes_in[output_obj]
                                    )
                new_objects = set()
                new_objects.update(
                    ('input', obj) for obj in activity.input_object_types
                    if ('input', obj) not in covered_objects
                    )
                end_object = set()
                end_object = set(enddocs_types) & set(activity.input_object_types)
                new_objects.update(
                    ('output', obj) for obj in activity.output_object_types
                    if ('output', obj) not in covered_objects
                    )
                
                new_covered_instances_objecttype_input = defaultdict(set)
                new_covered_instances_objecttype_output = defaultdict(set)
                # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
                for rule, processinstances in activity.instanceList.items():
                    for pi, value in processinstances.items():
                        for (_, _, _, _, _, _, (docid1, docid2)) in value:
                            if dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.input_object_types):
                                if end_object:
                                    if docid1 in enddocs and end_object in new_objects:
                                        self.debug_print(f"Remove new objects found (objects: {end_object}) because it is an endobject")
                                        new_objects.remove(end_object)
                                if not docid1 in covered_instances_objecttype_input[dataframe.at[docid1, 'cluster']] and docid1 not in enddocs:
                                    new_covered_instances_objecttype_input[dataframe.at[docid1, 'cluster']].add(docid1)
                               
                            if dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.input_object_types):
                                if end_object:
                                    if docid2 in enddocs and end_object in new_objects:
                                        self.debug_print(f"Remove new objects found (objects: {end_object}) because it is an endobject")
                                        new_objects.remove(end_object)
                                if not docid2 in covered_instances_objecttype_input[dataframe.at[docid2, 'cluster']] and docid2 not in enddocs:
                                    new_covered_instances_objecttype_input[dataframe.at[docid2, 'cluster']].add(docid2)
                                
                            if dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.output_object_types):
                                if not docid1 in covered_instances_objecttype_output[dataframe.at[docid1, 'cluster']]:
                                    new_covered_instances_objecttype_output[dataframe.at[docid1, 'cluster']].add(docid1)
                                
                            if dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.output_object_types):
                                if not docid2 in covered_instances_objecttype_output[dataframe.at[docid2, 'cluster']]:
                                    new_covered_instances_objecttype_output[dataframe.at[docid2, 'cluster']].add(docid2)

                if (new_attributes and self.each_attribute_by_object) or (new_attributs_all and not self.each_attribute_by_object):
                    self.debug_print(f"New attributes found (attributs: {new_attributes}) for activity in second pass: {activity.name}")
                    add_activity=True
                
                if add_activity:
                    optimized.append(activity)
                    for key, values in new_covered_instances_objecttype_input.items():
                        covered_instances_objecttype_input[key].update(values)
                    for key, values in new_covered_instances_objecttype_output.items():
                        covered_instances_objecttype_output[key].update(values)                                     
                    covered_paths.add(path)
                    covered_objects.update(new_objects)
                    covered_attributs_all.update(new_attributs_all)

                    # Aktualisiere für jedes Output-Objekt seine empfangenen Attribute
                    for output_obj in activity.output_object_types:
                        covered_attributes_in[output_obj].update(new_attributes)
           
            newsecond_activities = []
            for score, _, activity in second_activities:
                reduce_score = False

                for optimized_activity in optimized:
                    for input_obj in activity.input_object_types:
                        for opt_input in optimized_activity.input_object_types:
                            if input_obj[0] == opt_input[0] and input_obj[1] != opt_input[1]:
                                reduce_score = True
                    for output_obj in activity.output_object_types:
                        for opt_output in optimized_activity.output_object_types:
                            if output_obj[0] == opt_output[0] and output_obj[1] != opt_output[1]:
                                reduce_score = True
                
                if reduce_score:
                    self.debug_print(f"Reduced score for activity {activity.name} due to existing activity type with same input / output type but different variant")
                    score -= 1.0

                newsecond_activities.append((
                    score,
                    activity.name,  # Für stabile Sortierung
                    activity
                ))
                    
            newsecond_activities.sort(key=lambda x: x[0], reverse=True)
            for score, _, activity in newsecond_activities:
                if score < self.min_score:
                    break
                path = (frozenset(activity.input_object_types), 
                    frozenset(activity.output_object_types))
                add_second_activity=False
                
                new_attributes = set()
                new_attributs_all = set()   
                input_set = set((input[0] for input in activity.input_object_types))
                output_set = set((output[0] for output in activity.output_object_types))
                if input_set != output_set:
                    for rule_type, keys in activity.rules:
                        if rule_type in [RuleType.SAME_KEY_VALUE_PAIR, RuleType.SAME_VALUE]:
                            if (keys[0] not in covered_attributs_all and keys[1] not in covered_attributs_all):
                                new_attributs_all.update(
                                    key for key in keys 
                                    if key not in covered_attributs_all
                                ) 
                            # Prüfe für jedes Output-Objekt, ob es das Attribut schon hat
                            for output_obj in activity.output_object_types:
                                if (keys[0] not in covered_attributes_in[output_obj] and keys[1] not in covered_attributes_in[output_obj]):
                                    new_attributes.update(
                                        key for key in keys 
                                        if key not in covered_attributes_in[output_obj]
                                    )
                new_covered_instances_objecttype_input = defaultdict(set)
                new_covered_instances_objecttype_output = defaultdict(set)
                inputs = set()
                outputs = set()
                # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
                for rule, processinstances in activity.instanceList.items():
                    for pi, value in processinstances.items():
                        for (_, _, _, _, _, _, (docid1, docid2)) in value:
                            if dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.input_object_types):
                                inputs.add(docid1)
                                if not docid1 in covered_instances_objecttype_input[dataframe.at[docid1, 'cluster']]:
                                    new_covered_instances_objecttype_input[dataframe.at[docid1, 'cluster']].add(docid1)
                               
                            if dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.input_object_types):
                                inputs.add(docid2)
                                if not docid2 in covered_instances_objecttype_input[dataframe.at[docid2, 'cluster']]:
                                    new_covered_instances_objecttype_input[dataframe.at[docid2, 'cluster']].add(docid2)
                                
                            if dataframe.at[docid1, 'cluster'] in (t[0] for t in activity.output_object_types):
                                outputs.add(docid1)
                                if not docid1 in covered_instances_objecttype_output[dataframe.at[docid1, 'cluster']]:
                                    new_covered_instances_objecttype_output[dataframe.at[docid1, 'cluster']].add(docid1)
                                
                            if dataframe.at[docid2, 'cluster'] in (t[0] for t in activity.output_object_types):
                                outputs.add(docid2)
                                if not docid2 in covered_instances_objecttype_output[dataframe.at[docid2, 'cluster']]:
                                    new_covered_instances_objecttype_output[dataframe.at[docid2, 'cluster']].add(docid2)

                if (new_attributes and self.each_attribute_by_object) or (new_attributs_all and not self.each_attribute_by_object):
                    self.debug_print(f"New attributes found for activity in third pass: {activity.name}")
                    add_second_activity=True
                
                elif new_covered_instances_objecttype_output:
                    self.debug_print(f"New docs found for activity in third pass: {activity.name}")
                    self.debug_print(f"New output docs found for activity: {new_covered_instances_objecttype_output} (old: {covered_instances_objecttype_output})")
                    self.debug_print(f"New input docs found for activity: {new_covered_instances_objecttype_input} (old: {covered_instances_objecttype_input})")
                    self.debug_print(f"Start docs: {startdocs} and end docs: {enddocs}")
                    if inputs.isdisjoint(enddocs) and outputs.isdisjoint(startdocs):
                        add_second_activity=True
                    else:
                        self.debug_print(f"Found new docs for start or end docs for activity in third pass: {activity.name}")
                
                if add_second_activity:
                    optimized.append(activity)
                    for key, values in new_covered_instances_objecttype_input.items():
                        covered_instances_objecttype_input[key].update(values)
                    for key, values in new_covered_instances_objecttype_output.items():
                        covered_instances_objecttype_output[key].update(values)
                    self.debug_print(f"Added activity: {activity.name} to optimized list")
                    covered_paths.add(path)
                    covered_objects.update(new_objects)
                    covered_attributs_all.update(new_attributs_all)

                    # Aktualisiere für jedes Output-Objekt seine empfangenen Attribute
                    for output_obj in activity.output_object_types:
                        covered_attributes_in[output_obj].update(new_attributes)

                    

            # TODO vergleichen von den regeln von unterschiedlichen Aktivitäten, nur wenn gleiche Instanzen und Dokumente
            for activity in optimized:
                keys_to_delete_activity = []

                for other_activity in optimized:
                    if activity == other_activity:
                        continue
                    if set(activity.input_object_types).isdisjoint(set(other_activity.input_object_types)) and set(activity.output_object_types).isdisjoint(set(other_activity.output_object_types)):
                        #self.debug_print(f"Found no overlapping objects: {activity.name} and {other_activity.name}")
                        continue
                    keys_to_delete_other = []
                    #self.debug_print(f"Found overlapping objects: {activity.name} and {other_activity.name}")
                    
                    # wenn sie nicht die gleichen docs verwenden, dann kann man sie nicht löschen
                    if self.have_not_compatible_docs(activity, other_activity):
                        #self.debug_print(f"Found no overlapping docs : {activity.name} and {other_activity.name}")
                        continue

                    for (rule_type, keys), processIDs in list(activity.instanceList.items()):   
                        deleted = False
                        for (other_rule_type, other_keys), other_processIDs in other_activity.instanceList.items():
                            if deleted:
                                break
                            if other_keys != keys and (keys[0] in other_keys or keys[1] in other_keys) \
                                and (rule_type == RuleType.SAME_VALUE or rule_type == RuleType.SAME_COMMON_VALUE or rule_type == RuleType.SAME_KEY_VALUE_PAIR) \
                                    and (other_rule_type == RuleType.SAME_VALUE or other_rule_type == RuleType.SAME_COMMON_VALUE or other_rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                                
                                if len(processIDs)*0.8 > len(other_processIDs):
                                    self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {other_activity.name} because of {rule_type} with keys {keys} for {activity.name}")
                                    keys_to_delete_other.append((other_rule_type, other_keys, other_processIDs))
                                elif len(processIDs) < len(other_processIDs)*0.8:
                                    self.debug_print(f"Removing less significant rule by same used attributs {rule_type} with keys {keys} for {activity.name} because of {other_rule_type} with keys {other_keys} for {other_activity.name}")
                                    keys_to_delete_activity.append((rule_type, keys, processIDs))
                                    deleted = True
                                    break
                                else: 
                                    if (other_rule_type != RuleType.SAME_KEY_VALUE_PAIR and rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                                        self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {other_activity.name} because of {rule_type} with keys {keys} for {activity.name}")
                                        keys_to_delete_other.append((other_rule_type, other_keys, other_processIDs))
                                    elif (rule_type != RuleType.SAME_KEY_VALUE_PAIR and other_rule_type == RuleType.SAME_KEY_VALUE_PAIR):
                                        self.debug_print(f"Removing less significant rule by same used attributs {rule_type} with keys {keys} for {activity.name} because of {rule_type} with keys {keys} for {activity.name}")
                                        keys_to_delete_activity.append((rule_type, keys, processIDs))
                                        deleted = True
                                        break
                                    elif (rule_type != RuleType.SAME_VALUE and other_rule_type == RuleType.SAME_VALUE):
                                        self.debug_print(f"Removing less significant rule by same used attributs {rule_type} with keys {keys} for {activity.name} because of {other_rule_type} with keys {other_keys} for {other_activity.name}")
                                        keys_to_delete_activity.append((rule_type, keys, processIDs))
                                        deleted = True
                                        break
                                    elif (other_rule_type != RuleType.SAME_VALUE and rule_type == RuleType.SAME_VALUE):
                                        self.debug_print(f"Removing less significant rule by same used attributs {other_rule_type} with keys {other_keys} for {other_activity.name} because of {rule_type} with keys {keys} for {activity.name}")
                                        keys_to_delete_other.append((other_rule_type, other_keys, other_processIDs))
                                        self.debug_print(f"Marked for deletion: rule {other_rule_type} with keys {other_keys} for {other_activity.name} because of {rule_type} with keys {keys} for {activity.name}")
                      
                    for del_rule_type, del_keys, del_processIDs in keys_to_delete_other:
                        self.debug_print(f"Deleting rule {del_rule_type} with keys {del_keys} for {other_activity.name}")
                        if (del_rule_type, del_keys) in other_activity.instanceList.items():
                            del other_activity.instanceList[(del_rule_type, del_keys)]
                        if (del_rule_type, del_keys) in other_activity.rules:
                            other_activity.rules.remove((del_rule_type, del_keys))

                for del_rule_type, del_keys, del_processIDs in keys_to_delete_activity:
                    self.debug_print(f"Deleting rule {del_rule_type} with keys {del_keys} for {activity.name}")
                    if (del_rule_type, del_keys) in activity.instanceList.items():
                        del activity.instanceList[(del_rule_type, del_keys)]
                    if (del_rule_type, del_keys) in activity.rules:
                        activity.rules.remove((del_rule_type, del_keys))
                    

            new_optimized = []
            for activity in optimized:    
                if len(activity.rules) > 0:
                    new_optimized.append(activity)

            return new_optimized

        return optimize_paths()

    def optimize_merged_activity_types(self, activity_list):
        self.debug_print(f"optimize aggregated AT")
        merged_activities = []
        activity_map = defaultdict(list)
        visited_in = set()
        visited_out = set()

        # Map activities by both their inputs and outputs
        for activity in activity_list:
            for input_obj in activity.input_object_types:
                activity_map[('input', input_obj[0])].append(activity)
            for output_obj in activity.output_object_types:
                activity_map[('output', output_obj[0])].append(activity)
        
        same_input_activities = set()
        same_output_activities = set()
        for activity in activity_list:
            if activity not in visited_in:                
                visited_in.add(activity)
                for input_obj in activity.input_object_types:
                    for related in activity_map[('input', input_obj[0])]:
                        if related not in visited_in and related != activity:                            
                            visited_in.add(activity)
                            if related != activity:
                                if set(related.input_object_types) & set(activity.input_object_types):
                                    types = set(related.input_object_types) & set(activity.input_object_types)
                                    if self.used_same_docs(activity, related, types):
                                        self.debug_print(f"Found same input activity: {related.name} and {activity.name} with same used docs")
                                        added=False
                                        for type in types:
                                            if(self.dataframe.loc[self.dataframe['cluster'] == type[0], 'process_instance_independent'].any()):
                                                #related.add_output_object_type(type)
                                                #activity.add_output_object_type(type)
                                                added = True
                                            else:
                                                added = False
                                        if not added:
                                            same_input_activities.add((activity,related))

            if activity not in visited_out:                
                visited_out.add(activity)
                for related in activity_map[('output', input_obj[0])]:
                    if related not in visited_out:                        
                        visited_out.add(activity)
                        if related != activity:
                            if set(related.output_object_types) & set(activity.output_object_types):
                                types = set(related.output_object_types) & set(activity.output_object_types)
                                if self.used_same_docs(activity, related, types):
                                    self.debug_print(f"Found same input activity: {related.name} and {activity.name} with same used docs")
                                    added=False
                                    for type in types:
                                        if(self.dataframe.loc[self.dataframe['cluster'] == type[0], 'process_instance_independent'].any()):
                                            #related.add_output_object_type(type)
                                            #activity.add_output_object_type(type)
                                            added = True
                                        else:
                                            added = False
                                    if not added:
                                        same_output_activities.add((activity,related))

        if same_input_activities or same_output_activities:
            merged_activities = self.update_both(activity_list, same_input_activities, same_output_activities)    
        else:
            return activity_list
        return merged_activities
    
    def update_both(self, activity_list, same_input_activities, same_output_activities):
        visited_in = []
        visited_out = []
        activiyadded = []
        outputobjects = []
        merged_activities = []
        for (activity1, activity2) in same_input_activities:
            if activity1 and activity2 in visited_in:
                continue
            elif activity1 in visited_in:
                merged_activities.append(activity1)
                continue
            elif activity2 in visited_in:
                merged_activities.append(activity1)
                continue
            visited_in.append(activity1)
            visited_in.append(activity2)    
            for input_obj in activity1.input_object_types:
                if input_obj in activity2.input_object_types:
                    # TODO nach Score vorgehen
                    if len(activity1.input_object_types) > len(activity2.input_object_types):
                        if len(activity2.input_object_types) > 1:
                            activity2.input_object_types.remove(input_obj)
                            nameold = activity2.name
                            name_new = (tuple(self.mapping[x[0]] for x in activity2.input_object_types), tuple(self.mapping[x[0]] for x in activity2.output_object_types))
                            activity2.name = name_new                           
                            merged_activities.append(activity2)
                        else:
                            outputobjects.append((activity2, self.used_docs_out(activity2)))
                        merged_activities.append(activity1)

                        #self.debug_print(f"Removed input object type {input_obj} from old activity {nameold} activity {activity2.name}")
                    if len(activity1.input_object_types) < len(activity2.input_object_types):
                        if len(activity1.input_object_types) > 1:
                            activity1.input_object_types.remove(input_obj)
                            nameold = activity1.name
                            name_new = (tuple(self.mapping[x[0]] for x in activity1.input_object_types), tuple(self.mapping[x[0]] for x in activity1.output_object_types))
                            activity1.name = name_new
                            merged_activities.append(activity1)
                        else:
                            outputobjects.append((activity1, self.used_docs_out(activity1)))
                        merged_activities.append(activity2)
                        #self.debug_print(f"Removed input object type {input_obj} from old activity {nameold} activity {activity2.name}")
        
        for (activity1, activity2) in same_output_activities:
            if activity1 and activity2 in visited_out:
                continue
            elif activity1 in visited_out:
                merged_activities.append(activity1)
                continue
            elif activity2 in visited_out:
                merged_activities.append(activity1)
                continue
            visited_out.append(activity1)
            visited_out.append(activity2)    
            for output in activity1.output_object_types:
                if output in activity2.output_object_types:
                    # TODO nach Score vorgehen
                    if len(activity1.output_object_types) < len(activity2.output_object_types):
                        if len(activity2.output_object_types) > 1:
                            activity2.output_object_types.remove(input_obj)
                            nameold = activity2.name
                            name_new = (tuple(self.mapping[x[0]] for x in activity2.input_object_types), tuple(self.mapping[x[0]] for x in activity2.output_object_types))
                            activity2.name = name_new                           
                            merged_activities.append(activity2)
                        else:
                            outputobjects.append((activity2, self.used_docs_out(activity2)))
                        merged_activities.append(activity1)

                        #self.debug_print(f"Removed input object type {input_obj} from old activity {nameold} activity {activity2.name}")
                    if len(activity1.output_object_types) > len(activity2.output_object_types):
                        if len(activity1.output_object_types) > 1:
                            activity1.output_object_types.remove(input_obj)
                            nameold = activity1.name
                            name_new = (tuple(self.mapping[x[0]] for x in activity1.input_object_types), tuple(self.mapping[x[0]] for x in activity1.output_object_types))
                            activity1.name = name_new
                            merged_activities.append(activity1)
                        else:
                            outputobjects.append((activity1, self.used_docs_out(activity1)))
                        merged_activities.append(activity2)


        useddocsall = defaultdict(set)

        for activity in merged_activities:
            if not any(activity in t for t in same_input_activities): 
                for output in activity.output_object_types:
                    for rule, processinstances in activity.instanceList.items():
                        for pi, value in processinstances.items():
                            for (_, _, _, _, _, _, (docid1, docid2)) in value:
                                if self.dataframe.at[docid1, 'cluster'] == output[0]:
                                    if output in useddocsall:
                                        useddocsall[output].add(docid1)
                                    else:
                                        useddocsall[output]=(docid1)   
                                if self.dataframe.at[docid2, 'cluster'] == output[0]:
                                    if output in useddocsall:
                                        useddocsall[output].add(docid2)
                                    else:
                                        useddocsall[output]=(docid2)   
        for activity in activity_list:
            if not any(activity in t for t in same_input_activities): 
                for output in activity.output_object_types:
                    for rule, processinstances in activity.instanceList.items():
                        for pi, value in processinstances.items():
                            for (_, _, _, _, _, _, (docid1, docid2)) in value:
                                if self.dataframe.at[docid1, 'cluster'] == output[0]:
                                    useddocsall[output].add(docid1)
                                if self.dataframe.at[docid2, 'cluster'] == output[0]:
                                    useddocsall[output].add(docid2)
                merged_activities.append(activity)

        for (activity, useddocs) in outputobjects:
            for type, docs in useddocs.items():
                if docs in useddocsall[type]:
                    self.debug_print(f"all outputs used")

                    continue
                else:
                    self.debug_print(f"add output object type for activity {activity.name}")
                    for activity2 in merged_activities:
                        if activity.input_object_types[0] in activity2.output_object_types:

                            self.debug_print(f"add output object type for activity {activity2.name} an {type}")

                            #merged_activities.remove(activity2)
                            #TODO instanzen un Regeln und co
                            activity2.add_output_object_type(type)
                            name_new2 = (tuple(self.mapping[activity.input_object_types[0][0]]), tuple(self.mapping[x[0]] for x in activity2.output_object_types))        
                            for score, _, activityscored in self.scored_content_AT:#
                                all_instances = {}
                                if name_new2==activityscored.name:
                                    for key, pis in activityscored.instanceList.items():
                                        for pi, values in pis.items():
                                            if key in all_instances:
                                                if pi in all_instances[key]:
                                                    all_instances[key][pi].append(values)
                                                else:
                                                    all_instances[key][pi] = values
                                            else:
                                                all_instances[key] = {pi: values}
                                    for key, pis in activity2.instanceList.items():
                                        for pi, values in pis.items():
                                            if key in all_instances:
                                                if pi in all_instances[key]:
                                                    all_instances[key][pi].append(values)
                                                else:
                                                    all_instances[key][pi] = values
                                            else:
                                                all_instances[key] = {pi: values}
            
                                    activity2.instanceList.clear()            
                                    activity2.add_instance(all_instances)

                                    activity2.add_rule(activityscored.rules)
                            name_new = (tuple(self.mapping[x[0]] for x in activity2.input_object_types), tuple(self.mapping[x[0]] for x in activity2.output_object_types))
                            activity2.name = name_new
                            self.debug_print(f"add output object type for activity {activity2.name} an {type}")
                            #merged_activities.append(activity2)                      

        return merged_activities

    def used_same_docs(self, activity1: ActivityType, activity2: ActivityType, types) -> bool:
        used_instances_objecttype_input1 = set()
        used_instances_objecttype_input2 = set()
        # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
        
        for type in types:
            for rule, processinstances in activity1.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] == type[0]:
                            used_instances_objecttype_input1.add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] == type[0]:
                            used_instances_objecttype_input1.add(docid2)
            for rule, processinstances in activity2.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] == type[0]:
                            used_instances_objecttype_input2.add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] == type[0]:
                            used_instances_objecttype_input2.add(docid2)
        overlap = len(used_instances_objecttype_input1 & used_instances_objecttype_input2)
        total = len(used_instances_objecttype_input1 | used_instances_objecttype_input2)
        
        total_overlap_score = 0
        if total > 0:
            total_overlap_score = overlap / total
    
        if total_overlap_score>0.8:
            return True
        return False
    
    def used_same_docs2(self, activity1: ActivityType, activity2: ActivityType, types) -> bool:
        used_instances_objecttype_input1 = set()
        used_instances_objecttype_input2 = set()
        # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
        for type in types:
            for rule, processinstances in activity1.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] == type:
                            used_instances_objecttype_input1.add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] == type:
                            used_instances_objecttype_input1.add(docid2)
            for rule, processinstances in activity2.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] == type:
                            used_instances_objecttype_input2.add(docid1)
                            
                        if self.dataframe.at[docid2, 'cluster'] == type:
                            used_instances_objecttype_input2.add(docid2)
        overlap = len(used_instances_objecttype_input1 & used_instances_objecttype_input2)
        total = len(used_instances_objecttype_input1 | used_instances_objecttype_input2)
        
        total_overlap_score = 0
        if total > 0:
            return overlap / total
    
        return 1
    
    def used_docs_out(self, activity1) -> bool:
        used_instances_objecttype_output = defaultdict(set)
        # Check for used docs (wenn schon eine aktivität existiert, die die gleichen docs als input/output verwenden will wie eine andere aktivität, dann nicht ergänzen. (input für input und ouput für ooutput überprüfen                    
        for output in activity1.output_object_types:       
            for rule, processinstances in activity1.instanceList.items():
                for pi, value in processinstances.items():
                    for (_, _, _, _, _, _, (docid1, docid2)) in value:
                        if self.dataframe.at[docid1, 'cluster'] == output[0]:                            
                            used_instances_objecttype_output[output].add(docid1)                        
                        if self.dataframe.at[docid2, 'cluster'] == output[0]:
                            used_instances_objecttype_output[output].add(docid2)
        self.debug_print(f"add output object type for activity {used_instances_objecttype_output}")
                
        return used_instances_objecttype_output
