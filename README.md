# Research Management System (RMS)

A Django-based system for managing research proposals with a 6-step workflow.

## Tech Stack

- **Backend**: Django, Django Rest Framework (DRF)
- **Database**: MySQL
- **Frontend**: HTML, CSS (Bootstrap), JavaScript (Axios)

## Setup Instructions

1.  **Environment Setup**:

    - Ensure Python and MySQL are installed.
    - Create a virtual environment: `python -m venv venv`
    - Activate it: `.\venv\Scripts\activate` (Windows)
    - Install dependencies: `pip install -r requirements.txt`

2.  **Database Configuration**:

    - Create a MySQL database named `rms`.
    - Update `.env` file with your MySQL credentials if they differ from the default.

3.  **Migrations**:

    - Run `python manage.py migrate` to set up the database tables.

4.  **Run Server**:
    - Run `python manage.py runserver`
    - Access the application at `http://127.0.0.1:8000/`

## Workflow

1.  **Register/Login**: Users can register as 'Participant' or 'Admin'.
2.  **Participant**: Uploads a proposal.
3.  **Admin**:
    - **Step 1**: Format Check (Accept/Reject).
    - **Step 2**: Plagiarism Check (Input %, >20% auto-reject).
    - **Step 3**: Evaluation (Input 2 marks, Sum <65 auto-reject).
    - **Step 4**: Seminar (Input attendance/acceptance).
    - **Step 5**: Research Committee (Participant uploads budget, Admin approves).
    - **Step 6**: Rector Approval (Final Accept/Reject).

## API Endpoints

- `/api/users/register/`
- `/api/users/login/`
- `/api/proposals/` (CRUD and workflow actions)
