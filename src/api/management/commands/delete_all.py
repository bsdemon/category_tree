from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import Category, CategorySimilarity
from api.services import CategoryService


class Command(BaseCommand):
    help = "Delete ALL categories and similarity relations. USE WITH CAUTION."

    @transaction.atomic
    def handle(self, *args, **options):
        CategorySimilarity.objects.all().delete()
        Category.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("All categories and their similarities are deleted."))
