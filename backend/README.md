# MineWatch Backend

## Run

1. Create a virtualenv and install deps:

```bash
pip install -r requirements.txt
```

2. Start the API:

```bash
uvicorn main:app --reload --port 8000
```

Health check:

- http://localhost:8000/health
