from Model.PetriNet.Node import Node as node
from Model.PetriNet.Inscription import Inscription
from Model.Instances import Instances
class Arc(Instances):
    def __init__(self, inst_id, name, source:node, sink:node, inscription=None):
        super().__init__(inst_id, name)
        self._source = source
        self._sink = sink
        self.inscription = Inscription()
        self.inscription.add_text(inscription) if inscription is not None else None