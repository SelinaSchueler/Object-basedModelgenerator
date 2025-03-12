class Net():
    def __init__(self, name):
        self._name = name
        self.netPlaces = {}
        self.netTransitions = {}
        self.netArcs = {}
            
    def append_place(self, place):
        self.netPlaces[place.inst_id]= place

    def append_transition(self, transition):
        self.netTransitions[transition.inst_id] = transition

    def append_arc(self, arc):
        self.netArcs[arc.inst_id]=arc

    def print_net(self):
        print(f"Net: {self._name}")
        print("Places:")
        for place_id, place in self.netPlaces.items():
            print(f"  Place: {place.name}")
        print("Transitions:")
        for transition_id, transition in self.netTransitions.items():
            print(f"  Transition: {transition.name}")
        print("Arcs:")
        for arc_id, arc in self.netArcs.items():
            print(f"  Arc: {arc.name}")