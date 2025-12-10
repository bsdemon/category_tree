from __future__ import annotations
from typing import Any, Optional, List
from ninja import Schema


class CategoryBase(Schema):
    name: str
    description: str = ""


class CategoryCreate(CategoryBase):
    parent_id: Optional[int] = None


class CategoryUpdate(Schema):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None


class CategoryOut(Schema):
    id: int
    name: str
    description: str
    image: Optional[str]
    parent_id: Optional[int]

class CategoryTreeNode(Schema):
    id: int
    name: str
    description: str
    parent_id: Optional[int]
    children: List["CategoryTreeNode"] = [] 


class MoveCategoryIn(Schema):
    new_parent_id: Optional[int] = None


class SimilarCategoryIn(Schema):
    other_id: int


class MessageOut(Schema):
    detail: str


# Fix forward references
CategoryTreeNode.model_rebuild()
