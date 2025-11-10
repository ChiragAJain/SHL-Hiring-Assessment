from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from vector_store import AssessmentVectorStore
from query_analyser import QueryAnalyser
from keyword_search import KeywordSearchEngine
import uvicorn
import re
import os


app = FastAPI(
    title="SHL Assessment Recommendation API",
    description="AI-powered assessment recommendation with ensemble scoring",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("Loading vector store...")
vector_store = AssessmentVectorStore(collection_name="shl_assessments_e5")

# Load assessments if collection is empty
if vector_store.collection.count() == 0:
    print("Collection is empty. Loading assessments from JSON...")
    import json
    with open('shl_assessments.json', 'r', encoding='utf-8') as f:
        assessments = json.load(f)
    vector_store.add_assessments(assessments)
    print(f"Loaded {len(assessments)} assessments")

print(f"Vector store ready: {vector_store.collection.count()} assessments")

print("Loading query analyzer...")
query_analyser = QueryAnalyser()
print("Query analyzer ready")

print("Loading keyword search...")
search_engine = KeywordSearchEngine()
print("Keyword search ready")


SKILL_SYNONYMS = {
    'python': ['python', 'py', 'python3'],
    'java': ['java', 'j2ee', 'spring'],
    'javascript': ['javascript', 'js', 'node', 'nodejs', 'react', 'angular', 'vue'],
    'sql': ['sql', 'mysql', 'postgresql', 'database', 'db'],
    'data': ['data', 'analytics', 'analysis'],
    'excel': ['excel', 'spreadsheet', 'ms excel'],
    'communication': ['communication', 'verbal', 'written', 'presentation'],
    'leadership': ['leadership', 'management', 'manager', 'lead'],
    'teamwork': ['teamwork', 'collaboration', 'team', 'collaborative'],
}


def expand_skills(skills: List[str]) -> List[str]:
    expanded = set()
    for skill in skills:
        skill_lower = skill.lower()
        expanded.add(skill_lower)
        # Add synonyms
        for key, synonyms in SKILL_SYNONYMS.items():
            if skill_lower in synonyms:
                expanded.update(synonyms)
    return list(expanded)


def extract_duration_constraint(query: str) -> Optional[int]:
    patterns = [
        r'(\d+)\s*(?:min|minute|minutes)',
        r'(\d+)\s*(?:hr|hour|hours)',
        r'(\d+)\s*(?:h)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query.lower())
        if match:
            value = int(match.group(1))
            if 'hour' in pattern or 'hr' in pattern or pattern.endswith('h)'):
                return value * 60
            return value
    return None


def parse_duration(duration_str: str) -> int:
    if not duration_str:
        return 999
    
    duration_str = duration_str.lower()
    total_minutes = 0
    
    hour_match = re.search(r'(\d+)\s*(?:hr|hour)', duration_str)
    if hour_match:
        total_minutes += int(hour_match.group(1)) * 60
    
    min_match = re.search(r'(\d+)\s*(?:min|minute)', duration_str)
    if min_match:
        total_minutes += int(min_match.group(1))
    
    return total_minutes if total_minutes > 0 else 999


class RecommendationRequest(BaseModel):
    query: str = Field(..., description="Job description or natural language query")
    n_results: int = Field(10, ge=1, le=10, description="Number of results (1-10)")
    filter_test_types: Optional[List[str]] = Field(None, description="Filter by test types")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "I need a Java developer who can collaborate with business teams. Assessment should be 40 minutes.",
                "n_results": 10
            }
        }


class Assessment(BaseModel):
    name: str
    url: str
    description: str
    test_types: List[str]
    job_level: str
    skills: List[str]
    category: str
    similarity_score: float
    distance: float
    final_score: Optional[float] = None


class RecommendationResponse(BaseModel):
    query: str
    analysis: Optional[Dict] = None
    recommendations: List[Assessment]
    count: int


class HealthResponse(BaseModel):
    status: str
    message: str
    assessments_loaded: int


