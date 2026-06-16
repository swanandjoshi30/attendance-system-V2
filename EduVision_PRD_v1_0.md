# VisionAttend — Production PRD

**Version:** 1.0 | **Date:** June 2025 | **Status:** Draft for Review

---

## Document Header

| Property | Value |
|----------|-------|
| **Product Name** | VisionAttend — AI-Powered Dual-Camera Attendance System |
| **Target Market** | Offices, Schools, Colleges, Factories |
| **Core Stack** | FastAPI + React + PostgreSQL + InsightFace |
| **Deployment** | On-premise + Cloud hybrid (Docker/K8s) |
| **Confidentiality** | CONFIDENTIAL |

---

## 1. Executive Summary & Vision

VisionAttend is a production-grade, AI-powered attendance management platform that uses dual CCTV cameras at entry/exit points to automatically detect, recognize, and log attendance for employees and students — eliminating manual registers, buddy-punching, and administrative overhead.

Unlike the current prototype (single-camera, Tkinter-based, no chat interface), VisionAttend is architected from day one for scale, accuracy, and conversational AI — meaning any admin or teacher can ask in plain English: **"Was Atharva present yesterday?"** and the system fetches the answer instantly from a live database.

### 1.1 Problem Statement

- **Manual Attendance Issues**: Slow, error-prone, and easily faked
- **Biometric Limitations**: Existing systems require physical contact (hygiene issues post-COVID)
- **Data Query Problems**: No easy way to query attendance data — requires SQL knowledge or complex reports
- **Prototype Limitations**: Single camera, no in/out tracking, no natural language interface
- **Scalability Issues**: Scaling to multi-site, multi-room requires proper service-oriented architecture

### 1.2 Solution Overview

- **Dual IP CCTV Cameras** per entrance: one faces inward (entry), one outward (exit)
- **InsightFace / ArcFace** deep learning models for 99%+ face recognition accuracy
- **Multi-face Detection** handles groups entering simultaneously (up to 8-10 faces/frame)
- **Natural Language AI Chat** (Claude / GPT-4o) translates queries to SQL in real-time
- **REST API Backend** (FastAPI) + React dashboard with live feeds and analytics
- **PostgreSQL with TimescaleDB** extension for time-series attendance data at scale
- **On-premise Edge Processing** + cloud sync for reliability and compliance

---

## 2. Architecture Overview

### 2.1 Why NOT n8n — Architecture Recommendation

> **⚠️ FUTURE SCOPE NOTE:** The original plan considered using n8n as middleware, but production requirements demand a dedicated microservices architecture instead.

#### n8n Limitations at Production Scale

| Concern | n8n Behavior | Production Impact |
|---------|-------------|-------------------|
| **Latency** | HTTP webhook round-trips add 200–800ms per hop | Unacceptable for real-time face recognition pipeline |
| **Scalability** | Single-node by default, clustering is complex | Cannot handle 50+ cameras or 500+ concurrent users |
| **State Management** | Stateless workflows, no native session handling | Multi-turn AI chat requires persistent conversation context |
| **Custom Logic** | Limited code nodes, hard to debug | Face pipeline needs Python numpy/OpenCV inline |
| **Security** | Webhooks are public endpoints by default | Exposes sensitive biometric data without extra work |
| **Cost** | Cloud n8n scales by workflow executions | High-volume recognition = high recurring cost |
| **Monitoring** | Basic execution logs only | No APM, tracing, alerting for production SLAs |

### 2.2 Recommended Production Architecture

Replace n8n with a clean microservices stack:

| Layer | Technology | Role |
|-------|-----------|------|
| **Edge Processing** | Python service on NVR/local server | Camera capture, face detection, encoding (runs at edge, no cloud needed for recognition) |
| **API Gateway** | FastAPI + Nginx | Single entry point, auth, rate limiting, routing |
| **AI Chat Service** | LangChain + Claude API / GPT-4o | NL → SQL translation with conversation memory, schema-aware |
| **Database** | PostgreSQL + TimescaleDB | Attendance records, face encodings, analytics hypertables |
| **Message Queue** | Redis Streams / RabbitMQ | Decouples camera events from database writes; handles bursts |
| **Frontend** | React + Vite + TailwindCSS | Dashboard, live feeds, chat interface, reports |
| **Auth** | JWT + OAuth2 (Keycloak or Auth0) | Role-based access: admin, teacher, viewer, HR |
| **Monitoring** | Prometheus + Grafana | Real-time system health, recognition accuracy, queue depth |
| **Deployment** | Docker + Kubernetes (or Docker Compose for SMB) | Horizontal scaling, rolling updates, zero-downtime deploys |

**15-DAY PROTOTYPE:** Focus on FastAPI, PostgreSQL, and React (skip Redis/Grafana complexity initially)

---

## 3. Face Recognition: Model Selection & Justification

