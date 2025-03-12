import Model.ObjectModel.ObjectRelation as ObjectRelation
from Model.ObjectModel.ObjectRelation import ObjectRelation
import Model.ObjectModel.ObjectType as ObjectType
from Model.ObjectModel.ObjectType import ObjectType
from Model.Instances import Instances

class ObjectModel():
    def __init__(self, name, modelObjectType = None, modelObjectRelation = None, noneModelObjectRelation = None):
        self.name = name
        self.modelObjectType = modelObjectType or []
        self.modelObjectRelation = modelObjectRelation or []
        self.noneModelObjectRelation = noneModelObjectRelation or []
            
    def add_objectType(self, objectType: ObjectType):
        self.modelObjectType.append(objectType)

    def add_ObjectRelation(self, objectRelation):
        # Überprüfe, ob eine Beziehung zwischen den beiden Typen bereits existiert
        existing_relation = self.get_relation_by_types(objectRelation.input_object_type, objectRelation.output_object_type)

        if existing_relation:
            # Füge die Regel zur existierenden Relation hinzu
            existing_relation.add_rule(objectRelation.rules)
        else:
            # Füge die neue Relation hinzu, da sie noch nicht existiert
            self.modelObjectRelation.append(objectRelation)
    def add_NoneObjectRelation(self, objectRelation):
        # Überprüfe, ob eine Beziehung zwischen den beiden Typen bereits existiert
        existing_relation = self.get_none_relation_by_types(objectRelation.input_object_type, objectRelation.output_object_type)

        if existing_relation:
            # Füge die Regel zur existierenden Relation hinzu
            existing_relation.add_rule(objectRelation.rules)
        else:
            # Füge die neue Relation hinzu, da sie noch nicht existiert
            self.noneModelObjectRelation.append(objectRelation)
        # notex = False
        # for i, (relation) in enumerate(self.noneModelObjectRelation):
        #     if (
        #         relation.input_object_type == objectRelation.input_object_type
        #         and relation.output_object_type == objectRelation.output_object_type
        #     ):
        #         notex = True
        #         relation.add_rule(objectRelation.rules)
        #         self.noneModelObjectRelation[i] = relation

        #         print(f"  bearbeitet None-ObjectRelation: {self.noneModelObjectRelation[i].name}")
        #         print(f"                : {len(self.noneModelObjectRelation[i].rules)}")
            
        # if not notex:
        #     print(f"  neues None-ObjectRelation: {objectRelation.name}")
        #     print(f"                : {len(objectRelation.rules)}")
        #     self.noneModelObjectRelation.append(objectRelation)


    def get_relation_by_types(self, input_type, output_type):
        # Durchsuche die bestehenden Relationen, um eine Beziehung zu finden
        for relation in self.modelObjectRelation:
            if (
                relation.input_object_type == input_type
                and relation.output_object_type == output_type
            ):
                return relation
        return None    


    def get_none_relation_by_types(self, input_type, output_type):
        # Durchsuche die bestehenden Relationen, um eine Beziehung zu finden
        for relation in self.noneModelObjectRelation:
            if (
                relation.input_object_type == input_type
                and relation.output_object_type == output_type
            ):
                return relation
        return None   

    def find_object_type_by_name(self, type_name):
        for obj_type in self.modelObjectType:
            if obj_type.name == type_name:
                return obj_type
        return None
    
    def print_objectmodel(self):
        print(f"Objectmodel: {self.name}")
        print("Objecttypes:")
        for objecttype in self.modelObjectType:
            print(f"  Objecttype: {objecttype.name}")
        print("ObjectRelation:")
        for objectRelation in self.modelObjectRelation:
            print(f"  ObjectRelation: {objectRelation.name}")
            for rule in objectRelation.rules:
                print(f"                : {rule[1]}")

        for noneobjectRelation in self.noneModelObjectRelation:
            print(f"  None-ObjectRelation: {noneobjectRelation.name}")