import os

# Unit tests never connect; point the engine at a dummy psycopg2 URL so importing
# app.database works regardless of the shell environment.
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
