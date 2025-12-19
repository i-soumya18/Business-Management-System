# 🚀 Quick Start Guide

This guide will help you set up and run the Business Management System.

## Prerequisites

- Docker & Docker Compose 24.0+
- Python 3.11+
- Node.js 20+ (for frontend)
- Git 2.40+

## Setup Instructions

### 1. Clone and Configure

```bash
# Clone the repository
cd "/home/aspire/Projects/Business Management System"

# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

### 2. Configure Environment

Edit the `.env` file with your configuration:

```bash
# Essential configurations
SECRET_KEY="your-secret-key-here"
JWT_SECRET_KEY="your-jwt-secret-key-here"

# Database (already configured for Docker)
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/bms_db"

# Redis
REDIS_URL="redis://:redis123@localhost:6379/0"

# MongoDB
MONGODB_URL="mongodb://admin:admin123@localhost:27017"
```

### 3. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Or start individual services
docker-compose up -d postgres
docker-compose up -d redis
docker-compose up -d mongodb
```

### 4. Run Backend

```bash
cd backend

# Activate virtual environment
source venv/bin/activate

# Run migrations
alembic upgrade head

# Initialize default data (roles, permissions, admin user)
python scripts/init_default_data.py

# Start server
uvicorn app.main:app --reload
```

The API will be available at:
- **API:** http://localhost:8000
- **Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### 5. Default Credentials

**Admin User:**
- Email: `admin@example.com`
- Password: `Admin123!`

⚠️ **IMPORTANT:** Change the admin password immediately after first login!

## Development Workflow

### Running Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py

# Run with markers
pytest -m unit
pytest -m integration
```

### Code Quality

```bash
# Format code
black app tests

# Sort imports
isort app tests

# Lint
flake8 app
pylint app

# Type checking
mypy app

# Or run all at once with pre-commit
pre-commit run --all-files
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# View migration history
alembic history
```

### Docker Commands

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f postgres

# Restart service
docker-compose restart backend

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Rebuild service
docker-compose up -d --build backend
```

## API Usage

### 1. Register a User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

### 3. Access Protected Endpoint

```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. List Users (Admin)

```bash
curl -X GET http://localhost:8000/api/v1/users/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```
business-management-system/
├── backend/                # FastAPI backend
│   ├── app/
│   │   ├── api/           # API routes
│   │   ├── core/          # Core configuration
│   │   ├── models/        # SQLAlchemy models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── services/      # Business logic
│   │   ├── repositories/  # Data access
│   │   └── main.py        # Application entry
│   ├── tests/             # Tests
│   ├── alembic/           # Migrations
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## Troubleshooting

### Database Connection Error

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Migration Issues

```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d postgres
alembic upgrade head
python scripts/init_default_data.py
```

### Redis Connection Error

```bash
# Check Redis
docker-compose ps redis
docker-compose logs redis

# Test Redis connection
redis-cli -h localhost -p 6379 -a redis123 ping
```

## Next Steps

- [X] Phase 0: Foundation setup ✅
- [X] Phase 1.1: Authentication & User Management ✅
- [ ] Phase 1.2: Role Management API
- [ ] Phase 1.3: Inventory Module
- [ ] Phase 2: Multi-Channel Sales
- [ ] Phase 3: CRM & Finance
- [ ] Phase 4: ML/AI Pipeline

## Support

- **Documentation:** http://localhost:8000/docs
- **Issues:** Create an issue in the repository
- **Email:** support@yourbusiness.com

---

Built with ❤️ for the garment industry
