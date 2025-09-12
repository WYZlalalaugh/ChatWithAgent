"""
基础数据模型
"""

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String, Text, JSON
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TimestampMixin:
    """时间戳混入类"""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow, 
        nullable=False
    )


class BaseModel(Base, TimestampMixin):
    """基础模型类"""
    
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"