from ninja import Schema
from typing import List, Optional

class ErrorResponse(Schema):
    detail: str
    code: int
    
class BranchSchema(Schema):
    name: str
    protected: bool
    last_commit_sha: str
    last_commit_url: str


class RepositorySchema(Schema):
    id: int
    name: str
    full_name: str
    private: bool
    description: Optional[str]
    html_url: str
    language: Optional[str]
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    branches: List[BranchSchema] = []