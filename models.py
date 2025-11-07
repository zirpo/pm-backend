from sqlalchemy import Column, Integer, String, Text
from database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    # Store JSON as a Text string
    plan_json = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}')>"