# **This file defines the actual database tables using SQLAlchemy models.**

from sqlalchemy import Column, Integer, String, Text  
from .database import Base \# Import the Base from database.py  
class Project(Base):  
"""  
This is the database model for the 'projects' table.  
SQLAlchemy will automatically create this table based on this class.  
"""  
tablename \= "projects"  
\# The primary key for the project  
id \= Column(Integer, primary\_key=True, index=True)

\# The name of the project  
name \= Column(String, index=True)

\# The 'state' of the project. This column stores the entire  
\# project plan as a JSON string.  
plan\_json \= Column(Text, default="{}")  
