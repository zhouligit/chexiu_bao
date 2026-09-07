from datetime import datetime

from sqlalchemy.orm import Session


def generate_serial_no(db: Session, model, field: str, prefix: str) -> str:
    today = datetime.now().strftime("%Y%m%d")
    pattern = f"{prefix}{today}%"
    column = getattr(model, field)
    count = db.query(model).filter(column.like(pattern)).count()
    return f"{prefix}{today}{count + 1:04d}"
