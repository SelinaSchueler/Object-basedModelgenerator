# NetGenerator

NetGenerator is a tool designed for generating and analyzing process models from various data sources. It leverages several libraries to perform tasks such as data transformation, information extraction, and activity generation.

## Features

- **Transformation**: Convert raw data into structured formats.
- **Information Extraction**: Extract meaningful information from documents and logs.
- **Activity Generation**: Generate activities based on extracted information and process models.

## Libraries Used

### Data Processing and Analysis

- **Pandas**: For data manipulation and analysis.
- **NumPy**: For numerical operations and array handling.

### Machine Learning and NLP

- **scikit-learn**: For machine learning algorithms and data preprocessing.
- **nltk**: For natural language processing tasks.
- **transformers**: For advanced NLP tasks.
- **langchain-openai**: For integrating OpenAI's language models.

### Process Mining

- **PM4Py**: For process mining and event log analysis.

### Visualization

- **Matplotlib**: For creating static, animated, and interactive visualizations.
- **PyQt5**: For creating graphical user interfaces.
- **graphviz**: For Petri net visualization.

### Miscellaneous

- **PIL**: For image processing.
- **dateutil**: For complex date manipulations.
- **networkx**: For creating and analyzing complex networks.
- **genson**: For generating JSON Schemas from JSON objects.

## Installation

To install the required libraries, you can use the following command:

```bash
pip install pandas numpy scikit-learn nltk transformers langchain-openai pm4py matplotlib PyQt5 pillow python-dateutil networkx genson
```

Additionally, you need to install Graphviz for Petri net visualization:

```bash
# For Windows
choco install graphviz

# For macOS
brew install graphviz

# For Linux
sudo apt-get install graphviz
```
## Usage

### 1. Data Transformation

Use the transformation modules to convert raw data into structured formats. This step involves reading data from various sources and transforming it into a format suitable for further processing.

Example:
```python
from Controller.PreDataAnalyse.PreInstancegenerator import PreInstanceGenerator

# Initialize the generator
generator = PreInstanceGenerator(debug=True)

# Generate instances from file paths
file_paths = ['path/to/file1.json', 'path/to/file2.json']
instances = generator.generateinstances(file_paths)
```

### 2. Information Extraction

Extract information from documents and logs using the information extraction modules. This step involves classifying documents, generating process instances, and extracting object types and relations.

Example:
```python
from Controller.Informationextraction.ObjecttypeGenerator.DocumentClassifier import DocumentClassifier
from Controller.Informationextraction.ProcessinstanceClassifier import ProcessInstanceClassifier
from Controller.Informationextraction.ObjecttypeGenerator.ObjectGenerator import ObjectTypeGenerator
from Controller.Informationextraction.ObjectRelationGenerator import ObjectRelationGenerator

# Classify documents
clusterer = DocumentClassifier(max_features=1000, debug=True)
updated_df = clusterer.classify_documents(instances)

# Classify process instances
classifier = ProcessInstanceClassifier(updated_df, debug=True)
process_instances, process_pairs, notused = classifier.classify_documents()

# Generate object types
objecttypegenerator = ObjectTypeGenerator(debug=True)
object_type_list = objecttypegenerator.generateObjectTypes(updated_df)

# Generate object relationship types
objectrelationgenerator = ObjectRelationGenerator(debug=True)
final_content_based_objectrelations, final_time_based_objectrelations = objectrelationgenerator.generateObjectRelations(updated_df, process_instances, process_pairs)
```

### 3. Activity Type and Petri Net Generation Generation

Generate activities based on the extracted information and process models. This step involves creating activities from the identified object relations and generating a Petri net for visualization.

Example:
```python
from Controller.Informationextraction.ActivityGenerator.ActivityGenerator import ActivityGenerator
from Controller.Transformation.PNGenerator import EventlogPNGenerator

# Generate activities
activitygenerator = ActivityGenerator(updated_df, debug=True)
time_based_AT, figure = activitygenerator.generate_activities(final_time_based_objectrelations, process_instances)
content_based_AT = activitygenerator.generate_content_activities(final_content_based_objectrelations, process_instances)

# Generate Petri net
timebased_petri_net_generator = EventlogPNGenerator(debug=True)
figures, figures2, net_content = timebased_petri_net_generator.generate_eventlog_petri_net(updated_df, time_based_AT, content_based_AT)
```

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue.

## License

This project is licensed under the MIT License.