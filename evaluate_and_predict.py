"""
Evaluate on training data and generate predictions for test data
Reads from GenAI Dataset Excel file
"""

import pandas as pd
import csv
import json
from vector_store import AssessmentVectorStore
from query_analyser import QueryAnalyser
import re
from typing import List, Dict, Set

# Configuration
DATASET_FILE = "Gen_AI Dataset.xlsx"
TRAIN_SHEET = "Train-Set"
TEST_SHEET = "Test-Set"
OUTPUT_FILE = "chirag_jain.csv"

# Skill synonyms for query expansion
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
        for key, synonyms in SKILL_SYNONYMS.items():
            if skill_lower in synonyms:
                expanded.update(synonyms)
    return list(expanded)


def extract_duration_constraint(query: str):
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


def get_recommendations_local(query: str, n_results: int = 10) -> List[str]:
    """Get recommendations using local engine"""
    
    # Analyze query
    try:
        if query_analyser:
            analysis = query_analyser.analyse_query(query)
        else:
            analysis = {'search_query': query, 'required_skills': [], 'required_test_types': ['K', 'P'], 'job_level': '', 'role': ''}
    except Exception as e:
        print(f"    Warning: LLM analysis failed: {str(e)}")
        analysis = {'search_query': query, 'required_skills': [], 'required_test_types': ['K', 'P'], 'job_level': '', 'role': ''}
    
    search_query = analysis.get('search_query', query)
    duration_constraint = extract_duration_constraint(query)
    llm_skills = analysis.get('required_skills', [])
    expanded_skills = expand_skills(llm_skills)
    
    # Retrieve results
    all_results = vector_store.search(
        query=search_query,
        n_results=100,
        filter_test_types=None
    )
    
    # Ensemble scoring
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
        scored_results.append(res)
    
    # Sort by score
    sorted_results = sorted(scored_results, key=lambda x: x['final_score'], reverse=True)
    
    # K/P balancing
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
            if i < len(best_k) and len(final_recommendations) < n_results:
                final_recommendations.append(best_k[i])
            if i < len(best_p) and len(final_recommendations) < n_results:
                final_recommendations.append(best_p[i])
    elif llm_wants_k:
        final_recommendations.extend(best_k[:n_results])
    elif llm_wants_p:
        final_recommendations.extend(best_p[:n_results])
    else:
        final_recommendations.extend(best_k[:n_results // 2])
        final_recommendations.extend(best_p[:n_results // 2])
    
    unique_recs = list({rec['url']: rec for rec in final_recommendations}.values())
    
    if len(unique_recs) < n_results:
        for res in best_other:
            if len(unique_recs) >= n_results:
                break
            if res['url'] not in {r['url'] for r in unique_recs}:
                unique_recs.append(res)
    
    results = sorted(unique_recs, key=lambda x: x['final_score'], reverse=True)[:n_results]
    
    # Return URLs
    return [r['url'] for r in results]


def calculate_recall_at_k(predicted: List[str], ground_truth: List[str], k: int = 10) -> float:
    """Calculate Recall@K"""
    if not ground_truth:
        return 0.0
    
    predicted_set = set(predicted[:k])
    ground_truth_set = set(ground_truth)
    
    hits = len(predicted_set & ground_truth_set)
    return hits / len(ground_truth_set)


def evaluate_on_training_data(train_df: pd.DataFrame) -> float:
    """Evaluate Recall@10 on training data"""
    print("="*60)
    print("Evaluating on Training Data")
    print("="*60)
    print()
    
    # Group by query to get all ground truth URLs
    query_groups = train_df.groupby('Query')['Assessment_url'].apply(list).to_dict()
    
    recall_scores = []
    
    for idx, (query, ground_truth) in enumerate(query_groups.items(), 1):
        if not ground_truth:
            continue
        
        print(f"[{idx}/{len(query_groups)}] Query: {query[:60]}...")
        print(f"  Ground truth: {len(ground_truth)} URLs")
        
        try:
            predicted = get_recommendations_local(query, n_results=10)
            recall = calculate_recall_at_k(predicted, ground_truth, k=10)
            recall_scores.append(recall)
            print(f"  Recall@10: {recall:.4f}")
        except Exception as e:
            print(f"  Error: {str(e)}")
        
        print()
    
    mean_recall = sum(recall_scores) / len(recall_scores) if recall_scores else 0.0
    
    print("="*60)
    print(f"Mean Recall@10: {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    print(f"Evaluated on {len(recall_scores)} queries")
    print("="*60)
    print()
    
    return mean_recall


def generate_test_predictions(test_df: pd.DataFrame, output_file: str):
    """Generate predictions for test data in long format"""
    print("="*60)
    print("Generating Test Predictions")
    print("="*60)
    print()
    
    all_rows = []
    
    for idx, row in test_df.iterrows():
        query = row['Query']  # Column name is 'Query'
        
        print(f"[{idx+1}/{len(test_df)}] Query: {query[:60]}...")
        
        try:
            urls = get_recommendations_local(query, n_results=10)
            
            # Create one row per recommendation
            for url in urls:
                if url:  # Only add non-empty URLs
                    all_rows.append({
                        'Query': query,
                        'Assessment_url': url
                    })
            
            print(f"  [OK] Got {len(urls)} recommendations")
        except Exception as e:
            print(f"  [ERROR] {str(e)}")
        
        print()
    
    # Write to CSV in long format
    print(f"Writing results to {output_file}...")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['Query', 'Assessment_url'])
        
        # Data - one row per recommendation
        for row_data in all_rows:
            writer.writerow([row_data['Query'], row_data['Assessment_url']])
    
    print(f"[OK] Successfully created {output_file}")
    print(f"  Total rows: {len(all_rows)}")
    print(f"  Format: Long format (one row per recommendation)")
    print()


def main():
    """Main function"""
    global vector_store, query_analyser
    
    print("="*60)
    print("SHL Assessment Evaluation & Prediction")
    print("="*60)
    print()
    
    # Check if dataset file exists
    try:
        print(f"Loading dataset from {DATASET_FILE}...")
        train_df = pd.read_excel(DATASET_FILE, sheet_name=TRAIN_SHEET)
        test_df = pd.read_excel(DATASET_FILE, sheet_name=TEST_SHEET)
        print(f"[OK] Loaded {len(train_df)} training queries")
        print(f"[OK] Loaded {len(test_df)} test queries")
        print()
    except FileNotFoundError:
        print(f"[ERROR] {DATASET_FILE} not found!")
        print()
        print("Please:")
        print(f"1. Place the GenAI Dataset Excel file in this directory")
        print(f"2. Update DATASET_FILE variable in this script if filename is different")
        print(f"3. Update TRAIN_SHEET and TEST_SHEET if sheet names are different")
        return
    except Exception as e:
        print(f"[ERROR] Loading dataset: {str(e)}")
        return
    
    # Initialize components
    print("Loading vector store...")
    try:
        vector_store = AssessmentVectorStore(collection_name="shl_assessments_e5")
        print("Vector store initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize vector store: {e}")
        return
    
    # Check if assessments are already loaded
    try:
        print("Checking collection count...")
        count = vector_store.collection.count()
        print(f"[OK] Vector store has {count} assessments")
        
        if count == 0:
            print("[WARNING] Collection is empty. Please run vector_store.py first to load assessments.")
            print("Attempting to load now...")
            with open('shl_assessments.json', 'r', encoding='utf-8') as f:
                assessments = json.load(f)
            print(f"Loaded {len(assessments)} assessments from file")
            print("Adding to vector store (this may take 5-10 minutes)...")
            vector_store.add_assessments(assessments)
            print(f"[OK] Successfully added {len(assessments)} assessments")
        elif count < 300:
            print(f"[WARNING] Only {count} assessments found. Expected ~377.")
    except Exception as e:
        print(f"[ERROR] Failed to check/load assessments: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("Loading query analyzer...")
    try:
        query_analyser = QueryAnalyser()
        print("Query analyzer ready")
    except Exception as e:
        print(f"[ERROR] Loading query analyzer: {str(e)}")
        print("Continuing without LLM analysis (will use basic keyword matching)")
        query_analyser = None
    print()
    
    # Evaluate on training data
    mean_recall = evaluate_on_training_data(train_df)
    
    # Generate test predictions
    generate_test_predictions(test_df, OUTPUT_FILE)
    
    print("="*60)
    print("Summary")
    print("="*60)
    print(f"Mean Recall@10 (Training): {mean_recall:.4f} ({mean_recall*100:.2f}%)")
    print(f"Test Predictions: {OUTPUT_FILE}")
    print("="*60)


if __name__ == "__main__":
    main()
