# **This file's only job is to configure the database.**

# **It creates the engine and the session factory.**

from sqlalchemy import create\_engine  
from sqlalchemy.ext.declarative import declarative\_base  
from sqlalchemy.orm import sessionmaker

# **1\. Define the database URL. This creates a file named 'projects.db'.**

SQLALCHEMY\_DATABASE\_URL \= "sqlite:///./projects.db"

# **2\. Create the SQLAlchemy engine.**

# **connect\_args is needed only for SQLite to allow it to be used by multiple threads (which FastAPI does).**

engine \= create\_engine(  
SQLALCHEMY\_DATABASE\_URL, connect\_args={"check\_same\_thread": False}  
)

# **3\. Create a SessionLocal class. This is the factory for all new database sessions.**

SessionLocal \= sessionmaker(autocommit=False, autoflush=False, bind=engine)

# **4\. Create a Base class. Our database models will inherit from this.**

Base \= declarative\_base()