import os, sys

from matplotlib import pyplot as plt

#'/home/user/example/parent/child'
current_path = os.path.abspath('.')

#'/home/user/example/parent'
parent_path = os.path.dirname(current_path)

sys.path.append(parent_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'child.settings')

from Model.ObjectModel.ObjectType import ObjectType
from Model.Activity.ActivityType import ActivityRelationType, ActivityType
from Model.PetriNet.Place import Place
from Model.PetriNet.Arc import Arc
from Model.PetriNet.Net import Net
from Model.PetriNet.Transition import Transition
from typing import List
import pandas as pd
import pm4py
from pm4py.objects.log.obj import EventLog, Trace, Event  # PM4Py classes for process mining and event logs
from pm4py.util.xes_constants import DEFAULT_NAME_KEY, DEFAULT_TIMESTAMP_KEY, DEFAULT_TRACEID_KEY  # Constants for event log attributes
from pm4py.algo.discovery.alpha import algorithm as alpha_miner  # Heuristic process discovery algorithm
from pm4py.algo.discovery.alpha.variants import plus as alpha_miner_plus
from pm4py.algo.discovery.heuristics import algorithm as heuristic_miner  # Heuristic process discovery algorithm
from pm4py.objects.conversion.process_tree import converter as pt_converter
from pm4py.objects.conversion.process_tree.variants import to_petri_net

from pm4py.algo.discovery.inductive import algorithm as inductiv_miner  # Heuristic process discovery algorithm
from pm4py.algo.discovery.footprints import algorithm as footprints_discovery
from pm4py.visualization.footprints import visualizer as fp_visualizer
from pm4py.objects.petri_net.obj import PetriNet, Marking
from pm4py.objects.petri_net.utils import petri_utils
# Hole den Dot-String aus dem GraphViz-Objekt
from PIL import Image
import io
from pm4py.visualization.petri_net import visualizer as vis_factory  # Visualization tools for Petri nets
from PIL import Image  # Python Imaging Library for image processing
from datetime import datetime  # Standard library for handling dates and times
from graphviz import Digraph
from View.PetriNetVisualizer import PetriNetVisualizer
from PyQt5.QtCore import pyqtSignal

# Constants for event log attributes
DEFAULT_NAME_KEY = 'concept:name'
DEFAULT_TIMESTAMP_KEY = 'time:timestamp'
DEFAULT_TRACEID_KEY = 'concept:case_id'
DEFAULT_START_TIMESTAMP_KEY = 'time:start'  # XES standard for start timestamp
DEFAULT_END_TIMESTAMP_KEY = 'time:end'      # XES standard for end timestamp
DEFAULT_DURATION_KEY = 'time:duration'      # XES standard for duration

