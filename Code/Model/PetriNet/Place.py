from Model.PetriNet.Node import Node

class Place(Node):
    def __init__(self, inst_id, name, schema):
        super().__init__(inst_id, name)        
        self._schema = schema