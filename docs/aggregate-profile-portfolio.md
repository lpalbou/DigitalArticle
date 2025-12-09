# Aggregate Profile Portfolio - Design Document

## Overview

This document outlines the design for an **aggregate profile portfolio** feature that tracks and displays a person's skills, interests, and expertise across multiple notebooks over time.

### Current State (Single Notebook)
- Profile extraction happens per-notebook
- Shows skills demonstrated in ONE notebook only
- No historical tracking
- No skill strength indicators

### Vision (Aggregate Portfolio)
- Track skills across ALL user notebooks
- Show skill strength based on frequency of use
- Display timeline of skill acquisition and usage
- Provide growth tracking and evolution over time
- Enable portfolio export for CVs, LinkedIn, etc.

---

## Use Cases

### Use Case 1: Researcher Portfolio
**Scenario**: Dr. Sarah has created 50 notebooks over 2 years analyzing clinical trial data, genomics data, and medical imaging.

**Current limitation**: Each notebook shows isolated skills.

**With aggregate portfolio**:
- Profile shows: "Expert in Clinical Research (demonstrated in 35 notebooks)"
- Timeline shows when she started using PK/PD modeling (6 months ago)
- Growth chart shows progression from basic to expert in survival analysis
- Portfolio export for grant applications

### Use Case 2: Data Scientist Growth Tracking
**Scenario**: John is learning machine learning and wants to track his progress.

**Current limitation**: No way to see skill evolution.

