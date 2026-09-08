from dataclasses import dataclass


@dataclass
class CurrentUser:
    id: int
    store_id: int
    username: str
    name: str
    role: str
