from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    # Роль-шаблон прав: viewer | calculator (режимщик) | operator | editor | admin
    role = Column(String, nullable=False, default="viewer")
    # Города, к которым есть доступ (коды через запятую, cities.py); NULL — все
    cities = Column(Text, nullable=True)
    # Отличия прав от шаблона роли (permissions.py), JSON; NULL — права роли
    permissions = Column(Text, nullable=True)

class ActivityLog(Base):
    """Журнал действий пользователей (activity.py): входы, правки, расчёты, выгрузки — общий для городов."""
    __tablename__ = "activity_log"
    id = Column(Integer, primary_key=True)
    at = Column(DateTime, nullable=False, index=True)
    username = Column(String(100), index=True)
    city = Column(String(20))
    action = Column(String(20), nullable=False, index=True)
    method = Column(String(8))
    path = Column(String(300))
    status = Column(Integer)
    duration_ms = Column(Integer)
    ip = Column(String(64))
    user_agent = Column(String(300))
    details = Column(Text)

class UserPermission(Base):
    __tablename__ = "user_permissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    schema_name = Column(String, nullable=False)
    read_access = Column(Boolean, default=False)
    write_access = Column(Boolean, default=False)