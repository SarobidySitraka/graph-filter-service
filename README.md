# Neo4j Graph Filter Microservice

A production-ready microservice for advanced filtering of Neo4j graph databases with support for complex queries, multiple operators, and relationship traversal.

## 🚀 Features

### Core Capabilities
- **Advanced Node Filtering**: Filter nodes by types, properties, and labels
- **Relationship Filtering**: Filter relationships with direction and depth control
- **Multiple Operators**: 
  - Comparison: `=`, `!=`, `>`, `>=`, `<`, `<=`
  - Text: `CONTAINS`, `STARTS WITH`, `ENDS WITH`
  - Membership: `IN`, `NOT IN`
  - Pattern: `REGEX` (=~)
- **Logical Operators**: Combine filters with `AND`, `OR`, `NOT`
- **Text Search**: Global search across labels and properties
- **Pagination**: Built-in skip/limit support
- **Active Filters Summary**: Track applied filters

### Technical Features
- **FastAPI**: Modern async Python web framework
- **Pydantic V2**: Request/response validation with type safety
- **UV Package Manager**: Fast, reliable dependency management
- **Docker Support**: Multi-stage builds with health checks
- **Singleton Pattern**: Efficient Neo4j connection pooling
- **Comprehensive Logging**: Structured logging with configurable levels
- **Error Handling**: Custom exceptions with detailed error messages
- **Testing**: Pytest with fixtures and integration tests

## 📋 Prerequisites

- **Python**: 3.12 or higher
- **Neo4j**: 5.x
- **UV**: Latest version ([installation guide](https://docs.astral.sh/uv/))
- **Docker** (optional): For containerized deployment

## 🛠️ Installation

### Local Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd neo4j-filter-service
```

2. **Install UV** (if not already installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Set up the project**
```bash
# Create virtual environment and install dependencies
uv sync

# For development dependencies
uv sync --dev
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your Neo4j credentials
```

5. **Run the service**
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

#### Using Docker Compose (Recommended)
```bash
# Start Neo4j and the filter service
docker-compose up -d

# View logs
docker-compose logs -f filter_service

# Stop services
docker-compose down
```

#### Using Docker Only
```bash
# Build the image
docker build -t neo4j-filter-service .

# Run the container
docker run -d \\
  -p 8000:8000 \\
  -e NEO4J_URI=bolt://neo4j:7687 \\
  -e NEO4J_USER=neo4j \\
  -e NEO4J_PASSWORD=password \\
  --name filter_service \\
  neo4j-filter-service
```

## 📖 API Documentation

Once the service is running, access the interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🔌 API Endpoints

### Health Check
```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "neo4j_connected": true,
  "version": "1.0.0"
}
```

### Filter Nodes
```http
POST /api/v1/nodes/filter
```

**Request Body:**
```json
{
  "node_filter": {
    "node_types": ["Person"],
    "property_filters": [
      {
        "property_name": "age",
        "operator": ">",
        "value": 10000000
      },
      {
        "property_name": "status",
        "operator": "=",
        "value": "Active"
      }
    ],
    "logical_operator": "AND"
  },
  "search_query": "John",
  "limit": 100,
  "skip": 0
}
```

**Response:**
```json
{
  "total": 42,
  "limit": 100,
  "skip": 0,
  "data": [
    {
      "id": 123,
      "labels": ["Person"],
      "properties": {
        "name": "John Doe",
        "age": 10000001,
        "status": "Active"
      }
    }
  ],
  "active_filters": [
    "Type: Person",
    "age > 10000000",
    "status = Active",
    "Search: John"
  ]
}
```

### Filter Relationships
```http
POST /api/v1/relationships/filter
```

**Request Body:**
```json
{
  "node_filter": {
    "node_types": ["Person"]
  },
  "relationship_filter": {
    "relationship_types": ["LOCATED_IN", "WORKS_AT"],
    "direction": "outgoing",
    "min_depth": 1,
    "max_depth": 2,
    "property_filters": [
      {
        "property_name": "since",
        "operator": ">=",
        "value": "2020-01-01"
      }
    ]
  },
  "limit": 50
}
```

**Response:**
```json
{
  "total": 15,
  "limit": 50,
  "skip": 0,
  "data": [
    {
      "id": 456,
      "type": "LOCATED_IN",
      "source": {
        "id": 123,
        "labels": ["Person"],
        "properties": {"name": "John"}
      },
      "target": {
        "id": 789,
        "labels": ["City"],
        "properties": {"name": "Paris"}
      },
      "properties": {
        "since": "2020-06-15"
      }
    }
  ],
  "active_filters": [
    "Type: Person",
    "Rel: LOCATED_IN, WORKS_AT"
  ]
}
```

## 💡 Usage Examples

### Python Client Example
```python
import requests

# Filter active persons over 25 years old
response = requests.post(
    "http://localhost:8000/api/v1/nodes/filter",
    json={
        "node_filter": {
            "node_types": ["Person"],
            "property_filters": [
                {
                    "property_name": "age",
                    "operator": ">",
                    "value": 25
                },
                {
                    "property_name": "status",
                    "operator": "=",
                    "value": "Active"
                }
            ],
            "logical_operator": "AND"
        },
        "limit": 100
    }
)

data = response.json()
print(f"Found {data['total']} matching nodes")
for node in data['data']:
    print(f"  - {node['properties']['name']}")
```

### cURL Examples

**Search for nodes:**
```bash
curl -X POST "http://localhost:8000/api/v1/nodes/filter" \\
  -H "Content-Type: application/json" \\
  -d '{
    "search_query": "engineering",
    "limit": 10
  }'