**With aggregate portfolio**:
- See when he first used scikit-learn (Notebook #3, 3 months ago)
- Track progression: Basic → Intermediate → Advanced
- Identify skill gaps (used pandas 50x, but never used PyTorch)
- Set learning goals based on missing skills

### Use Case 3: Team Expertise Directory
**Scenario**: Research team wants to know who has expertise in specific domains.

**Current limitation**: Can't search across users.

**With aggregate portfolio**:
- Search: "Who knows survival analysis?" → Returns Sarah (Expert, 35 notebooks)
- Team skill matrix shows collective capabilities
- Identify training needs

---

## Architecture

### Data Model

#### 1. User Profile Document
```json
{
  "user_id": "user123",
  "username": "sarah_researcher",
  "profile": {
    "created_at": "2023-01-15T10:00:00Z",
    "last_updated": "2025-12-08T14:30:00Z",
    "total_notebooks": 50,
    "domains": [...],
    "categories": [...],
    "skills": [...]
  }
}
```

#### 2. Domain Aggregate
```json
{
  "id": "biomedical",
  "name": "Biomedical Sciences",
  "confidence": 0.98,
  "notebook_count": 35,
  "first_seen": "2023-01-20T...",
  "last_seen": "2025-12-08T...",
  "usage_frequency": {
    "2023": 12,
    "2024": 18,
    "2025": 5
  }
}
```

#### 3. Category Aggregate
```json
{
  "id": "clinical_research",
  "name": "Clinical Research",
  "parent_domain": "biomedical",
  "notebook_count": 32,
  "strength": 0.95,
  "first_seen": "2023-01-20T...",
  "last_seen": "2025-12-08T..."
}
```

#### 4. Skill Aggregate
```json
{
  "id": "survival_analysis",
  "name": "Survival Analysis",
  "parent_category": "clinical_research",
  "proficiency": "Expert",
  "proficiency_history": [
    {"date": "2023-02-01", "level": "Basic", "notebook_id": "nb001"},
    {"date": "2023-06-15", "level": "Intermediate", "notebook_id": "nb015"},
    {"date": "2024-01-20", "level": "Advanced", "notebook_id": "nb025"},
    {"date": "2024-09-10", "level": "Expert", "notebook_id": "nb040"}
  ],
  "notebook_count": 28,
  "strength": 0.93,
  "first_seen": "2023-02-01T...",
  "last_seen": "2025-12-07T...",
  "evidence_samples": [
    {
      "notebook_id": "nb040",
      "notebook_title": "Phase III Survival Analysis",
      "date": "2025-12-07",
      "evidence": ["Kaplan-Meier curves", "Cox regression", "Time-dependent covariates"]
    }
  ],
  "related_skills": ["pk_pd_modeling", "cdisc_standards"],
  "libraries_used": ["lifelines", "pandas", "matplotlib"]
}
```

#### 5. Skill Usage Timeline Event
```json
{
  "skill_id": "survival_analysis",
  "notebook_id": "nb040",
  "notebook_title": "Phase III Survival Analysis",
  "date": "2025-12-07T14:30:00Z",
  "proficiency_at_time": "Expert",
  "evidence": ["Kaplan-Meier curves", "Cox regression"]
}
```

---

## API Design

### Endpoints

#### 1. Get User Aggregate Profile
```
GET /api/users/{user_id}/profile
```

**Response**:
```json
{
  "user": {
    "id": "user123",
    "username": "sarah_researcher",
    "total_notebooks": 50
  },
  "profile": {
    "domains": [...],
    "categories": [...],
    "skills": [...]
  },
  "statistics": {
    "total_skills": 45,
    "expert_skills": 8,
    "advanced_skills": 15,
    "intermediate_skills": 18,
    "basic_skills": 4
  },
  "metadata": {
    "graph_type": "aggregate_profile",
    "layout_hint": "hierarchical_timeline"
  }
}
```

#### 2. Get Skill Timeline
```
GET /api/users/{user_id}/skills/{skill_id}/timeline
```

**Response**:
```json
{
  "skill": {
    "id": "survival_analysis",
    "name": "Survival Analysis",
    "current_proficiency": "Expert"
  },
  "timeline": [
    {
      "date": "2023-02-01",
      "notebook_id": "nb001",
      "notebook_title": "First Clinical Trial Analysis",
      "proficiency": "Basic",
      "evidence": ["Used lifelines library"]
    },
    {
      "date": "2023-06-15",
      "notebook_id": "nb015",
      "notebook_title": "Kaplan-Meier Analysis",
      "proficiency": "Intermediate",
      "evidence": ["KM curves", "Log-rank test"]
    }
  ],
  "proficiency_progression": [
    {"date": "2023-02-01", "level": "Basic"},
    {"date": "2023-06-15", "level": "Intermediate"},
    {"date": "2024-01-20", "level": "Advanced"},
    {"date": "2024-09-10", "level": "Expert"}
  ]
}
```

#### 3. Get User Growth Report
```
GET /api/users/{user_id}/growth?start_date=2023-01-01&end_date=2025-12-31
```

**Response**:
```json
{
  "period": {
    "start": "2023-01-01",
    "end": "2025-12-31"
  },
  "growth": {
    "new_domains": 3,
    "new_categories": 8,
    "new_skills": 42,
    "proficiency_improvements": 15
  },
  "skills_by_quarter": [
    {"quarter": "2023-Q1", "new_skills": 5, "total_skills": 5},
    {"quarter": "2023-Q2", "new_skills": 8, "total_skills": 13},
    ...
  ],
  "notable_achievements": [
    {
      "type": "proficiency_upgrade",
      "skill": "Survival Analysis",
      "from": "Advanced",
      "to": "Expert",
      "date": "2024-09-10"
    }
  ]
}
```

#### 4. Update Profile from Notebook
```
POST /api/users/{user_id}/profile/update-from-notebook
```

**Request**:
```json
{
  "notebook_id": "nb051",
  "profile_extraction": {
    "domains": [...],
    "categories": [...],
    "skills": [...]
  }
}
```

**Response**:
```json
{
  "updated": true,
  "changes": {
    "new_skills": ["bayesian_methods"],
    "proficiency_upgrades": [
      {"skill": "regression", "from": "Intermediate", "to": "Advanced"}
    ]
  }
}
```

#### 5. Export Portfolio
```
GET /api/users/{user_id}/profile/export?format={format}
```

**Formats**:
- `json`: Full aggregate profile JSON
- `markdown`: Markdown CV format
- `html`: Styled HTML portfolio page
- `jsonld`: Semantic JSON-LD for interoperability

---

## Database Schema (Proposed)

### Option A: MongoDB (Document Store)

**Collections**:

1. **`user_profiles`**
   - Document per user
   - Embedded domains, categories, skills
   - Fast reads, denormalized

2. **`skill_timeline_events`**
   - One document per skill usage event
   - Used for timeline queries
   - Indexed on: `user_id`, `skill_id`, `date`

**Pros**: Flexible schema, fast reads, natural fit for hierarchical data
**Cons**: Requires MongoDB setup, complex aggregation queries

### Option B: PostgreSQL (Relational)

**Tables**:

1. **`user_profiles`**
   - `user_id`, `username`, `created_at`, `updated_at`

2. **`user_domains`**
   - `user_id`, `domain_id`, `notebook_count`, `confidence`, `first_seen`, `last_seen`

3. **`user_categories`**
   - `user_id`, `category_id`, `parent_domain_id`, `notebook_count`, `strength`

4. **`user_skills`**
   - `user_id`, `skill_id`, `parent_category_id`, `current_proficiency`, `notebook_count`, `strength`

5. **`skill_timeline_events`**
   - `user_id`, `skill_id`, `notebook_id`, `date`, `proficiency`, `evidence`

6. **`skill_proficiency_history`**
   - `user_id`, `skill_id`, `date`, `old_level`, `new_level`, `notebook_id`

**Pros**: Strong consistency, complex queries, mature tooling
**Cons**: More rigid schema, requires migrations

### Option C: Hybrid (Current JSON + Index)

**Storage**:
- Keep current JSON file storage for notebooks
- Add SQLite index for aggregate queries
- Store aggregate profile in `users/{user_id}/aggregate_profile.json`

**Index Schema** (SQLite):
```sql
CREATE TABLE user_skills (
    user_id TEXT,
    skill_id TEXT,
    skill_name TEXT,
    proficiency TEXT,
    notebook_count INTEGER,
    first_seen DATETIME,
    last_seen DATETIME,
    PRIMARY KEY (user_id, skill_id)
);

CREATE TABLE skill_events (
    user_id TEXT,
    skill_id TEXT,
    notebook_id TEXT,
    date DATETIME,
    proficiency TEXT,
    FOREIGN KEY (user_id, skill_id) REFERENCES user_skills(user_id, skill_id)
);
```

**Pros**: No new infrastructure, incremental adoption, backward compatible
**Cons**: Less scalable, manual index maintenance

**Recommendation**: Start with **Option C (Hybrid)** for MVP, migrate to **Option A (MongoDB)** if usage grows.

---

## Implementation Plan

### Phase 1: Backend Aggregation Service (Week 1-2)

**Tasks**:
1. Create `AggregateProfileService` class
2. Implement `aggregate_profiles_for_user(user_id)` method
3. Build skill strength calculation algorithm
4. Implement proficiency progression detection
5. Add caching layer (Redis or in-memory)

**Algorithm: Skill Strength Calculation**
```python
def calculate_skill_strength(skill_usage_count, total_notebooks, recent_usage_weight):
    """
    Strength = (usage_count / total_notebooks) * recent_usage_multiplier

    Recent usage multiplier:
    - Last 30 days: 1.5x
    - Last 90 days: 1.2x
    - Last 180 days: 1.0x
    - Older: 0.8x
    """
    base_strength = skill_usage_count / max(total_notebooks, 1)
    strength_with_recency = base_strength * recent_usage_weight
    return min(strength_with_recency, 1.0)
```

**Algorithm: Proficiency Progression Detection**
```python
def detect_proficiency_upgrade(skill_id, new_proficiency, skill_history):
    """
    Track proficiency changes over time.

    Proficiency levels: Basic (0) < Intermediate (1) < Advanced (2) < Expert (3)

    Only upgrade if:
    - New level > previous level
    - At least 2 notebooks demonstrate new level
    """
    level_map = {"Basic": 0, "Intermediate": 1, "Advanced": 2, "Expert": 3}

    current_level = level_map[skill_history[-1]["proficiency"]]
    new_level = level_map[new_proficiency]

    if new_level > current_level:
        return True  # Proficiency upgrade detected
    return False
```

### Phase 2: Timeline & Growth Tracking (Week 3)

**Tasks**:
1. Create `SkillTimelineService` class
2. Implement timeline event storage
3. Build growth report generator
4. Add notable achievements detection

**Notable Achievements Examples**:
- First use of a new library
- Proficiency upgrade (Basic → Intermediate, etc.)
- Milestone notebooks (10th, 50th, 100th)
- Skill mastery (Expert level achieved)
- Domain breadth (worked in 3+ domains)

### Phase 3: API Endpoints (Week 4)

**Tasks**:
1. Implement 5 new API endpoints (listed above)
2. Add authentication/authorization checks
3. Implement rate limiting
4. Add API documentation (OpenAPI/Swagger)

### Phase 4: Frontend Visualization (Week 5-6)

**Tasks**:
1. Create "My Portfolio" page component
2. Build timeline visualization (D3.js or Chart.js)
3. Add skill strength indicators
4. Implement growth charts
5. Add export buttons (Markdown, HTML, JSON-LD)

**UI Components**:

1. **Portfolio Dashboard**
   - Header: User name, total notebooks, date range selector
   - Domain cards: Expertise level, number of categories/skills
   - Top skills: Ranked by strength
   - Recent activity: Last 10 skill usages

2. **Skill Timeline View**
   - Horizontal timeline with skill acquisition points
   - Proficiency progression line chart
   - Notable achievements markers
   - Evidence popover on hover

3. **Growth Report**
   - New skills by quarter (bar chart)
   - Proficiency distribution (pie chart)
   - Domain expertise radar chart
   - Activity heatmap (GitHub-style)

4. **Export Options**
   - Download as PDF portfolio
   - Copy markdown for LinkedIn
   - Generate HTML resume
   - Export JSON-LD for semantic web

### Phase 5: Incremental Updates (Week 7)

**Tasks**:
1. Hook into notebook save event
2. Trigger profile update on new notebook creation
3. Implement incremental aggregation (don't re-scan all notebooks)
4. Add background job queue (Celery or similar)

**Incremental Update Flow**:
```
Notebook saved
    ↓
Extract single-notebook profile (existing LLM extractor)
    ↓
Compare with user's aggregate profile
    ↓
Detect changes (new skills, proficiency upgrades)
    ↓
Update aggregate profile incrementally
    ↓
Emit notification (optional): "You gained Expert level in Survival Analysis!"
```

---

## Data Migration Strategy

### Initial Migration (Existing Users)

For users with existing notebooks:

1. **One-time bulk aggregation**:
   ```python
   for user in users:
       notebooks = get_user_notebooks(user.id)
       for notebook in notebooks:
           profile = extract_profile(notebook)  # Use existing LLM extractor
           update_aggregate_profile(user.id, profile, notebook.created_at)
   ```

2. **Handle missing timestamps**:
   - Use notebook `created_at` for first_seen
   - Use notebook `updated_at` for last_seen
   - Infer proficiency progression from chronological order

3. **Backfill timeline events**:
   - Create timeline events for each skill in each notebook
   - Sort chronologically to build proficiency history

### Ongoing Updates

For new notebooks:
- Trigger aggregation on notebook save
- Update incrementally (don't rescan all notebooks)
- Cache aggregate profile for fast reads

---

## Open Questions & Decisions Needed

### 1. User Authentication
**Question**: How do we identify users?
**Options**:
- A: Use notebook `author` field (current, but not authenticated)
- B: Add proper user authentication (OAuth, email/password)
- C: Use local machine username (good for single-user)

**Recommendation**: Start with **A** (author field), plan for **B** (auth system).

### 2. Privacy & Data Sharing
**Question**: Should aggregate profiles be shareable?
**Options**:
- A: Private only (user can export manually)
- B: Public profiles with shareable URLs
- C: Configurable privacy (public/private/team-only)

**Recommendation**: Start with **A**, add **C** later.

### 3. Skill Taxonomy
**Question**: How do we ensure consistent skill naming across notebooks?
**Options**:
- A: Free-form (LLM decides skill names)
- B: Controlled vocabulary (predefined skill taxonomy)
- C: Hybrid (LLM suggests, user approves/maps)

**Recommendation**: Start with **A**, add **C** for power users.

### 4. Multi-User Deployment
**Question**: Is this for single-user or multi-user deployment?
**Current**: Digital Article is single-user (local deployment)
**Future**: May need multi-tenant support

**Recommendation**: Design APIs for multi-user, but implement single-user first.

---

## Success Metrics

### User Engagement
- % of users who view their aggregate profile
- Average time spent on portfolio page
- Export usage (# of exports per user)

### Profile Quality
- Average skills per user
- Distribution of proficiency levels (should see progression over time)
- Skill diversity (# of domains per user)

### System Performance
- Profile aggregation time (target: <5 seconds for 100 notebooks)
- API response time (target: <500ms for profile retrieval)
- Cache hit rate (target: >80%)

---

## Future Enhancements (Beyond Initial Implementation)

### 1. AI-Powered Insights
- Skill gap analysis: "You know pandas and matplotlib, consider learning seaborn"
- Career path suggestions: "Your profile matches: Clinical Data Scientist"
- Learning recommendations: "To reach Expert in ML, focus on deep learning"

### 2. Team Features
- Team skill matrix: Who knows what in the organization
- Collaboration recommendations: Connect experts with learners
- Skill-based project matching

### 3. Gamification
- Achievements/badges for milestones
- Skill level-up notifications
- Learning streaks and goals

### 4. Integration
- Export to LinkedIn (auto-update skills section)
- Import from ORCID or ResearchGate
- Integration with learning platforms (Coursera, DataCamp)

---

## References

### Similar Systems
- **LinkedIn Skills**: Manual entry, endorsements, skill assessments
- **GitHub Profile**: Contribution graph, language statistics
- **Stack Overflow Developer Story**: Reputation, tags, timeline
- **ResearchGate**: Publications, research interests, citation metrics

### Technical Resources
- D3.js timeline visualization: https://observablehq.com/@d3/horizontal-tree
- Proficiency level modeling: CEFR Framework (A1-C2)
- Skill taxonomies: ESCO, O*NET, LinkedIn Skills Graph

---

## Conclusion

The aggregate profile portfolio feature will transform Digital Article from a single-notebook analysis tool into a comprehensive career development and skills tracking platform. By automatically aggregating skills across notebooks and tracking progression over time, users gain valuable insights into their expertise and growth.

**Next Steps**:
1. Get stakeholder approval on architecture (MongoDB vs Hybrid approach)
2. Decide on authentication strategy
3. Begin Phase 1 implementation (Backend Aggregation Service)
4. Create UI mockups for user feedback

**Estimated Timeline**: 7 weeks for full implementation (MVP)
**Estimated Effort**: 1 engineer full-time

---

**Document Version**: 1.0
**Created**: 2025-12-08
**Status**: Proposal - Pending Implementation
