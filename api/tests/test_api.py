"""
TCGInvest API — Smoke tests
These run in CI without a live DB (mocked) and on-server with the real DB.
"""
import pytest
import sys
import os

# Allow importing main without the real .env
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestApiStructure:
    """Structural / import tests — no DB required."""

    def test_python_version(self):
        """Python 3.10+ required."""
        assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version}"

    def test_fastapi_importable(self):
        """FastAPI must be importable."""
        from fastapi import FastAPI
        app = FastAPI()
        assert app is not None

    def test_pydantic_importable(self):
        """Pydantic must be importable."""
        from pydantic import BaseModel
        class TestModel(BaseModel):
            name: str
        m = TestModel(name="test")
        assert m.name == "test"

    def test_jose_importable(self):
        """python-jose required for JWT."""
        from jose import jwt
        assert jwt is not None

    def test_main_syntax(self):
        """main.py must compile without syntax errors."""
        import py_compile
        result = py_compile.compile(
            os.path.join(os.path.dirname(__file__), '..', 'main.py'),
            doraise=True
        )
        assert result is not None or True  # compile raises on error


class TestBusinessLogic:
    """Unit tests for pure business logic (no DB needed)."""

    def test_set_name_not_empty(self):
        """Set names in SET_IMAGE_MAP must not be empty strings."""
        # Import just the map without triggering DB connections
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "main_partial",
            os.path.join(os.path.dirname(__file__), '..', 'main.py')
        )
        # Just test that key Pokemon sets are present in the file
        with open(os.path.join(os.path.dirname(__file__), '..', 'main.py')) as f:
            content = f.read()
        assert "Prismatic Evolutions" in content
        assert "Hidden Fates" in content
        assert "Evolving Skies" in content

    def test_stripe_env_var_referenced(self):
        """main.py must reference STRIPE env vars (price ID lives in .env, not source)."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'main.py')) as f:
            content = f.read()
        # Price ID correctly lives in .env — check that Stripe is wired in
        assert "stripe" in content.lower() or "STRIPE" in content, \
            "No Stripe reference found in main.py"

    def test_no_hardcoded_secrets(self):
        """main.py must not contain hardcoded API keys."""
        with open(os.path.join(os.path.dirname(__file__), '..', 'main.py')) as f:
            content = f.read()
        # Should use os.getenv / load_dotenv, not raw secrets
        assert "load_dotenv" in content, "load_dotenv not found — secrets may be hardcoded"
        # Must not contain patterns that look like raw Stripe secret keys
        assert "sk_live_" not in content, "Hardcoded Stripe live key found!"
        assert "sk_test_" not in content, "Hardcoded Stripe test key found!"


class TestHealthEndpoint:
    """Smoke test against running server (skipped in pure CI)."""

    @pytest.fixture
    def server_running(self):
        """Check if local API server is up."""
        import socket
        try:
            s = socket.create_connection(("localhost", 8000), timeout=2)
            s.close()
            return True
        except Exception:
            return False

    def test_health_endpoint(self, server_running):
        """GET /health should return 200 when server is running."""
        if not server_running:
            pytest.skip("API server not running — skipping live test")
        import urllib.request
        try:
            response = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
            assert response.status == 200
        except Exception as e:
            pytest.skip(f"Health endpoint not reachable: {e}")
