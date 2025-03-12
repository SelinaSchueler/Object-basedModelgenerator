import os
import json
import xml.etree.ElementTree as ET
from PyQt5.QtCore import pyqtSignal

class FileConverter:
    def __init__(self, debug=False, log_signal: pyqtSignal = None):
        self.debug = debug
        self.log_signal = log_signal

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)  
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(f"[TERMINAL] {message}")

    def convert_file(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.json':
            return self.process_json(file_path)
        elif file_extension == '.xml':
            return self.convert_xml_to_json(file_path)
        else:
            self.debug_print(f"Unsupported file format: {file_extension}")
            return None

    def process_json(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            return data
        except Exception as e:
            self.debug_print(f"Error processing JSON file: {e}")
            return None

    def convert_xml_to_json(self, file_path):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            return self.xml_to_dict(root)
        except Exception as e:
            self.debug_print(f"Error converting XML to JSON: {e}")
            return None

    def xml_to_dict(self, element):
        if len(element) == 0:
            return element.text
        result = {}
        for child in element:
            result[child.tag] = self.xml_to_dict(child)
        return result

# Example usage
if __name__ == "__main__":
    converter = FileConverter(debug=True)
    file_path = "path/to/your/file"
    data = converter.convert_file(file_path)
    if data:
        print("File processed successfully.")
    else:
        print("File processing failed.")