```

**Filter with IN operator:**
```bash
curl -X POST "http://localhost:8000/api/v1/nodes/filter" \\
  -H "Content-Type: application/json" \\
  -d '{
    "node_filter": {
      "node_types": ["Person"],
      "property_filters": [
        {
          "property_name": "country",
          "operator": "IN",
          "value": ["USA", "Canada", "Mexico"]
        }
      ]
    },
    "limit": 50
  }'
```

## 🧪 Testing

### Run All Tests
```bash
uv run pytest
```

### Run Specific Test Files
```bash
uv run pytest tests/test_api.py
uv run pytest tests/test_query_builder.py
```

### Run with Coverage
```bash
uv run pytest --cov=app --cov-report=html
```

### Run with Verbose Output
```bash
uv run pytest -v -s
```

## 🔧 Development

### Code Quality Tools

**Format code with Black:**
```bash
uv run black app/
```

**Lint with Ruff:**
```bash
uv run ruff check app/
```

**Type checking with mypy:**
```bash
uv run mypy app/
```

### Adding Dependencies

**Add a production dependency:**
```bash
uv add package-name
```

**Add a development dependency:**
```bash
uv add --dev package-name
```

**Update dependencies:**
```bash
uv lock
uv sync
```

## 📁 Project Structure

```
neo4j-filter-service/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Configuration
│   ├── core/
│   │   ├── __init__.py
│   │   ├── enums.py              # Enumerations
│   │   ├── models.py             # Pydantic models
│   │   └── exceptions.py         # Custom exceptions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── neo4j_service.py      # Neo4j connection
│   │   ├── filter_service.py     # Filter logic
│   │   └── query_builder.py      # Cypher builder
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py       # FastAPI dependencies
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── nodes.py          # Node endpoints
│   │       ├── relationships.py  # Relationship endpoints
│   │       └── health.py         # Health endpoint
│   └── utils/
│       ├── __init__.py
│       └── logger.py             # Logging setup
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_query_builder.py
│   └── test_filter_service.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
└── README.md
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEO4J_URI` | Neo4j connection URI | `bolt://localhost:7687` |
| `NEO4J_USER` | Neo4j username | `neo4j` |
| `NEO4J_PASSWORD` | Neo4j password | `password` |
| `APP_NAME` | Application name | `Neo4j Filter Service` |
| `APP_VERSION` | Application version | `1.0.0` |
| `DEBUG` | Debug mode | `False` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `API_V1_PREFIX` | API version prefix | `/api/v1` |
| `CORS_ORIGINS` | Allowed CORS origins | `["http://localhost:3000"]` |
| `DEFAULT_PAGE_SIZE` | Default pagination size | `100` |
| `MAX_PAGE_SIZE` | Maximum pagination size | `1000` |

## 🐛 Troubleshooting

### Neo4j Connection Issues
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Check logs
docker logs neo4j_db

# Test connection
cypher-shell -u neo4j -p password123
```

### Service Not Starting
```bash
# Check logs
docker logs filter_service

# Verify environment variables
docker exec filter_service env | grep NEO4J
```

### UV Issues
```bash
# Clear cache
uv cache clean

# Reinstall dependencies
rm uv.lock
uv sync
```

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📧 Support

For issues and questions:
- Open an issue on GitHub
- Contact: your.email@example.com

---

Built with ❤️ using FastAPI, Neo4j, and UV