The prototype uses OpenCV Haar Cascades with pixel-distance comparison — this is fundamentally insufficient for commercial use. Here is the full model analysis:

### 3.1 Detection Stage: Finding Faces in Frame

| Model | Speed | Multi-Face | Accuracy | Recommendation |
|-------|-------|-----------|----------|-----------------|
| Haar Cascade (current) | Fast | Yes (limited) | ~70% in varied lighting | ❌ Not suitable — poor accuracy |
| **YOLOv8-face** | Very fast (5ms/frame) | Excellent (20+ faces) | 98%+ detection rate | ✅ **USE FOR DETECTION** |
| RetinaFace | Fast (8ms) | Excellent | 99%+ detection rate | ✅ Best-in-class alternative |
| MTCNN | Moderate (25ms) | Good | 97%+ detection rate | ⚠️ Good fallback, slower |
| MediaPipe Face Detection | Real-time | Up to 6 faces | 96%+ | ⚠️ Good for mobile/edge, limited |

**✅ DECISION for 15-DAY PROTOTYPE:** Use **YOLOv8-face** for detection (fastest, handles crowds, pre-trained weights available)

### 3.2 Recognition Stage: Identifying Who the Face Belongs To

| Model | Accuracy (LFW) | Speed | License | Recommendation |
|-------|----------------|-------|---------|-----------------|
| OpenCV pixel comparison (current) | ~60% | Fast | Open | ❌ Too inaccurate for production |
| Dlib face_recognition (128-d) | 99.38% | Moderate | Open | ⚠️ Good but struggles with CCTV angles |
| **InsightFace / ArcFace** | **99.77%** | Fast (GPU) / OK (CPU) | MIT | ✅ **RECOMMENDED** |
| FaceNet (Google) | 99.65% | Moderate | Open | ✅ Excellent alternative |
| DeepFace (ensemble) | 99.6%+ | Slow | MIT | ⚠️ Good for verification, slow for 1:N |
| AWS Rekognition | 99%+ | Cloud latency | Commercial | ⚠️ SaaS option — data leaves premises |

**✅ DECISION for 15-DAY PROTOTYPE:** **YOLOv8-face** (detection) + **InsightFace ArcFace** (recognition). Achieves <15ms per frame on NVIDIA T4 GPU and <80ms on CPU. Handles faces at angles up to 45 degrees and partial occlusions.

### 3.3 Multi-Face Handling

For doors where groups enter simultaneously (classrooms, office rush hour):

- YOLOv8-face detects all faces in one forward pass — typically 5-15ms for full HD frame
- InsightFace runs recognition on each detected ROI in parallel (threadpool)
- Each face produces an independent 512-dimensional embedding
- Cosine similarity search against registered embeddings database
- pgvector PostgreSQL extension enables fast nearest-neighbor search at scale (millions of embeddings in <50ms)
- Deduplication: if same person detected in 3 consecutive frames, log only once

**15-DAY PROTOTYPE:** Implement basic multi-face detection; optimize deduplication and caching later.

---

## 4. Camera Specifications for CCTV

CCTV camera selection is critical — the wrong camera choice will make even the best model fail.

### 4.1 Camera Hardware Requirements

| Parameter | Minimum | Recommended | Reason |
|-----------|---------|-------------|--------|
| **Resolution** | 1080p (2MP) | 4MP or 4K (8MP) | Higher res = detect faces at greater distances |
| **Frame Rate** | 15 FPS | 25–30 FPS | Smooth recognition; 15 FPS misses fast-walking subjects |
| **Shutter Type** | Global shutter | Global shutter | Rolling shutter blurs fast movement — critical failure point |
| **Low Light / WDR** | WDR 120dB | WDR 130dB + IR | Entrances have backlight (bright outside, dark inside) |
| **IR Night Vision** | 20m IR range | 30m IR range | After-hours access, underground parking, dimly lit corridors |
| **Lens Focal Length** | 2.8mm–8mm fixed | 2.8mm (wide) + varifocal | 2.8mm for door-width capture; varifocal for corridors |
| **Compression** | H.264 | H.265+ | Reduces bandwidth 40–50% without quality loss |
| **Connection** | PoE (Ethernet) | PoE+ or PoE++ | Single cable for power + data |
| **Protocol** | RTSP | RTSP + ONVIF | ONVIF enables standard integration with any NVR |
| **IP Rating** | IP65 | IP67 | Outdoor entrance protection from rain and dust |

### 4.2 Recommended Camera Products

