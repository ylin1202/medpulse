# MedPulse

This project is a full-stack Clinical Decision Support System and multi-modal medical health information retrieval platform. The system uses a modern distributed microservices architecture: a Flutter frontend, and a dual-core backend consisting of FastAPI (a LangGraph + Gemma-3 + Gemini dual-RAG inference engine) and Flask (core business logic, JWT authentication, and the drug/pharmacy data gateway), combined with PostgreSQL (pgvector vector database) and Redis for distributed caching and state management. It natively implements constrained JSON decoding on a locally fine-tuned Gemma model, dense + sparse dual-path retrieval with Reciprocal Rank Fusion (RRF Hybrid Search), semantic fact-checking retrieval over the PUBHEALTH dataset, card-based rendering of OpenFDA drug monographs, native marker clustering for Taiwan-wide NHI-contracted pharmacies, and strict medical-education and physiological safety guardrails (negative constraints) at the generation layer.

## Highlights

* **LangGraph Agentic State Machine**: Orchestrates a multi-node state machine with LangGraph, featuring built-in adversarial prompt-injection regex filtering, fine-tuned entity extraction, an automatic retry self-correction reflection loop, and RAG summary generation.
* **Constrained Decoding with Gemma-3**: Fine-tunes Gemma-3 and produces a GGUF-quantized model, using llama_cpp's JSON Grammar (LlamaGrammar) to force structured JSON output, eliminating structural parsing failures and format hallucination.
* **Two-Tier Lab Benchmark Retrieval & RRF Fusion**: The first tier performs exact SQL batch matching against standard reference values; unmatched items automatically trigger a second tier of dense cosine similarity + sparse full-text search, with semantic completion and non-medical noise filtering via Reciprocal Rank Fusion (RRF, threshold 0.0163).
* **Semantic Fact-Checking via pgvector**: Based on the all-MiniLM-L6-v2 embedding model and PostgreSQL pgvector (IVFFlat / HNSW indexes), performs vector similarity retrieval over the PUBHEALTH medical fact-checking database, with Gemini generating objective fact-check summaries.
* **Strict CDSS Compliance & Safety Guardrails**: Injects negative constraints into prompt engineering, strictly limiting the system to discussing theoretical/physiological context only, avoiding any illegal diagnosis or prescription-related disputes.
* **Multi-Tier Redis Caching & Resilience**: FastAPI uses SHA-256 deterministic hash inference caching (TTL: 1hr); Flask uses a 10-minute pass-through cache; all cache operations implement a safe fallback mechanism to prevent cache failures from blocking the main flow.
* **Distributed IP Rate Limiting & JWT Revocation**: Combines Flask-Limiter with atomic Redis counters to implement email verification code anti-abuse (3 req/min), login brute-force protection (5 req/min), and AI analysis rate limiting (5 req/min), with real-time token revocation via a Redis JTI blacklist.
* **OpenFDA Drug Monographs & User Bookmarks**: Integrates the OpenFDA drug database, modularly rendering clinical monograph cards, and maintains a personal bookmark list via PostgreSQL foreign keys and an `ON CONFLICT` idempotency mechanism.
* **Geospatial Pharmacy Locator & Marker Clustering**: Integrates native Google Maps marker clustering, supporting fast switching across Taiwan's counties/cities and real-time visual filtering of NHI-contracted pharmacies.
* **Dockerized Microservices**: A fully containerized architecture orchestrating the FastAPI AI inference service, the Flask business API, PostgreSQL (pgvector/PostGIS), and Redis.

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Flutter (Dart) · google_maps_flutter | Cross-platform client app, map marker clustering, and Markdown medical content rendering |
| **AI & RAG Engine** | FastAPI (Python) · LangGraph · llama.cpp | Clinical state machine orchestration, Gemma fine-tuned inference, and dual-RAG pipeline |
| **LLM & Embeddings** | Gemma 3 · all-MiniLM-L6-v2 · Google Gemini | Clinical entity extraction, semantic vectorization, and CDSS medical summary generation |
| **Core API Gateway** | Flask · Flask-JWT-Extended · Flask-Mail | User authentication (Email OTP / JWT), drug search, and bookmark management |
| **Database & Vector** | PostgreSQL (pgvector / PostGIS) | Lab metric benchmark database, PUBHEALTH vector table, and pharmacy spatial data |
| **Cache & Limiter** | Redis | Semantic inference caching, verification code storage, JWT revocation blacklist, and IP rate limiting |
| **Deployment** | Docker · Docker Compose | Multi-container microservice orchestration and environment isolation |