class EventlogPNGenerator:
    def __init__(self, debug: bool = False, database_visualization: bool = False, log_signal: pyqtSignal = None):
        self.debug = debug
        self.visualizer = PetriNetVisualizer(database_visualization)
        self.log_signal = log_signal  # Add log_signal parameter

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(message)

    def create_event_log(self, dataframe: pd.DataFrame, time_based_AT) -> EventLog:
        """
        Erstellt ein EventLog aus dem DataFrame.
        """
        log = EventLog()
        traces = self.create_traces_from_df(dataframe, time_based_AT)
        
        # Sicherheitsprüfung
        if traces:
            for trace in traces:
                log.append(trace)
        else:
            print("Warnung: Keine Traces generiert")
        
        return log
    
    def convert_gviz_to_matplotlib(self, gviz) -> plt.Figure:
        """Konvertiert ein GraphViz-Objekt in eine matplotlib Figure"""
        
        # Rendere das GraphViz-Objekt als PNG
        png = gviz.pipe(format='png')
        
        # Konvertiere PNG zu Image
        img = Image.open(io.BytesIO(png))
        
        # Erstelle matplotlib Figure
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(img)
        ax.axis('off')  # Verstecke die Achsen
        
        return fig

    def generate_eventlog_petri_net(self, dataframe: pd.DataFrame, time_based_AT, content_based_AT) -> dict:
        """Generiert verschiedene Petri-Netz Visualisierungen"""
        mapping = dataframe.groupby('cluster')['doc_type'].agg(lambda x: x.value_counts().index[0]).to_dict()
        independents = dataframe[dataframe['process_instance_independent']]['doc_type'].tolist()
        figures = {}
        figures2 = {}

        # Without Object Order
        log2 = self.create_event_log_withoutObjectOrder(dataframe)
        net_without_order, initial_marking2, final_marking2 = alpha_miner.apply(log2)
        gviz = self.visualizer.visualize(net_without_order, True, initial_marking2, final_marking2)
        figures['Process Mining without Object Order-Relationship-AT-Merge'] = self.visualizer.convert_gviz_to_image(gviz)
        
        #log with merged AT
        log = self.create_event_log(dataframe, time_based_AT)
        self.print_event_log(log)

        # Footprints
        fp_log = footprints_discovery.apply(log, variant=footprints_discovery.Variants.ENTIRE_EVENT_LOG)
        gviz = fp_visualizer.apply(fp_log)
        figures['Footprint with Object Order-Relationship-AT-Merge'] = self.visualizer.convert_gviz_to_image(gviz)
        
        # Alpha Miner
        net_alpha, initial_marking, final_marking = alpha_miner.apply(log)
        gviz = self.visualizer.visualize(net_alpha, True, initial_marking, final_marking, filename="Alpha Miner")
        figures['Alpha Miner'] = self.visualizer.convert_gviz_to_image(gviz)

        # Alpha Plus Miner
        net_plus, initial_marking, final_marking = alpha_miner_plus.apply(log)
        gviz = self.visualizer.visualize(net_plus, True, initial_marking, final_marking, filename="Alpha Plus")
        figures['Alpha Plus'] = self.visualizer.convert_gviz_to_image(gviz)

        # Heuristic Miner
        net_heuristic, initial_marking, final_marking = heuristic_miner.apply(log)
        gviz = self.visualizer.visualize(net_heuristic, True, initial_marking, final_marking, filename="Heuristic")
        figures['Heuristic'] = self.visualizer.convert_gviz_to_image(gviz)

        # Inductive Miner
        process_tree  = inductiv_miner.apply(log)
        # Convert process tree to Petri net with parameters to preserve readable names
        parameters = {
            "format": "readable"  # Direct parameter instead of using Parameters enum
        }
        net_inductive, initial_marking, final_marking = pt_converter.apply(process_tree, 
                                                                        variant=pt_converter.Variants.TO_PETRI_NET, 
                                                                        parameters=parameters)
        gviz = self.visualizer.visualize(net_inductive, True, initial_marking, final_marking, filename="Inductive")
        figures['Inductive'] = self.visualizer.convert_gviz_to_image(gviz)

        # Time-based AT
        net_time, dec = self.create_pn_based_on_AT(time_based_AT, "Zeitbasierte AT", mapping, dataframe)
        gviz = self.visualizer.visualize(net_time, False, filename="Zeitbasierte AT")
        figures2['Zeitbasierte AT'] = self.visualizer.convert_gviz_to_image(gviz)

        # Content-based AT
        net_content, decorations = self.create_contend_pn_based_on_AT(content_based_AT, "Inhaltsbasierte AT", mapping, dataframe)
        gviz = self.visualizer.visualize(net_content, False, initial_marking=independents, filename="Inhaltsbasierte AT", independents=independents)
        figures2['Inhaltsbasierte AT'] = self.visualizer.convert_gviz_to_image(gviz)

        return figures, figures2, net_content

    def create_contend_pn_based_on_AT(self, time_based_AT, name, mapping, dataframe):
        # Create a new Petri net
        net2 = PetriNet(name)
        decorations = {}
        
        # Create a new Net object
        net = Net(name)
        
        # Create places based on time_based_AT
        places = []
        for activity in time_based_AT:
            inputset = set(input_type[0] for input_type in activity.input_object_types)
            outputset = set(output_type[0] for output_type in activity.output_object_types)
            for input_type in inputset:
                # if dataframe[dataframe['cluster'] == input_type]['process_instance_independent'].iloc[0] and all(input_type not in activity2.output_object_types for activity2 in time_based_AT):
                #     activity.add_output_object_type(input_type)
                place_name = f"{mapping[input_type]}"
                if place_name not in places:
                    places.append(place_name)
                    place = PetriNet.Place(place_name)
                    # Enhanced place decorations with adjusted size and styling
                    place_decoration = {
                        "label": place_name,  # Use truncated name for label
                        "width": 50,  # Fixed width since names are now shorter
                        "height": 40,
                        "style": "filled",
                        "fillcolor": "#E8E8E8"
                    }
                    decorations[place] = place_decoration
                    place.label = place_name  # Add label to place
                    net2.places.add(place)
                    
                    # Create and add Place object to Net
                    net_place = Place(place_name, place_name, {})
                    net.append_place(net_place)
                    
            for output_type in outputset:
                place_name = f"{mapping[output_type]}"
                if place_name not in places:
                    places.append(place_name)
                    place = PetriNet.Place(place_name)
                    # Enhanced place decorations with adjusted size and styling
                    place_decoration = {
                        "label": place_name,  # Use truncated name for label
                        "width": 50,  # Fixed width since names are now shorter
                        "height": 40,
                        "style": "filled",
                        "fillcolor": "#E8E8E8"
                    }
                    decorations[place] = place_decoration                    
                    place.label = place_name  # Add label to place
                    net2.places.add(place)
                    
                    # Create and add Place object to Net
                    net_place = Place(place_name, place_name, {})
                    net.append_place(net_place)

        # Create transitions and arcs based on time_based_AT
        transitions = []
        arcs = []
        for activity in time_based_AT:
            transition_name = ""
            for place in net2.places:
                if place.name == activity.name:
                    transition_name =   "T: "
                    break
            transition_name = transition_name + activity.name
            transitions.append(transition_name)
            transition = PetriNet.Transition(transition_name)
            transition.label = transition_name  # Add label to transition
            net2.transitions.add(transition)
            visited_input = []
            visited_output = []
            # Create and add Transition object to Net
            net_transition = Transition(transition_name, transition_name)
            net.append_transition(net_transition)
            inputset = set(input_type[0] for input_type in activity.input_object_types)
            outputset = set(output_type[0] for output_type in activity.output_object_types)

            for input_type in inputset:
                if input_type in visited_input:
                    continue
                place_name = f"{mapping[input_type]}"
                arcs.append((place_name, transition_name))
                for place in net2.places:
                    if place.name == place_name:
                        petri_utils.add_arc_from_to(place, transition, net2)
                        break
                
                # Create and add Arc object to Net
                net_arc = Arc(f"{place_name}_to_{transition_name}", f"{place_name} to {transition_name}", net.netPlaces[place_name], net_transition)
                net.append_arc(net_arc)
                visited_input.append(input_type)
            
            for output_type in outputset:
                if output_type in visited_output:
                    continue
                place_name = f"{mapping[output_type]}"
                arcs.append((transition_name, place_name))
                for place in net2.places:
                    if place.name == place_name:
                        petri_utils.add_arc_from_to(transition, place, net2)
                        break
                # Create and add Arc object to Net
                net_arc = Arc(f"{transition_name}_to_{place_name}", f"{transition_name} to {place_name}", net_transition, net.netPlaces[place_name])
                net.append_arc(net_arc)
                visited_output.append(output_type)

        # Ensure all place and transition names are strings
        for place in net2.places:
            place.name = str(place.name)
            decorations = {place: {"label": place.name}}
            place.label = place.name  # Ensure label is set
        for transition in net2.transitions:
            transition.name = str(transition.name)
            transition.label = transition.name  # Ensure label is set

        return net2, decorations #, net
    
    def create_pn_based_on_AT(self, time_based_AT, name, mapping, dataframe):
            # Create a new Petri net
            net2 = PetriNet(name)
            decorations = {}
            
            # Create a new Net object
            net = Net(name)
            
            # Create places based on time_based_AT
            places = []
            for activity in time_based_AT:
                # da doppelte einträge wenn mehrere varianten
                inputset = set(input_type[0] for input_type in activity.input_object_types)
                outputset = set(output_type[0] for output_type in activity.output_object_types)
               
                for input_type in inputset:
                    # if dataframe[dataframe['cluster'] == input_type]['process_instance_independent'].iloc[0] and all(input_type not in activity2.output_object_types for activity2 in time_based_AT):
                    #     activity.add_output_object_type(input_type)
                    place_name = f"{mapping[input_type]}"
                    if place_name not in places:
                        places.append(place_name)
                        place = PetriNet.Place(place_name)
                        # Enhanced place decorations with adjusted size and styling
                        place_decoration = {
                            "label": place_name,  # Use truncated name for label
                            "width": 50,  # Fixed width since names are now shorter
                            "height": 40,
                            "style": "filled",
                            "fillcolor": "#E8E8E8"
                        }
                        decorations[place] = place_decoration
                        place.label = place_name  # Add label to place
                        net2.places.add(place)
                        
                        # Create and add Place object to Net
                        net_place = Place(place_name, place_name, {})
                        net.append_place(net_place)
                        
                for output_type in outputset:
                    place_name = f"{mapping[output_type]}"
                    if place_name not in places:
                        places.append(place_name)
                        place = PetriNet.Place(place_name)
                        # Enhanced place decorations with adjusted size and styling
                        place_decoration = {
                            "label": place_name,  # Use truncated name for label
                            "width": 50,  # Fixed width since names are now shorter
                            "height": 40,
                            "style": "filled",
                            "fillcolor": "#E8E8E8"
                        }
                        decorations[place] = place_decoration                    
                        place.label = place_name  # Add label to place
                        net2.places.add(place)
                        
                        # Create and add Place object to Net
                        net_place = Place(place_name, place_name, {})
                        net.append_place(net_place)

            # Create transitions and arcs based on time_based_AT
            transitions = []
            arcs = []
            for activity in time_based_AT:
                transition_name = activity.name
                transitions.append(transition_name)
                transition = PetriNet.Transition(transition_name)
                transition.label = transition_name  # Add label to transition
                net2.transitions.add(transition)

                # da doppelte einträge wenn mehrere varianten
                inputset = set(input_type[0] for input_type in activity.input_object_types)
                outputset = set(output_type[0] for output_type in activity.output_object_types)
               
                
                # Create and add Transition object to Net
                net_transition = Transition(transition_name, transition_name)
                net.append_transition(net_transition)
            
                for input_type in inputset:
                    place_name = f"{mapping[input_type]}"
                    arcs.append((place_name, transition_name))
                    for place in net2.places:
                        if place.name == place_name:
                            petri_utils.add_arc_from_to(place, transition, net2)
                            break
                    
                    # Create and add Arc object to Net
                    net_arc = Arc(f"{place_name}_to_{transition_name}", f"{place_name} to {transition_name}", net.netPlaces[place_name], net_transition)
                    net.append_arc(net_arc)
                
                for output_type in outputset:
                    place_name = f"{mapping[output_type]}"
                    arcs.append((transition_name, place_name))
                    for place in net2.places:
                        if place.name == place_name:
                            petri_utils.add_arc_from_to(transition, place, net2)
                            break
                    # Create and add Arc object to Net
                    net_arc = Arc(f"{transition_name}_to_{place_name}", f"{transition_name} to {place_name}", net_transition, net.netPlaces[place_name])
                    net.append_arc(net_arc)

            # Ensure all place and transition names are strings
            for place in net2.places:
                place.name = str(place.name)
                decorations = {place: {"label": place.name}}
                place.label = place.name  # Ensure label is set
            for transition in net2.transitions:
                transition.name = str(transition.name)
                transition.label = transition.name  # Ensure label is set

            return net2, decorations #, net

    def create_event_log_withoutObjectOrder(self, dataframe: pd.DataFrame) -> EventLog:
            """
            Erstellt ein EventLog aus dem DataFrame.
            """
            log = EventLog()
            traces = self.create_traces_from_df_withoutObjectOrder(dataframe)
            
            # Sicherheitsprüfung
            if traces:
                for trace in traces:
                    log.append(trace)
            else:
                print("Warnung: Keine Traces generiert")
            
            return log
    
    def create_traces_from_df_withoutObjectOrder(self, df: pd.DataFrame) -> List[Trace]:
        self.debug_print(f"Starting trace creation with DataFrame of shape: {df.shape}")   
        
        df['case_ids'] = df['process_instances'].apply(lambda x: x if isinstance(x, list) else [])
        df_exploded = df.explode('case_ids')
        self.debug_print(f"After explode, DataFrame shape: {df_exploded.shape}")
        
        traces = []
        for case_id, case_docs in df_exploded.groupby('case_ids'):
            self.debug_print(f"\nProcessing case_id: {case_id}")
            self.debug_print(f"Number of documents in case: {len(case_docs)}")
            
            activities = case_docs[
                ~case_docs['process_instance_independent'] & 
                case_docs['final_timestamp'].notna()
            ]
            self.debug_print(f"After filtering, number of activities: {len(activities)}")
            
            activities_sorted = activities.sort_values('final_timestamp')
            self.debug_print(f"Sorted timestamps: {activities_sorted['final_timestamp'].tolist()}")
            
            trace = Trace()
            trace.attributes[DEFAULT_TRACEID_KEY] = case_id
            
            activities_list = list(activities_sorted.iterrows())
            self.debug_print(f"Number of activities to process: {len(activities_list)}")

            for i in range(len(activities_list) - 1):
                _, current_doc = activities_list[i]
                _, next_doc = activities_list[i + 1]
                
                event = Event()
                event[DEFAULT_NAME_KEY] = f"(('{current_doc['doc_type']}'),('{next_doc['doc_type']}'))"
                # Use the timestamp of the later document
                event[DEFAULT_TIMESTAMP_KEY] = next_doc['final_timestamp']
                
                trace.append(event)
            
            if len(trace) > 0:
                self.debug_print(f"Adding trace with {len(trace)} events")
                traces.append(trace)
            else:
                self.debug_print("No events in trace, skipping")

        self.debug_print(f"\nTotal traces created: {len(traces)}")
        return traces


    def create_traces_from_df(self, df: pd.DataFrame, time_based_AT) -> List[Trace]:
        self.debug_print(f"Starting trace creation with DataFrame of shape: {df.shape}")
        
        df['case_ids'] = df['process_instances'].apply(lambda x: x if isinstance(x, list) else [])
        df_exploded = df.explode('case_ids')
        self.debug_print(f"After explode, DataFrame shape: {df_exploded.shape}")
         # Create a set of valid cluster pairs from time_based_AT for faster lookup
        activity_transitions = {}
        activity_to_add = {}
        for activity in time_based_AT:
            possible_pairs1= set()
            for pi, timebased in activity.instanceList.items():
                pair = (pi[1], pi[2])
                if pair not in possible_pairs1:
                    possible_pairs1.add(pair)

            if activity.type == ActivityRelationType.AGGREGATED_TIME_BASED:
                activity_name = activity.name
                activity_transitions[activity_name] = {
                    'inputs': set(activity.input_object_types),
                    'outputs': set(activity.output_object_types),
                    'instances':set(activity.instanceList.keys()),
                    'possible_pairs': possible_pairs1
                }
           
            elif activity.type == ActivityRelationType.TIME_BASED:
                activity_to_add[activity.input_object_types[0], activity.output_object_types[0]] = set(activity.instanceList.keys())
                # for possible_pair in possible_pairs1:
                #     activity_to_add[possible_pair] = set(activity.instanceList.keys())
        
        traces = []

        for case_id, case_docs in df_exploded.groupby('case_ids'):
            savedTimestamps = {}
            aggregated_events = {}
            self.debug_print(f"\nProcessing case_id: {case_id}")
            self.debug_print(f"Number of documents in case: {len(case_docs)}")
            
            activities = case_docs[
                ~case_docs['process_instance_independent'] & 
                case_docs['final_timestamp'].notna()
            ] 

            activities_sorted = activities.sort_values('final_timestamp')
            self.debug_print(f"Sorted timestamps: {activities_sorted['final_timestamp'].tolist()}")
            
            trace = Trace()
            trace.attributes[DEFAULT_TRACEID_KEY] = case_id
            
            activities_list = list(activities_sorted.iterrows())
            self.debug_print(f"Number of activities to process: {len(activities_list)}")

            for i in range(len(activities_list) - 1):
                _, current_doc = activities_list[i]
                _, next_doc = activities_list[i + 1]
                
                current_cluster = current_doc['cluster']
                next_cluster = next_doc['cluster']
                variantid1 = current_doc['variantID']
                variantid2= next_doc['variantID']
                key1 = (current_cluster, variantid1)
                key2 = (next_cluster, variantid2)
                
                savedTimestamps[key1] = (current_doc['final_timestamp'], current_doc['doc_type'])
                savedTimestamps[key2] = (next_doc['final_timestamp'], next_doc['doc_type'])
             
            for activity_name, transition in activity_transitions.items():
                i = 0
                self.debug_print(f"Check {activity_name} in case {case_id}")

                for (caseidt, (c1, v1), (c2, v2)) in transition['instances']:
                    timestamp1 = None
                    timestamp2 = None
                    if caseidt != case_id and ((c1, v1), (c2, v2)) not in transition['possible_pairs'] :
                        self.debug_print(f"Not Creating event for {activity_name} in case {case_id} and pairs ({c1},{v1}) with ({c2},{v2})")
                        continue
                    if (c1, v1) in savedTimestamps:
                        if timestamp1 == None:
                            timestamp1 = savedTimestamps[(c1, v1)][0]
                        else:
                            if timestamp1 < savedTimestamps[(c1, v1)][0]:
                                timestamp1 = timestamp1 + (savedTimestamps[(c1, v1)] - timestamp1) / 2
                            else:
                                timestamp1= savedTimestamps[(c1, v1)][0] + (timestamp1 - savedTimestamps[(c1, v1)][0]) / 2
                    if (c2, v2) in savedTimestamps:
                        if timestamp2 == None:
                            timestamp2 = savedTimestamps[(c2, v2)][0]
                        else:
                            if timestamp2 < savedTimestamps[(c2, v2)][0]:
                                timestamp2 = timestamp2 + (savedTimestamps[(c2, v2)][0] - timestamp2) / 2
                            else:
                                timestamp2 = savedTimestamps[(c2, v2)][0] + (timestamp2 - savedTimestamps[(c2, v2)][0]) / 2

                    if timestamp1 != None and timestamp2 != None:
                        if not any(activity_name == key[0] for key in aggregated_events):
                            docs = set()
                            docs.add((c1, v1))
                            docs.add((c2, v2))
                            aggregated_events[(activity_name, i)] = (activity_name, timestamp1, timestamp2, docs)
                            self.debug_print(f"Creating new event for {activity_name} ({i}) in case {case_id} with docs {docs}")

                        else:
                            for key, value in aggregated_events.items():
                                eventname, i = key
                                activity_name2, timestamp1old, timestamp2old, docs = value
                                if eventname != activity_name:
                                    continue

                                if (c1,v1) in docs or (c2,v2) in docs:
                                    if (c1,v1) not in docs:
                                        docs.add((c1, v1))
                                    if (c2,v2) not in docs:
                                        docs.add((c2,v2))
                                    if timestamp1 < timestamp1old:
                                        timestamp1 = timestamp1 + (timestamp1old - timestamp1) / 2
                                    else:
                                        timestamp1= timestamp1old + (timestamp1 - timestamp1old) / 2
                                    if timestamp2 < timestamp2old:
                                        timestamp2 = timestamp2 + (timestamp2old - timestamp2) / 2
                                    else:
                                        timestamp2 = timestamp2old + (timestamp2 - timestamp2old) / 2

                                    aggregated_events[key] = (activity_name, timestamp1, timestamp2, docs)
                                    self.debug_print(f"Updated event for {activity_name} ({i}) in case {case_id} with docs {docs}")
                                    break
                                else:
                                    i += 1
                                    docs = set()
                                    docs.add((c1, v1))
                                    docs.add((c2, v2))
                                    aggregated_events[(activity_name, i)] = (activity_name, timestamp1, timestamp2, docs)                      
                                    self.debug_print(f"Creating an other event for {activity_name} ({i}) in case {case_id} with docs {docs}")
                                    break
                            


            for (keyin, keyout), ids in activity_to_add.items():
                doc_in = ""
                doc_out = ""
                for (caseidt, (c1, v1), (c2, v2)) in ids:
                    timestamp1 = None
                    timestamp2 = None
                    if caseidt != case_id:
                        continue
                    if (c1, v1) in savedTimestamps:
                        doc_in = savedTimestamps[(c1, v1)][1]
                        if timestamp1 == None:
                            timestamp1 = savedTimestamps[(c1, v1)][0]
                        else:
                            if timestamp1 < savedTimestamps[(c1, v1)][0]:
                                timestamp1 = timestamp1 + (savedTimestamps[(c1, v1)] - timestamp1) / 2
                            else:
                                timestamp1= savedTimestamps[(c1, v1)][0] + (timestamp1 - savedTimestamps[(c1, v1)][0]) / 2
                    if (c2, v2) in savedTimestamps:
                        doc_out = savedTimestamps[(c2, v2)][1]
                        if timestamp2 == None:
                            timestamp2 = savedTimestamps[(c2, v2)][0]
                        else:
                            if timestamp2 < savedTimestamps[(c2, v2)][0]:
                                timestamp2 = timestamp2 + (savedTimestamps[c2, v2][0] - timestamp2) / 2
                            else:
                                timestamp2 = savedTimestamps[(c2, v2)][0] + (timestamp2 - savedTimestamps[(c2, v2)]) / 2

                    if timestamp1 != None and timestamp2 != None:
                        activity_name = f"(('{doc_in}'), ('{doc_out}'))"

                        if (((c1, v1), (c2, v2))) in aggregated_events:                        
                            if timestamp1 < aggregated_events[((c1, v1), (c2, v2))][1]:
                                timestamp1 = timestamp1 + (aggregated_events[((c1, v1), (c2, v2))][1] - timestamp1) / 2
                            else:
                                timestamp1= aggregated_events[((c1, v1), (c2, v2))][1] + (timestamp1 - aggregated_events[((c1, v1), (c2, v2))][1]) / 2
                            if timestamp2 < aggregated_events[((c1, v1), (c2, v2))][2]:
                                timestamp2 = timestamp2 + (aggregated_events[(c1, v1), (c2, v2)][2] - timestamp2) / 2
                            else:
                                timestamp2 = aggregated_events[((c1, v1), (c2, v2))][2] + (timestamp2 - aggregated_events[((c1, v1), (c2, v2))][2]) / 2

                        # if timestamp1 < timestamp2:  # Only create event if timestamps are in correct order
                        aggregated_events[((c1, v1), (c2, v2))] = (activity_name, timestamp1, timestamp2, None)               
                            

            sorted_aggregated_events = sorted(
                aggregated_events.items(), 
                key=lambda x: (x[1][1], x[1][2])  # Sort by both start and end timestamps
            )
            self.debug_print(f"sorted events {sorted_aggregated_events}")

            # Add aggregated activity type events to trace
            for keyid, (key, timestamp1, timestamp2, docs) in sorted_aggregated_events:
                self.debug_print(f"Creating event for {keyid}")
                event = Event()
                event[DEFAULT_NAME_KEY] = key
                start_timestamp = timestamp1  # Start time from input document
                end_timestamp = timestamp2   # End time from output document
                event[DEFAULT_START_TIMESTAMP_KEY] = start_timestamp
                event[DEFAULT_END_TIMESTAMP_KEY] = end_timestamp
                # Calculate the midpoint between start and end timestamps
                midpoint_timestamp = start_timestamp + (end_timestamp - start_timestamp) / 2
                event[DEFAULT_TIMESTAMP_KEY] = midpoint_timestamp  # Use midpoint timestamp for compatibility
                event[DEFAULT_DURATION_KEY] = (end_timestamp - start_timestamp).total_seconds()
                #event[DEFAULT_TIMESTAMP_KEY] = timestamp
                trace.append(event)

            if len(trace) > 0:
                self.debug_print(f"Adding trace with {len(trace)} events")
                traces.append(trace)
            else:
                self.debug_print("No events in trace, skipping")

        self.debug_print(f"\nTotal traces created: {len(traces)}")
        return traces

    def print_event_log(self, log: EventLog) -> None:
        """
        Druckt den EventLog mit Fehlerbehandlung.
        """
        for case_index, case in enumerate(log):
            self.debug_print(f"Case {case_index + 1}:")
            for event in case:
                try:
                    # Sicherer Zugriff auf Event-Attribute
                    name = event[DEFAULT_NAME_KEY]
                    timestamp = event[DEFAULT_TIMESTAMP_KEY]
                    case_id = case_index
                    self.debug_print(f"  Activity: {name}, StartTimestamp: {timestamp}, CaseID: {case_id}")
                except Exception as e:
                    self.debug_print(f"Error printing event: {str(e)}")

