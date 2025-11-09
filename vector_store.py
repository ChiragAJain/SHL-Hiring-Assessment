import json
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import os


class AssessmentVectorStore:
    
    def __init__(self, collection_name: str = "shl_assessments_e5", persist_directory: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_directory)

        print("Loading E5-large-v2 model...")
        self.model = SentenceTransformer('intfloat/e5-large-v2')
        print(f'Model loaded: {self.model.get_sentence_embedding_dimension()} dimensions')

        self.collection =  self.client.get_or_create_collection(
            name = collection_name,
            metadata = {
                "description": "SHL Assessment embeddings (E5-large-v2)",
                "hnsw:space": "cosine"
            }
        )
        print(f"Collection '{collection_name}' ready with {self.collection.count()} items")
    
    def create_assessment_text(self, assessment: Dict[str, Any]) -> str:
        parts = [f"Assessment: {assessment['name']}",f"Description: {assessment.get('description','')}",]
        if assessment.get('job_level'):
            parts.append(f"Job Level: {assessment['job_level']}")
        if assessment.get('test_types'):
            parts.append(f"Test Types: {', '.join(assessment['test_types'])}")
        if assessment.get('skills'):
            parts.append(f"Skills: {', '.join(assessment['skills'])}")
        if assessment.get('duration'):
            parts.append(f"Duration: {assessment['duration']}")
        
        return ' | '.join(parts)
        
    
    def add_assessments(self, assessments: List[Dict[str, Any]]):
        print(f"\nAdding {len(assessments)} assessments to vector store.")
        ids = []
        documents = []
        metadatas = []

        for i,assessment in enumerate(assessments):
            ids.append(f"assessment_{i}")
            doc_text = self.create_assessment_text(assessment)
            documents.append(doc_text)
            metadata = {
                'name': assessment['name'],
                'url': assessment['url'],
                'description': assessment.get('description','')[:500],
                'test_types':', '.join(assessment.get('test_types',[])),
                'job_level': assessment.get('job_level',''),
                'skills':", ".join(assessment.get('skills',[])),
                'category': assessment.get('category',''),
            }
            metadatas.append(metadata)
    
        embeddings = self.model.encode(documents,show_progress_bar = True)

        print('Adding to ChromaDB...')
        self.collection.add(
            ids = ids,
            embeddings = embeddings.tolist(),
            documents = documents,
            metadatas = metadatas
        )

        print(f"Successfully added {len(assessments)} assessments")
        print(f"Total items in collections: {self.collection.count()}")

    def search(self, query: str, n_results: int = 5,filter_test_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        if n_results < 5:
            print(f"Results must be at least 5. Adjusting from {n_results} to 5")
            n_results = 5
        
        print(f"\nSearching for: '{query}'")
        query_embedding = self.model.encode([query])[0]
        where_filter = None
        if filter_test_types:
            pass 
            
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=n_results*2,
            include = ['metadatas','documents','distances']
        )

        assessments = []
        for i in range(len(results['ids'][0])):
            metadata = results['metadatas'][0][i]
            distance = results['distances'][0][i]

            if filter_test_types:
                assessment_types = metadata['test_types'].split(",")
                if not any(t in assessment_types for t in filter_test_types):
                    continue
            
            similarity_score = 1 - (distance / 2)

            assessment = {
                'name': metadata['name'],
                'url': metadata['url'],
                'description': metadata['description'],
                'test_types': metadata['test_types'].split(','),
                'job_level': metadata['job_level'],
                'skills': metadata['skills'].split(',') if metadata['skills'] else [],
                'category': metadata['category'],
                'similarity_score': round(similarity_score, 4),
                'distance': round(distance, 4)
            }
            assessments.append(assessment)
            if len(assessments) >= n_results:
                break
        print(f"Found {len(assessments)} matching assessments")
        return assessments
    
    def load_from_json(self, json_file: str = "shl_assessments.json"):
        if self.collection.count()>0:
            print(f"Collection has {self.collection.count()} items.")
            response = input("Clear and reload? (Y/N): ")
            if(response.lower() == 'y'):
                self.client.delete_collection(self.collection.name)
                self.collection = self.client.create_collection(
                    name = self.collection.name,
                    metadata = {
                        "description": "SHL Assessment embeddings",
                        "hnsw:space": "cosine"
                    }
                )
                print("Collection cleared")
            else:
                print("Keeping existing data")
                return
        with open(json_file,'r',encoding ='utf-8') as f:
            assessments = json.load(f)
        print(f"Loaded {len(assessments)} assessments from file")
        self.add_assessments(assessments)

def main():
    print("=== SHL Assessment Vector Store Test ===\n")
    
    store = AssessmentVectorStore()
    store.load_from_json()
    
    test_queries = [
        "I need an AI research intern who possess knowledge of RAG, LLM, and MCPs",
        "Looking for entry-level data analyst that has great communication skills",
        "Need someone with Python, SQL and data analysis skills",
        "Hiring for leadership and management positions",
    ]
    
    print("\n" + "="*60)
    print("TESTING SEARCH FUNCTIONALITY")
    print("="*60)
    
    for query in test_queries:
        print(f"\n{'='*60}")
        results = store.search(query, n_results=5)
        
        print(f"\nTop 5 results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['name']}")
            print(f"   Score: {result['similarity_score']}")
            print(f"   Types: {', '.join(result['test_types'])}")
            print(f"   Skills: {', '.join(result['skills'])}")
            print(f"   URL: {result['url']}")



if __name__ == "__main__":
    main()