## System Architecture

```
                               +------------------------------------------+
                               |        Flutter Client Application        |
                               |------------------------------------------|
                               | • Lab Metric Explorer (Markdown Render)  |
                               | • Geospatial Pharmacy Map (Clustering)   |
                               | • Fact-Check & Drug Monograph Cards      |
                               +--------------------+---------------------+
                                                    |
                                       RESTful APIs (Dio Client)
                                                    |
                         +--------------------------+--------------------------+
                         |                                                     |
                         v (Port 8000: /api/v1/*)                              v (Port 5001: /api/v1/*)
        +----------------------------------+                  +----------------------------------+
        |   FastAPI AI Service (Dual-RAG)  |                  |    Flask Core API Gateway        |
        |----------------------------------|                  |----------------------------------|
        | • POST /api/v1/analyze           |                  | • /api/v1/auth (OTP, JWT, JTI)   |
        | • POST /api/v1/factcheck         |                  | • /api/v1/drugs (OpenFDA & Mono) |
        | • Middleware (Correlation ID)    |                  | • /api/v1/pharmacies (GeoSpatial)|
        | • LangGraph State Machine        |                  | • /api/v1/favorites (Bookmarks)  |
        +--------+----------------+--------+                  +--------+----------------+--------+
                 |                |                                    |                |
                 |                | Redis Cache / Rate Limit           |                |
                 |                v                                    |                |
                 |     +----------------------+                        |                |
                 |     |    Redis 7 Cache     |<-----------------------+                |
                 |     |----------------------|                                         |
                 |     | • medical_rag:<hash> | • verify:<email> (OTP)                  |
                 |     | • rate_limit:analyze | • blacklist:<jti> (Revoke)              |
                 |     | • cache:drugs:*      | • cache:pharmacies:*                    |
                 |     +----------------------+                                         |
                 |                                                                      |
                 v                                                                      v
        +---------------------------------------------------------------------------------------+
        |                  PostgreSQL Database (asyncpg [AI] / psycopg2 Pool [Flask])           |
        |---------------------------------------------------------------------------------------|
        | • medical_metrics (MIMIC-IV Reference Ranges, Units & Definitions)                    |
        | • factcheck_vectors (PUBHEALTH Claims, Embeddings, IVFFlat / HNSW Index)              |
        | • drugs & user_favorites (OpenFDA Package Inserts, User Bookmarks with FK Cascades)   |
        | • pharmacies & users (Spatial Coordinates, Password Hashes & Verification Status)     |
        +---------------------------------------------------------------------------------------+
```

## Data Flow: Auth & Revocation

```
[Registration Flow]                          [Logout / Revocation Flow]
          │                                                │
          ▼                                                ▼
POST /api/v1/auth/send-code                      POST /api/v1/auth/logout
(Generate 6-digit OTP & Store in Redis)          (Extract JTI from Bearer JWT)
          │                                                │
          ▼                                                ▼
POST /api/v1/auth/register                       Calculate Remaining Token Lifespan
(Verify OTP -> Create User -> Issue JWT)         (TTL = exp - current_timestamp)
          │                                                │
          ▼                                                ▼
      JWT Issued                                  Redis: SETEX blacklist:<jti> <TTL>
                                                           │
                                                           ▼
                                            Protected Requests (@jwt_required):
                                            check_if_token_is_revoked -> Deny (401)
```

## Core Engineering Highlights

### LangGraph Adaptive State Machine & Constrained Decoding

