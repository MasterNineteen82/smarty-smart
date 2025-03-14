from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Card(Base):
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True, index=True)
    atr = Column(String, unique=True, index=True)
    name = Column(String)
    status = Column(String)
    
    def __repr__(self):
        return f"<Card(id={self.id}, atr={self.atr}, name={self.name}, status={self.status})>"