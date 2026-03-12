"""patient_lifestyle table — nutrition, exercise, sleep, mental health, functional, SDOH, reproductive (1:1 with patient).

Each domain stored as JSON for flexibility — schema evolves without migration.
"""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class PatientLifestyle(Base, TimestampMixin):
    __tablename__ = "patient_lifestyle"

    lifestyle_id: Mapped[str] = mapped_column(
        String(26), primary_key=True, default=generate_ulid
    )
    patient_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("patients.patient_id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )

    # --- Dinh dưỡng ---
    # {"meals_per_day": 3, "vegetables_daily": true, "fast_food_freq": "weekly",
    #  "soda_freq": "rarely", "caffeine_cups": 2, "special_diet": "none"}
    nutrition: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Vận động ---
    # {"gym": false, "walking_daily": true, "sitting_hours": 8,
    #  "yoga": false, "muscle_pain": true, "exercise_minutes_per_week": 120}
    exercise: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Giấc ngủ ---
    # {"hours_per_night": 6, "quality": "fair", "insomnia": true,
    #  "sleep_aids": false, "bedtime": "23:00", "wake_time": "06:00"}
    sleep: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Tâm lý ---
    # {"stress_level": 7, "stress_sources": ["work", "finance"],
    #  "mood": "fair", "anxiety": true, "meditation": false, "social_support": "good"}
    mental_health: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Functional Status (ADL) ---
    # {"self_care": "independent", "mobility": "independent",
    #  "daily_activities": "independent", "needs_assistance": false}
    functional_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- SDOH (Social Determinants of Health) ---
    # {"housing_stable": true, "food_security": true,
    #  "transportation": true, "social_support": true, "financial_difficulty": false}
    sdoh: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # --- Reproductive / Endocrine ---
    # {"menstrual_status": "regular", "pregnancies": 2, "menopause": false,
    #  "thyroid_condition": "none", "hormone_therapy": false}
    reproductive_health: Mapped[dict | None] = mapped_column(JSON, nullable=True)
