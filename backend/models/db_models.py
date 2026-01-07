from sqlalchemy import Column, Integer, String, Text, UniqueConstraint, Index

from backend.database import Base, get_session
from backend.models import Champions


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

    ROLES = ['top', 'jungle', 'middle', 'bottom', 'utility']
    PRESET_TYPES = ['pick', 'ban']

    @classmethod
    def get_preset(cls, role: str, preset_type: str) -> list[dict]:
        """Get champions for a specific role and preset type"""
        with get_session() as session:
            presets = session.query(cls).filter_by(
                role=role, preset_type=preset_type
            ).order_by(cls.position).all()

            return [
                {
                    'id': p.champion_id,
                    'name': p.champion_name,
                    'position': p.position
                }
                for p in presets
            ]

    @classmethod
    def get_all_presets(cls) -> dict:
        """Get all presets organized by role and type"""
        result = {}
        for role in cls.ROLES:
            result[role] = cls.get_preset(role, 'pick')
            result[f'{role}_ban'] = cls.get_preset(role, 'ban')
        return result

    @classmethod
    def set_preset(cls, role: str, preset_type: str, champions: list[dict]):
        """Set champions for a specific role and preset type"""
        with get_session() as session:
            session.query(cls).filter_by(role=role, preset_type=preset_type).delete()

            for position, champ in enumerate(champions):
                session.add(cls(
                    role=role,
                    preset_type=preset_type,
                    champion_id=champ['id'],
                    champion_name=champ['name'],
                    position=position
                ))
            session.commit()

    @classmethod
    def add_champion_to_preset(cls, role: str, preset_type: str, champion_id: int, champion_name: str):
        """Add a champion to the end of a preset"""
        with get_session() as session:
            max_pos = session.query(cls.position).filter_by(
                role=role, preset_type=preset_type
            ).order_by(cls.position.desc()).first()

            new_position = (max_pos[0] + 1) if max_pos else 0

            existing = session.query(cls).filter_by(
                role=role, preset_type=preset_type, champion_id=champion_id
            ).first()

            if existing:
                existing.position = new_position
            else:
                session.add(cls(
                    role=role,
                    preset_type=preset_type,
                    champion_id=champion_id,
                    champion_name=champion_name,
                    position=new_position
                ))
            session.commit()

    @classmethod
    def remove_champion_from_preset(cls, role: str, preset_type: str, champion_id: int):
        """Remove a champion from a preset"""
        with get_session() as session:
            preset = session.query(cls).filter_by(
                role=role, preset_type=preset_type, champion_id=champion_id
            ).first()

            if preset:
                removed_position = preset.position
                session.delete(preset)

                session.query(cls).filter(
                    cls.role == role,
                    cls.preset_type == preset_type,
                    cls.position > removed_position
                ).update({cls.position: cls.position - 1})

                session.commit()

    @classmethod
    def move_champion(cls, role: str, preset_type: str, champion_id: int, new_position: int):
        """Move a champion to a new position in the preset"""
        with get_session() as session:
            preset = session.query(cls).filter_by(
                role=role, preset_type=preset_type, champion_id=champion_id
            ).first()

            if not preset:
                return

            old_position = preset.position

            if old_position == new_position:
                return

            if old_position < new_position:
                session.query(cls).filter(
                    cls.role == role,
                    cls.preset_type == preset_type,
                    cls.position > old_position,
                    cls.position <= new_position
                ).update({cls.position: cls.position - 1})
            else:
                session.query(cls).filter(
                    cls.role == role,
                    cls.preset_type == preset_type,
                    cls.position >= new_position,
                    cls.position < old_position
                ).update({cls.position: cls.position + 1})

            preset.position = new_position
            session.commit()

    @classmethod
    def clear_preset(cls, role: str, preset_type: str):
        """Clear all champions from a preset"""
        with get_session() as session:
            session.query(cls).filter_by(role=role, preset_type=preset_type).delete()
            session.commit()

    @classmethod
    def clear_all(cls):
        """Clear all presets"""
        with get_session() as session:
            session.query(cls).delete()
            session.commit()

    @classmethod
    def import_from_champions(cls, champions: Champions):
        """Import presets from Champions model"""
        role_mapping = {
            'top': ('top', 'top_ban'),
            'jungle': ('jungle', 'jungle_ban'),
            'middle': ('middle', 'middle_ban'),
            'bottom': ('bottom', 'bottom_ban'),
            'utility': ('utility', 'utility_ban')
        }

        for role, (pick_attr, ban_attr) in role_mapping.items():
            pick_champs = getattr(champions, pick_attr, [])
            cls.set_preset(role, 'pick', [
                {'id': c.id, 'name': c.name} for c in pick_champs
            ])

            ban_champs = getattr(champions, ban_attr, [])
            cls.set_preset(role, 'ban', [
                {'id': c.id, 'name': c.name} for c in ban_champs
            ])

    @classmethod
    def is_empty(cls) -> bool:
        """Check if database has any presets"""
        with get_session() as session:
            count = session.query(cls).count()
            return count == 0


class Setting(Base):
    __tablename__ = 'settings'

    key = Column(String(50), primary_key=True)
    value = Column(Text, nullable=False)

    @classmethod
    def init_default_settings(cls):
        """Initialize default settings if not exist"""
        with get_session() as session:
            for key in ['auto_accept', 'auto_ban', 'auto_pick']:
                existing = session.query(cls).filter_by(key=key).first()
                if not existing:
                    session.add(cls(key=key, value='1'))
            session.commit()

    @classmethod
    def get_setting(cls, key: str) -> bool:
        """Get a boolean setting value"""
        with get_session() as session:
            setting = session.query(cls).filter_by(key=key).first()
            return setting.value == '1' if setting else True

    @classmethod
    def set_setting(cls, key: str, value: bool):
        """Set a boolean setting value"""
        with get_session() as session:
            setting = session.query(cls).filter_by(key=key).first()
            if setting:
                setting.value = '1' if value else '0'
            else:
                session.add(cls(key=key, value='1' if value else '0'))
            session.commit()

    @classmethod
    def get_all_settings(cls) -> dict:
        """Get all settings as a dictionary"""
        with get_session() as session:
            settings = session.query(cls).all()
            return {s.key: s.value == '1' for s in settings}