| Use Case | Product | Approx. Cost (INR) | Notes |
|----------|---------|------------------|-------|
| Standard office door | Hikvision DS-2CD2143G2-I | 12,000–18,000 | 4MP, IR, WDR, PoE — excellent value |
| High-traffic (school gate) | Dahua IPC-HDW2831T-AS | 14,000–20,000 | 8MP, AI face detection onboard |
| Outdoor entrance | Axis P3245-V | 40,000+ | Premium, 1080p, excellent in rain/sun |
| Budget option | TP-Link Tapo C320WS | 4,000–8,000 | 1080p, only for indoor low-traffic use |
| NVR (8 cameras) | Hikvision DS-7608NI-K2 | 20,000–30,000 | 8-channel PoE NVR with ONVIF support |

**15-DAY PROTOTYPE:** Use any available IP camera with RTSP support; optimize camera selection in production phase.

### 4.3 Camera Placement & Field of View

- **Mount height:** 2.0–2.4 meters from floor (eye level capture, avoid top-of-head angle)
- **Angle:** Slightly downward tilt (10–15 degrees), NOT looking down steeply
- **Entry camera:** Faces inward, captures face as person enters (well-lit from inside)
- **Exit camera:** Faces outward, captures face as person exits (positioned inside the door)
- **Distance from door:** 1.0–1.5 meters from door frame (face fully visible before passing)
- **Overlap zone:** Both cameras should cover the 0.5m zone at the threshold
- **Lighting:** Install supplementary LED strip at 2.2m height facing outward to eliminate backlight
- **Minimum face pixel size:** 80x80 pixels in frame for reliable recognition

**Rule of Thumb:** At 2.8mm lens on a 4MP camera, you reliably capture faces within a 3-meter width at 2-meter distance.

---

## 5. System Architecture — Full Technical Design

### 5.1 High-Level Architecture

```
LAYER 1 — EDGE (On-premises hardware)
    [IP CCTV Camera IN] --------\
    [IP CCTV Camera OUT] -------/  → [NVR / Edge Server]
                                     (Python face pipeline)
                                           │
LAYER 2 — API (Docker containers)         │
    [Redis Queue] ← face events ←─────────┤
    [FastAPI Backend]                     │
    ├── [Auth Service]                    │
    ├── [Attendance Service] ←────────────┘
    └── [AI Chat Service]
        (LangChain + Claude)
            │
LAYER 3 — DATA                          │
    [PostgreSQL + TimescaleDB + pgvector] ←─────┘
            │
LAYER 4 — FRONTEND                      │
    [React Dashboard + AI Chat UI] ←────┘
```

### 5.2 Edge Processing Pipeline

This is the most critical component — running on a local server or NVR with Python:

1. **Camera Capture:** RTSP stream pulled via OpenCV VideoCapture or FFmpeg (hardware-decoded)
2. **Frame Sampling:** Process every 3rd frame at 30 FPS = 10 FPS effective. Configurable per camera.
3. **Face Detection:** YOLOv8-face model runs on the batch. Outputs bounding boxes + confidence scores.
4. **Quality Filter:** Reject faces with confidence <0.85, size <80px, blur score >100 (Laplacian)
5. **Face Alignment:** 5-point landmark detection (eyes, nose, corners of mouth), affine warp to 112x112px
6. **Embedding:** InsightFace ArcFace model generates 512-d float32 embedding
7. **Matching:** pgvector cosine similarity search against registered embeddings (<L2 distance 0.4 = match)
8. **Dedup Check:** If same person matched in last 5 minutes on same camera, skip. Redis TTL key.
9. **Direction Detection:** Entry vs exit determined by which camera (IN or OUT) generated the event
10. **Event Publish:** JSON event pushed to Redis Stream: `{prn, camera_id, direction, confidence, timestamp}`
11. **API Worker:** FastAPI background worker consumes Redis stream, writes to PostgreSQL AttendanceLogs

**15-DAY PROTOTYPE:** Implement steps 1-7 and 10-11; optimize steps 8-9 later.

### 5.3 Technology Stack Summary

| Component | Technology | Version | Why This Choice |
|-----------|-----------|---------|-----------------|
| **Face Detection** | YOLOv8-face (Ultralytics) | v8.x | Fastest multi-face detector; MIT license; active community |
| **Face Recognition** | InsightFace (ArcFace) | buffalo_l model | 99.77% LFW accuracy; runs on CPU for small deployments |
| **Edge Runtime** | Python | 3.11+ | Performance improvements; onnxruntime for model inference |
| **API Backend** | FastAPI | 0.110+ | Async-native; automatic OpenAPI docs; fastest Python web framework |
| **AI Chat** | LangChain + Claude | claude-sonnet-4-6 | ⚠️ FUTURE SCOPE: Best NL-to-SQL performance, tool use, schema understanding |
| **Message Queue** | Redis Streams | 7.x | ⚠️ FUTURE SCOPE: Ultra-low latency; persistent; consumer groups |
| **Database** | PostgreSQL 16 + TimescaleDB + pgvector | 16.x | ACID; time-series compression; vector similarity search |
| **Frontend** | React 18 + Vite + TailwindCSS | 18.x | Fast builds; component library (shadcn); TypeScript support |
| **Auth** | JWT + Refresh Tokens (python-jose) | — | Stateless; multi-tenant ready; standard |
| **Video Streaming** | WebRTC / HLS via mediamtx | Latest | ⚠️ FUTURE SCOPE: Low-latency live feed to browser |
| **Containerization** | Docker + Docker Compose | 25+ | Single-command deploy; reproducible environments |
| **Monitoring** | Prometheus + Grafana | Latest | ⚠️ FUTURE SCOPE: Industry standard; pre-built dashboards |
| **Reverse Proxy** | Nginx | 1.25+ | SSL termination; rate limiting; WebSocket support |

