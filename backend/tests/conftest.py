import os

# Tests run on throwaway SQLite, never on the Neon DB. Must be set before app modules import settings.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-123"
os.environ["LLM_PROVIDER"] = "mock"
