from django.db import models
from django.db.models import Q, F

class Category(models.Model):
    name = models.CharField(max_length=255)
    path = models.CharField(max_length=1024, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="img/categories/", blank=True, null=True)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    similar_categories = models.ManyToManyField( # type: ignore # do not annotate ORM fields
        "self",
        through="CategorySimilarity",
        symmetrical=False,
        related_name="similar_to",
    )

    class Meta:
        verbose_name_plural = "Categories" 
        indexes = [
            models.Index(fields=["parent"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return self.name

class CategorySimilarity(models.Model):
    """
    Similarity connection between two categories
    category1_id < category2_id
    and we do not allow  (A, A).
    """

    category1 = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="similarity_as_category1",
    )
    category2 = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="similarity_as_category2",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Category similarities" 
        constraints = [
            # disable A ~ A
            models.CheckConstraint(
                condition=~Q(category1=F("category2")),
                name="no_self_similarity",
            ),
            # order: category1_id < category2_id
            models.CheckConstraint(
                condition=Q(category1__lt=F("category2")),
                name="category1_lt_category2",
            ),
            # unique constraint: A < B
            models.UniqueConstraint(
                fields=["category1", "category2"],
                name="unique_similarity_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["category1"]),
            models.Index(fields=["category2"]),
        ]

    def __str__(self) -> str:
        return f"{self.category1.id} ~ {self.category2.id}"