**15-DAY PROTOTYPE:** Focus on FastAPI, PostgreSQL, React, and basic Docker Compose. Skip Redis, Grafana, and advanced monitoring.

---

## 6. Database Schema — Production Design

The database is redesigned from the prototype with pgvector for embeddings, TimescaleDB hypertable for attendance logs, multi-tenant support, and full audit trail.

### 6.1 Extensions Required

```sql
CREATE EXTENSION IF NOT EXISTS pgvector;        -- vector similarity search
CREATE EXTENSION IF NOT EXISTS timescaledb;     -- time-series optimization
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- UUID generation
```

### 6.2 Core Tables

```sql
-- ORGANIZATIONS (multi-tenant: one row per office/school)
CREATE TABLE organizations (
    org_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    org_type VARCHAR(50) CHECK (org_type IN ('office','school','college','factory')),
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LOCATIONS (buildings/branches within an org)
CREATE TABLE locations (
    location_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,  -- e.g. 'Building A', 'Main Campus'
    address TEXT
);

-- CAMERAS (each physical CCTV unit)
CREATE TABLE cameras (
    camera_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    location_id UUID REFERENCES locations(location_id),
    name VARCHAR(100) NOT NULL,  -- e.g. 'Main Door IN'
    direction VARCHAR(10) CHECK (direction IN ('IN','OUT','BOTH')),
    rtsp_url TEXT,                -- encrypted at rest
    is_active BOOLEAN DEFAULT TRUE,
    last_seen TIMESTAMPTZ          -- health monitoring
);

-- PERSONS (unified: employees + students in same table)
CREATE TABLE persons (
    person_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(org_id),
    external_id VARCHAR(50),  -- PRN / Employee ID / Roll No
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(200) UNIQUE,
    phone VARCHAR(20),
    person_type VARCHAR(20) CHECK (person_type IN ('employee','student','visitor','contractor')),
    department VARCHAR(100),  -- 'Computer Science', 'Engineering Dept'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- FACE_EMBEDDINGS (using pgvector for fast similarity search)
CREATE TABLE face_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding vector(512) NOT NULL,  -- pgvector type
    model_version VARCHAR(50) DEFAULT 'buffalo_l_v1',
    quality_score FLOAT,              -- higher = better enrollment image
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- CRITICAL: IVFFlat index for fast nearest-neighbor search
CREATE INDEX ON face_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ATTENDANCE_LOGS (TimescaleDB hypertable for time-series queries)
CREATE TABLE attendance_logs (
    log_id UUID DEFAULT uuid_generate_v4(),
    person_id UUID REFERENCES persons(person_id),
    camera_id UUID REFERENCES cameras(camera_id),
    direction VARCHAR(10) CHECK (direction IN ('IN','OUT')),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- partition key
    confidence FLOAT NOT NULL,                      -- recognition confidence 0-1
    snapshot_url TEXT,                              -- S3/MinIO path to face snapshot
    session_id UUID,                                -- links IN and OUT events for same visit
    PRIMARY KEY (log_id, timestamp)
);

-- Convert to hypertable (TimescaleDB): automatic time-based partitioning
-- ⚠️ FUTURE SCOPE: Run this after table creation
-- SELECT create_hypertable('attendance_logs', 'timestamp', chunk_time_interval => INTERVAL '1 week');
```

**15-DAY PROTOTYPE:** Use basic PostgreSQL (skip TimescaleDB hypertable conversion); implement pgvector indexing later.

### 6.3 Derived Views for AI Chat Queries

```sql
-- Daily summary view (AI queries this most often)
-- ⚠️ FUTURE SCOPE: Implement this for advanced analytics
CREATE MATERIALIZED VIEW daily_attendance AS
SELECT p.full_name,
       p.external_id,
       p.department,
       DATE(al.timestamp) AS date,
       MIN(al.timestamp) FILTER (WHERE al.direction='IN') AS check_in,
       MAX(al.timestamp) FILTER (WHERE al.direction='OUT') AS check_out,
       EXTRACT(EPOCH FROM (MAX(al.timestamp) FILTER (WHERE al.direction='OUT')
         - MIN(al.timestamp) FILTER (WHERE al.direction='IN')))/3600 AS hours_present,
       CASE WHEN MIN(al.timestamp) FILTER (WHERE al.direction='IN') IS NOT NULL 
            THEN 'present' ELSE 'absent' END AS status
FROM persons p
LEFT JOIN attendance_logs al ON p.person_id = al.person_id
GROUP BY p.person_id, DATE(al.timestamp);
```

