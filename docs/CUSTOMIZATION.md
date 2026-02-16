# 🎨 Customization Guide

This guide explains how to customize Job Finder to match your specific job search criteria, skills, and preferences.

---

## Table of Contents

- [Profile Configuration](#profile-configuration)
- [Scoring Rules](#scoring-rules)
- [Tech Dictionary](#tech-dictionary)
- [Filter Settings](#filter-settings)
- [Advanced Customization](#advanced-customization)
- [Examples & Use Cases](#examples--use-cases)

---

## Profile Configuration

### Location: `config/profile.yaml`

Your profile defines what you're looking for and how jobs should be scored against your criteria.

### Basic Structure

```yaml
name: "Your Name"
roles:
  - "Backend Developer"
  - "Software Engineer"
  - "Python Developer"

skills:
  - name: "Python"
    experience_years: 5
    proficiency: 9
  - name: "FastAPI"
    experience_years: 3
    proficiency: 8

preferences:
  remote: "yes"
  locations:
    - "Berlin"
    - "Munich"
    - "Remote"
  contract_types:
    - "Festanstellung"
    - "Freiberuflich"

profile_text: |
  Senior Backend Developer with 5+ years of experience in Python...
```

### Skills Configuration

**Fields**:
- `name` (required): Technology name (must match tech_dictionary.json)
- `experience_years` (required): Years of experience (0-20+)
- `proficiency` (required): Self-rated skill level (1-10)

**Example**:

```yaml
skills:
  # High proficiency, lots of experience
  - name: "C#"
    experience_years: 7
    proficiency: 10
  
  # Learning/junior level
  - name: "Kubernetes"
    experience_years: 1
    proficiency: 5
  
  # Expert level
  - name: "PostgreSQL"
    experience_years: 8
    proficiency: 9
```

**Tips**:
- Add ALL technologies you've worked with (even briefly)
- Be honest with proficiency (affects scoring accuracy)
- Include frameworks, not just languages
- Consider related skills (e.g., Django + Flask + FastAPI)

### Preferences

**Remote Work**:
```yaml
preferences:
  remote: "yes"      # Full remote preferred
  # remote: "hybrid" # 1-3 days onsite OK
  # remote: "no"     # Onsite only
```

**Locations**:
```yaml
preferences:
  locations:
    - "Remote"           # Remote-first
    - "Berlin"           # Willing to work in Berlin
    - "Munich"           # Or Munich
    - "Hamburg"          # Or Hamburg
```

**Contract Types**:
```yaml
preferences:
  contract_types:
    - "Festanstellung"   # Full-time employment
    - "Freiberuflich"    # Freelance
    # - "Teilzeit"       # Part-time
    # - "Werkvertrag"    # Contract work
```

### Profile Text

This is your "elevator pitch" - used for TF-IDF semantic matching.

**Good Example**:

```yaml
profile_text: |
  Senior Backend Developer with 8+ years of experience building scalable 
  microservices in Python and C#. Expert in FastAPI, Django, .NET Core, 
  PostgreSQL, Redis, and Docker. Strong knowledge of cloud platforms (AWS, Azure) 
  and CI/CD pipelines. Passionate about clean code, TDD, and DevOps practices.
  
  Looking for remote backend or full-stack roles in fintech, e-commerce, or SaaS 
  companies. Prefer agile teams with strong engineering culture.
```

**Tips**:
- Write 3-5 sentences (~100-200 words)
- Include ALL technologies you know
- Mention industries/domains you prefer
- Add soft skills and methodologies (Agile, TDD, etc.)
- Use keywords that appear in job descriptions

---

## Scoring Rules

### Location: `config/scoring_rules.yaml`

Scoring rules control how jobs are evaluated and ranked (0-100 scale).

### Component Weights

```yaml
weights:
  tfidf_similarity: 40         # Semantic match (0-40 points)
  tech_stack_match: 30         # Technology matching (0-30 points)
  remote_priority: 15          # Remote work (0-15 points)
  keyword_match: 10            # Keywords (0-10 points)
  contract_type: 5             # Contract type (0-5 points)

# Total = 100 points
```

**Customization Scenarios**:

1. **Prioritize Tech Stack**:
```yaml
weights:
  tfidf_similarity: 30
  tech_stack_match: 40    # Focus on matching technologies
  remote_priority: 15
  keyword_match: 10
  contract_type: 5
```

2. **Remote-First Focus**:
```yaml
weights:
  tfidf_similarity: 35
  tech_stack_match: 25
  remote_priority: 25     # Strong preference for remote
  keyword_match: 10
  contract_type: 5
```

3. **Semantic Matching Priority**:
```yaml
weights:
  tfidf_similarity: 50    # Maximize overall description match
  tech_stack_match: 20
  remote_priority: 15
  keyword_match: 10
  contract_type: 5
```

### Tech Stack Scoring

Define which technologies give bonus/penalty points:

```yaml
tech_stack:
  high_value:
    - name: "Python"
      points: 10          # +10 points if Python mentioned
    - name: "FastAPI"
      points: 8
    - name: "Docker"
      points: 7
    - name: "Kubernetes"
      points: 6
    - name: "PostgreSQL"
      points: 5
  
  negative:
    - name: "PHP"
      points: -5          # -5 points if PHP mentioned
    - name: "jQuery"
      points: -3
    - name: "WordPress"
      points: -8
```

**Best Practices**:
- List 10-15 high-value techs
- Use higher points for must-have skills
- Negative points for dealbreakers
- Keep points balanced (don't overshadow other components)

**Example Scenarios**:

1. **React Developer**:
```yaml
tech_stack:
  high_value:
    - name: "React"
      points: 12
    - name: "TypeScript"
      points: 10
    - name: "Next.js"
      points: 8
    - name: "GraphQL"
      points: 7
    - name: "Jest"
      points: 5
  
  negative:
    - name: "Angular"
      points: -4
    - name: "Vue"
      points: -3
```

2. **DevOps Engineer**:
```yaml
tech_stack:
  high_value:
    - name: "Kubernetes"
      points: 12
    - name: "Terraform"
      points: 10
    - name: "Docker"
      points: 9
    - name: "AWS"
      points: 8
    - name: "Ansible"
      points: 7
```

### Keywords Scoring

Define positive and negative keywords to filter jobs:

```yaml
keywords:
  positive:
    - keyword: "senior"
      points: 3
    - keyword: "remote"
      points: 3
    - keyword: "flexible hours"
      points: 2
    - keyword: "agile"
      points: 2
    - keyword: "startup"
      points: 2
    - keyword: "scale-up"
      points: 2
  
  negative:
    - keyword: "junior"
      points: -4
    - keyword: "intern"
      points: -5
    - keyword: "onsite required"
      points: -5
    - keyword: "50% travel"
      points: -6
    - keyword: "legacy"
      points: -3
```

**Tips**:
- Case-insensitive matching
- Use phrases (multi-word) for specificity
- Add domain-specific terms (e.g., "fintech", "e-commerce")
- Include soft skills you value ("TDD", "code review")

### Remote Priority Scoring

Built-in remote scoring (can't be customized directly, but affects weight):

```python
# Internal scoring logic
remote_scores = {
    "100% Remote": 15,
    "Hybrid (1-2 days onsite)": 12,
    "Hybrid (3+ days onsite)": 8,
    "Onsite": 0
}
```

**Adjust via weight**:
- Set `remote_priority: 25` if remote is critical
- Set `remote_priority: 5` if you're flexible

---

## Tech Dictionary

### Location: `config/tech_dictionary.json`

The tech dictionary contains 200+ technologies for extraction from job descriptions.

### Structure

```json
{
  "languages": {
    "Python": ["Python", "python", "py"],
    "C#": ["C#", "CSharp", "C Sharp", "csharp"],
    "TypeScript": ["TypeScript", "TS", "typescript"]
  },
  "frameworks": {
    ".NET": [".NET", "dotnet", ".NET Core", ".NET Framework", "ASP.NET"],
    "Django": ["Django", "django"],
    "FastAPI": ["FastAPI", "fastapi", "Fast API"]
  },
  "databases": {
    "PostgreSQL": ["PostgreSQL", "Postgres", "postgres", "PSQL"],
    "MongoDB": ["MongoDB", "mongo", "Mongo DB"]
  }
}
```

### Adding New Technologies

1. **Find the right category**:
   - `languages`: Python, Java, C#, TypeScript, etc.
   - `frameworks`: React, Django, .NET, Spring, etc.
   - `databases`: PostgreSQL, MongoDB, Redis, etc.
   - `cloud`: AWS, Azure, GCP, Heroku, etc.
   - `devops`: Docker, Kubernetes, Jenkins, etc.
   - `tools`: Git, VS Code, Postman, etc.

2. **Add aliases** (all possible names):

```json
{
  "databases": {
    "PostgreSQL": [
      "PostgreSQL",
      "Postgres",
      "postgres",
      "PSQL",
      "psql",
      "pg"
    ]
  }
}
```

3. **Update your profile** to include the new tech:

```yaml
skills:
  - name: "PostgreSQL"   # Must match key in tech_dictionary.json
    experience_years: 5
    proficiency: 9
```

### Example: Adding Machine Learning Tools

```json
{
  "ml_frameworks": {
    "TensorFlow": ["TensorFlow", "tensorflow", "tf", "TF"],
    "PyTorch": ["PyTorch", "pytorch", "torch"],
    "scikit-learn": ["scikit-learn", "sklearn", "sci-kit learn"],
    "Keras": ["Keras", "keras"]
  },
  "ml_tools": {
    "Jupyter": ["Jupyter", "jupyter", "Jupyter Notebook", "JupyterLab"],
    "MLflow": ["MLflow", "mlflow", "ML Flow"],
    "Weights & Biases": ["Weights & Biases", "wandb", "W&B"]
  }
}
```

**Then add to profile**:

```yaml
skills:
  - name: "TensorFlow"
    experience_years: 3
    proficiency: 8
  - name: "PyTorch"
    experience_years: 2
    proficiency: 7
```

**And scoring rules**:

```yaml
tech_stack:
  high_value:
    - name: "TensorFlow"
      points: 10
    - name: "PyTorch"
      points: 10
```

---

## Filter Settings

### Location: `config/settings.py`

Environment-level filters applied before scoring.

### Available Filters

```python
# In .env file
MIN_SCORE=40                  # Only show jobs scoring ≥40
MAX_JOB_AGE_DAYS=30          # Ignore jobs posted >30 days ago
LOCATION_FILTER=Berlin,Remote # Only these locations
CONTRACT_FILTER=Festanstellung # Only this contract type
```

**Examples**:

1. **Strict Filtering** (for experienced devs):
```env
MIN_SCORE=60
MAX_JOB_AGE_DAYS=7
LOCATION_FILTER=Remote
CONTRACT_FILTER=Festanstellung
```

2. **Broad Net** (for job seekers open to anything):
```env
MIN_SCORE=20
MAX_JOB_AGE_DAYS=90
# No location filter
# No contract filter
```

### Scraper-Specific Settings

```python
# In .env
MAX_CONCURRENT_REQUESTS=5     # Parallel requests (don't overload servers)
REQUEST_DELAY_SECONDS=1       # Delay between requests
CACHE_TTL_HOURS=24           # Cache scraped data for 24h
```

---

## Advanced Customization

### Custom Scoring Component

Add your own scoring logic in `scorers/components/`:

```python
# scorers/components/salary_component.py
from scorers.base import BaseScorer
from models.job import Job

class SalaryComponent(BaseScorer):
    """Score jobs based on salary range."""
    
    def score(self, job: Job) -> float:
        """
        Award points based on salary:
        - €70k+: 10 points
        - €60-70k: 7 points
        - €50-60k: 5 points
        - Unknown: 0 points
        """
        if not job.salary:
            return 0.0
        
        # Parse salary (e.g., "€60k-70k")
        try:
            salary_avg = self._parse_salary(job.salary)
            if salary_avg >= 70000:
                return 10.0
            elif salary_avg >= 60000:
                return 7.0
            elif salary_avg >= 50000:
                return 5.0
        except:
            pass
        
        return 0.0
    
    def _parse_salary(self, salary_str: str) -> float:
        # Implement parsing logic
        pass
```

**Register in `scorers/aggregator.py`**:

```python
from scorers.components.salary_component import SalaryComponent

class ScoringAggregator:
    def __init__(self, ...):
        self.components = [
            ("tfidf", TfidfComponent(...), 35),      # Reduce weight
            ("tech_stack", TechStackComponent(...), 30),
            ("remote", RemoteComponent(...), 15),
            ("keywords", KeywordComponent(...), 10),
            ("salary", SalaryComponent(), 10),       # Add new
        ]
```

### Custom Scraper Filter

Add post-scraping filters in `processors/filter.py`:

```python
class JobFilter:
    def filter_jobs(self, jobs: List[Job]) -> List[Job]:
        filtered = []
        for job in jobs:
            # Custom filter: only German language jobs
            if self._is_german_job(job):
                filtered.append(job)
        return filtered
    
    def _is_german_job(self, job: Job) -> bool:
        german_keywords = ["Deutsch", "German", "DE", "Deutschland"]
        return any(kw in job.description for kw in german_keywords)
```

---

## Examples & Use Cases

### Use Case 1: Senior React Developer (Remote-Only)

**profile.yaml**:
```yaml
name: "Jane Doe"
roles:
  - "Frontend Developer"
  - "React Developer"
  - "Senior Engineer"

skills:
  - name: "React"
    experience_years: 6
    proficiency: 10
  - name: "TypeScript"
    experience_years: 5
    proficiency: 9
  - name: "Next.js"
    experience_years: 3
    proficiency: 8
  - name: "GraphQL"
    experience_years: 4
    proficiency: 8

preferences:
  remote: "yes"
  locations:
    - "Remote"
  contract_types:
    - "Festanstellung"
    - "Freiberuflich"

profile_text: |
  Senior Frontend Developer with 6+ years of React experience...
```

**scoring_rules.yaml**:
```yaml
weights:
  tfidf_similarity: 30
  tech_stack_match: 35      # Focus on tech
  remote_priority: 20       # Remote critical
  keyword_match: 10
  contract_type: 5

tech_stack:
  high_value:
    - name: "React"
      points: 15
    - name: "TypeScript"
      points: 12
    - name: "Next.js"
      points: 10
  
  negative:
    - name: "Angular"
      points: -5
    - name: "jQuery"
      points: -8

keywords:
  positive:
    - keyword: "senior"
      points: 3
    - keyword: "remote"
      points: 3
  
  negative:
    - keyword: "onsite"
      points: -10
```

**.env**:
```env
MIN_SCORE=50
MAX_JOB_AGE_DAYS=14
LOCATION_FILTER=Remote
```

### Use Case 2: Junior Python Developer (Learning Phase)

**profile.yaml**:
```yaml
name: "John Smith"
roles:
  - "Backend Developer"
  - "Python Developer"
  - "Junior Engineer"

skills:
  - name: "Python"
    experience_years: 2
    proficiency: 6
  - name: "Django"
    experience_years: 1
    proficiency: 5
  - name: "PostgreSQL"
    experience_years: 1
    proficiency: 5

preferences:
  remote: "hybrid"
  locations:
    - "Berlin"
    - "Munich"
    - "Remote"
  contract_types:
    - "Festanstellung"

profile_text: |
  Junior Python Developer with 2 years of experience...
```

**scoring_rules.yaml**:
```yaml
weights:
  tfidf_similarity: 45      # Broader matching
  tech_stack_match: 25
  remote_priority: 10       # Flexible on remote
  keyword_match: 15
  contract_type: 5

tech_stack:
  high_value:
    - name: "Python"
      points: 10
    - name: "Django"
      points: 8
  
  negative:
    # No negatives - open to learning

keywords:
  positive:
    - keyword: "junior"
      points: 5             # Target junior roles
    - keyword: "mentoring"
      points: 3
    - keyword: "training"
      points: 3
  
  negative:
    - keyword: "10+ years"
      points: -10
```

**.env**:
```env
MIN_SCORE=30               # Lower bar
MAX_JOB_AGE_DAYS=60
```

### Use Case 3: DevOps Engineer (Specialized)

**profile.yaml**:
```yaml
skills:
  - name: "Kubernetes"
    experience_years: 5
    proficiency: 9
  - name: "Terraform"
    experience_years: 4
    proficiency: 9
  - name: "AWS"
    experience_years: 6
    proficiency: 10
  - name: "Docker"
    experience_years: 7
    proficiency: 10
```

**scoring_rules.yaml**:
```yaml
tech_stack:
  high_value:
    - name: "Kubernetes"
      points: 15            # Must-have
    - name: "Terraform"
      points: 12
    - name: "AWS"
      points: 10
    - name: "Docker"
      points: 8
    - name: "Ansible"
      points: 7
  
  negative:
    - name: "manual deployment"
      points: -10           # Deal-breaker
```

---

## Testing Your Configuration

After customizing, test your changes:

```bash
# Run with default scrapers
python main.py

# Check scoring accuracy
python main.py --top-n 50 --output results_test.json

# Dry-run (scrape but don't save)
python main.py --scrapers remoteok hackernews --output test.json
```

**Check logs**:
```bash
tail -f logs/app.log

# Look for:
# - "Scored X jobs"
# - "Top job: <title> with score Y"
# - Filter stats
```

---

## Troubleshooting

### Issue: Jobs Not Matching Profile

**Symptoms**:
- All scores are low (<30)
- No jobs pass filters

**Solutions**:
1. Lower `MIN_SCORE` in `.env`
2. Increase weights for less strict components
3. Add more skills to `profile.yaml`
4. Expand `profile_text` with more keywords
5. Check tech names match `tech_dictionary.json`

### Issue: Wrong Jobs Scoring High

**Symptoms**:
- Irrelevant jobs have high scores
- e.g., PHP jobs when you want Python

**Solutions**:
1. Add negative techs in `scoring_rules.yaml`
2. Add negative keywords ("PHP", "WordPress")
3. Increase `tech_stack_match` weight
4. Review `profile_text` (remove generic terms)

### Issue: Tech Not Extracted

**Symptoms**:
- Tech stack shows `[]` even though tech is in description

**Solutions**:
1. Check tech name in `tech_dictionary.json`
2. Add aliases (e.g., "PostgreSQL" + "Postgres" + "PSQL")
3. Case sensitivity: add both "Docker" and "docker"

---

## Resources

- **Main README**: [../README.md](../README.md)
- **Scoring Architecture**: `scorers/` directory
- **Tech Extraction**: `extractors/tech_extractor.py`
- **Example Configs**: `config/*.yaml`

---

**Need help? [Open an issue](https://github.com/DmtiriyK/Job_finder_V2/issues)**
