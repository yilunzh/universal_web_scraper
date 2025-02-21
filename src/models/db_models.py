from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success"

class URLStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class LogLevel(enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"
    
    id = Column(Integer, primary_key=True)
    job_name = Column(String)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    urls = relationship("JobURL", back_populates="job", cascade="all, delete-orphan")

class JobURL(Base):
    __tablename__ = "job_urls"
    
    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('scrape_jobs.id', ondelete='CASCADE'), nullable=False)
    url = Column(String, nullable=False)
    status = Column(Enum(URLStatus), nullable=False, default=URLStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    job = relationship("ScrapeJob", back_populates="urls")
    data = relationship("ScrapedData", back_populates="job_url", uselist=False)
    logs = relationship("ScrapeLog", back_populates="job_url")

class ScrapedData(Base):
    __tablename__ = "scraped_data"
    
    id = Column(Integer, primary_key=True)
    job_url_id = Column(Integer, ForeignKey('job_urls.id', ondelete='CASCADE'), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    job_url = relationship("JobURL", back_populates="data")

class ScrapeLog(Base):
    __tablename__ = "scrape_logs"
    
    id = Column(Integer, primary_key=True)
    job_url_id = Column(Integer, ForeignKey('job_urls.id', ondelete='CASCADE'), nullable=False)
    log_message = Column(String, nullable=False)
    log_level = Column(Enum(LogLevel), nullable=False, default=LogLevel.INFO)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    job_url = relationship("JobURL", back_populates="logs") 