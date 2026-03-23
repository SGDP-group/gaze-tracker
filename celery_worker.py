"""
Celery worker startup script.
"""

import sys
import os

if __name__ == "__main__":
    # Use the correct Celery 5.0+ syntax
    os.system("uv run python -m celery -A src.services.celery_app.celery_app worker --loglevel=info")
