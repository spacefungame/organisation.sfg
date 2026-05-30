"""
Connecteur API Qweekle - Gravity Center
========================================
Module d'interface avec l'API de réservation Qweekle.

Si aucune clé API n'est configurée, le module bascule
automatiquement en mode démonstration avec des données fictives.

╔════════════════════════════════════════════════════════════╗
║  POUR CONFIGURER L'API QWEEKLE :                         ║
║  1. Contactez le support Qweekle pour obtenir votre clé  ║
║  2. Renseignez QWEEKLE_API_KEY dans config.py            ║
║  3. Adaptez _parse_api_response() au format réel de      ║
║     la réponse API (voir les commentaires dans la méthode)║
╚════════════════════════════════════════════════════════════╝
"""

import datetime
import logging

import requests

from config import QWEEKLE_API_KEY, QWEEKLE_BASE_URL, Reservation

logger = logging.getLogger(__name__)


class QweekleClient:
    """Client pour l'API Qweekle."""

    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or QWEEKLE_API_KEY
        self.base_url = base_url or QWEEKLE_BASE_URL

    def is_configured(self) -> bool:
        """Vérifie si la clé API est renseignée."""
        return bool(self.api_key and self.api_key.strip())

    def get_reservations(
        self,
        date_start: datetime.date,
        date_end: datetime.date,
    ) -> list:
        """
        Récupère les réservations d'anniversaires.

        Si l'API n'est pas configurée → mode démonstration.
        """
        if not self.is_configured():
            logger.info("API Qweekle non configurée — mode démonstration.")
            from modules.demo_data import generate_demo_reservations
            return generate_demo_reservations(date_start)

        try:
            data = self._fetch_from_api(
                endpoint="/reservations",
                params={
                    "date_start": date_start.isoformat(),
                    "date_end": date_end.isoformat(),
                    "type": "birthday",
                },
            )
            return self._parse_api_response(data)
        except Exception as e:
            logger.error("Erreur API Qweekle : %s", e)
            return []

    def _fetch_from_api(self, endpoint: str, params: dict = None) -> dict:
        """Effectue une requête GET authentifiée vers l'API Qweekle."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def _parse_api_response(self, data: dict) -> list:
        """
        Transforme la réponse JSON de l'API en objets Reservation.

        ╔═══════════════════════════════════════════════════════════════╗
        ║ ADAPTEZ CETTE MÉTHODE au format réel de l'API Qweekle.     ║
        ║                                                             ║
        ║ Le code ci-dessous est un EXEMPLE basé sur un format        ║
        ║ hypothétique. Remplacez les noms de champs ("booking_id",   ║
        ║ "client_name", etc.) par ceux de votre API.                 ║
        ║                                                             ║
        ║ Pour connaître le format exact, faites un appel test :      ║
        ║   import requests                                           ║
        ║   r = requests.get(url, headers=headers, params=params)     ║
        ║   print(r.json())                                           ║
        ╚═══════════════════════════════════════════════════════════════╝
        """
        reservations = []
        items = data.get("reservations", data.get("data", []))

        for i, item in enumerate(items):
            try:
                # ── Parsing des heures ───────────────────────────
                # Adaptez selon le format Qweekle
                start_str = item.get("start_time", "10:00")
                end_str = item.get("end_time", "12:00")

                start_parts = start_str.split(":")
                end_parts = end_str.split(":")

                reservation = Reservation(
                    id=str(item.get("booking_id", f"qwk-{i}")),
                    reservation_number=str(item.get("reference", f"QWK-{i}")),
                    client_name=item.get("client_name", "Inconnu"),
                    date=datetime.date.fromisoformat(item.get("date", "2025-01-01")),
                    start_time=datetime.time(int(start_parts[0]), int(start_parts[1])),
                    end_time=datetime.time(int(end_parts[0]), int(end_parts[1])),
                    activities=item.get("activities", ""),
                    nb_persons=int(item.get("nb_persons", 0)),
                    child_name=item.get("child_name", ""),
                    child_age=str(item.get("child_age", "")),
                    comment=item.get("comment", ""),
                    paid=bool(item.get("paid", False)),
                )
                reservations.append(reservation)
            except Exception as e:
                logger.warning("Erreur parsing réservation #%d : %s", i, e)
                continue

        return reservations
