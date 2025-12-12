"""Migration to create collections and collection_items tables.

Run with: python -m migrations.002_create_collections_tables
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


def migrate():
    """Create collections and collection_items tables."""
    settings = get_settings()

    # Parse SQLite path from URL (sqlite+aiosqlite:///path/to/db.sqlite)
    db_path = settings.sqlite_url.replace("sqlite+aiosqlite:///", "")

    print(f"Connecting to database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if collections table already exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='collections'"
    )
    if cursor.fetchone():
        print("Table 'collections' already exists. Skipping migration.")
        conn.close()
        return

    # Create collections table
    print("Creating 'collections' table...")
    cursor.execute("""
        CREATE TABLE collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL,
            slug VARCHAR(100) UNIQUE NOT NULL,
            description TEXT,
            cover_url TEXT,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create index on slug
    cursor.execute("CREATE INDEX idx_collections_slug ON collections(slug)")

    # Create collection_items table
    print("Creating 'collection_items' table...")
    cursor.execute("""
        CREATE TABLE collection_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            item_type VARCHAR(10) NOT NULL,
            url TEXT NOT NULL,
            thumbnail_url TEXT,
            title VARCHAR(500),
            source_url TEXT,
            domain VARCHAR(200),
            embed_type VARCHAR(20),
            video_id VARCHAR(50),
            sort_order INTEGER DEFAULT 0,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for collection_items
    cursor.execute(
        "CREATE INDEX idx_collection_items_collection_id ON collection_items(collection_id)"
    )
    cursor.execute(
        "CREATE INDEX idx_collection_items_sort_order ON collection_items(collection_id, sort_order)"
    )

    conn.commit()

    print("Migration completed successfully!")
    conn.close()


if __name__ == "__main__":
    migrate()
