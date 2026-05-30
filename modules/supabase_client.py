"""
Client Supabase - Gravity Center
=================================
Lit et écrit les réservations depuis la base de données Supabase
via l'API REST (pas de dépendance supplémentaire, utilise requests).
"""
import datetime
import logging
from typing import Optional

import requests
import streamlit as st

from config import Reservation

logger = logging.getLogger(__name__)


def _get_credentials() -> tuple[str, str] | None:
    """Récupère l'URL et la clé Supabase depuis les secrets Streamlit."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        if url and key:
            return url, key
    except (KeyError, FileNotFoundError):
        pass
    return None


def is_configured() -> bool:
    """Vérifie si Supabase est configuré."""
    return _get_credentials() is not None


def _headers(key: str) -> dict:
    """En-têtes d'authentification pour l'API REST Supabase."""
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def get_reservations(target_date: datetime.date) -> list[dict]:
    """
    Récupère les réservations depuis Supabase pour une date donnée.

    Returns:
        Liste de dicts avec les données brutes de la table.
        Retourne une liste vide si non configuré ou en cas d'erreur.
    """
    creds = _get_credentials()
    if not creds:
        return []

    url, key = creds

    try:
        response = requests.get(
            f"{url}/rest/v1/reservations",
            headers=_headers(key),
            params={
                "date": f"eq.{target_date.isoformat()}",
                "order": "start_time.asc",
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("Erreur lecture Supabase : %s", e)
        return []


def row_to_reservation(row: dict) -> Reservation:
    """Convertit une ligne Supabase en objet Reservation."""
    date_parts = row["date"].split("-")
    st_parts = row["start_time"].split(":")
    et_parts = row["end_time"].split(":")

    return Reservation(
        id=str(row.get("id", "")),
        reservation_number=str(row.get("qweekle_id", row.get("id", ""))),
        client_name=row.get("client_name", ""),
        date=datetime.date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2])),
        start_time=datetime.time(int(st_parts[0]), int(st_parts[1])),
        end_time=datetime.time(int(et_parts[0]), int(et_parts[1])),
        activities=row.get("activities", ""),
        nb_persons=row.get("nb_persons", 0),
        assigned_table=row.get("assigned_table"),
        child_name=row.get("child_name", ""),
        child_age=str(row.get("child_age", "")),
        brownie=row.get("brownie", 0),
        gateau_crepes=row.get("gateau_crepes", 0),
        donuts=row.get("donuts", 0),
        bonbons=row.get("bonbons", 0),
        kidibul=row.get("kidibul", 0),
        chips=row.get("chips", 0),
        crepes=row.get("crepes", 0),
        granite_200=row.get("granite_200", 0),
        granite_350=row.get("granite_350", 0),
        break_time=row.get("break_time", ""),
        comment=row.get("comment", ""),
        arrived=row.get("arrived", False),
        paid=row.get("paid", False),
    )


def get_webhook_logs(limit: int = 20) -> list[dict]:
    """Récupère les derniers logs de webhooks (pour debug)."""
    creds = _get_credentials()
    if not creds:
        return []

    url, key = creds

    try:
        response = requests.get(
            f"{url}/rest/v1/webhook_logs",
            headers=_headers(key),
            params={
                "order": "received_at.desc",
                "limit": str(limit),
            },
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("Erreur lecture webhook_logs : %s", e)
        return []
