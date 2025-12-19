from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional
import os
import re
from src.infrastructure.db.session import Base

class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    patient_age = Column(Integer)
    patient_gender = Column(String)
    chief_complaint = Column(Text)
    diagnosis = Column(String)
    difficulty_level = Column(String, default="medium")  # easy, medium, hard
    category = Column(String, index=True)
    
    # Audio/Analysis fields
    audio_path = Column(String, nullable=True)
    transcript = Column(Text, nullable=True)
    nelson_context = Column(Text, nullable=True)
    status = Column(String, default="UPLOADED") # UPLOADED, PROCESSING, COMPLETED, FAILED

    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    created_by = relationship("User", back_populates="cases")
    submissions = relationship("Submission", back_populates="case", cascade="all, delete-orphan")
    summary = relationship("CaseSummary", back_populates="case", uselist=False, cascade="all, delete-orphan")
    differential_diagnoses = relationship("DifferentialDiagnosis", back_populates="case", cascade="all, delete-orphan")
    pubmed_articles = relationship("PubMedArticle", back_populates="case", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="case", cascade="all, delete-orphan")

    @property
    def date(self) -> datetime:
        encounter = self._extract_encounter_date()
        if encounter:
            return encounter
        file_date = self._get_file_creation_date()
        if file_date:
            return file_date
        return self.created_at

    def _extract_encounter_date(self) -> Optional[datetime]:
        if not self.transcript:
            return None
        text = self.transcript
        patterns = [
            r"(?:encounter date|date of encounter|visit date|date of visit)\s*[:\-]\s*(.+)",
            r"(?:seen on|visited on)\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                date_str = match.group(1).strip().split("\n")[0].strip()
                parsed = self._parse_date_string(date_str)
                if parsed:
                    return parsed
        generic_patterns = [
            r"\b(\d{4}-\d{1,2}-\d{1,2})\b",
            r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b",
            r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b",
        ]
        for pattern in generic_patterns:
            match = re.search(pattern, text)
            if match:
                parsed = self._parse_date_string(match.group(1))
                if parsed:
                    return parsed
        return None

    def _get_file_creation_date(self) -> Optional[datetime]:
        if not self.audio_path:
            return None
        try:
            ts = os.path.getctime(self.audio_path)
            return datetime.fromtimestamp(ts)
        except OSError:
            return None

    @staticmethod
    def _parse_date_string(date_str: str) -> Optional[datetime]:
        candidates = [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%d-%m-%Y",
            "%m-%d-%Y",
            "%d %b %Y",
            "%d %B %Y",
        ]
        for fmt in candidates:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None


class Submission(Base):
    """Student submissions for cases"""
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer_text = Column(Text, nullable=False)
    score = Column(Integer)
    feedback = Column(Text)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    case = relationship("Case", back_populates="submissions")
    user = relationship("User", back_populates="submissions")


class CaseSummary(Base):
    __tablename__ = "case_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), unique=True, nullable=False)
    chief_complaint = Column(Text)
    history = Column(Text)
    vitals = Column(Text)
    
    case = relationship("Case", back_populates="summary")


class DifferentialDiagnosis(Base):
    __tablename__ = "differential_diagnoses"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    condition = Column(String, nullable=False)
    probability = Column(String)
    reasoning = Column(Text)
    
    case = relationship("Case", back_populates="differential_diagnoses")


class PubMedArticle(Base):
    __tablename__ = "pubmed_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    summary = Column(Text)
    
    case = relationship("Case", back_populates="pubmed_articles")
