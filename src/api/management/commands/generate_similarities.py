from __future__ import annotations

import random
from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Category, CategorySimilarity


TARGET_SIMILARITIES = 200_000
BATCH_SIZE = 5_000
random.seed(42)


class Command(BaseCommand):
    help = "Generate ~200k random CategorySimilarity relations"

    def handle(self, *args, **options):
        category_ids = list(
            Category.objects.values_list("id", flat=True)
        )

        total_categories = len(category_ids)
        if total_categories < 2:
            self.stdout.write(self.style.ERROR("Not enough categories to create similarities"))
            return

        self.stdout.write(self.style.NOTICE(f"Found {total_categories} categories"))
        self.stdout.write(self.style.NOTICE("Generating similarities..."))

        created_count = 0
        batch = []

        # To avoid endless loop if database already has many similarities
        existing_pairs = set(
            CategorySimilarity.objects.values_list("category1_id", "category2_id")
        )

        while created_count < TARGET_SIMILARITIES:
            # random pick
            a, b = random.sample(category_ids, 2)
            c1, c2 = (a, b) if a < b else (b, a)

            pair = (c1, c2)
            if pair in existing_pairs:
                continue

            existing_pairs.add(pair)

            batch.append(CategorySimilarity(category1_id=c1, category2_id=c2))
            created_count += 1

            # bulk insert when batch is full
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    CategorySimilarity.objects.bulk_create(batch, ignore_conflicts=True)
                self.stdout.write(self.style.SUCCESS(f"Inserted {created_count} similarities..."))
                batch = []

        # Insert remaining
        if batch:
            with transaction.atomic():
                CategorySimilarity.objects.bulk_create(batch, ignore_conflicts=True)

        self.stdout.write(self.style.SUCCESS(f"Done. Total created: {created_count}"))
