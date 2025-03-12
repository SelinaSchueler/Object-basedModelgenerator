from Model.Instances import Instances

#import .Instances as Instances
from enum import Enum

class ObjectCategory(Enum):
    PROCESS_INSTANCE = "ProcessInstance"  # Alle Dokumente gehören zu einer spezifischen Prozessinstanz
    PROCESS_INSTANCE_INDEPENDENT = "MultiInstance"      # Alle Dokumente gehören zu mehreren Prozessinstanzen
    MIXED = "Mixed"                       # Gemischte Zuordnung von Dokumenten
    INDEPENDENT = "Independent"  


class ObjectType(Instances):
    def __init__(self, inst_id, name, attributes_or_json_schema=None, df_refs=None, category=None, instances=None):
        super().__init__(inst_id, name)        
        # Initialisiere die Attributliste
        self.attributes = self.convert_schema_to_dict(attributes_or_json_schema)
        self.jsonSchema = attributes_or_json_schema
        self.df_refs = df_refs if df_refs is not None else []
        self.category = category if category is not None else ObjectCategory.INDEPENDENT 
        self.instances = instances if instances is not None else 0

    def convert_schema_to_dict(self, schema):
        """
        Converts a JSON Schema to a dictionary with attribute types and required fields.
        
        Args:
            schema (dict): JSON Schema to convert
            
        Returns:
            dict: Dictionary containing:
                - attributes: Dict of attribute names and their types
                - required: List of required attribute names
        """
        def extract_properties(properties, required_fields=None):
            attributes = {}
            required = set(required_fields or [])
            
            for prop_name, prop_details in properties.items():
                # Ensure 'type' key exists in prop_details
                if 'type' not in prop_details:
                    continue
                
                # Handle nested arrays
                if prop_details['type'] == 'array':
                    if 'items' in prop_details and 'properties' in prop_details['items']:
                        nested_result = extract_properties(
                            prop_details['items']['properties'],
                            prop_details['items'].get('required', [])
                        )
                        attributes[prop_name] = {
                            'type': 'array',
                            'items': nested_result['attributes']
                        }
                        # Add nested required fields with proper prefix
                        for req in nested_result['required']:
                            required.add(f"{prop_name}.{req}")
                    else:
                        attributes[prop_name] = {'type': 'array'}
                
                # Handle nested objects
                elif prop_details['type'] == 'object':
                    if 'properties' in prop_details:
                        nested_result = extract_properties(
                            prop_details['properties'],
                            prop_details.get('required', [])
                        )
                        attributes[prop_name] = {
                            'type': 'object',
                            'properties': nested_result['attributes']
                        }
                        # Add nested required fields with proper prefix
                        for req in nested_result['required']:
                            required.add(f"{prop_name}.{req}")
                    else:
                        attributes[prop_name] = {'type': 'object'}
                
                # Handle basic types
                else:
                    attributes[prop_name] = {'type': prop_details['type']}
                    
                    # Add format if present
                    if 'format' in prop_details:
                        attributes[prop_name]['format'] = prop_details['format']
                    
                    # Add enum if present
                    if 'enum' in prop_details:
                        attributes[prop_name]['enum'] = prop_details['enum']
            
            return {
                'attributes': attributes,
                'required': list(required)
            }

        # Start conversion from the root
        if 'properties' not in schema:
            return {'attributes': {}, 'required': []}
        
        result = extract_properties(schema['properties'], schema.get('required', []))
        
        # Clean up the structure for better readability
        flattened_attributes = {}
        flattened_required = set()
        
        def flatten_attributes(attrs, prefix=''):
            for name, details in attrs.items():
                full_name = f"{prefix}{name}" if prefix else name
                
                if 'type' in details and details['type'] in ['object', 'array']:
                    if details['type'] == 'object' and 'properties' in details:
                        flatten_attributes(details['properties'], f"{full_name}.")
                    elif details['type'] == 'array' and 'items' in details:
                        flattened_attributes[full_name] = f"array of {details['items']}"
                else:
                    flattened_attributes[full_name] = details['type']
        
        flatten_attributes(result['attributes'])
        
        return {
            'attributes': flattened_attributes,
            'required': result['required']
        }