**Grammar-constrained decoding**: Pre-compiles a JSON Schema via `llama_cpp.LlamaGrammar`, and uses Gemma-3 — fine-tuned on 1,200 samples — to constrain token generation so it can only produce output matching the compiled grammar tree, completely eliminating JSON parsing failures.

**Self-correction reflection loop**: If the extracted output format is abnormal, a LangGraph conditional edge automatically routes the state back to Node 1 for a retry, adjusting the temperature (0.1 → 0.3) on retry to explore the correct decision boundary.

### Two-Tier RAG Retrieval & RRF Fusion

**Tier 1 (Exact Batch Match)**: Uses normalization and stemming/de-pluralization for term matching, retrieving standard reference values and definitions in a single SQL batch query via `ANY($1::text[])`, avoiding N+1 query bottlenecks.

**Tier 2 (Hybrid Search Fallback + RRF)**: For unmatched items, generates dense vectors via SentenceTransformer and combines them with PostgreSQL full-text search (`ts_rank_cd`) using Reciprocal Rank Fusion:

$$\text{RRF Score} = \frac{1}{60 + \text{Dense Rank}} + \frac{1}{60 + \text{Sparse Rank}}$$

A threshold of RRF ≥ 0.0163 is set to automatically filter out non-medical noise (e.g., vehicle voltage readings, unrelated terms).

### PUBHEALTH Semantic Fact-Checking & Dual-Model Fallback

Based on pgvector's `<=>` cosine distance operator and IVFFlat / HNSW indexes, supports real-time semantic fact-checking.

Retrieval results are passed into a Gemini dual-model fallback pipeline (gemini-3.6-flash → gemini-3.5-flash), which automatically switches and retries when quota limits (HTTP 429) are hit, dynamically generating a 100–150 word objective fact-check rationale.

### Strict CDSS Regulatory Safety Guardrails (Negative Constraints)

A negative constraint is built into the prompt:

```
4. Strictly provide educational and physiological context only. Do NOT provide a personal diagnosis, clinical prescription, or definitive medical conclusion.
```

This ensures the AI only offers neutral commentary on physiological mechanisms and lab-metric abnormality risk, and never crosses the line into personal diagnosis or prescription.

## Repository Structure

