# SIGA - Sistema Integrado de Gestão Acadêmica

## Overview
This is a Django-based school management system (SIGA - Sistema Integrado de Gestão Acadêmica) for managing academic institutions. The system is in Portuguese and supports both university and general education modules.

**Purpose**: Academic institution management including student enrollment, courses, payments, documents, and administrative functions.

**Current State**: Fully functional with SQLite database.

## Project Architecture

### Tech Stack
- **Backend**: Django 5.2.x
- **Database**: SQLite (db.sqlite3)
- **PDF Generation**: ReportLab
- **Language**: Python 3.11

### Directory Structure
```
/
├── escola_sistema/        # Django project settings
│   ├── settings.py        # Main configuration
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI application
├── core/                  # Main application
│   ├── migrations/        # Database migrations
│   ├── static/            # Static files (images, CSS)
│   ├── templates/         # HTML templates
│   ├── models.py          # Database models
│   ├── views.py           # View functions
│   └── urls.py            # App URL routes
├── manage.py              # Django management script
└── db.sqlite3             # SQLite database
```

### Key Models
- `Curso` - Courses
- `Inscricao` - Enrollments
- `AnoAcademico` - Academic years
- `Semestre` - Semesters
- `PerfilUsuario` - User profiles
- `Subscricao` - Subscriptions
- `Documento` - Documents
- `Escola` - Schools

## Development

### Running the Server
```bash
python manage.py runserver 0.0.0.0:5000
```

### Database Operations
```bash
python manage.py migrate          # Apply migrations
python manage.py makemigrations   # Create new migrations
python manage.py createsuperuser  # Create admin user
```

### Admin Access
- URL: `/admin/`
- Create superuser first with `python manage.py createsuperuser`

## Configuration Notes
- `ALLOWED_HOSTS = ['*']` - Configured for Replit proxy
- `CSRF_TRUSTED_ORIGINS` includes Replit domains
- Language: Portuguese (pt-br)
- Timezone: Africa/Luanda

## Recent Changes
- 2025-12-30: Initial Replit environment setup
  - Configured Django workflow on port 5000
  - Installed dependencies (django, reportlab)
