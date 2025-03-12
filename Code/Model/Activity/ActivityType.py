from enum import Enum
from Model.Instances import Instances
class ActivityType(Instances):
    def __init__(self, inst_id, name, type, individualScore = 0):
        super().__init__(inst_id, name)
        self.all_object_types = []
        self.input_object_types =  []
        self.output_object_types_names = []
        self.output_object_types = []
        self.input_object_types_names = []
        self.instanceList = {}
        self.rules = []
        self.type = type
        self.label = name
        self.individualScore = individualScore

    def named_all_object_types(self, mapping):
        for object_type in self.input_object_types:
            if isinstance(object_type, tuple):
                if object_type[0] in mapping:
                    self.input_object_types_names.append((mapping[object_type[0]], object_type[1]))
                else:
                    self.all_object_types_names.append((object_type[0], object_type[1]))
            else:
                if object_type in mapping:
                    self.input_object_types_names.append((mapping[object_type], 0))
                else:
                    self.all_object_types_names.append((object_type, 0))
        for object_type in self.output_object_types:
            if isinstance(object_type, tuple):
                if object_type[0] in mapping:
                    self.output_object_types_names.append((mapping[object_type[0]], object_type[1]))
                else:
                    self.all_object_types_names.append((object_type[0], object_type[1]))
            else:
                if object_type in mapping:
                    self.output_object_types_names.append((mapping[object_type],0))
                else:
                    self.all_object_types_names.append((object_type,0)) 

    def add_input_object_type(self, input_object_type):
        if input_object_type not in self.input_object_types:
            self.input_object_types.append(input_object_type)

    def add_instance(self, instance):
        if isinstance(instance, dict):
            self.instanceList.update(instance)
        elif isinstance(instance, tuple):
            self.instanceList[instance[0]] = instance[1]
    
    def add_relation_instance(self, instance):
        if isinstance(instance, dict):
            for key, pis in instance.items():
                for pi, values in pis.items():
                    instancekey = (pi, self.input_object_types[0], self.output_object_types[0])
                    if key in self.instanceList:
                        if instancekey in self.instanceList[key]:
                            self.instanceList[key][instancekey].append(values)
                        else:
                            self.instanceList[key][instancekey] = values
                    else:
                        self.instanceList[key] = {instancekey: values}


                #self.instanceList.update(instance)
        # elif isinstance(instance, tuple):
        #     instancekey = (pi, self.input_object_types[0], self.output_object_types[0])
        #     self.instanceList[instance[0]][instancekey] = instance[1]

    def add_output_object_type(self, output_object_type):
        if output_object_type not in self.output_object_types:
            self.output_object_types.append(output_object_type)

    def add_rule(self, rule):
        for r in rule:
            if r not in self.rules:
                self.rules.append(r)

    def checkRule(self, relevant_doc):
        is_possible = True
        return is_possible


class ActivityRelationType(Enum):
    TIME_BASED = "zeitbasierter Zusammenhang"
    AGGREGATED_TIME_BASED = "aggregierter zeitbasierter Zusammenhang"
    CONTENT_BASED = "inhaltsbasierte Zusammenhang"
    NO_RELATION = "kein Zusammenhang, da nur KEYWORD übereinstimmt"