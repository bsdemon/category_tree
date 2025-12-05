from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Union

from django.db import transaction

from .models import Category, CategorySimilarity

UNSET = object()


@dataclass
class CategoryCreateData:
    name: str
    description: str = ""
    parent_id: Optional[int] = None


@dataclass
class CategoryUpdateData:
    name: Optional[str] = None
    description: Optional[str] = None
    # UNSET = do not touch parent, None = become root, int = move under new parent
    parent_id: Union[int, None, object] = UNSET


class CategoryService:
    @staticmethod
    @transaction.atomic
    def create_category(data: CategoryCreateData) -> Category:
        """
        Create a new category and assign its path.
        """
        parent: Optional[Category] = None
        if data.parent_id is not None:
            try:
                parent = Category.objects.select_for_update().get(id=data.parent_id)
            except Category.DoesNotExist:
                raise Category.DoesNotExist(f"Parent category {data.parent_id} not found")

        category = Category.objects.create(
            name=data.name,
            description=data.description,
            parent=parent,
            path="",
        )

        if parent:
            category.path = f"{parent.path}.{category.id}"
        else:
            category.path = str(category.id)

        category.save(update_fields=["path"])
        return category


    @staticmethod
    @transaction.atomic
    def delete_category(category_id: int) -> None:
        """
        Delete a category and its entire subtree (because of on_delete=CASCADE).
        """
        category = Category.objects.select_for_update().get(id=category_id)
        category.delete()


    @staticmethod
    def list_categories() -> List[Category]:
        return list(Category.objects.all().order_by("id"))
    
    
    @staticmethod
    def get_category(category_id: int) -> Category:
        """
        Return a single category by its ID.
        """
        return Category.objects.get(id=category_id)


    @staticmethod
    def list_by_parent(parent_id: int) -> List[Category]:
        return list(Category.objects.filter(parent_id=parent_id).order_by("id"))

    @staticmethod
    def list_roots() -> List[Category]:
        return list(Category.objects.filter(parent__isnull=True).order_by("id"))

    @staticmethod
    def compute_depth_from_path(path: str) -> int:
        segments = [s for s in path.split(".") if s]
        return len(segments) - 1

    @staticmethod
    def list_by_depth(depth: int) -> List[Category]:
        qs = Category.objects.all()
        result: List[Category] = []
        for c in qs:
            if CategoryService.compute_depth_from_path(c.path) == depth:
                result.append(c)
        return result

    @staticmethod
    def search_by_name(query: str) -> List[Category]:
        return list(Category.objects.filter(name__icontains=query).order_by("name"))

    @staticmethod
    def build_full_tree() -> List[dict]:
        categories = list(Category.objects.all())
        nodes: Dict[int, dict] = {}
        children_map: Dict[Optional[int], List[int]] = {}

        for c in categories:
            nodes[c.id] = {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "parent_id": c.parent_id,
                "children": [],
            }
            children_map.setdefault(c.parent_id, []).append(c.id)

        def attach_children(parent_id: Optional[int]) -> List[dict]:
            items: List[dict] = []
            for child_id in children_map.get(parent_id, []):
                node = nodes[child_id]
                node["children"] = attach_children(child_id)
                items.append(node)
            return items

        return attach_children(None)

    @staticmethod
    def build_subtree(category_id: int) -> dict:
        root = Category.objects.get(id=category_id)
        categories = list(Category.objects.filter(path__startswith=root.path))

        nodes: Dict[int, dict] = {}
        children_map: Dict[int, List[int]] = {}

        for c in categories:
            nodes[c.id] = {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "parent_id": c.parent_id,
                "children": [],
            }
            if c.parent_id is not None:
                children_map.setdefault(c.parent_id, []).append(c.id)

        def attach(node_id: int) -> dict:
            node = nodes[node_id]
            node["children"] = [
                attach(child_id) for child_id in children_map.get(node_id, [])
            ]
            return node

        return attach(root.id)

    @staticmethod
    @transaction.atomic
    def _reparent_category(category: Category, new_parent_id: Optional[int]) -> None:
        old_path = category.path

        if new_parent_id is not None:
            if new_parent_id == category.id:
                raise ValueError("Category cannot be parent of itself")
            new_parent = Category.objects.select_for_update().get(id=new_parent_id)
            category.parent = new_parent
            category.path = f"{new_parent.path}{category.id}/"
        else:
            category.parent = None
            category.path = f"{category.id}/"

        category.save(update_fields=["parent", "path", "name", "description"])

        descendants = Category.objects.filter(path__startswith=old_path).exclude(
            id=category.id
        )
        for d in descendants:
            suffix = d.path[len(old_path) :]
            d.path = f"{category.path}{suffix}"
            d.save(update_fields=["path"])

    @staticmethod
    @transaction.atomic
    def update_category(category_id: int, data: CategoryUpdateData) -> Category:
        category = Category.objects.select_for_update().get(id=category_id)

        if data.name is not None:
            category.name = data.name
        if data.description is not None:
            category.description = data.description

        if data.parent_id is not None and data.parent_id is not UNSET and data.parent_id != category.parent_id:
            new_parent_id = int(data.parent_id) if isinstance(data.parent_id, int) else None
            CategoryService._reparent_category(category, new_parent_id)
        else:
            category.save(update_fields=["name", "description"])

        return category

    @staticmethod
    @transaction.atomic
    def move_category(category_id: int, new_parent_id: Optional[int]) -> Category:
        category = Category.objects.select_for_update().get(id=category_id)
        CategoryService._reparent_category(category, new_parent_id)
        return category

    @staticmethod
    @transaction.atomic
    def delete_category_and_subtree(category_id: int) -> None:
        category = Category.objects.select_for_update().get(id=category_id)
        Category.objects.filter(path__startswith=category.path).delete()

    # Similarity operations

    @staticmethod
    def list_similar_categories(category_id: int) -> List[Category]:
        category = Category.objects.get(id=category_id)
        return list(category.similar_categories.all())

    @staticmethod
    @transaction.atomic
    def add_similarity(category_id: int, other_id: int) -> None:
        if category_id == other_id:
            raise ValueError("Category cannot be similar to itself")

        c1 = Category.objects.select_for_update().get(id=category_id)
        c2 = Category.objects.select_for_update().get(id=other_id)

        if c1.id < c2.id:
            CategorySimilarity.objects.get_or_create(category1=c1, category2=c2)
        else:
            CategorySimilarity.objects.get_or_create(category1=c2, category2=c1)

    @staticmethod
    @transaction.atomic
    def remove_similarity(category_id: int, other_id: int) -> None:
        c1 = Category.objects.select_for_update().get(id=category_id)
        c2 = Category.objects.select_for_update().get(id=other_id)

        if c1.id < c2.id:
            CategorySimilarity.objects.filter(category1=c1, category2=c2).delete()
        else:
            CategorySimilarity.objects.filter(category1=c2, category2=c1).delete()

