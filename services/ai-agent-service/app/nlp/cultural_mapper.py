"""Cultural Mapper — Ánh xạ biểu đạt văn hóa Việt Nam → thuật ngữ y khoa Western."""

import structlog

logger = structlog.get_logger()

# In-memory cultural expressions database (will migrate to PostgreSQL later)
CULTURAL_EXPRESSIONS: list[dict] = [
    {
        "expression": "bị nóng trong",
        "variants": ["nóng trong người", "nóng trong", "bị nóng"],
        "medical_meaning": "Internal inflammation/infection symptoms — elevated body temperature, systemic inflammatory response",
        "medical_terms": ["inflammation", "fever", "infection"],
        "confidence": 0.90,
    },
    {
        "expression": "gió độc",
        "variants": ["bị gió", "trúng gió", "cảm gió"],
        "medical_meaning": "Fever with chills, body aches, upper respiratory symptoms — often viral illness",
        "medical_terms": ["fever", "chills", "myalgia", "URI"],
        "confidence": 0.85,
    },
    {
        "expression": "bị lạnh",
        "variants": ["bị lạnh vào người", "cảm lạnh"],
        "medical_meaning": "Common cold symptoms, hypothermia, or fever onset with chills",
        "medical_terms": ["common cold", "hypothermia", "chills"],
        "confidence": 0.80,
    },
    {
        "expression": "bốc hỏa",
        "variants": ["lên cơn nóng"],
        "medical_meaning": "Hot flashes — vasomotor symptoms, often menopausal",
        "medical_terms": ["hot flashes", "vasomotor symptoms", "menopause"],
        "confidence": 0.85,
    },
    {
        "expression": "yếu thận",
        "variants": ["thận yếu", "thận hư"],
        "medical_meaning": "Kidney weakness in traditional Vietnamese medicine — fatigue, sexual dysfunction, lower back pain, frequent urination",
        "medical_terms": ["fatigue", "lower back pain", "frequent urination", "erectile dysfunction"],
        "confidence": 0.75,
    },
    {
        "expression": "máu nóng",
        "variants": ["nóng máu", "máu nóng trong người"],
        "medical_meaning": "Blood heat — skin conditions, acne, rashes, irritability",
        "medical_terms": ["dermatitis", "acne", "urticaria", "irritability"],
        "confidence": 0.80,
    },
    {
        "expression": "chạy bệnh",
        "variants": ["bệnh chạy"],
        "medical_meaning": "Disease spreading or metastasizing in the body",
        "medical_terms": ["metastasis", "spreading", "progression"],
        "confidence": 0.70,
    },
    {
        "expression": "huyết áp lên",
        "variants": ["lên huyết áp", "tăng huyết áp"],
        "medical_meaning": "Hypertension episode or spike in blood pressure",
        "medical_terms": ["hypertension", "high blood pressure"],
        "confidence": 0.95,
    },
    {
        "expression": "đường lên",
        "variants": ["lên đường", "đường huyết cao"],
        "medical_meaning": "Blood sugar spike, hyperglycemia",
        "medical_terms": ["hyperglycemia", "high blood sugar"],
        "confidence": 0.90,
    },
    {
        "expression": "bị phong",
        "variants": ["trúng phong", "đánh phong"],
        "medical_meaning": "Stroke or sudden paralysis — traditional Vietnamese term for cerebrovascular event",
        "medical_terms": ["stroke", "CVA", "paralysis"],
        "confidence": 0.85,
    },
]


class CulturalMapper:
    """Phát hiện và ánh xạ biểu đạt văn hóa trong text."""

    def map_expressions(self, text: str) -> list[dict]:
        """Phát hiện biểu đạt văn hóa VN trong text. Returns list of matches."""
        found: list[dict] = []
        text_lower = text.lower()

        for expr in CULTURAL_EXPRESSIONS:
            all_variants = [expr["expression"]] + expr["variants"]
            for variant in all_variants:
                if variant.lower() in text_lower:
                    found.append(
                        {
                            "original": variant,
                            "medical_meaning": expr["medical_meaning"],
                            "medical_terms": expr["medical_terms"],
                            "confidence": expr["confidence"],
                        }
                    )
                    break  # One match per expression is enough

        if found:
            logger.info(
                "cultural_expression.detected",
                count=len(found),
                expressions=[f["medical_terms"][0] for f in found],
            )

        return found
