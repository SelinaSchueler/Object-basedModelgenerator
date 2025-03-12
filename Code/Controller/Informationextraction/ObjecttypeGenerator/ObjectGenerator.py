import json
from Model.ObjectModel.ObjectType import ObjectType
from Model.ObjectModel.ObjectType import ObjectCategory
import genson as gen  # Genson library is used to generate JSON Schemas from JSON objects
from PyQt5.QtCore import pyqtSignal

class ObjectTypeGenerator:
    def __init__(self, debug: bool = False, log_signal: pyqtSignal = None):
        self.debug = debug
        self.log_signal = log_signal  # Add log_signal parameter

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(message)

    # Function to generate object types from a document
    def generateObjectTypes(self, documents_df):
        """
        Generiert ObjectTypes direkt aus dem DataFrame, gruppiert nach doc_type.
        Speichert zusätzlich die DataFrame-Referenzen im ObjectType.
        
        Args:
            documents_df: DataFrame mit den Spalten 'doc_type' und 'content'
            
        Returns:
            list: Liste von ObjectType-Instanzen
        """
             
        objectTypeList = []
    
        # Für jeden eindeutigen doc_type
        for type_name in documents_df['doc_type'].unique():
        # JSON Schema Builder für diesen Typ
            json_schema_builder = gen.SchemaBuilder()
        
        # Hole alle Dokumente dieses Typs
            type_docs = documents_df[documents_df['doc_type'] == type_name]
            self.debug_print(f"Found {len(type_docs)} documents of type {type_name}")

        # Sammle Referenzen für diesen Typ
            df_refs = []
        
            instances = 0
            # Verarbeite jedes Dokument
            for idx in type_docs.index:
                instances += documents_df.at[idx, 'arrays_found']
                # Referenz speichern
                df_refs.append(idx)
                
                # Schema generieren
                #content = documents_df.at[idx, 'content']
                content = json.loads(documents_df.at[idx, 'content_string'])
                self.debug_print(f"Content sample: {str(content)[:50]}...")

                # Bei Array-Dokumenten alle Einträge einzeln hinzufügen
                if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict):
                                json_schema_builder.add_object(item)
                else:
                        if isinstance(content, dict):
                            json_schema_builder.add_object(content)
                            self.debug_print(f"Added dict to schema: {str(content)[:50]}...")
                        else:
                            self.debug_print(f"Warning: Unexpected content type: {type(content)}")
                # Schema generieren und überprüfen
                generated_schema = json_schema_builder.to_schema()
                self.debug_print(f"Generated schema for {type_name}: {str(generated_schema)[:200]}...")

                # Bestimme die Kategorie basierend auf den Zuordnungen
                assignments = type_docs['process_assignments'].values
                
                if all(a == 1 for a in assignments):
                    category = ObjectCategory.PROCESS_INSTANCE
                elif any(a > 1 for a in assignments):
                    category = ObjectCategory.PROCESS_INSTANCE_INDEPENDENT
                    instances 
                    #documents_df.loc[documents_df['doc_type'] == type_name, 'process_instance_independent'] = True
                elif all(a == 0 for a in assignments):
                    category = ObjectCategory.INDEPENDENT
                else:
                    category = ObjectCategory.MIXED

            # Erstelle ObjectType mit generiertem Schema und Referenzen
            objectType = ObjectType(
                type_name,
                type_name,
                generated_schema,
                df_refs,
                category,
                instances
            )
            objectTypeList.append(objectType)

        self.debug_print("Identified object_types:")
                # Direkt die einzelnen Tupel aus dem rules Dictionary ausgeben

        for objectType in objectTypeList:
            name = objectType.name
            schema = objectType.jsonSchema
            df_refs = objectType.df_refs
            category = objectType.category
            self.debug_print(f"Object-Type: {name}, Schema: {schema}, OIs: {df_refs}, Object Type Kategorie: {category}")

    
        return objectTypeList