---

## 7. AI Chat Interface — NL-to-SQL Architecture

### 7.1 Architecture

> ⚠️ **FUTURE SCOPE:** AI chat with natural language queries is a Phase 4+ feature, after core recognition system is stable.

**For 15-day prototype:** Focus on basic API endpoints; implement AI chat in Phase 4.

- **Model:** Claude claude-sonnet-4-6 (best NL-to-SQL performance, tool use, schema understanding)
- **Framework:** LangChain SQL Agent with custom SQLDatabaseToolkit pointed at PostgreSQL
- **Memory:** ConversationBufferWindowMemory (last 10 turns) stored in Redis per session
- **Schema Injection:** Full table schema + sample data injected into system prompt at startup
- **Safety:** All queries are READ-ONLY (separate DB user with SELECT only permissions)
- **Result Formatting:** Claude formats results as natural language + optionally a structured table

### 7.2 Example Queries the System Handles (Future)

| Natural Language Query | Generated SQL (simplified) | Response Format |
|------------------------|---------------------------|-----------------|
| Was Atharva present yesterday? | SELECT status FROM daily_attendance WHERE full_name ILIKE '%Atharva%' AND date = CURRENT_DATE - 1 | Text: 'Yes, Atharva checked in at 9:14 AM and left at 6:02 PM' |
| Who was absent today in Computer Science? | SELECT full_name FROM daily_attendance WHERE department='Computer Science' AND date=TODAY AND status='absent' | Bulleted list of names |
| Show me attendance for this week | SELECT * FROM daily_attendance WHERE person_id=? AND date >= date_trunc('week', NOW()) | Table with check-in/out times |
| How many hours did Priya work last month? | SELECT SUM(hours_present) FROM daily_attendance WHERE full_name ILIKE '%Priya%'... | Text: '168.5 hours across 21 working days' |
| Who arrives late most often? | SELECT full_name, COUNT(*) as late_count FROM daily_attendance WHERE EXTRACT(HOUR FROM check_in) >= 10... | Ranked table |

---

## 8. Frontend Architecture

### 8.1 Pages & Modules

| Page | Key Features |
|------|-------------|
| **Dashboard** | Live camera feeds (WebRTC), today's attendance count, late arrivals alert, real-time log ticker |
| **AI Chat** | ⚠️ FUTURE SCOPE: Conversational interface, query history, result tables, export to CSV/Excel |
| **People Management** | Register person (multi-photo enrollment), edit details, deactivate, bulk import CSV |
| **Reports** | ⚠️ FUTURE SCOPE: Date-range picker, department filter, export PDF/Excel, attendance heatmap calendar |
| **Camera Management** | Add/edit/delete cameras, live RTSP preview, health status, ONVIF auto-discovery |
| **Settings** | ⚠️ FUTURE SCOPE: Working hours config, leave calendar, notification rules, webhook alerts |
| **Audit Log** | ⚠️ FUTURE SCOPE: All system events: who registered whom, manual overrides, failed recognitions |

**15-DAY PROTOTYPE:** Focus on Dashboard, People Management, Camera Management, and basic attendance log view. Implement Reports and AI Chat later.

### 8.2 Live Video Feed Approach

- **Backend:** mediamtx (formerly rtsp-simple-server) receives RTSP from cameras
- **Transcoding:** Converts to HLS (Low-Latency HLS, ~2s delay) or WebRTC (<500ms delay)
- **Frontend:** hls.js library for HLS playback
- **Face Annotation:** FastAPI WebSocket streams bounding box JSON to frontend
- **Canvas Rendering:** Frontend draws boxes on HTML5 Canvas overlaid on video element

**15-DAY PROTOTYPE:** Display RTSP streams directly via HLS; skip WebRTC and real-time annotation overlay.

---

## 9. Unique Differentiating Features

### Core Features (15-Day Prototype)

- ✅ **Dual-Camera Attendance Tracking** — Automatic IN/OUT detection via CCTV
- ✅ **Face Recognition** — YOLOv8 detection + InsightFace recognition (99%+ accuracy)
- ✅ **Person Enrollment** — Register multiple face photos per person
- ✅ **Attendance Dashboard** — View real-time and historical attendance logs
- ✅ **REST API** — Full programmatic access to attendance data
- ✅ **Role-Based Access** — Admin, Manager, Viewer roles
- ✅ **Camera Management** — Add, edit, and monitor CCTV cameras

### Future Scope Features (Phase 2-7)

#### Phase 2+: Analytics & Reporting

