import json
import re
from typing import List, Dict, Set
from collections import Counter


class KeywordSearchEngine:
    
    def __init__(self, assessments_file: str = 'shl_assessments.json'):
        with open(assessments_file, 'r', encoding='utf-8') as f:
            self.assessments = json.load(f)
        
        print(f"Loaded {len(self.assessments)} assessments")
        self._build_index()
    
    def _build_index(self):
        for assessment in self.assessments:
            text_parts = [
                assessment.get('name', ''),
                assessment.get('description', ''),
                ' '.join(assessment.get('skills', [])),
                assessment.get('category', ''),
                assessment.get('job_level', ''),
                ' '.join(assessment.get('test_types', []))
            ]
            
            full_text = ' '.join(text_parts).lower()
            keywords = set(re.findall(r'\b\w+\b', full_text))
            
            assessment['_keywords'] = keywords
            assessment['_full_text'] = full_text
    
    def extract_query_keywords(self, query: str) -> Set[str]:
        query_lower = query.lower()
        words = re.findall(r'\b\w+\b', query_lower)
        
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'should', 'could', 'may', 'might', 'must', 'can',
                     'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between',
                     'into', 'through', 'during', 'before', 'after', 'above', 'below',
                     'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over',
                     'under', 'again', 'further', 'then', 'once', 'here', 'there',
                     'when', 'where', 'why', 'how', 'all', 'both', 'each', 'few',
                     'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
                     'only', 'own', 'same', 'so', 'than', 'too', 'very', 'i', 'me',
                     'my', 'we', 'our', 'you', 'your', 'he', 'him', 'his', 'she',
                     'her', 'it', 'its', 'they', 'them', 'their', 'what', 'which',
                     'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'if',
                     'or', 'as', 'until', 'while', 'but', 'because', 'and'}
        
        keywords = set(w for w in words if w not in stop_words and len(w) > 2)
        
        return keywords
    
    def extract_metadata(self, query: str) -> Dict:
        query_lower = query.lower()
        
        metadata = {
            'job_level': None,
            'duration': None,
            'test_types': []
        }
        
        if any(term in query_lower for term in ['entry level', 'entry-level', 'graduate', 'new grad']):
            metadata['job_level'] = 'Entry Level'
        elif any(term in query_lower for term in ['senior', 'lead', 'principal']):
            metadata['job_level'] = 'Senior Level'
        elif any(term in query_lower for term in ['mid level', 'mid-level', 'intermediate']):
            metadata['job_level'] = 'Mid Level'
        elif any(term in query_lower for term in ['executive', 'ceo', 'coo', 'cfo', 'cto', 'vp', 'director']):
            metadata['job_level'] = 'Executive'
        
        if any(term in query_lower for term in ['40 minutes', 'forty minutes', '40 mins']):
            metadata['duration'] = '40'
        elif any(term in query_lower for term in ['1 hour', 'one hour', '60 minutes']):
            metadata['duration'] = '60'
        elif any(term in query_lower for term in ['30 minutes', 'thirty minutes', '30 mins']):
            metadata['duration'] = '30'
        
        if any(term in query_lower for term in ['java', 'python', 'sql', 'programming', 'technical', 'coding']):
            metadata['test_types'].append('K')
        
        if any(term in query_lower for term in ['personality', 'behavioral', 'teamwork', 'collaboration', 
                                                 'communication', 'interpersonal', 'leadership', 'cultural']):
            metadata['test_types'].append('P')
        
        if any(term in query_lower for term in ['problem solving', 'analytical', 'reasoning', 'aptitude']):
            metadata['test_types'].append('A')
        
        return metadata
    
    def search(self, query: str, n_results: int = 10) -> List[Dict]:
        query_keywords = self.extract_query_keywords(query)
        metadata = self.extract_metadata(query)
        query_lower = query.lower()
        
        print(f"\nQuery keywords: {list(query_keywords)[:10]}")
        print(f"Metadata: {metadata}")
        
        programming_languages = {
            'java', 'python', 'javascript', 'sql', 'c++', 'c#', 'php', 'ruby',
            'swift', 'kotlin', 'go', 'rust', 'typescript', 'scala', 'r', 'matlab',
            'perl', 'shell', 'bash', 'powershell', 'html', 'css', 'react', 'angular',
            'vue', 'node', 'django', 'flask', 'spring', 'hibernate', '.net', 'asp'
        }
        
        roles = {
            'developer', 'engineer', 'analyst', 'manager', 'director', 'ceo', 'coo',
            'cfo', 'cto', 'architect', 'consultant', 'specialist', 'administrator',
            'coordinator', 'lead', 'senior', 'junior', 'intern', 'associate',
            'executive', 'officer', 'designer', 'tester', 'qa', 'devops', 'data'
        }
        
        soft_skills = {
            'communication', 'leadership', 'teamwork', 'collaboration', 'interpersonal',
            'problem-solving', 'analytical', 'creative', 'adaptability', 'flexibility',
            'cultural', 'personality', 'behavioral', 'emotional', 'intelligence'
        }
        
        scored_assessments = []
        
        for assessment in self.assessments:
            score = 0.0
            
            name_lower = assessment.get('name', '').lower()
            assessment_keywords = assessment['_keywords']
            assessment_skills = [s.lower() for s in assessment.get('skills', [])]
            
            for lang in programming_languages:
                if lang in query_lower:
                    if lang in name_lower:
                        score += 5.0
                    elif lang in assessment_skills:
                        score += 3.0
                    elif lang in assessment_keywords:
                        score += 2.0
            
            for role in roles:
                if role in query_lower:
                    if role in name_lower:
                        score += 4.0
                    elif role in assessment_keywords:
                        score += 2.0
            
            for skill in soft_skills:
                if skill in query_lower:
                    if skill in name_lower:
                        score += 3.0
                    elif skill in assessment_keywords:
                        score += 1.5
            
            experience_patterns = ['years', 'year', 'experience', 'yrs']
            if any(pattern in query_lower for pattern in experience_patterns):
                import re
                numbers = re.findall(r'\b(\d+)\s*(?:years?|yrs?)\b', query_lower)
                if numbers:
                    if 'senior' in assessment.get('job_level', '').lower():
                        score += 2.0
                    elif 'mid' in assessment.get('job_level', '').lower():
                        score += 1.0
            
            if metadata['job_level']:
                assessment_level = assessment.get('job_level', '')
                if metadata['job_level'].lower() in assessment_level.lower():
                    score += 2.0
            
            if metadata['duration']:
                assessment_duration = assessment.get('duration', '')
                if metadata['duration'] in assessment_duration:
                    score += 1.5
            
            if metadata['test_types']:
                assessment_types = assessment.get('test_types', [])
                type_matches = set(metadata['test_types']) & set(assessment_types)
                score += len(type_matches) * 1.0
            
            keyword_matches = query_keywords & assessment_keywords
            score += len(keyword_matches) * 0.5
            
            for keyword in query_keywords:
                if len(keyword) > 3 and keyword in name_lower:
                    score += 3.0
            
            assessment['_score'] = score
            scored_assessments.append(assessment)
        
        scored_assessments.sort(key=lambda x: x['_score'], reverse=True)
        
        results = []
        for assessment in scored_assessments[:n_results]:
            result = {
                'name': assessment['name'],
                'url': assessment['url'],
                'description': assessment['description'],
                'test_types': assessment['test_types'],
                'job_level': assessment['job_level'],
                'skills': assessment['skills'],
                'category': assessment['category'],
                'duration': assessment.get('duration', ''),
                'similarity_score': min(assessment['_score'] / 20.0, 1.0),
                'distance': max(1.0 - (assessment['_score'] / 20.0), 0.0),
                'final_score': assessment['_score']
            }
            results.append(result)
        
        return results


def test_search():
    engine = KeywordSearchEngine()
    
    test_queries = [
        "I am hiring for Java developers who can also collaborate effectively with my business teams.",
        "I want to hire a Senior Data Analyst with 5 years of experience and expertise in SQL, Excel and Python.",
        "I want to hire new graduates for a sales role in my company, the budget is for about an hour for each test.",
        "I am looking for a COO for my company in China and I want to see if they are culturally a right fit."
    ]
    
    for query in test_queries:
        print("\n" + "="*80)
        print(f"Query: {query}")
        print("="*80)
        
        results = engine.search(query, n_results=5)
        
        print(f"\nTop 5 Results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['name']}")
            print(f"   Score: {result['final_score']:.2f}")
            print(f"   Types: {result['test_types']}")
            print(f"   Skills: {result['skills'][:5]}")


if __name__ == "__main__":
    test_search()
