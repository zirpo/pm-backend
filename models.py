from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    # Store JSON as a Text string
    plan_json = Column(Text, nullable=True)

    # Relationship to ProjectDocument
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"


class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    file_name = Column(String, index=True, nullable=False)
    gemini_corpus_doc_id = Column(String, unique=True, index=True, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship to Project
    project = relationship("Project", back_populates="documents")

    def __repr__(self):
        return f"<ProjectDocument(id={self.id}, project_id={self.project_id}, file_name='{self.file_name}')>"