- **Attendance Reports** — Daily, weekly, monthly summaries with filters
- **Department-wise Analytics** — Presence patterns by department
- **Attendance Heatmap** — Visual calendar showing presence patterns
- **Export Capabilities** — CSV, Excel, PDF export

#### Phase 3+: Advanced AI

- **AI Chat Interface** — Natural language queries on attendance data ("Was John present yesterday?")
- **Natural Language Processing** — Claude-powered SQL generation
- **Conversational Memory** — Multi-turn conversations with context

#### Phase 4+: HR Integration & Automation

- **Visitor Management** — Register and auto-check-out visitors
- **Leave Calendar Integration** — Sync with Google Calendar / Outlook / Zoho
- **Overtime Tracking** — Automatic calculation beyond shift end
- **WhatsApp/Telegram Bot** — Parent/student notifications via messaging apps

#### Phase 5+: Advanced Recognition Features

- **Face Quality Scoring** — Reject poor enrollment photos, prompt re-capture
- **Mask & Accessory Handling** — Model fine-tuned on masked faces
- **Face Aging Re-enrollment** — Automatic re-enrollment after 12 months
- **Offline Resilience** — Local SQLite cache during network outages
- **Multi-Enrollment** — 5-8 photos per person for improved accuracy (85% → 99%+)

#### Phase 6+: Enterprise Features

- **Smart Shift Detection** — Automatically detect morning/afternoon/night shifts
- **Anomaly Alerts** — Enter but never exit, tailgating detection
- **Privacy Mode** — Blur faces in stored snapshots, retain only embeddings (GDPR/DPDP compliant)
- **Mobile App** — iOS/Android native apps for on-the-go attendance checks

#### Phase 7+: Deployment & Scale

- **Kubernetes Deployment** — Horizontal scaling for 50+ cameras
- **Multi-Site Support** — Centralized management across multiple offices/schools
- **VPN & Edge Mesh** — Tailscale integration for secure camera connectivity
- **SLA Monitoring** — Enterprise-grade uptime and performance guarantees

---

## 10. Security & Compliance

### 10.1 Data Security

- **Biometric Data Encryption:** Face embeddings stored encrypted at rest (AES-256)
- **RTSP URL Protection:** Camera URLs encrypted in database, decrypted only by edge service
- **API Security:** All endpoints require JWT; face snapshots in MinIO with pre-signed URLs (1-hour expiry)
- **Database Permissions:** Separate read-only PostgreSQL user for AI chat service (SELECT only)
- **Audit Trail:** All admin actions logged to immutable audit_log table
- **SSL/TLS:** All communication encrypted in transit

### 10.2 Compliance

- **India DPDP Act 2023:** Consent recorded during enrollment; biometric data deletion on request
- **GDPR (EU customers):** ⚠️ FUTURE SCOPE: Data residency controls, right to erasure, processing logs
- **Role-Based Access Control (RBAC):** Admin > Manager > Teacher/HR > Viewer
- **Two-Factor Authentication:** ⚠️ FUTURE SCOPE: For admin accounts

**15-DAY PROTOTYPE:** Implement JWT auth, role-based API endpoints, and encrypted database storage. Implement 2FA and full GDPR compliance in later phases.

---

## 11. Deployment Architecture

### 11.1 Small Deployment (1-5 cameras, single office/school)

**Recommended for 15-DAY PROTOTYPE:**

- **Single Server:** 8-core CPU, 16GB RAM, 1TB SSD (Intel NUC or mini PC)
- **Docker Compose:** All services on one machine
  - PostgreSQL + TimescaleDB
  - FastAPI backend
  - React frontend (served by Nginx)
  - Edge Python service (face recognition pipeline)
- **Optional:** Redis for message queue (Phase 2+)
- **Monthly Cost:** ~INR 0 (on-premise) + INR 800/month cloud API for AI chat (future phase)

### 11.2 Medium Deployment (5-50 cameras, multi-building)

**⚠️ FUTURE SCOPE: Phase 5+**

- Edge servers at each building (mini PC per 5-8 cameras)
- Central cloud VM (AWS/GCP/Azure, 4-core, 8GB): API + database
- VPN tunnel from edge servers to cloud API
- Monthly cost: ~INR 5,000-15,000 cloud + AI API costs

### 11.3 Large Deployment (50+ cameras, enterprise)

**⚠️ FUTURE SCOPE: Phase 6+**

- Kubernetes cluster (3-node minimum): API pods scale horizontally
- PostgreSQL on managed service (AWS RDS with TimescaleDB, or Supabase)
- Redis on ElastiCache
- CDN for React frontend (CloudFront)
- Edge nodes per building, connected via VPN mesh (Tailscale)

---

## 12. API Design — Key Endpoints

### Core Endpoints (15-Day Prototype)

