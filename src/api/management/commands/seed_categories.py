from __future__ import annotations

import random
import string
from typing import List

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Category
from api.services import CategoryCreateData, CategoryService


ROOT_CATEGORIES = [
    "Плодове и зеленчуци",
    "Месо и риба",
    "Млечни и яйца",
    "Колбаси и деликатеси",
    "Бистро",
    "Пекарна",
    "Био",
    "Фермерски пазар",
    "Специални храни",
    "Замразени храни",
    "Основни храни и консерви",
    "Сладко и солено",
    "Напитки",
    "За бебето и детето",
    "Козметичнна и лична грижа",
    "За дома и офиса",
    "Зоомагазин",
    "Аптека",
]

LOREM_WORDS = [
    "lorem",
    "ipsum",
    "dolor",
    "sit",
    "amet",
    "consectetur",
    "adipiscing",
    "elit",
    "sed",
    "do",
    "eiusmod",
    "tempor",
    "incididunt",
    "ut",
    "labore",
    "et",
    "dolore",
    "magna",
    "aliqua",
    "veniam",
    "quis",
    "nostrud",
    "exercitation",
    "ullamco",
    "laboris",
    "nisi",
    "aliquip",
    "ex",
    "ea",
    "commodo",
    "consequat",
    "duis",
    "aute",
    "irure",
    "in",
    "reprehenderit",
    "voluptate",
    "velit",
    "esse",
    "cillum",
    "eu",
    "fugiat",
    "nulla",
    "pariatur",
]

MAX_TOTAL_CATEGORIES = 2000
MAX_DEPTH_UNDER_ROOT = 4  # depth levels under root
MIN_CHILDREN_L1 = 8       # Layer 1 min children
MAX_CHILDREN_L1 = 12      # Layer 1 max children
MIN_CHILDREN_OTHER = 0    # The rest layers min children
MAX_CHILDREN_OTHER = 6    # The rest layers max children


def random_name() -> str:
    """Generate a random category name from lorem words."""
    word_count = random.randint(2, 3)
    words = random.sample(LOREM_WORDS, word_count)
    return " ".join(w.capitalize() for w in words)


def random_image_name() -> str:
    """Generate random jpg file name (without path)."""
    chars = string.ascii_lowercase + string.digits
    base = "".join(random.choices(chars, k=12))
    return f"{base}.jpg"


class Command(BaseCommand):
    help = "Seed demo category tree with roots and random children (evenly spread across roots)"

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)

        # 1) Ensure all roots exist
        root_categories: List[Category] = []

        for name in ROOT_CATEGORIES:
            root = (
                Category.objects.filter(name=name, parent__isnull=True)
                .order_by("id")
                .first()
            )
            if root is None:
                data = CategoryCreateData(
                    name=name,
                    description="",
                    parent_id=None,
                )
                root = CategoryService.create_category(data)

                # set random image name
                root.image = random_image_name()
                root.save(update_fields=["image"])

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created root: {root.id} -> {root.name} (image={root.image})"
                    )
                )
            else:
                self.stdout.write(self.style.WARNING(f"Using existing root: {name}"))

            root_categories.append(root)

        total_categories = Category.objects.count()
        self.stdout.write(
            self.style.NOTICE(
                f"Starting with {total_categories} categories in DB (roots included)"
            )
        )

        # 2) Build tree breadth-first across ALL roots
        current_level_parents: List[Category] = root_categories[:]

        for depth in range(1, MAX_DEPTH_UNDER_ROOT + 1):
            if not current_level_parents:
                break
            if total_categories >= MAX_TOTAL_CATEGORIES:
                break

            self.stdout.write(
                self.style.NOTICE(
                    f"Generating children at depth {depth} for {len(current_level_parents)} parents"
                )
            )

            next_level_parents: List[Category] = []

            for parent in current_level_parents:
                if total_categories >= MAX_TOTAL_CATEGORIES:
                    break

                if depth == 1:
                    children_count = random.randint(MIN_CHILDREN_L1, MAX_CHILDREN_L1)
                else:
                    children_count = random.randint(
                        MIN_CHILDREN_OTHER, MAX_CHILDREN_OTHER
                    )

                for _ in range(children_count):
                    if total_categories >= MAX_TOTAL_CATEGORIES:
                        break

                    data = CategoryCreateData(
                        name=random_name(),
                        description="",
                        parent_id=parent.id,
                    )
                    child = CategoryService.create_category(data)

                    # set random image name
                    child.image = random_image_name()
                    child.save(update_fields=["image"])

                    total_categories += 1
                    next_level_parents.append(child)

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created category: {child.id} -> {child.name} "
                            f"(parent={parent.id}, depth={depth}, image={child.image})"
                        )
                    )

            if not next_level_parents:
                # No more nodes created on this depth
                break

            current_level_parents = next_level_parents

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding completed. Total categories in DB: {total_categories}"
            )
        )
