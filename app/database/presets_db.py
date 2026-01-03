import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from app.config import DATA_DIR


class PresetsDatabase:
    """Database for storing champion presets"""

    ROLES = ['top', 'jungle', 'middle', 'bottom', 'utility']
    PRESET_TYPES = ['pick', 'ban']

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATA_DIR / 'presets.db'
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create presets table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS presets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    preset_type TEXT NOT NULL,
                    champion_id INTEGER NOT NULL,
                    champion_name TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    UNIQUE(role, preset_type, champion_id)
                )
            ''')

            # Create index for faster queries
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_role_type
                ON presets(role, preset_type)
            ''')

            # Create settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Initialize default settings if not exist
            cursor.execute('''
                INSERT OR IGNORE INTO settings (key, value) VALUES
                ('auto_accept', '1'),
                ('auto_ban', '1'),
                ('auto_pick', '1')
            ''')

    def get_preset(self, role: str, preset_type: str) -> list[dict]:
        """Get champions for a specific role and preset type"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT champion_id, champion_name, position
                FROM presets
                WHERE role = ? AND preset_type = ?
                ORDER BY position
            ''', (role, preset_type))

            return [
                {
                    'id': row['champion_id'],
                    'name': row['champion_name'],
                    'position': row['position']
                }
                for row in cursor.fetchall()
            ]

    def get_all_presets(self) -> dict:
        """Get all presets organized by role and type"""
        result = {}
        for role in self.ROLES:
            result[role] = self.get_preset(role, 'pick')
            result[f'{role}_ban'] = self.get_preset(role, 'ban')
        return result

    def set_preset(self, role: str, preset_type: str, champions: list[dict]):
        """Set champions for a specific role and preset type"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clear existing preset
            cursor.execute('''
                DELETE FROM presets
                WHERE role = ? AND preset_type = ?
            ''', (role, preset_type))

            # Insert new champions
            for position, champ in enumerate(champions):
                cursor.execute('''
                    INSERT INTO presets (role, preset_type, champion_id, champion_name, position)
                    VALUES (?, ?, ?, ?, ?)
                ''', (role, preset_type, champ['id'], champ['name'], position))

    def add_champion_to_preset(self, role: str, preset_type: str, champion_id: int, champion_name: str):
        """Add a champion to the end of a preset"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get max position
            cursor.execute('''
                SELECT COALESCE(MAX(position), -1) as max_pos
                FROM presets
                WHERE role = ? AND preset_type = ?
            ''', (role, preset_type))
            max_pos = cursor.fetchone()['max_pos']

            # Insert new champion
            cursor.execute('''
                INSERT OR REPLACE INTO presets (role, preset_type, champion_id, champion_name, position)
                VALUES (?, ?, ?, ?, ?)
            ''', (role, preset_type, champion_id, champion_name, max_pos + 1))

    def remove_champion_from_preset(self, role: str, preset_type: str, champion_id: int):
        """Remove a champion from a preset"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get position of champion to remove
            cursor.execute('''
                SELECT position FROM presets
                WHERE role = ? AND preset_type = ? AND champion_id = ?
            ''', (role, preset_type, champion_id))
            row = cursor.fetchone()

            if row:
                removed_position = row['position']

                # Delete champion
                cursor.execute('''
                    DELETE FROM presets
                    WHERE role = ? AND preset_type = ? AND champion_id = ?
                ''', (role, preset_type, champion_id))

                # Update positions of remaining champions
                cursor.execute('''
                    UPDATE presets
                    SET position = position - 1
                    WHERE role = ? AND preset_type = ? AND position > ?
                ''', (role, preset_type, removed_position))

    def move_champion(self, role: str, preset_type: str, champion_id: int, new_position: int):
        """Move a champion to a new position in the preset"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get current position
            cursor.execute('''
                SELECT position FROM presets
                WHERE role = ? AND preset_type = ? AND champion_id = ?
            ''', (role, preset_type, champion_id))
            row = cursor.fetchone()

            if not row:
                return

            old_position = row['position']

            if old_position == new_position:
                return

            if old_position < new_position:
                # Moving down: shift others up
                cursor.execute('''
                    UPDATE presets
                    SET position = position - 1
                    WHERE role = ? AND preset_type = ?
                    AND position > ? AND position <= ?
                ''', (role, preset_type, old_position, new_position))
            else:
                # Moving up: shift others down
                cursor.execute('''
                    UPDATE presets
                    SET position = position + 1
                    WHERE role = ? AND preset_type = ?
                    AND position >= ? AND position < ?
                ''', (role, preset_type, new_position, old_position))

            # Update champion position
            cursor.execute('''
                UPDATE presets
                SET position = ?
                WHERE role = ? AND preset_type = ? AND champion_id = ?
            ''', (new_position, role, preset_type, champion_id))

    def clear_preset(self, role: str, preset_type: str):
        """Clear all champions from a preset"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM presets
                WHERE role = ? AND preset_type = ?
            ''', (role, preset_type))

    def clear_all(self):
        """Clear all presets"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM presets')

    def import_from_champions(self, champions: 'Champions'):
        """Import presets from Champions model"""
        role_mapping = {
            'top': ('top', 'top_ban'),
            'jungle': ('jungle', 'jungle_ban'),
            'middle': ('middle', 'middle_ban'),
            'bottom': ('bottom', 'bottom_ban'),
            'utility': ('utility', 'utility_ban')
        }

        for role, (pick_attr, ban_attr) in role_mapping.items():
            # Import picks
            pick_champs = getattr(champions, pick_attr, [])
            self.set_preset(role, 'pick', [
                {'id': c.id, 'name': c.name} for c in pick_champs
            ])

            # Import bans
            ban_champs = getattr(champions, ban_attr, [])
            self.set_preset(role, 'ban', [
                {'id': c.id, 'name': c.name} for c in ban_champs
            ])

    def is_empty(self) -> bool:
        """Check if database has any presets"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM presets')
            return cursor.fetchone()['count'] == 0

    # Settings methods
    def get_setting(self, key: str) -> bool:
        """Get a boolean setting value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            return row['value'] == '1' if row else True

    def set_setting(self, key: str, value: bool):
        """Set a boolean setting value"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            ''', (key, '1' if value else '0'))

    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM settings')
            return {row['key']: row['value'] == '1' for row in cursor.fetchall()}