| Method | Endpoint | Description |
|--------|----------|-------------|
| **POST** | `/api/v1/auth/login` | JWT login (email + password) |
| **POST** | `/api/v1/auth/refresh` | Refresh access token |
| **POST** | `/api/v1/persons/enroll` | Register new person with face photos (multi-photo) |
| **GET** | `/api/v1/persons` | List all persons with filters |
| **GET** | `/api/v1/persons/{person_id}` | Get person details |
| **PUT** | `/api/v1/persons/{person_id}` | Update person info |
| **POST** | `/api/v1/cameras` | Add new camera |
| **GET** | `/api/v1/cameras` | List all cameras with health status |
| **GET** | `/api/v1/cameras/{camera_id}/snapshot` | Get latest snapshot from camera |
| **GET** | `/api/v1/attendance/logs` | Get attendance logs with filters |
| **GET** | `/api/v1/attendance/today` | Get today's attendance summary |
| **GET** | `/api/v1/attendance/person/{person_id}` | Get attendance for specific person |
| **POST** | `/api/v1/attendance/manual` | Manual attendance entry (admin override) |
| **WebSocket** | `/ws/v1/events` | Real-time attendance event stream |

### Future Endpoints (Phase 2+)

| Method | Endpoint | Description |
|--------|----------|-------------|
| **POST** | `/api/v1/chat/query` | ⚠️ FUTURE: Natural language query → AI response + SQL |
| **GET** | `/api/v1/attendance/report` | ⚠️ FUTURE: Generate attendance report with filters |
| **GET** | `/api/v1/analytics/latecomers` | ⚠️ FUTURE: Get habitual late arrivals statistics |
| **GET** | `/api/v1/live/{camera_id}/hls.m3u8` | ⚠️ FUTURE: Live HLS stream for a camera |

---

## 13. Development Roadmap

### Phase 0: Foundation (Weeks 1-2) — 15-DAY PROTOTYPE FOCUS

**Deliverables:**
- [ ] PostgreSQL schema with pgvector setup
- [ ] FastAPI skeleton with JWT authentication
- [ ] Docker Compose configuration
- [ ] InsightFace integration POC (face embedding generation)
- [ ] OpenCV basic camera capture

**Tasks:**
- Set up PostgreSQL 16 database locally
- Create tables: organizations, locations, cameras, persons, face_embeddings, attendance_logs
- Build FastAPI boilerplate with Pydantic models
- Implement JWT auth (login, refresh tokens)
- Test InsightFace model loading and embedding generation
- Write Docker Compose file for local development

### Phase 1: Core Recognition (Weeks 3-5) — 15-DAY PROTOTYPE COMPLETION

**Deliverables:**
- [ ] Edge pipeline (YOLOv8 + InsightFace)
- [ ] Multi-face detection and recognition
- [ ] IN/OUT direction logic
- [ ] Face enrollment API with quality filtering
- [ ] Basic attendance logging

**Tasks:**
- Implement YOLOv8-face model loading via Ultralytics
- Build frame processing loop: capture → detect → recognize → match
- Add person enrollment endpoint with multi-photo support
- Implement simple deduplication (skip duplicate in <5 minutes)
- Write attendance_logs to PostgreSQL
- Build basic face quality checks (blur, size, confidence)

### Phase 2: API Expansion & Dashboard (Weeks 6-8)

**Deliverables:**
- [ ] Complete REST API endpoints
- [ ] Role-Based Access Control (RBAC)
- [ ] WebSocket real-time event streaming
- [ ] React dashboard with attendance log view
- [ ] Camera management UI

### Phase 3: Frontend & Reporting (Weeks 9-11)

**Deliverables:**
- [ ] Live CCTV camera feed (HLS streaming)
- [ ] Person registration UI
- [ ] Attendance reports (daily, weekly, monthly)
- [ ] Export to CSV
- [ ] Responsive mobile-friendly design

### Phase 4: AI Chat (Weeks 12-13) — ⚠️ FUTURE SCOPE

**Deliverables:**
- [ ] LangChain SQL agent setup
- [ ] Claude API integration
- [ ] Natural language query processing
- [ ] Conversation memory (Redis)
- [ ] Chat UI in React dashboard

### Phase 5: Hardening (Weeks 14-16) — ⚠️ FUTURE SCOPE

**Deliverables:**
- [ ] Load testing (Locust)
- [ ] Edge case handling (network failures, corrupted frames)
- [ ] Prometheus + Grafana monitoring setup
- [ ] Security audit
- [ ] Performance optimization

### Phase 6: Unique Features (Weeks 17-20) — ⚠️ FUTURE SCOPE

**Deliverables:**
- [ ] WhatsApp/Telegram bot integration
- [ ] Visitor management system
- [ ] Leave calendar integration
- [ ] Analytics heatmap
- [ ] Attendance anomaly detection

### Phase 7: Production Launch (Week 21) — ⚠️ FUTURE SCOPE

