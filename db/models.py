from datetime import datetime
from sqlalchemy import Column, String, BigInteger, Boolean, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Bot(Base):
    __tablename__ = 'bots'
    
    id = Column(String(32), primary_key=True)
    name = Column(String(50))
    description = Column(String(200))
    current_qr = Column(Text)
    authed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    
    users = relationship('User', secondary='users_bots_mul', back_populates='bots')


class User(Base):
    __tablename__ = 'users'
    
    tg_id = Column(BigInteger, primary_key=True)
    data = Column(JSON)  # {'notifications': True, ...}
    created_at = Column(DateTime, default=func.now())
    
    bots = relationship('Bot', secondary='users_bots_mul', back_populates='users')


class UserBotAssociation(Base):
    __tablename__ = 'users_bots_mul'
    
    user_id = Column(BigInteger, ForeignKey('users.tg_id'), primary_key=True)
    bot_id = Column(String(32), ForeignKey('bots.id'), primary_key=True)
    created_at = Column(DateTime, default=func.now()) 