```
├── ai-service/                           # FastAPI AI & Dual-RAG microservice
│   ├── agent/                            # LangGraph state machine & retrieval modules
│   │   ├── __init__.py
│   │   ├── database.py                   # Batch exact-match queries & hybrid RRF retrieval
│   │   ├── grammar.py                    # LlamaGrammar JSON constraint compilation
│   │   └── graph.py                      # LangGraph node definitions, safety checks & workflow compilation
│   ├── api/                              # FastAPI routing & dependency injection
│   │   ├── __init__.py
│   │   ├── deps.py                       # asyncpg pool & Redis dependency injection
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── clinical.py           # Clinical note analysis endpoint (POST /analyze)
│   │       │   └── factcheck.py          # Semantic fact-check endpoint (POST /factcheck)
│   │       ├── __init__.py
│   │       └── router.py                 # v1 router registration entry point
│   ├── core/                             # Core configuration & logging modules
│   │   ├── __init__.py
│   │   ├── config.py                     # Environment variable binding
│   │   └── logging.py                    # Formatted logger
│   ├── data/                             # Dataset storage directory
│   ├── model/                            # GGUF model storage directory
│   │   └── ...
│   ├── schemas/                          # Request & response data structures
│   │   ├── __init__.py
│   │   ├── clinical.py                   # ClinicalTextRequest & AnalysisResponse
│   │   └── factcheck.py                  # FactCheckRequest & FactCheckResponse
│   ├── scripts/                          # Data processing & ETL scripts
│   │   ├── clean_mimic.py                # MIMIC-IV raw data ETL & top-20 metric extraction
│   │   ├── eval_pipeline.py              # Automated benchmark testing & evaluation script
│   │   ├── generate_dataset.py           # Clinical entity fine-tuning dataset synthesis script
│   │   ├── generate_factcheck_parquet.py # PUBHEALTH vector serialization script
│   │   ├── import_factcheck.py           # pgvector fact-check dataset batch import script
│   │   ├── init_db.py                    # PostgreSQL schema & pgvector/HNSW initialization
│   │   └── populate_embeddings.py        # Lab metric vector batch generation & write
│   ├── services/                         # Domain services
│   │   ├── __init__.py
│   │   ├── cache_service.py              # Redis SHA-256 caching & sliding-window rate limiting
│   │   └── factcheck_service.py          # pgvector semantic retrieval & Gemini fact-check generation
│   ├── test/                             # Service test modules
│   │   ├── load_test.js                  # k6 / JS load stress test script
│   │   └── test_api.py                   # FastAPI unit & integration tests
│   ├── .dockerignore
│   ├── .env                              # AI service environment variables
│   ├── .gitignore
│   ├── Dockerfile                        # AI service Docker build file
│   ├── main.py                           # FastAPI app entry point, lifespan & middleware
│   └── requirements.txt                  # Python dependencies
├── medpulse-flask/                       # Flask core business backend
│   ├── app/
│   │   ├── models/                       # DAO data access objects
│   │   │   ├── drug.py                   # OpenFDA drug data queries
│   │   │   ├── fact_check.py             # PUBHEALTH related data queries
│   │   │   ├── favorite.py               # User drug bookmarks & foreign key relations
│   │   │   ├── pharmacy.py               # Pharmacy geospatial data queries
│   │   │   └── user.py                   # User accounts & password hashing
│   │   ├── routes/                       # Flask route blueprints
│   │   │   ├── auth.py                   # Registration, login, OTP & token revocation
│   │   │   ├── drug.py                   # Drug pagination & package insert detail API
│   │   │   ├── fact_check.py             # Fact-check pagination & detail API
│   │   │   ├── favorite.py               # Bookmark list & status check API
│   │   │   └── pharmacy.py               # Pharmacy list & county/city filter API
│   │   ├── tests/                        # Backend test modules
│   │   │   ├── __init__.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_drugs.py
│   │   │   ├── test_fact_check.py
│   │   │   ├── test_favorite.py
│   │   │   └── test_pharmacies.py
│   │   ├── utils/                        # Core utility library
│   │   │   ├── cache.py                  # Redis caching service with safe fallback
│   │   │   ├── db.py                     # psycopg2 connection pool & safe executor
│   │   │   ├── limiter.py                # Distributed IP rate limiter
│   │   │   └── __init__.py
│   │   ├── extensions.py                 # Flask-Mail extension instance
│   │   └── __init__.py                   # Application factory function (create_app)
│   ├── scripts/                          # Data initialization scripts
│   │   ├── drug-label-0014.json          # Raw OpenFDA drug package insert data
│   │   ├── import_drugs.py               # Drug data parsing & import script
│   │   ├── import_pharmacies.py          # Taiwan-wide pharmacy geodata import script
│   │   └── pharmacies.json               # Raw NHI pharmacy coordinate data
│   ├── .dockerignore
│   ├── .env                              # Flask service environment variables
│   ├── .gitignore
│   ├── config.py                         # Flask global environment variable configuration
│   ├── Dockerfile                        # Flask Docker build file
│   ├── requirements.txt                  # Python dependencies
│   └── run.py                            # Flask server entry point (Port: 5001)
├── medpulse_flutter/                     # Flutter cross-platform frontend app
│   ├── lib/
│   │   ├── core/                         # Core networking, auth & shared widget modules
│   │   │   ├── auth/
│   │   │   │   └── auth_service.dart     # Auth state management & token access
│   │   │   ├── network/
│   │   │   │   └── api_client.dart       # Dio dual-endpoint network config (Flask / FastAPI)
│   │   │   └── widgets/
│   │   │       ├── fact_check_rag_dialog.dart # Fact-check detail dialog
│   │   │       └── pagination_bar.dart   # Pagination control widget
│   │   ├── features/                     # Feature modules
│   │   │   ├── drug/                     # Drug search & monograph
│   │   │   │   ├── data/drug_model.dart
│   │   │   │   └── presentation/
│   │   │   │       ├── drug_detail_screen.dart
│   │   │   │       └── drug_search_screen.dart
│   │   │   ├── fact_check/               # Medical fact-checking
│   │   │   │   ├── data/fact_check_model.dart
│   │   │   │   └── presentation/
│   │   │   │       ├── fact_check_detail_screen.dart
│   │   │   │       └── fact_check_screen.dart
│   │   │   ├── favorite/                 # Personal bookmark management
│   │   │   │   ├── data/favorite_service.dart
│   │   │   │   └── presentation/
│   │   │   │       ├── favorite_button.dart
│   │   │   │       └── favorite_screen.dart
│   │   │   ├── lab_metric/               # Clinical lab metrics & AI analysis
│   │   │   │   ├── data/analysis_model.dart
│   │   │   │   └── presentation/lab_metric_screen.dart
│   │   │   ├── map/                      # Pharmacy geolocation & marker clustering
│   │   │   │   ├── data/pharmacy_model.dart
│   │   │   │   └── presentation/pharmacy_map_screen.dart
│   │   │   └── profile/presentation/     # Profile, auth modal & disclaimers
│   │   │       ├── auth_modal.dart
│   │   │       ├── main_navigation_screen.dart
│   │   │       └── profile_screen.dart
│   │   └── main.dart                     # App entry point
│   ├── .env                              # Flutter frontend environment variables
│   ├── analysis_options.yaml
│   ├── pubspec.yaml                      # Flutter dependencies
│   └── README.md
├── docker-compose.yml                    # Container microservice orchestration file
```

