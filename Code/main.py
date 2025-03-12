import os, sys

from Controller.PreDataAnalyse.PreInstancegenerator import PreInstanceGenerator
from Controller.Informationextraction.ObjecttypeGenerator.DocumentClassifier import DocumentClassifier
from Controller.Transformation.Ruleextactor import DecisionPointAnalyzer
from testdatagenerator import TestDataGenerator

#'/home/user/example/parent/child'
current_path = os.path.abspath('.')

#'/home/user/example/parent'
parent_path = os.path.dirname(current_path)

sys.path.append(parent_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'child.settings')

import Controller.Informationextraction.DocToObjectModel.ObjectModelGenerator as omg
from Model.ObjectModel.ObjectModel import ObjectModel
from Controller.Informationextraction.ProcessinstanceClassifier import ProcessInstanceClassifier
from Controller.Informationextraction.ObjecttypeGenerator.ObjectGenerator import ObjectTypeGenerator
from Controller.Informationextraction.ObjectRelationGenerator import ObjectRelationGenerator
from Controller.Informationextraction.ActivityGenerator.ActivityGenerator import ActivityGenerator
from Controller.Transformation.PNGenerator import EventlogPNGenerator, generate_JSONPN
import nltk
import glob
nltk.download('punkt')

# generator = TestDataGenerator()
# data = generator.generate_all_data(num_kunden=5, num_produkte=7, num_bestellungen=10)
# generator.save_to_files()

# Dateipfad zur JSON-Datei
file_paths = []
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestellung\Bestellung1.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestellung\Bestellung2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestellung\Bestellung3.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestellung\Bestellung4.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestellung\Bestellung5.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestellung\Bestellung6.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestätigung\Bestätigung1.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestätigung\Bestätigung2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestätigung\Bestätigung3.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestätigung\Bestätigung4.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestätigung\Bestätigung5.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Bestätigung\Ablehnung6.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Lieferschein\Lieferschein1.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Lieferschein\Lieferschein2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Lieferschein\Lieferschein3.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Lieferschein\Lieferschein4.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Lieferschein\Lieferschein5.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Rechnung\Rechnung1.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Rechnung\Rechnung2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Rechnung\Rechnung3.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Rechnung\Rechnung4.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Rechnung\Rechnung5.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Produkt.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Kunden.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\Zahlungen\Zahlung1.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON\\Reklamation\Reklamation1.json')

# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Bestellung.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Bestätigung.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Lieferschein.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Rechnung.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Produkt.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Kunden.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Bestellung2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Bestätigung2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Lieferschein2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Rechnung2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Produkt2.json')
# file_paths.append(r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\Testfall1\Kunden2.json')

# # Pfad zum Ordner mit den JSON-Dateien
# folder_path = r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON Schlinge'
# folder_path = r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON Schlinge copy'

#folder_path = r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON AND'

#folder_path = r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON XOR'
#folder_path = r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\JSON Iteration'
folder_path = r'C:\Users\jy1115.KIT\NetGenerator\NetGenerator\2 Ressourcen\Testdaten\XML'
# folder_path = r'C:\ProcessModelGenerator\\Testfiles'

file_paths = []
for root, dirs, files in os.walk(folder_path):
    for file in files:
        if file.endswith(('.json', '.xml', '.txt')):
            file_paths.append(os.path.join(root, file))
        
# # Alle JSON-Dateien im Ordner hinzufügen
#file_paths.extend(glob.glob(os.path.join(folder_path, '*.json')))

# JSON-Datei einlesen
debug = True

#TODO preData
    # Datenerstellung, Datenstrukturierung, Datenbereinigung

# preData that stores all documents in a list of instances
generator = PreInstanceGenerator(True)
instances = generator.generateinstances(file_paths)

#Information extraction from the documents
# 1. Generate DocTypes
# 2. Generate ProcessInstances
# 3. Generate ObjectTypes
# # 4. Generate ObjectRelations


clusterer = DocumentClassifier(1000, debug)
updated_df = clusterer.classify_documents(instances)
  
classifier = ProcessInstanceClassifier(updated_df, debug)
process_instances, process_pairs, notused = classifier.classify_documents()

objecttypegenerator = ObjectTypeGenerator(debug)
object_type_list = objecttypegenerator.generateObjectTypes(updated_df)

objectrelationgenerator = ObjectRelationGenerator(debug)
final_content_based_objectrelations, final_time_based_objectrelations = objectrelationgenerator.generateObjectRelations(updated_df, process_instances, process_pairs)



object_relations = []

# Create object model
objectModel = ObjectModel("Order to Delivery")
#objectModel = omg.generateObjectModel(object_type_list, objectModel, object_relations)
#objectModel.print_objectmodel()
activitygenerator = ActivityGenerator(updated_df, True)
time_based_AT, figure = activitygenerator.generate_activities(final_time_based_objectrelations, process_instances)
content_based_AT = activitygenerator.generate_content_activities(final_content_based_objectrelations, process_instances)

timebased_petri_net_generator = EventlogPNGenerator(True)
figures, figures2, net_content = timebased_petri_net_generator.generate_eventlog_petri_net(updated_df, time_based_AT, content_based_AT)


analyzer = DecisionPointAnalyzer(debug)
#path_groups, decision_trees = analyzer.analyze_decision_points(net_content, updated_df, content_based_AT)

#json_net = generate_JSONPN(objectModel, activity_list)
#json_net.print_net()

#TODO Generate activities
#TODO Activity inscriptions: Relations and decision trees
#TODO Generate Petri Net
#TODO Net Checker
#TODO Export