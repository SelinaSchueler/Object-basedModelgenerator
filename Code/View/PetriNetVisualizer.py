from graphviz import Digraph
from PIL import Image
import io
import pm4py
from typing import Dict, Any, Optional
import re

class PetriNetVisualizer:
    def __init__(self, database_visualization=False):
        self.database_visualization = database_visualization
        self.default_place_attrs = {
            'shape': 'circle',
            'width': '1.2',    # Vergrößert von 0.6
            'height': '1.2',   # Vergrößert von 0.6
            'fontsize': '11',
            'style': 'filled',
            'fillcolor': '#FFFFFF',
            'fixedsize': 'true'  # Stellt sicher, dass alle Stellen gleich groß sind
        }

        self.database_place_attrs = {
            'shape': 'circle',
            'width': '1.2',    # Vergrößert von 0.6
            'height': '1.2',   # Vergrößert von 0.6
            'fontsize': '11',
            'style': 'filled',
            'fillcolor': '#D3D3D3',  # Helleres Grau
            'fixedsize': 'true'  # Stellt sicher, dass alle Stellen gleich groß sind
        }
        
        self.default_transition_attrs = {
            'shape': 'rect',
            'width': '2.0',    # Vergrößert von 0.8
            'height': '0.8',   # Vergrößert von 0.5
            'fontsize': '11',
            'style': 'filled',
            'fillcolor': '#FFFFFF',
            'fixedsize': 'true'  # Stellt sicher, dass alle Transitionen gleich groß sind
        }
        
        self.default_arc_attrs = {
            'arrowsize': '0.8',
            'fontsize': '11'
        }

        self.default_arc_attrs = {
            'arrowsize': '0.8',
            'fontsize': '11'
        }
    def extract_parts(self, activity_name):
        """Extracts the front and back parts of an activity name."""
        if not activity_name:  # Handle None or empty string case
            return None, None
            
            # Entferne unnötige Leerzeichen komplett, sodass keine Inkonsistenzen bleiben
        cleaned_name = re.sub(r"\s+", "", activity_name.strip())

        # Regex, um verschachtelte Werte korrekt zu extrahieren (robust ohne Leerzeichen)
        match = re.match(r"^\(\((.*?)\),\((.*?)\)\)$", cleaned_name)
        if match:
            # Extrahiere die vorderen und hinteren Teile
            front, back = match.groups()

            # Bereinige und splitte bei Komma
            front_parts = [part.strip("()' ") for part in front.split(',')]
            back_parts = [part.strip("()' ") for part in back.split(',')]

            return set(front_parts), set(back_parts)  # Gib Mengen zurück
        return None, None
    
    def rename_place(self, place, net):
        """Renames a place based on all connected transitions."""
        front_parts = set()  # Single set for all parts
        back_parts = set()

        for arc in net.arcs:
            # Check incoming arcs
            if arc.target == place and hasattr(arc.source, 'label'):
                front, back = self.extract_parts(arc.source.label)
                if back:
                    for part in back:
                        back_parts.add(part)

            # Check outgoing arcs
            if arc.source == place and hasattr(arc.target, 'label'):
                front, back = self.extract_parts(arc.target.label)
                if front:
                    for part in front:
                        front_parts.add(part)

        # Find shared elements
        common_parts = front_parts & back_parts
        if not common_parts:
            common_parts = front_parts if front_parts else back_parts

        if common_parts:
            # Join all unique parts with commas and wrap in parentheses
            new_name = f"({','.join(sorted(common_parts))})"  # Sort for consistent ordering
            return new_name

        return place.name
    
    def visualize(self, net, rename_places=False, initial_marking=None, final_marking=None, 
             filename="petrinet", format="png", custom_decorations: Dict[Any, Dict] = None, independents=None):
        """
        Erstellt eine verbesserte Visualisierung eines Petri-Netzes.
        """
        if not self.database_visualization:
            independents = None

        dot = Digraph('petrinet', filename=filename)
        dot.attr(rankdir='LR')  # Left to right layout
        
        # Globale Graph-Attribute
        dot.attr('node', fontname='Helvetica')
        dot.attr('edge', fontname='Helvetica')
        
        # Places
        for place in net.places:
            name = ""
            if place.name:
                name = place.name
            label = self.rename_place(place, net) if rename_places else place.name
            if label:
                # Füge Zeilenumbruch nach dem Komma in "),(" ein
                label = label.replace(",", ",\n")
            else:
                label = place.name
            
            if independents is not None and place.name in independents:
                attrs = self.database_place_attrs.copy()
            else:
                attrs = self.default_place_attrs.copy()
            # Markierung hinzufügen wenn vorhanden
            if initial_marking and place in initial_marking or (independents is not None and place.name in independents):
                #label = f"{label}\n({initial_marking[place.name]})"
                attrs['penwidth'] = '2'
            if final_marking and place in final_marking:
                attrs['penwidth'] = '2'
                attrs['peripheries'] = '2'
                
            # Custom decorations für Places
            if custom_decorations and place in custom_decorations:
                attrs.update(custom_decorations[place])
                
            dot.node(place.name, label, **attrs)
        
        # Transitions
        for trans in net.transitions:
            attrs = self.default_transition_attrs.copy()
            # if filename == 'Inductive':
            #     trans.name = ""
            #     trans.label = ""
            if trans.name:
                # Füge Zeilenumbruch nach dem Komma in "),(" ein
                label = trans.name.replace("),(", "),\n(")
                label = label.replace("), (", "),\n(")

            elif trans.label:
                # Füge Zeilenumbruch nach dem Komma in "),(" ein
                label = trans.label.replace("),(", "),\n(")
                label = label.replace("), (", "),\n(")

            
            # Custom decorations für Transitionen
            if custom_decorations and trans in custom_decorations:
                attrs.update(custom_decorations[trans])
                
            # Sonderbehandlung für unsichtbare Transitionen
            if trans.label is None:
                attrs['style'] = 'filled'
                attrs['fillcolor'] = '#808080'
                label = ''
            
            dot.node(trans.name, label, **attrs)
        
        # Arcs
        for arc in net.arcs:
            if independents is not None and arc.source.name in independents:
                attrs = self.default_arc_attrs.copy()
                attrs['dir'] = 'none'
            else:
                attrs = self.default_arc_attrs.copy()
            # Custom decorations für Kanten
            if custom_decorations and arc in custom_decorations:
                attrs.update(custom_decorations[arc])
                
            # Gewichtete Kanten speziell markieren
            if arc.weight > 1:
                attrs['label'] = str(arc.weight)
                attrs['penwidth'] = str(1 + 0.5 * arc.weight)
            
            dot.edge(arc.source.name, arc.target.name, **attrs)
        
        # Render
        dot.render(filename=filename, format=format, cleanup=True)
        return dot
        
    def convert_gviz_to_image(self, gviz) -> Image:
        """Converts a Graphviz object to a PIL Image."""
        png = gviz.pipe(format='png')
        return Image.open(io.BytesIO(png))

    def add_frequency_decoration(self, net, log, filename="petrinet_with_frequency"):
        """
        Fügt Häufigkeitsinformationen zum Petri-Netz hinzu.
        """
        # Berechne Häufigkeiten
        replay_result = pm4py.conformance_diagnostics_token_based_replay(log, net)
        element_counts = self._calculate_element_frequencies(replay_result, net)
        
        # Erstelle Dekorationen basierend auf Häufigkeiten
        decorations = {}
        max_count = max(element_counts.values()) if element_counts else 1
        
        for element, count in element_counts.items():
            # Normalisiere Häufigkeit zwischen 0 und 1
            intensity = count / max_count
            
            if isinstance(element, pm4py.objects.petri_net.obj.PetriNet.Place):
                decorations[element] = {
                    'fillcolor': f"#{int(255 * (1-intensity)):02x}{int(255):02x}{int(255):02x}",
                    'label': f"{element.name}\n({count})"
                }
            elif isinstance(element, pm4py.objects.petri_net.obj.PetriNet.Transition):
                decorations[element] = {
                    'fillcolor': f"#{int(255):02x}{int(255 * (1-intensity)):02x}{int(255 * (1-intensity)):02x}",
                    'label': f"{element.label if element.label else ''}\n({count})"
                }
        
        # Visualisiere mit Häufigkeitsdekorationen
        return self.visualize(net, custom_decorations=decorations, filename=filename)

    def _calculate_element_frequencies(self, replay_result, net):
        """
        Berechnet die Häufigkeit der Nutzung jedes Elements im Petri-Netz.
        """
        element_counts = {}
        
        for trace_result in replay_result:
            if not trace_result['trace_is_fit']:
                continue
                
            visited_elements = trace_result['activated_transitions'] + \
                             trace_result['visited_places']
            trace_count = trace_result['trace_occurrence']
            
            for element in visited_elements:
                if element not in element_counts:
                    element_counts[element] = 0
                element_counts[element] += trace_count
        
        return element_counts