def generate_JSONPN(objectmodel, activitytypes):
    name = "JSON-Net"
    net = Net(name)
    for objectType in objectmodel.modelObjectType:
        place = objectToJSONPlace(objectType)
        net.append_place(place)
    for activitytype in activitytypes:
        activityToJSONTransition(activitytype, net)
    for activitytype in activitytypes:
        activityToDBJSONTransition(activitytype, net)
    net = checkPN(net)
    return net

# Convert an object type to a JSON place representation in the Petri Net
def objectToJSONPlace(object_type):
    # Ensure the input is an instance of ObjectType, raise an error if not
    if not isinstance(object_type, ObjectType):
        raise ValueError("Input must be an instance of ObjectType")
    # If the input is valid, create a Place instance using the object type's information
    else: 
        place_instance = Place(object_type.inst_id, object_type.name, object_type.jsonSchema)
    # Return the created Place instance
    return place_instance

# Convert an activity type to a JSON transition representation in the Petri Net
def activityToJSONTransition(activity_type, net:Net):
    # Ensure the input is an instance of ActivityType, raise an error if not
    if not isinstance(activity_type, ActivityType):
        raise ValueError("Input must be an instance of ActivityType")
    # If the activity type does not include "DB" in its name, proceed to create a Transition instance
    elif not ("DB" in activity_type.name): 
        transition_instance = Transition(activity_type.name, activity_type.name)

        # For each input object type of the activity, create an Arc from the input place to the transition
        for input in activity_type.input_object_types:
            id = f"Kante in {activity_type.inst_id}"  # Create a unique ID for the arc
            name = f"{input.name} zu {activity_type.name}"  # Name the arc using input and activity names
            arc_instance = Arc(id, name, net.netPlaces[input.inst_id], transition_instance)  # Create the Arc instance
            net.append_arc(arc_instance)  # Add the arc to the net

        # For each output object type of the activity, create an Arc from the transition to the output place
        for output in activity_type.output_object_types:
            id2 = f"Kante aus {activity_type.inst_id}"  # Create a unique ID for the arc
            name2 = f"{activity_type.name} zu {output.name}"  # Name the arc using activity and output names
            arc_instance2 = Arc(id2, name2, transition_instance, net.netPlaces[output.inst_id])  # Create the Arc instance
            net.append_arc(arc_instance2)  # Add the arc to the net

        # Optionally, convert activity rules to inscriptions for the transition (commented out, indicating a TODO or placeholder for future implementation)
        #transition_instance = rulesToInstriptions(activity_type.rules, transition_instance)
        
        # Add the transition to the net
        net.append_transition(transition_instance)