## Services & Port Mappings

| Service | Container | Internal/External Port | Description |
|---------|-----------|-------------------------|--------------|
| **ai-service** | medpulse-ai-service | 8000:8000 | FastAPI clinical agent, dual-RAG & Gemini integration service |
| **flask-api** | medpulse-flask | 5001:5001 | Flask business API gateway, JWT auth & drug/pharmacy data service |
| **redis** | medpulse-redis | 6379:6379 | Distributed inference cache, OTP storage, JWT blacklist & rate-limit storage |

The database runs as an external service and is not included in the Docker Compose orchestration above.

## Quickstart

**Configure environment variables**

```
# Copy global and per-service environment variable templates
cp .env.example .env
cp medpulse-flask/.env.example medpulse-flask/.env
cp ai-service/.env.example ai-service/.env
```

Make sure to fill in a valid `GEMINI_API_KEY`, `MAIL_USERNAME`, `MAIL_PASSWORD`, and database connection parameters in the config files.

**Start all microservice containers**

```
docker compose up -d --build
```

**Database initialization & data import**

```
# 1. Initialize MIMIC lab metrics & pgvector schema
docker compose exec ai-service python scripts/init_db.py

# 2. Generate and write 384-dimensional lab metric vector embeddings
docker compose exec ai-service python scripts/populate_embeddings.py

# 3. Batch import the PUBHEALTH fact-check vector dataset
docker compose exec ai-service python scripts/import_factcheck.py

# 4. Import OpenFDA drug package inserts and Taiwan-wide pharmacy geocoordinates
docker compose exec flask-api python scripts/import_drugs.py
docker compose exec flask-api python scripts/import_pharmacies.py
```

**Run automated evaluation & benchmarking**

```
docker compose exec ai-service python scripts/eval_pipeline.py
```

Runs an evaluation matrix covering exact matching, Hybrid RRF completion, noise filtering, prompt-injection protection, and cache acceleration.

## Protocols & API Reference

### Clinical RAG & Fact-Checking (FastAPI - Port 8000)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/analyze` | Accepts a clinical note; performs LangGraph entity extraction, MIMIC benchmark retrieval, and Gemini CDSS summary generation. |
| `POST` | `/api/v1/factcheck` | Accepts a health-concern statement; performs pgvector semantic similarity retrieval and fact-check summary generation. |
| `GET` | `/health` | Checks the AI service's health status and running version. |

