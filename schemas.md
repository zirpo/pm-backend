# **This file defines the Pydantic models (schemas).**

# **These models define the shape of the data your API expects in requests**

# **and the shape of the data it sends in responses. This is your API's "contract".**

from pydantic import BaseModel  
from typing import Any, Dict

# **\--- Project Schemas \---**

class ProjectBase(BaseModel):  
"""Base schema for a project, used for creating new projects."""  
name: str  
class ProjectCreate(ProjectBase):  
"""Schema used when creating a new project."""  
pass  
class Project(ProjectBase):  
"""Schema used when reading a project from the API."""  
id: int  
plan\_json: Dict\[str, Any\] \# We'll automatically parse the JSON string to a dict  
class Config:  
    orm\_mode \= True \# Tells Pydantic to read data even if it's an ORM model

# **\--- Endpoint Request/Response Schemas \---**

class UpdateRequest(BaseModel):  
"""The JSON body required for the /project/update endpoint."""  
project\_id: int  
update\_text: str  
class UpdateResponse(BaseModel):  
"""The JSON response from the /project/update endpoint."""  
project\_id: int  
new\_plan: Dict\[str, Any\]  
class RecommendRequest(BaseModel):  
"""The JSON body required for the /project/recommend endpoint."""  
project\_id: int  
user\_question: str  
class RecommendResponse(BaseModel):  
"""The JSON response from the /project/recommend endpoint."""  
project\_id: int  
recommendation\_markdown: str