# Placeholder for a function to handle activities specifically related to database operations
def activityToDBJSONTransition(activity_type, net:Net):
    if not isinstance(activity_type, ActivityType):
            raise ValueError("Input must be an instance of ActivityType")
    # Erstelle eine Instanz der Place-Klasse mit dem JSON Schema als Token
    elif ("DB" in activity_type.name): 
        dbName = activity_type.name.split("DB")[1].strip()
        if(dbName==activity_type.output_object_types[0].name):
            id = f"Kante in {activity_type.input_object_types[0].name}"
            name = f"{dbName} zu {activity_type.input_object_types[0].name}-Erstellung"
            transitionName=f"{activity_type.input_object_types[0].name}-Erstellung"
        else:
            id = f"Kante in {activity_type.output_object_types[0].name}"
            name = f"{dbName} zu {activity_type.output_object_types[0].name}-Erstellung"
            transitionName=f"{activity_type.output_object_types[0].name}-Erstellung"
        arc_instance = Arc(id,name,net.netPlaces[dbName],net.netTransitions[transitionName])
        net.append_arc(arc_instance)

def rulesToInstriptions(rules, transition:Transition):
    for rule in rules:
        transition_with_inscriptions = transition.add_inscription_text(rule)
    return transition_with_inscriptions

#TODO
# Define a function to check the validity of the Petri Net and return the verified net
def checkPN(net):
    # Implementation of the checkPN function goes here
    # This could involve verifying the structure of the net, ensuring there are no isolated places or transitions, etc.
    return net