**Deliverables:**
- [ ] Pilot deployment at 1 office/school
- [ ] Feedback collection and bug fixes
- [ ] SLA monitoring setup
- [ ] Documentation and training

---

## 14. Success Metrics & KPIs

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| **Face Recognition Accuracy** | >99% true positive rate | Weekly audit: manual check of 100 random recognitions |
| **False Accept Rate** | <0.01% | Monthly penetration test with unknown faces |
| **Recognition Latency** | <500ms per face end-to-end | Prometheus histogram p99 |
| **System Uptime** | 99.5% monthly | Grafana uptime monitor |
| **Chat Query Accuracy** | >95% correct SQL generated | ⚠️ FUTURE: Monthly evaluation set of 50 standard queries |
| **Enrollment Time** | <3 minutes per person | Measured in pilot deployment |
| **Multi-face Throughput** | 10 faces simultaneously | Stress test with group photos |
| **Camera Recovery Time** | <30 seconds after reconnect | Automated camera kill/restart test |

---

## 15. Competitive Differentiation

| Competitor | Their Weakness | Our Advantage |
|------------|----------------|--------------|
| **Matrix COSEC** (India) | No AI chat, complex UI, expensive hardware lock-in | Open hardware (any IP camera), conversational AI (future), modern web UI |
| **ZKTeco** | Contact-based biometrics, no NL interface, legacy software | Contactless CCTV-native, AI-powered queries (future) |
| **Darwinbox Attendance** | No face recognition, relies on GPS/WiFi | True camera-based recognition, works in any environment |
| **greytHR** | HR software with basic attendance, no camera integration | Purpose-built recognition engine with potential HR integration (future) |
| **Custom n8n solution** | High latency, hard to scale, limited monitoring | Production microservices, sub-500ms, Kubernetes-ready (future) |

---

## 16. Core Features Summary for 15-Day Prototype

### What You'll Have After 15 Days

✅ **Fully Functional Attendance System**
- Dual CCTV camera integration (IN/OUT tracking)
- 99%+ face recognition accuracy via InsightFace
- Automatic person enrollment with multi-photo support
- Real-time attendance logging to PostgreSQL
- Dashboard showing attendance logs and today's summary

✅ **Production-Ready Foundation**
- FastAPI REST API with JWT authentication
- PostgreSQL with pgvector for face embeddings
- Role-based access control (admin, manager, viewer)
- Docker Compose for easy deployment
- Comprehensive audit logging

✅ **Fully Operational MVP**
- Person registration interface
- Camera management interface
- Real-time attendance monitoring dashboard
- Attendance log viewer with date filters
- Manual attendance override capability

### What's Deferred to Future Phases

⏳ **AI Chat Interface** — Natural language queries (Phase 4+)
⏳ **Advanced Analytics** — Heatmaps, trends, anomalies (Phase 3+)
⏳ **Visitor Management** — Guest check-in/out (Phase 4+)
⏳ **Mobile App** — iOS/Android native apps (Phase 6+)
⏳ **Kubernetes Scaling** — Multi-site, 50+ camera deployments (Phase 6+)
⏳ **Integration APIs** — WhatsApp, leave calendar, HR systems (Phase 5+)
⏳ **Advanced Security** — 2FA, GDPR compliance, privacy mode (Phase 5+)

---

## 17. Getting Started: 15-Day Implementation Checklist

### Week 1: Foundation (Days 1-7)

- [ ] Day 1: Set up PostgreSQL, create schema, Docker setup
- [ ] Day 2-3: FastAPI boilerplate, JWT auth, basic models
- [ ] Day 4-5: InsightFace POC, embed generation, test with local images
- [ ] Day 6-7: Camera RTSP integration, frame capture loop, test with live camera

### Week 2: Core Features (Days 8-14)

- [ ] Day 8-9: YOLOv8 integration, face detection pipeline
- [ ] Day 10-11: Face matching, attendance logging, enrollment API
- [ ] Day 12-13: React dashboard (attendance logs, today's summary)
- [ ] Day 14: End-to-end testing, bug fixes, Docker Compose finalization

### Week 3: Polish (Days 15)

- [ ] Day 15: Final testing, deployment checklist, documentation

---

## Document Metadata

| Property | Value |
|----------|-------|
| **Version** | 1.0 |
| **Last Updated** | June 2025 |
| **Status** | Draft for Review |
| **Confidentiality** | CONFIDENTIAL |
| **Prepared By** | VisionAttend Engineering Team |
| **Copyright** | © 2025 VisionAttend. All rights reserved. |

---

**Document prepared June 2025 — VisionAttend Engineering Team**

*This PRD defines a production-grade attendance system architected for scale, accuracy, and conversational AI. Every decision is based on production requirements, not prototype comfort. The 15-day prototype focuses on core recognition accuracy; advanced features and enterprise scaling come in Phase 2+.*
