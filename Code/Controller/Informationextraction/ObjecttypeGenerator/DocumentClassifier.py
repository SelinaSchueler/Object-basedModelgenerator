from collections import defaultdict
import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
import string
from Controller.Informationextraction.ObjecttypeGenerator.NameGenerator import NameGenerator
from PyQt5.QtCore import pyqtSignal


#nltk.download('stopwords')

class DocumentClassifier:
    def __init__(self, max_features=1000, similarity_threshold=0.8, reference_uniqueness_threshold=0.9, max_depth=5, reuse_threshold=0.7, debug=False, log_signal: pyqtSignal = None):
        nltk.download('stopwords')
        self.vectorizer = TfidfVectorizer(max_features=max_features)
        # Anpassen der TF-IDF Parameter
        # self.vectorizer = TfidfVectorizer(
        #     max_features=max_features,
        #     ngram_range=(1, 2),  # Berücksichtigt auch Bi-Gramme
        #     min_df=2,  # Mindestens in 2 Dokumenten
        #     max_df=0.95  # In max 95% der Dokumente
        # )
        self.kmeans = None
        self.documents_df = None
        # Initialize stopwords within the class
        self.stop_words = set(stopwords.words('german'))
        self.debug = debug  # Add a debug flag
        self.log_signal = log_signal  # Add log_signal parameter
        # Define the thresholds
        self.thresholds = {
            'structure': {
                'similarity': similarity_threshold,
                'reference_uniqueness': reference_uniqueness_threshold,
                'max_depth': max_depth,
                'reuse_threshold': reuse_threshold
            }
        }

    def debug_print(self, message: str) -> None:
        if self.debug:
            message = str(message)
            if self.log_signal:
                self.log_signal.emit(message)
            else:
                print(f"[TERMINAL] {message}")
    
    def preprocess_text(self, text):
        # Add print statement to debug
        text = text.lower()  # Convert to lowercase
        if '"' in text:
            root_key = text.split('"')[1]  # Nimmt den ersten Key in Anführungszeichen
            text = f"{root_key} {text}" 
        tokens = nltk.word_tokenize(text)  # Tokenize text
        tokens = [token for token in tokens if token.isalnum()]  # Remove non-alphanumeric tokens
        tokens = [token for token in tokens if token not in self.stop_words]  # Remove stopwords
        preprocessed_text = ' '.join(tokens)
        self.debug_print(f"Preprocessed Text: {preprocessed_text}")
        return preprocessed_text    

    def find_optimal_clusters(self, X, max_k=10):
        iters = range(2, max_k + 1)
        sse = []
        silhouette_scores = []

        for k in iters:
            kmeans = KMeans(n_clusters=k, random_state=42)
            kmeans.fit(X)
            sse.append(kmeans.inertia_)
            silhouette_scores.append(silhouette_score(X, kmeans.labels_))

        # plt.figure(figsize=(10, 5))
        # plt.subplot(1, 2, 1)
        # plt.plot(iters, sse, marker='o')
        # plt.xlabel('Cluster Centers')
        # plt.ylabel('SSE')
        # plt.title('Elbow Method')

        # plt.subplot(1, 2, 2)
        # plt.plot(iters, silhouette_scores, marker='o')
        # plt.xlabel('Cluster Centers')
        # plt.ylabel('Silhouette Score')
        # plt.title('Silhouette Score Method')

        #plt.show()

        # Best number of clusters based on the highest Silhouette Score
        optimal_k = iters[silhouette_scores.index(max(silhouette_scores))]
        self.debug_print(f"Optimal number of clusters: {optimal_k}")
        return iters, sse, silhouette_scores, optimal_k

    def classify_documents(self, documents):
        self.documents_df = documents
        
        # Use an empty string if 'title' column is missing
        if 'title' not in self.documents_df.columns:
            self.documents_df['title'] = ""
        if 'flattened_content' not in self.documents_df.columns:
            self.documents_df['flattened_content'] = ""

        # Combine title and content for vectorization
        self.documents_df['text'] = self.documents_df['title'].astype(str) + " " + self.documents_df['flattened_content'].astype(str)
        self.documents_df['text'] = self.documents_df['text'].apply(self.preprocess_text)

        # Convert text to TF-IDF features
        X = self.vectorizer.fit_transform(self.documents_df['text'])
        
        # Find the optimal number of clusters
        iters, sse, silhouette_scores, optimal_clusters = self.find_optimal_clusters(X, max_k=10)

        # Apply K-Means clustering with the optimal number of clusters
        self.kmeans = KMeans(
            n_clusters=optimal_clusters,
            random_state=42,
            init='k-means++',  # Bessere Initialisierung
            n_init=10  # Mehrere Initialisierungsversuche
        )
        self.documents_df['cluster'] = self.kmeans.fit_predict(X)

        # Prepare the result
        # result = {}
        # for cluster_num in range(optimal_clusters):
        #     cluster_docs = self.documents_df[self.documents_df['cluster'] == cluster_num]
        #     result[f"Cluster_{cluster_num}"] = cluster_docs['filename'].tolist()
        # Get cluster sizes
        cluster_sizes = self.documents_df['cluster'].value_counts().sort_index().values
        
        # Update plots if GUI is available
        if hasattr(self, 'gui'):
            self.gui.update_clustering_plots(X, iters, sse, silhouette_scores, optimal_clusters, cluster_sizes)
        # return result
            # Temporäre 'text' Spalte entfernen, da sie nicht mehr benötigt wird
        self.documents_df = self.documents_df.drop('text', axis=1)

        self.check_uniform_structure()

         # TODO ClusterRenamer Instanz erstellen und Cluster Namen ändern
        renamer = NameGenerator()
        # classifier = NormalDocumentClassifier()
        # # Pfade der Instanzen werden den einzelnen Typen zugeordnet. Liste mit Doctype als Key und Pfaden in Liste.
        # orderedPaths = classifier.clusterPaths(paths)

            ##OpenAI-Name-Generator
            #orderedPaths = renamer.rename_clusters(orderedPaths)

            ##Pathname-NameGenerator
        self.documents_df  = renamer.rename_clusters_by_path(self.documents_df)

        return self.documents_df

    def check_uniform_structure(self):
        """
        Analysiert die strukturelle Uniformität aller Array-Einträge in den Dokumenten.
        Prüft auf Key-Übereinstimmung und speichert detaillierte Analyseergebnisse.
        
        Returns:
            DataFrame mit zusätzlichen Analyse-Spalten:
                - structure_uniform: Ob alle Arrays einheitlich sind
                - structure_base_keys: Basis-Keys der Arrays
                - structure_similarities: Ähnlichkeitswerte zwischen den Einträgen
                - structure_missing_keys: Fehlende Keys im Vergleich zur Basis
                - structure_extra_keys: Zusätzliche Keys im Vergleich zur Basis
                - arrays_found: Anzahl gefundener Arrays im Dokument
        """
        required_similarity = self.thresholds['structure']['similarity']

        def analyze_array_structure(entries):   
            """Analysiert die Struktur eines einzelnen Arrays."""
            if not entries or len(entries) < 2:
                return {
                    'is_uniform': False,
                    'base_keys': set(),
                    'similarities': [],
                    'missing_keys': {},
                    'extra_keys': {}
                }

            base_keys = set(entries[0].keys())
            similarities = []
            missing_keys = {}
            extra_keys = {}
            is_uniform = True
            
            for i, entry in enumerate(entries[1:], 1):
                current_keys = set(entry.keys())
                intersection = base_keys.intersection(current_keys)
                union = base_keys.union(current_keys)
                
                similarity = len(intersection) / len(union) if union else 0
                similarities.append(round(similarity, 3))
                
                if missing := base_keys - current_keys:
                    missing_keys[i] = missing
                if extra := current_keys - base_keys:
                    extra_keys[i] = extra
                    
                if similarity < required_similarity:
                    is_uniform = False
                    
            return {
                'is_uniform': is_uniform,
                'base_keys': base_keys,
                'similarities': similarities,
                'missing_keys': missing_keys,
                'extra_keys': extra_keys
            }

        def find_dict_arrays(obj):
            """Findet alle Arrays von Dictionaries in einem verschachtelten Objekt."""
            arrays = []
            
            if isinstance(obj, dict):
                for value in obj.values():
                    # Prüfe direkt auf Array von Dictionaries
                    if (isinstance(value, list) and value and 
                        all(isinstance(x, dict) for x in value)):
                        arrays.append(value)
                    # Rekursiv in verschachtelten Strukturen suchen
                    if isinstance(value, (dict, list)):
                        arrays.extend(find_dict_arrays(value))
                        
            elif isinstance(obj, list):
                # Prüfe ob aktuelle Liste ein Array von Dictionaries ist
                if all(isinstance(x, dict) for x in obj):
                    arrays.append(obj)
                # Rekursiv in Listenelementen suchen
                for item in obj:
                    if isinstance(item, (dict, list)):
                        arrays.extend(find_dict_arrays(item))
                        
            return arrays

        # Analysiere jedes Dokument
        for idx in self.documents_df.index:
            try:
                content = self.documents_df.at[idx, 'content']
                content = json.loads(content) if isinstance(content, str) else content
                
                dict_arrays = find_dict_arrays(content)

                if not dict_arrays:
                    continue
                    
                # Analysiere gefundene Arrays
                array_results = [analyze_array_structure(arr) for arr in dict_arrays]
                
                # Kombiniere Ergebnisse
                combined = {
                    'is_uniform': all(r['is_uniform'] for r in array_results),
                    'base_keys': [list(r['base_keys']) for r in array_results],
                    'similarities': [r['similarities'] for r in array_results],
                    'missing_keys': {i: r['missing_keys'] for i, r in enumerate(array_results) if r['missing_keys']},
                    'extra_keys': {i: r['extra_keys'] for i, r in enumerate(array_results) if r['extra_keys']}
                }
                
                # Speichere Ergebnisse
                self.documents_df.at[idx, 'structure_uniform'] = combined['is_uniform']
                self.documents_df.at[idx, 'structure_base_keys'] = json.dumps(combined['base_keys'])
                self.documents_df.at[idx, 'structure_similarities'] = json.dumps(combined['similarities'])
                self.documents_df.at[idx, 'structure_missing_keys'] = (
                    json.dumps(combined['missing_keys']) if combined['missing_keys'] else None
                )
                self.documents_df.at[idx, 'structure_extra_keys'] = (
                    json.dumps(combined['extra_keys']) if combined['extra_keys'] else None
                )

                if self.documents_df.at[idx, 'structure_uniform']:  # Uniforme Dokumente
                                    # Analysiere gefundene Arrays
                    array_len = max(len(arr) for arr in dict_arrays)
                    self.documents_df.at[idx, 'arrays_found'] = array_len
                    self.documents_df.at[idx, 'process_instance_independent'] = True
                else:
                    self.documents_df.at[idx, 'arrays_found'] = 1

            except Exception as e:
                print(f"Fehler bei Index {idx}: {str(e)}")
                continue

        if self.debug:
            self._print_uniformity_summary()

    def _print_uniformity_summary(self):
        """Gibt eine Zusammenfassung der Uniformitätsanalyse aus."""
        total_docs = len(self.documents_df)
        docs_with_arrays = self.documents_df['arrays_found'].notna().sum()
        uniform_docs = self.documents_df['structure_uniform'].sum()
        
        self.debug_print("\nUniformitätsanalyse Zusammenfassung:")
        self.debug_print(f"Gesamtanzahl Dokumente: {total_docs}")
        self.debug_print(f"Dokumente mit Arrays: {docs_with_arrays}")
        self.debug_print(f"Davon uniform: {uniform_docs}")
        
        if docs_with_arrays > 0:
            non_uniform = self.documents_df[
                self.documents_df['structure_uniform'] == False
            ]
            if len(non_uniform) > 0:
                self.debug_print("\nNicht uniforme Dokumente:")
                for idx in non_uniform.index:
                    self.debug_print(f"\nDokument {self.documents_df.at[idx, 'filename']}:")
                    self.debug_print(f"Gefundene Arrays: {self.documents_df.at[idx, 'arrays_found']}")
                    self.debug_print(f"Ähnlichkeiten: {self.documents_df.at[idx, 'structure_similarities']}")
                    if self.documents_df.at[idx, 'structure_missing_keys']:
                        self.debug_print(f"Fehlende Keys: {self.documents_df.at[idx, 'structure_missing_keys']}")


# Ordnet die einzelnen Dokumentenpfade nach Name der Datei einzelnen Dokumententypen zu. Liste mit Typename und dann den einzelnen paths
    
class NormalDocumentClassifier:  
    def clusterPaths(self, paths):
        orderedPaths = {}
        
        for path in paths:
            # Extrahiere den Dateinamen aus dem Pfad und entferne nummern
            file_name = os.path.splitext(os.path.basename(path))[0]
            file_name = self.clean_filename(file_name)

            # Überprüfe, ob ein Schlüssel bereits existiert, der dem Dateinamen ähnlich ist
            found_key = None
            for key in orderedPaths.keys():
                if file_name in key or key in file_name:
                    found_key = key
                    break

            # Wenn ein ähnlicher Schlüssel gefunden wurde, füge den Pfad zur existierenden Liste hinzu
            if found_key:
                orderedPaths[found_key].append(path)
            else:
                # Andernfalls erstelle einen neuen Schlüssel mit dem Dateinamen und füge den Pfad hinzu
                orderedPaths[file_name] = [path]
        return orderedPaths
    
    def clean_filename(self, file_name):
    # Entferne Zahlen aus dem Dateinamen
        cleaned_name = ''.join(char for char in file_name if not char.isnumeric())
        return cleaned_name