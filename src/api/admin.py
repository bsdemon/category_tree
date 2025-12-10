from django.contrib import admin

from .models import Category, CategorySimilarity


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "parent", "image")
    list_filter = ("parent",)
    search_fields = ("name", "description")
    raw_id_fields = ("parent",)


@admin.register(CategorySimilarity)
class CategorySimilarityAdmin(admin.ModelAdmin):
    list_display = ("id", "category1", "category2")
    search_fields = ("category1__name", "category2__name")
    raw_id_fields = ("category1", "category2")
    ordering = ("category1", "category2")