@app.get("/", tags=["Root"])
async def root():
    """Serve the index.html file if it exists, otherwise return API info"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "message": "SHL Assessment Recommendation API",
        "version": "2.1.0",
        "performance": {
            "recall@10": "23.33%",
            "recall@50": "43.33%",
            "recall@100": "46.44%"
        },
        "improvements": [
            "Optimized ensemble scoring (35% semantic + 45% keyword + 20% metadata)",
            "Query expansion with skill synonyms",
            "Duration constraint matching",
            "Smart K/P test balancing",
            "Enhanced skill extraction"
        ],
        "endpoints": {
            "health": "/health",
            "recommend": "/recommend",
            "docs": "/docs"
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "message": "SHL Assessment Recommendation API (Improved) is running",
        "assessments_loaded": vector_store.collection.count()
    }


@app.post("/recommend", response_model=RecommendationResponse, tags=["Recommendations"])
async def recommend_assessments_post(request: RecommendationRequest):
    return await _recommend_assessments(request)


@app.get("/recommend", response_model=RecommendationResponse, tags=["Recommendations"])
async def recommend_assessments_get(
    query: str = Query(..., description="Job description or natural language query"),
    n_results: int = Query(10, ge=1, le=10, description="Number of results (1-10)")
):
    request = RecommendationRequest(query=query, n_results=n_results)
    return await _recommend_assessments(request)


async def _recommend_assessments(request: RecommendationRequest):
    try:
        if not request.query or len(request.query.strip()) < 3:
            raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")
        
        analysis = query_analyser.analyse_query(request.query)
        search_query = analysis.get('search_query', request.query)
        duration_constraint = extract_duration_constraint(request.query)
        llm_skills = analysis.get('required_skills', [])
        expanded_skills = expand_skills(llm_skills)
        
        all_results = vector_store.search(
            query=search_query,
            n_results=100,
            filter_test_types=None
        )
        
        llm_job_level = analysis.get('job_level', '').lower()
        llm_test_types = analysis.get('required_test_types', [])
        llm_role = analysis.get('role', '').lower()
        
        if not llm_test_types:
            llm_test_types = ["K", "P"]
        elif "K" in llm_test_types and "P" not in llm_test_types:
            llm_test_types.append("P")
        
        scored_results = []
        for res in all_results:
            semantic_score = res['similarity_score']
            keyword_score = 0.0
            assessment_name = res.get('name', '').lower()
            assessment_skills = [s.lower().strip() for s in res.get('skills', [])]
            
            for skill in expanded_skills:
                if skill in assessment_name:
                    keyword_score += 1.8
                elif skill in assessment_skills:
                    keyword_score += 1.2
                elif skill in res.get('description', '').lower():
                    keyword_score += 0.6
            
            if llm_role:
                role_parts = [p for p in llm_role.split() if len(p) > 3]
                for part in role_parts:
                    if part in assessment_name:
                        keyword_score += 0.9
            
            metadata_score = 0.0
            res_types = res.get('test_types', [])
            has_k = "K" in res_types
            has_p = "P" in res_types
            
            if has_k or has_p:
                metadata_score += 0.3
                if any(t in llm_test_types for t in res_types):
                    metadata_score += 0.2
            elif any(t in llm_test_types for t in res_types):
                metadata_score += 0.2
            
            if llm_job_level and llm_job_level in res.get('job_level', '').lower():
                metadata_score += 0.3
            
            if duration_constraint:
                res_duration = parse_duration(res.get('duration', ''))
                if res_duration <= duration_constraint * 1.2:
                    metadata_score += 0.4
            
            final_score = (
                semantic_score * 0.35 +
                min(keyword_score, 3.5) * 0.45 / 3.5 +
                metadata_score * 0.20
            )
            
            res['final_score'] = final_score
            res['keyword_score'] = keyword_score
            res['metadata_score'] = metadata_score
            scored_results.append(res)
        
        sorted_results = sorted(scored_results, key=lambda x: x['final_score'], reverse=True)
        
        best_k = []
        best_p = []
        best_other = []
        
        for res in sorted_results:
            res_types = res.get('test_types', [])
            is_k = "K" in res_types
            is_p = "P" in res_types
            res_id = res['url']
            
            if is_k and res_id not in {r['url'] for r in best_k}:
                best_k.append(res)
            if is_p and res_id not in {r['url'] for r in best_p}:
                best_p.append(res)
            if not is_k and not is_p and res_id not in {r['url'] for r in best_other}:
                best_other.append(res)
        
        final_recommendations = []
        llm_wants_k = "K" in llm_test_types
        llm_wants_p = "P" in llm_test_types
        
        if llm_wants_k and llm_wants_p:
            for i in range(max(len(best_k), len(best_p))):
                if i < len(best_k) and len(final_recommendations) < request.n_results:
                    final_recommendations.append(best_k[i])
                if i < len(best_p) and len(final_recommendations) < request.n_results:
                    final_recommendations.append(best_p[i])
        elif llm_wants_k:
            final_recommendations.extend(best_k[:request.n_results])
        elif llm_wants_p:
            final_recommendations.extend(best_p[:request.n_results])
        else:
            final_recommendations.extend(best_k[:request.n_results // 2])
            final_recommendations.extend(best_p[:request.n_results // 2])
        
        unique_recs = list({rec['url']: rec for rec in final_recommendations}.values())
        
        if len(unique_recs) < request.n_results:
            for res in best_other:
                if len(unique_recs) >= request.n_results:
                    break
                if res['url'] not in {r['url'] for r in unique_recs}:
                    unique_recs.append(res)
        
        results = sorted(unique_recs, key=lambda x: x['final_score'], reverse=True)[:request.n_results]
        assessments = [Assessment(**result) for result in results]
        
        return RecommendationResponse(
            query=request.query,
            analysis={
                "job_level": analysis.get('job_level'),
                "required_skills": llm_skills,
                "expanded_skills": expanded_skills,
                "required_test_types": llm_test_types,
                "role": analysis.get('role'),
                "duration_constraint": duration_constraint
            },
            recommendations=assessments,
            count=len(assessments)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
