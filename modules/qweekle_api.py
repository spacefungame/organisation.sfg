"""
Connecteur API Qweekle - Gravity Center
========================================
Module d'interface avec l'API de réservation Qweekle.

Fournit :
  - Récupération des réservations (get_reservations)
  - Détails d'une commande (get_order_details)
  - Informations client (get_client)
  - Enrichissement automatique des réservations dont le nom
    client est manquant (enrich_reservations)

╔════════════════════════════════════════════════════════════╗
║  CONFIGURATION :                                          ║
║  1. Renseignez QWEEKLE_API_KEY dans .streamlit/secrets    ║
║     ou dans config.py en fallback                         ║
║  2. L'URL de base est définie dans config.QWEEKLE_BASE_URL║
╚════════════════════════════════════════════════════════════╝
"""

import datetime
import logging

import requests
import streamlit as st

from config import QWEEKLE_API_KEY, QWEEKLE_BASE_URL, Reservation

logger = logging.getLogger(__name__)

# Timeout global pour tous les appels API (en secondes)
_API_TIMEOUT = 10


class QweekleClient:
    """Client pour l'API Qweekle avec enrichissement des données."""

    def __init__(self, api_key: str = None, base_url: str = None):
        # Priorité : paramètre > secrets Streamlit > config.py
        self.api_key = api_key or self._read_api_key()
        self.base_url = base_url or QWEEKLE_BASE_URL

    @staticmethod
    def _read_api_key() -> str:
        """Cherche la clé API dans plusieurs emplacements des secrets."""
        # Tenter plusieurs formats TOML possibles
        for reader in [
            lambda: st.secrets["QWEEKLE_API_KEY"],           # Niveau racine
            lambda: st.secrets["qweekle"]["api_key"],        # [qweekle] section
            lambda: st.secrets["qweekle"]["QWEEKLE_API_KEY"],# [qweekle] section alt
            lambda: st.secrets["supabase"]["QWEEKLE_API_KEY"],# sous [supabase] par erreur
        ]:
            try:
                val = reader()
                if val and str(val).strip():
                    logger.info("Clé API Qweekle trouvée dans les secrets.")
                    return str(val).strip()
            except (KeyError, FileNotFoundError, AttributeError, TypeError):
                continue
        # Fallback config.py
        return QWEEKLE_API_KEY

    # ──────────────────────────────────────────────────────────
    #  État de la configuration
    # ──────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        """Vérifie si la clé API est renseignée."""
        return bool(self.api_key and self.api_key.strip())

    # ──────────────────────────────────────────────────────────
    #  Requête HTTP générique
    # ──────────────────────────────────────────────────────────

    def _fetch_from_api(self, endpoint: str, params: dict = None) -> dict:
        """Effectue une requête GET authentifiée vers l'API Qweekle."""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        logger.info("Appel API Qweekle : GET %s", url)
        response = requests.get(
            url, headers=headers, params=params, timeout=_API_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    # ──────────────────────────────────────────────────────────
    #  Endpoints API
    # ──────────────────────────────────────────────────────────

    def get_order_details(self, order_id: str) -> dict:
        """
        Récupère les détails complets d'une commande Qweekle.

        GET /orders/{order_id}
        Retourne le dict contenu dans la clé 'data' de la réponse.
        """
        try:
            response = self._fetch_from_api(f"/orders/{order_id}")
            data = response.get("data", {})
            logger.info(
                "Commande %s récupérée — client_id=%s, items=%d",
                order_id,
                data.get("client_id", "?"),
                len(data.get("items", [])),
            )
            return data
        except Exception as e:
            logger.error("Erreur récupération commande %s : %s", order_id, e)
            return {}

    def get_client(self, client_id: str) -> dict:
        """
        Récupère les informations d'un client Qweekle.

        GET /clients/{client_id}
        Retourne le dict contenu dans la clé 'data' (firstname, lastname, email, phone…).
        """
        try:
            response = self._fetch_from_api(f"/clients/{client_id}")
            data = response.get("data", {})
            logger.info(
                "Client %s récupéré — %s %s",
                client_id,
                data.get("firstname", ""),
                data.get("lastname", ""),
            )
            return data
        except Exception as e:
            logger.error("Erreur récupération client %s : %s", client_id, e)
            return {}

    # ──────────────────────────────────────────────────────────
    #  Enrichissement des réservations
    # ──────────────────────────────────────────────────────────

    def enrich_reservations(
        self, reservations: list[Reservation]
    ) -> list[Reservation]:
        """
        Enrichit TOUTES les réservations via l'API Qweekle.

        Pour chaque réservation :
          1. Appelle get_order_details(order_id) pour obtenir le client_id
          2. Appelle get_client(client_id) pour obtenir nom/prénom
          3. Met à jour client_name avec le vrai nom du client
          4. Met à jour nb_persons depuis la quantité du pack principal

        Ne bloque pas l'interface : en cas d'erreur, on log et on passe.
        """
        if not self.is_configured():
            logger.info("Enrichissement ignoré — API Qweekle non configurée.")
            return reservations

        logger.info("Début enrichissement de %d réservations via API Qweekle.", len(reservations))

        # Cache local pour éviter les appels en double dans un même batch
        _order_cache: dict[str, dict] = {}
        _client_cache: dict[str, dict] = {}

        for reservation in reservations:
            try:
                # ── Étape 1 : récupérer la commande ──────────────
                order_id = reservation.id
                if order_id in _order_cache:
                    order = _order_cache[order_id]
                else:
                    order = self.get_order_details(order_id)
                    _order_cache[order_id] = order

                if not order:
                    continue

                # ── Étape 2 : récupérer le client ────────────────
                client_id = order.get("client_id")
                if not client_id:
                    continue

                if client_id in _client_cache:
                    client = _client_cache[client_id]
                else:
                    client = self.get_client(client_id)
                    _client_cache[client_id] = client

                if not client:
                    continue

                # ── Étape 3 : mettre à jour le nom ───────────────
                firstname = (client.get("firstname") or "").strip()
                lastname = (client.get("lastname") or "").strip()
                full_name = f"{firstname} {lastname}".strip()

                if full_name:
                    old_name = reservation.client_name
                    reservation.client_name = full_name
                    if old_name != full_name:
                        logger.info("Nom : '%s' → '%s'", old_name, full_name)

                # ── Étape 4 : mettre à jour nb_persons ───────────
                items = order.get("items", [])
                for item in items:
                    item_type = (item.get("type") or "").upper()
                    parent_id = item.get("parent_id")
                    # Prendre le PACK principal (sans parent)
                    if item_type == "PACK" and not parent_id:
                        qty = item.get("qty") or 0
                        if qty and qty > 0:
                            reservation.nb_persons = int(qty)
                        break

            except Exception as e:
                logger.error(
                    "Erreur enrichissement réservation %s : %s",
                    reservation.id, e,
                )
                continue

        logger.info("Enrichissement terminé.")
        return reservations

    # ──────────────────────────────────────────────────────────
    #  Récupération directe des réservations (mode Qweekle pur)
    # ──────────────────────────────────────────────────────────

    def get_reservations(
        self,
        date_start: datetime.date,
        date_end: datetime.date,
    ) -> list:
        """
        Récupère les réservations d'anniversaires depuis l'API Qweekle.

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

    def _parse_api_response(self, data: dict) -> list:
        """
        Transforme la réponse JSON de l'API en objets Reservation.

        ╔═══════════════════════════════════════════════════════════════╗
        ║ ADAPTEZ CETTE MÉTHODE au format réel de l'API Qweekle.     ║
        ║ Le code ci-dessous est un EXEMPLE basé sur un format        ║
        ║ hypothétique.                                                ║
        ╚═══════════════════════════════════════════════════════════════╝
        """
        reservations = []
        items = data.get("reservations", data.get("data", []))

        for i, item in enumerate(items):
            try:
                # ── Parsing des heures ───────────────────────────
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
