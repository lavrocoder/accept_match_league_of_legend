from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.config import DATA_DIR
from backend.models import Champions

Base = declarative_base()


class Preset(Base):
    __tablename__ = 'presets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)
    preset_type = Column(String(10), nullable=False)
    champion_id = Column(Integer, nullable=False)
    champion_name = Column(String(50), nullable=False)
    position = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('role', 'preset_type', 'champion_id', name='uq_role_type_champion'),
        Index('idx_role_type', 'role', 'preset_type'),
    )


class Setting(Base):
    __tablename__ = 'settings'

    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)


class PresetsDatabase:
    """Database for storing champion presets"""

    ROLES = ['top', 'jungle', 'middle', 'bottom', 'utility']
    PRESET_TYPES = ['pick', 'ban']

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DATA_DIR / 'presets.db'
        self.engine = create_engine(f'sqlite:///{self.db_path}', echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_db()

    def _get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def _init_db(self):
        """Initialize database tables"""
        Base.metadata.create_all(self.engine)

        # Initialize default settings if not exist
        with self._get_session() as session:
            for key in ['auto_accept', 'auto_ban', 'auto_pick']:
                existing = session.query(Setting).filter_by(key=key).first()
                if not existing:
                    session.add(Setting(key=key, value='1'))
            session.commit()

    def get_preset(self, role: str, preset_type: str) -> list[dict]:
        """Get champions for a specific role and preset type"""
        with self._get_session() as session:
            presets = session.query(Preset).filter_by(
                role=role, preset_type=preset_type
            ).order_by(Preset.position).all()

            return [
                {
                    'id': p.champion_id,
                    'name': p.champion_name,
                    'position': p.position
                }
                for p in presets
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
        with self._get_session() as session:
            # Clear existing preset
            session.query(Preset).filter_by(role=role, preset_type=preset_type).delete()

            # Insert new champions
            for position, champ in enumerate(champions):
                session.add(Preset(
                    role=role,
                    preset_type=preset_type,
                    champion_id=champ['id'],
                    champion_name=champ['name'],
                    position=position
                ))
            session.commit()

    def add_champion_to_preset(self, role: str, preset_type: str, champion_id: int, champion_name: str):
        """Add a champion to the end of a preset"""
        with self._get_session() as session:
            # Get max position
            max_pos = session.query(Preset.position).filter_by(
                role=role, preset_type=preset_type
            ).order_by(Preset.position.desc()).first()

            new_position = (max_pos[0] + 1) if max_pos else 0

            # Check if champion already exists
            existing = session.query(Preset).filter_by(
                role=role, preset_type=preset_type, champion_id=champion_id
            ).first()

            if existing:
                existing.position = new_position
            else:
                session.add(Preset(
                    role=role,
                    preset_type=preset_type,
                    champion_id=champion_id,
                    champion_name=champion_name,
                    position=new_position
                ))
            session.commit()

    def remove_champion_from_preset(self, role: str, preset_type: str, champion_id: int):
        """Remove a champion from a preset"""
        with self._get_session() as session:
            preset = session.query(Preset).filter_by(
                role=role, preset_type=preset_type, champion_id=champion_id
            ).first()

            if preset:
                removed_position = preset.position
                session.delete(preset)

                # Update positions of remaining champions
                session.query(Preset).filter(
                    Preset.role == role,
                    Preset.preset_type == preset_type,
                    Preset.position > removed_position
                ).update({Preset.position: Preset.position - 1})

                session.commit()

    def move_champion(self, role: str, preset_type: str, champion_id: int, new_position: int):
        """Move a champion to a new position in the preset"""
        with self._get_session() as session:
            preset = session.query(Preset).filter_by(
                role=role, preset_type=preset_type, champion_id=champion_id
            ).first()

            if not preset:
                return

            old_position = preset.position

            if old_position == new_position:
                return

            if old_position < new_position:
                # Moving down: shift others up
                session.query(Preset).filter(
                    Preset.role == role,
                    Preset.preset_type == preset_type,
                    Preset.position > old_position,
                    Preset.position <= new_position
                ).update({Preset.position: Preset.position - 1})
            else:
                # Moving up: shift others down
                session.query(Preset).filter(
                    Preset.role == role,
                    Preset.preset_type == preset_type,
                    Preset.position >= new_position,
                    Preset.position < old_position
                ).update({Preset.position: Preset.position + 1})

            preset.position = new_position
            session.commit()

    def clear_preset(self, role: str, preset_type: str):
        """Clear all champions from a preset"""
        with self._get_session() as session:
            session.query(Preset).filter_by(role=role, preset_type=preset_type).delete()
            session.commit()

    def clear_all(self):
        """Clear all presets"""
        with self._get_session() as session:
            session.query(Preset).delete()
            session.commit()

    def import_from_champions(self, champions: Champions):
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
        with self._get_session() as session:
            count = session.query(Preset).count()
            return count == 0

    # Settings methods
    def get_setting(self, key: str) -> bool:
        """Get a boolean setting value"""
        with self._get_session() as session:
            setting = session.query(Setting).filter_by(key=key).first()
            return setting.value == '1' if setting else True

    def set_setting(self, key: str, value: bool):
        """Set a boolean setting value"""
        with self._get_session() as session:
            setting = session.query(Setting).filter_by(key=key).first()
            if setting:
                setting.value = '1' if value else '0'
            else:
                session.add(Setting(key=key, value='1' if value else '0'))
            session.commit()

    def get_all_settings(self) -> dict:
        """Get all settings as a dictionary"""
        with self._get_session() as session:
            settings = session.query(Setting).all()
            return {s.key: s.value == '1' for s in settings}
