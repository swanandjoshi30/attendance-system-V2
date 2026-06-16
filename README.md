# Attendance System V2

Basic face-recognition attendance prototype for local development.

This repository is being kept intentionally small for the first working prototype. The current goal is to make the registration and attendance kiosk flows reliable on a local machine, then expand toward the broader VisionAttend PRD in later phases.

## Quick Start

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Create a PostgreSQL database named `attendance2`, or set your own database values with environment variables.

3. Run the registration app:

```bash
python run_registration.py
```

4. Run the attendance kiosk:

```bash
python run_attendance.py
```

## Prototype Scope

- Tkinter-based registration app
- Tkinter-based attendance kiosk
- PostgreSQL-backed student, class, subject, and attendance storage
- Local webcam / RTSP camera support through OpenCV
- Face encoding and recognition with the current OpenCV-based engine
- Automatic schema bootstrap from the bundled SQL file

## What Is Deferred

- FastAPI backend
- React dashboard
- Redis queueing
- Production-grade InsightFace / YOLO pipeline
- AI chat and reporting services
- Kubernetes and monitoring stack

## Full Local Setup

### 1. Install Dependencies

Use a virtual environment if possible, then install the Python packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create the Database

Create a PostgreSQL database before starting the apps:

```bash
createdb attendance2
```

If you use a different name or credentials, set these environment variables:

- `ATTENDANCE_DB_HOST`
- `ATTENDANCE_DB_NAME`
- `ATTENDANCE_DB_USER`
- `ATTENDANCE_DB_PASSWORD`
- `ATTENDANCE_DB_PORT`

Example:

```bash
export ATTENDANCE_DB_NAME=attendance2
export ATTENDANCE_DB_USER=postgres
export ATTENDANCE_DB_PASSWORD='Pass@123'
export ATTENDANCE_DB_HOST=localhost
export ATTENDANCE_DB_PORT=5432
```

### 3. Start the Registration App

```bash
python run_registration.py
```

### 4. Start the Attendance Kiosk

```bash
python run_attendance.py
```

## What the Prototype Does

- Loads the bundled SQL schema automatically on startup
- Detects available local cameras through OpenCV
- Registers students with face encodings stored in PostgreSQL
- Marks attendance from the kiosk UI against the selected subject

## Database Bootstrap

The first startup runs the bundled [tables](tables) SQL script to create the prototype schema if it does not already exist.

## Prototype Data Model

The current prototype uses these tables:

- `Classes`
- `Subjects`
- `Students`
- `FaceEncodings`
- `AttendanceLog`

This matches the current code paths and keeps the first version simple enough to run locally before evolving into the production architecture described in [EduVision_PRD_v1_0.md](EduVision_PRD_v1_0.md).

## Next Development Step

After the prototype is stable, the next phase should be:

1. Replace the OpenCV face matcher with a proper detection + embedding pipeline.
2. Add a FastAPI service layer around enrollment and attendance logging.
3. Move the UI from Tkinter to a web dashboard.
4. Introduce role-based authentication and reporting.
