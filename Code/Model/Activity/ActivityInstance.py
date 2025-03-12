import Model.ObjectModel.ObjectType as ot
from Model.Instances import Instances
class ActivityInstance(Instances):
    def __init__(self, inst_id, name, processID, rules):
        super().__init__(inst_id, name)
        self.all_object_types = {}
        self.processID = processID
        self.rules = rules or []

    def add_rule(self, rule):
        self.rules.append(rule)
#TODO
#1) Vertrauenswürdigkeit
#2) Datenart (Unterschrift)
#3) Häufigkeit
#4) Dokumententyp
#5) Zeitstempel Prozessinstanzen
