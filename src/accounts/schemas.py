from ninja import Schema, ModelSchema
from .models import *
from typing import List, Optional


class ErrorResponse(Schema):
    detail: str
    code: int


class BranchSchema(ModelSchema):
    class Config:
        model = Branch
        model_fields = [
            "name",
            "protected",
            "last_commit_sha",
            "last_commit_url",
        ]


class RepositorySchema(ModelSchema):
    branches: List[BranchSchema]

    class Config:
        model = Repository
        model_fields = [
            "id",
            "name",
            "full_name",
            "private",
            "description",
            "html_url",
            "language",
            "stargazers_count",
            "forks_count",
            "open_issues_count",
        ]
