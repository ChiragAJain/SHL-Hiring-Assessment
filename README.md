# SHL Assessment Recommendation Engine

A Generative AI, FastAPI-integrated recommendation engine for assessments from the SHL product catalogue off of a natural query.

## What It Does

You describe a job role in plain English, and the system recommends the most relevant SHL assessments. It understands things like:
- Technical skills (Java, Python, SQL)
- Soft skills (communication, leadership, teamwork)
- Job levels (entry, mid, senior)
- Time constraints ("40 minutes", "1 hour")

## How It Works

The system uses a three-part approach:

1. **Semantic Search** - E5-large-v2 embeddings capture the meaning of your query
2. **Keyword Matching** - Direct matching for technical terms and skills
3. **LLM Analysis** - Gemini extracts structured requirements from natural language

These are combined with weighted ensemble scoring (35% semantic + 45% keyword + 20% metadata) to rank assessments.

## Performance

Tested on 90 real job queries:
- **Recall@10**: 23.33%
- **Recall@50**: 43.33%
- **Recall@100**: 46.44%

## Tech Stack

- **FastAPI** - API server
- **ChromaDB** - Vector database
- **Sentence Transformers** - E5-large-v2 embeddings (1024d)
- **Google Gemini** - Query analysis (gemini-2.0-flash-lite)
- **Python 3.10**

## Data Collection

The 377 SHL assessments in `shl_assessments.json` were collected using a custom web scraper built with Selenium. The scraper navigated through the SHL product catalogue, extracting:
- Assessment names and descriptions
- Test types (K, P, A, B, C, S)
- Required skills
- Job levels
- Duration estimates
- Product URLs

This data forms the foundation of our recommendation system.

## Setup

1. Clone the repo
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```
GEMINI_API_KEY=your_key_here
PORT=8000
```

4. Run the server:
```bash
python api.py
```

5. Open `index.html` in your browser or visit `http://localhost:8000`

## Deployment on Railway

The app is configured for one-click deployment on Railway:

1. Push to GitHub
2. Create new Project under Railway
3. Connect your repo
4. Add environment variable: `GEMINI_API_KEY`
5. Deploy (Railway auto-detects `procfile`)

Build takes about 5-10 minutes (downloads E5 model during build).

## API Usage

**POST /recommend**
```json
{
  "query": "I need a Java developer who can collaborate with business teams. Assessment should be 40 minutes.",
  "n_results": 10
}
```

**Response:**
```json
{
  "query": "...",
  "analysis": {
    "job_level": null,
    "required_skills": ["Java", "collaboration", "40 minutes"],
    "required_test_types": ["K", "P"],
    "role": "Java Developer"
  },
  "recommendations": [
    {
      "name": "Java Developer Test",
      "url": "https://...",
      "description": "...",
      "test_types": ["K"],
      "skills": ["Java", "Programming"],
      "similarity_score": 0.85,
      "final_score": 0.92
    }
  ]
}
```

## Project Structure

```
├── api.py                  # FastAPI server
├── vector_store.py         # Semantic search with E5-large-v2
├── query_analyser.py       # LLM query analysis
├── keyword_search.py       # Keyword matching engine
├── index.html              # Web interface
├── shl_assessments.json    # 377 SHL assessments
├── chroma_db/              # Vector database (created on first run)
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
└── runtime.txt             # Python version
```

## Development Notes

### Data Collection Process

Built a Selenium-based scraper to extract assessment data from the SHL website. The scraper handled:
- Dynamic page loading and JavaScript rendering
- Pagination across multiple product pages
- Structured data extraction from inconsistent HTML
- Rate limiting to avoid overwhelming the server

The result is a clean dataset of 377 assessments with standardized fields.

### Why E5-large-v2?

Initially tried BGE-M3 (2.27GB, 1024d) but it was slow to load. E5-large-v2 (1.3GB, 1024d) loads much faster with similar performance.

### The MCP Experiment

We explored using Model Context Protocol (MCP) to let the LLM directly query the vector database. The idea was to give Gemini more control over the search process.

**What I tried:**
- Created MCP server with tools for semantic search, keyword search, and metadata filtering
- Let Gemini decide which tools to use and how to combine results
- Hoped it would learn better search strategies

**Why it didn't work:**
- LLM tool calling added 2-3 seconds of latency
- Gemini's search strategy was inconsistent (sometimes only used one tool)
- Hard to debug when results were poor
- Lost control over the ensemble weighting
- The deterministic approach (fixed 35/45/20 weights) performed better

**Lesson learned:** LLMs are great for understanding queries, but search ranking is better handled by deterministic algorithms you can tune and debug.

### Ensemble Scoring Evolution

We tested different weight combinations:
- 50/30/20 (semantic heavy) - Good for vague queries, missed exact matches
- 30/50/20 (keyword heavy) - Good for technical terms, missed context
- **35/45/20 (balanced)** - Best overall performance ✓

The keyword component gets slightly more weight because technical skills (Java, Python, SQL) are critical for matching.

## Known Limitations

- Gemini API has rate limits (30 RPM on free tier)
- First query after deployment is slow (model loading)
- ChromaDB is in-memory, resets on restart (fine for 377 assessments)
- No user authentication
- Frontend is basic HTML/JS (no framework)

## Future Ideas

- Cache LLM analysis results
- Add assessment filtering by category
- Support for multiple languages
- User feedback loop to improve rankings
- A/B testing different ensemble weights

## License

MIT

---

Built as a learning project exploring semantic search, LLMs, and recommendation systems.
