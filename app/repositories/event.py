# app/repositories/event.py
from typing import Dict, List, Optional


class EventRepository:
    def __init__(self):
        self._events_db: List[Dict] = []
        self._id_counter: int = 1

    def create(self, event_data: dict) -> dict:
        new_event = {
            "id": self._id_counter,
            **event_data
        }
        self._events_db.append(new_event)
        self._id_counter += 1
        return new_event

    def get_by_name_and_date(self, name: str, event_date) -> Optional[dict]:
        for event in self._events_db:
            if event["name"].lower() == name.lower() and event["event_date"] == event_date:
                return event
        return None

    def clear(self) -> None:
        """Método auxiliar para limpiar la base de datos en las pruebas unitarias."""
        self._events_db.clear()
        self._id_counter = 1

    # Agregar dentro de la clase EventRepository en app/repositories/event.py
    def get_by_id(self, event_id: int) -> Optional[dict]:
        for event in self._events_db:
            if event["id"] == event_id:
                return event
        return None

    def update_available_spots(self, event_id: int, new_available_spots: int) -> Optional[dict]:
        event = self.get_by_id(event_id)
        if event:
            event["available_spots"] = new_available_spots
        return event


# Instancia singleton en memoria
event_repository = EventRepository()