---

### Authentication & Users (Flask Core API - Port 5001)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/send-code` | Sends a 6-digit email verification code (rate-limited to 3/min, stored in Redis for 5 minutes). |
| `POST` | `/api/v1/auth/register` | Verifies the OTP, creates the account password hash, and issues a JWT. |
| `POST` | `/api/v1/auth/login` | Verifies credentials and issues a JWT access token (rate-limited to 5/min). |
| `POST` | `/api/v1/auth/logout` | Extracts the JTI and writes it to the Redis blacklist, enabling real-time token revocation. |
| `GET` | `/api/v1/auth/me` | Gets the currently authenticated user's profile and status. |

---

### Drugs, Pharmacies & Bookmarks (Flask Core API - Port 5001)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/drugs` | Gets a paginated OpenFDA drug list (supports keyword/category filtering and a 10-minute cache). |
| `GET` | `/api/v1/drugs/{id}` | Gets the full package insert and monograph for a specific drug. |
| `GET` | `/api/v1/pharmacies` | Gets the list of NHI-contracted/non-contracted pharmacies across Taiwan (supports keyword and county/city filtering). |
| `GET` | `/api/v1/fact-checks` | Gets a paginated list of PUBHEALTH fact-checks. |
| `GET` | `/api/v1/fact-checks/{id}` | Gets the detailed record for a specific fact-check. |
| `POST` | `/api/v1/favorites` | Adds a drug to personal bookmarks (supports `ON CONFLICT` idempotency protection). |
| `DELETE` | `/api/v1/favorites/{drug_id}` | Removes a specific drug from the personal bookmark list. |
| `GET` | `/api/v1/favorites/check/{drug_id}` | Checks whether a specific drug already exists in the bookmark list. |
| `GET` | `/api/v1/favorites` | Gets the currently logged-in user's full bookmarked drug list. |

## Datasets

This system integrates and processes several authoritative medical and open datasets as its factual knowledge base for RAG retrieval augmentation, model fine-tuning, and geolocation:

### External Datasets (Public Datasets & Source)

**MIMIC-IV (Medical Information Mart for Intensive Care)**
* Extracts the top 20 most clinically frequent lab metrics (e.g., Hemoglobin, WBC, Glucose, Potassium), used as the benchmark database for standard reference values and units.

**MedlinePlus Medical Encyclopedia**
* Provides authoritative physiological definitions, clinical uses, and interpretation context for lab tests, used as fact grounding during RAG generation.

**PUBHEALTH Dataset**
* Covers a large body of professionally verified public health and medical fact-checking data, embedded with the all-MiniLM-L6-v2 model and stored in the pgvector vector store for semantic fact-checking.

**OpenFDA Drug Product Labels**
* Provides drug package inserts, including indications, dosage and administration, mechanism of action, and warnings.

**Taiwan NHI Contracted Pharmacies Dataset**
* Contains the name, address, phone number, latitude/longitude coordinates, and NHI contract status of pharmacies across Taiwan, driving the frontend's Google Maps marker clustering and filter map.

### Self-Constructed Synthetic Dataset

**MedPulse Clinical NER Instruction Dataset**
* **Scope**: Not a medical diagnosis dataset — focused on extracting lab-test names from clinical notes and aligning them with JSON grammar constraints (a structural NER task).
* **Knowledge grounding**: The metric list and synonym mappings are based on the MIMIC-IV laboratory dictionary and the authoritative MedlinePlus vocabulary, ensuring objective accuracy of medical terminology.
* **Construction method**: Using a programmatic synthesis pipeline combining 12 clinical narrative templates, random synonym permutation mapping, and 15% negative samples (e.g., general symptom statements unrelated to lab tests), 1,200 instruction-tuning records were synthesized to train the Gemma model to reliably extract standard lab-test keys from unstructured text.
