from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger)
    xp = Column(Integer, default=0)
    level = Column(Integer, default=0)
    last_message_time = Column(DateTime, default=datetime.utcnow)
    warnings = relationship("Warning", back_populates="user")
    voice_channels = relationship("VoiceChannel", back_populates="owner")


class Warning(Base):
    __tablename__ = "warnings"

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    guild_id = Column(BigInteger)
    moderator_id = Column(BigInteger)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    user = relationship("User", back_populates="warnings")


class VoiceChannel(Base):
    __tablename__ = "voice_channels"

    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger)
    owner_id = Column(BigInteger, ForeignKey("users.id"))
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    limit = Column(Integer, nullable=True)
    locked = Column(Boolean, default=False)
    owner = relationship("User", back_populates="voice_channels")


class GuildConfig(Base):
    __tablename__ = "guild_configs"

    guild_id = Column(BigInteger, primary_key=True)
    welcome_channel_id = Column(BigInteger, nullable=True)
    log_channel_id = Column(BigInteger, nullable=True)
    ticket_category_id = Column(BigInteger, nullable=True)
    voice_category_id = Column(BigInteger, nullable=True)
    automod_enabled = Column(Boolean, default=True)
    max_warnings = Column(Integer, default=3)
    warning_expire_days = Column(Integer, default=30)
