from __future__ import annotations

from typing import List

from django.http import Http404
from ninja import NinjaAPI, Router

from .models import Category
from .services import (
    CategoryCreateData,
    CategoryService,
    CategoryUpdateData,
)
from .schemas import (
    CategoryCreate,
    CategoryOut,
    CategoryTreeNode,
    CategoryUpdate,
    MessageOut,
    MoveCategoryIn,
    SimilarCategoryIn,
)

api = NinjaAPI()
router = Router(tags=["categories"])

def _category_to_schema(category: Category) -> CategoryOut:
    return CategoryOut(
        id=category.id,
        name=category.name,
        description=category.description,
        parent_id=category.parent_id,
        image=category.image
    )


@router.post("", response={201: CategoryOut, 404: MessageOut})
def create_category(request, data: CategoryCreate):
    try:
        created = CategoryService.create_category(
            CategoryCreateData(
                name=data.name,
                description=data.description,
                parent_id=data.parent_id,
            )
        )
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Parent category not found")

    return 201, _category_to_schema(created)


@router.get("", response=List[CategoryOut])
def list_categories(request):
    categories = CategoryService.list_categories()
    return [_category_to_schema(c) for c in categories]


@router.post("/similar", response={201: MessageOut, 400: MessageOut, 404: MessageOut},)
def add_similarity(request, data: SimilarCategoryIn):
    try:
        CategoryService.add_similarity(data.lead_id, data.follower_id)
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Category not found")
    except ValueError as exc:
        return 400, MessageOut(detail=str(exc))

    return 201, MessageOut(detail="Similarity created")


@router.get(
    "/by-parent/{parent_id}",
    response={200: List[CategoryOut], 404: MessageOut},
)
def list_by_parent(request, parent_id: int):
    categories = CategoryService.list_by_parent(parent_id)
    if not categories:
        return 404, MessageOut(detail="Category  not found")
    return [_category_to_schema(c) for c in categories]


@router.get("/roots", response=List[CategoryOut])
def list_roots(request):
    categories = CategoryService.list_roots()
    return [_category_to_schema(c) for c in categories]


@router.get("/by-depth/{depth}", response=List[CategoryOut])
def list_by_depth(request, depth: int):
    categories = CategoryService.list_by_depth(depth)
    return [_category_to_schema(c) for c in categories]


@router.get("/search", response=List[CategoryOut])
def search_categories(request, q: str):
    """
    Search categories by name (case-insensitive, partial match).
    Returns a list; empty list if nothing is found.
    """
    categories = CategoryService.search_by_name(q)
    return [_category_to_schema(c) for c in categories]


@router.get("/tree", response=List[CategoryTreeNode])
def get_full_tree(request):
    return CategoryService.build_full_tree()


@router.get("/{category_id}", response=CategoryOut)
def get_category(request, category_id: int):
    try:
        category = CategoryService.get_category(category_id)
    except Category.DoesNotExist:
        raise Http404("Category not found")
    return _category_to_schema(category)


@router.patch("/{category_id}", response={200: CategoryOut, 404: MessageOut},)
def update_category(request, category_id: int, data: CategoryUpdate):
    try:
        updated = CategoryService.update_category(
            category_id,
            CategoryUpdateData(
                name=data.name,
                description=data.description,
                parent_id=data.parent_id,
            ),
        )
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Category not found")

    return 200, _category_to_schema(updated)


@router.delete("/{category_id}", response={200: None, 404: MessageOut},)
def delete_category(request, category_id: int):
    try:
        CategoryService.delete_category_and_subtree(category_id)
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Category not found")
    return 200, None


@router.post("/{category_id}/move", response={200: CategoryOut, 400: MessageOut, 404: MessageOut},)
def move_category(request, category_id: int, data: MoveCategoryIn):
    try:
        moved = CategoryService.move_category(category_id, data.new_parent_id)
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Category not found")
    except ValueError as exc:
        return 400, MessageOut(detail=str(exc))

    return 200, _category_to_schema(moved)


@router.get("/{category_id}/subtree", response=CategoryTreeNode)
def get_subtree(request, category_id: int):
    try:
        subtree = CategoryService.build_subtree(category_id)
    except Category.DoesNotExist:
        raise Http404("Category not found")
    return subtree


@router.get("/{category_id}/similar", response={200: List[CategoryOut], 404: MessageOut},)
def list_similar_categories(request, category_id: int):
    try:
        similar = CategoryService.list_similar_categories(category_id)
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Category not found")

    return 200, [_category_to_schema(c) for c in similar]


@router.delete("/{category_id}/similar/{other_id}", response={200: None, 404: MessageOut},)
def remove_similarity(request, category_id: int, other_id: int):

    try:
        success = CategoryService.remove_similarity(category_id, other_id)
        if not success:
            return 404, MessageOut(detail="Similarity not found")
    except Category.DoesNotExist:
        return 404, MessageOut(detail="Category not found")

    return 200, None


api.add_router("/categories", router)
