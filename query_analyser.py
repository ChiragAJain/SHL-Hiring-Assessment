import os
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))


class QueryAnalyser:
    
    def __init__(self, model_name: str = "gemini-2.0-flash-lite"):
        self.model = genai.GenerativeModel(model_name)
        print(f"Query analyser initialized with {model_name}")

    
    def analyse_query(self, query: str) -> Dict:
        try:
            prompt = self._create_analysis_prompt(query)
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()

            if response_text.startswith("```json"):
                response_text = response_text.replace("```json","").replace("```","").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```","").strip()
            
            analysis = json.loads(response_text)
            return analysis
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print(f"Response was {response_text}")

            return {
                "job_level": None,
                "required_skills": [],
                "required_test_types": ["K", "P"],
                "role": "Unknown",
                "key_requirements": [],
                "search_query": query
            }
        except Exception as e:
            print(f"Error analysing query: {e}")
            return {
                "job_level": None,
                "required_skills": [],
                "required_test_types": ["K", "P"],
                "role": "Unknown",
                "key_requirements": [],
                "search_query": query
            }
       
    
    def _create_analysis_prompt(self, query: str) -> str:
        prompt = f"""You are an expert HR analyst. Your goal is to extract literal keywords to match a keyword-focused search engine. Return ONLY a valid JSON object.

Guidelines:
- job_level: Identify if the query mentions entry-level, junior, mid-level, senior, or executive. If not mentioned, use null.
- required_skills: Extract ALL literal technical skills, soft skills, and constraints (e.g., "Java", "communication", "SQL", "Excel", "Python", "40 minutes", "1 hour", "5 years").
- required_test_types: Determine NEEDED test types:
  * K = Knowledge & Skills (technical, programming, tools)
  * P = Personality & Behaviour (soft skills, teamwork)
  * A = Ability & Aptitude (problem-solving, analytical)
- search_query: Create a LITERAL keyword query. Combine the ENTIRE original query text with the extracted skills. DO NOT add synonyms. Be literal.

IMPORTANT: Always include BOTH K and P types when a role needs technical AND soft skills.

Here are some examples of perfect analysis:

---
Job Query: "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes."

JSON:
{{
  "job_level": null,
  "required_skills": ["Java", "collaboration", "business communication", "40 minutes"],
  "required_test_types": ["K", "P"],
  "role": "Java Developer",
  "key_requirements": ["Java technical skills", "effective collaboration", "40 minutes duration"],
  "search_query": "I am hiring for Java developers who can also collaborate effectively with my business teams. Looking for an assessment(s) that can be completed in 40 minutes. Java collaboration 40 minutes"
}}

---
Job Query: "I want to hire new graduates for a sales role in my company, the budget is for about an hour for each test."

JSON:
{{
  "job_level": "Entry Level",
  "required_skills": ["sales", "communication", "one hour", "1 hour"],
  "required_test_types": ["P", "C", "S"],
  "role": "Graduate Sales Role",
  "key_requirements": ["new graduates", "sales role", "1 hour duration"],
  "search_query": "I want to hire new graduates for a sales role in my company, the budget is for about an hour for each test. new graduates sales one hour 1 hour"
}}

---
Job Query: "I want to hire a Senior Data Analyst with 5 years of experience and expertise in SQL, Excel and Python."

JSON:
{{
  "job_level": "Senior Level",
  "required_skills": ["SQL", "Excel", "Python", "Data Analysis", "5 years"],
  "required_test_types": ["K", "A"],
  "role": "Senior Data Analyst",
  "key_requirements": ["5 years experience", "SQL", "Excel", "Python"],
  "search_query": "I want to hire a Senior Data Analyst with 5 years of experience and expertise in SQL, Excel and Python. Senior Data Analyst SQL Excel Python 5 years"
}}

---
Now, analyze the following query. Return ONLY the JSON object, nothing else.

Job Query: "{query}"

JSON:"""
        return prompt


def main():
    print("=== Query Analyzer Test ===\n")
    analyser = QueryAnalyser()
    
    # Test queries
    test_queries = [
        "Hiring for mid-level leadership and management positions with good knowledge on databases",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 60)
        
        analysis = analyser.analyse_query(query)
        
        print(f"Job Level: {analysis.get('job_level')}")
        print(f"Role: {analysis.get('role')}")
        print(f"Required Skills: {', '.join(analysis.get('required_skills', []))}")
        print(f"Required Test Types: {', '.join(analysis.get('required_test_types', []))}")
        print(f"Key Requirements: {', '.join(analysis.get('key_requirements', []))}")
        print()


if __name__ == "__main__":
    main()
