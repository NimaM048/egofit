from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("cart", "0026_alter_discountcode_is_active_alter_order_created_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderPaymentAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("amount", models.PositiveIntegerField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("initiated", "Initiated"),
                            ("paid", "Paid"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("authority", models.CharField(blank=True, max_length=64, null=True, unique=True)),
                ("ref_id", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("initiated_at", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_attempts",
                        to="cart.order",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["order", "status"], name="cart_orderp_order_i_cb2686_idx"),
                    models.Index(fields=["order", "created_at"], name="cart_orderp_order_i_384183_idx"),
                ],
            },
        ),
    ]
