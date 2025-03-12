import json
import os
from collections import defaultdict
from transformers import pipeline
import getpass
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
# Link to localai client
OPENAI_API_BASE="..."
# openai api key (also needed for localai , but sk- is enough)
OPENAI_API_KEY="..."
os.environ['OPENAI_API_BASE'] = OPENAI_API_BASE
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
#os.environ["OPENAI_API_KEY"] = getpass.getpass()
model = ChatOpenAI(model="gpt-4")

class NameGenerator:
    def __init__(self):
        pass
    
    def determine_cluster_name(self, documents):
        # Kombiniere alle Dokumente in einem einzigen String
        prompt = ChatPromptTemplate.from_template("tell me a short joke about {topic}")
        output_parser = StrOutputParser()

        chain = prompt | model | output_parser

        chain.invoke({"topic": "ice cream"})
        print(chain[0]['generated_text'])
    
        # combined_documents = " ".join(json.dumps(doc) for doc in documents)

        # prompt = ChatPromptTemplate.from_template("Bestimme den Cluster-Namen für die folgenden Dokumente: {combined_documents}\nCluster-Name:")
        # output_parser = StrOutputParser()

        # chain = prompt | model | output_parser
        # chain.invoke({"combined_documents": combined_documents})

        ##prompt = f"Bestimme den Cluster-Namen für die folgenden Dokumente: {combined_documents}\nCluster-Name:"
        #response = self.generator(prompt, max_length=50, num_return_sequences=1)
        cluster_name = chain[0]['generated_text'].split('Cluster-Name:')[1].strip().split('\n')[0]
        # return cluster_name
        return chain
    
    def rename_clusters(self, clusters):
        new_clusters = defaultdict(list)
        for cluster, paths in clusters.items():
            documents = []
            for path in paths:
                with open(path, 'r', encoding='utf-8') as file:
                    document = json.load(file)
                    documents.append(document)
            new_cluster_name = self.determine_cluster_name(documents)
            new_clusters[new_cluster_name].extend(paths)
        return new_clusters
    
    def rename_clusters_by_path(self, df):
        """
        Benennt die Cluster basierend auf dem ersten Dateinamen in jedem Cluster
        """
        # Gruppiere nach dem ursprünglichen Cluster
        for cluster in df['cluster'].unique():
            # Nimm den ersten Dateipfad aus diesem Cluster
            first_path = df[df['cluster'] == cluster]['filename'].iloc[0]
            
            # Extrahiere den Dateinamen ohne Zahlen
            new_cluster_name = os.path.splitext(os.path.basename(first_path))[0]
            new_cluster_name = ''.join(char for char in new_cluster_name if not char.isnumeric())
            
            print(f"Cluster '{cluster}' wird zu '{new_cluster_name}' umbenannt.")
            # Aktualisiere den Cluster-Namen im DataFrame
            df.loc[df['cluster'] == cluster, 'doc_type'] = new_cluster_name
        return df
    
    # def rename_clusters_by_path(self, clusters):
    #     # Entferne Zahlen aus dem Dateinamen
    #     new_clusters = defaultdict(list)
    #     for cluster, paths in clusters.items():
    #         new_cluster_name = os.path.splitext(os.path.basename(paths[0]))[0]
    #         new_cluster_name = ''.join(char for char in new_cluster_name if not char.isnumeric())
    #         new_clusters[new_cluster_name].extend(paths)
    #     return new_clusters

