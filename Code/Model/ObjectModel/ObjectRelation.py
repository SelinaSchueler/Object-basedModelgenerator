from enum import Enum
import Model.ObjectModel.ObjectType as ot
from Model.Instances import Instances
class ObjectRelation(Instances):
    def __init__(self, inst_id, name, objects, rules=None, process_instance = None):
        super().__init__(inst_id, name)
        self.objects = objects if objects is not None else {} #object type als key und Wahrscheinlichkeit Input und Output [IW, OW] als value
        self.rules = set()
        self.processinstances = process_instance if process_instance is not None else {}
        self.individualScore = 0
        if rules is not None:
            self.add_rule(rules)


    def add_rule(self, rule):
        if rule is not None:
            if isinstance(rule, list):
                for r in rule:
                    self.rules.add(r)
            else:
                self.rules.add(rule)
   
    def add_object(self, objeclist):
        for key, value in objeclist.items():
            if key not in self.objects:
                self.objects[key] = value

    def add_processinstance(self, keys, processIDs):
        if keys in self.processinstances:
            old = self.processinstances[keys]
            for key, value in processIDs.items():
                if key in old:
                    old[key].append(value)
                else:
                    old[key] = value
            self.processinstances[keys] = old
        else:    
            self.processinstances[keys] = processIDs

    def add_processinstance_timebased(self, processIDs):
            self.processinstances[processIDs] = "timebased"

    def add_related_processinstances(self, processIds):     
        for keys, item in processIds.items():
            if keys in self.processinstances:
                continue
            else:
                self.processinstances[keys] = "timebased"


class RealtationType(Enum):
    TIME_BASED_RELATION = "zeitbasierter Zusammenhang"
    USED_TIME_BASED_RELATION = "benutzter Zeitbasierter Zusammenhang"
    CONTENT_BASED_RELATION = "inhaltsbasierte Zusammenhang"
    NO_RELATION = "kein Zusammenhang, da nur KEYWORD übereinstimmt"
