from Model.PetriNet.Inscription import Inscription
from Model.PetriNet.Node import Node
class Transition(Node):
    def __init__(self, inst_id, name, inscription = None):
        super().__init__(inst_id, name)
        self.inscription = Inscription()
        self.inscription.add_text(inscription) if inscription is not None else None
        
    def add_inscription_text(self, text):
        self.inscription.add_text(text)