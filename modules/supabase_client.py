"""
Client Supabase - Gravity Center
=================================
Lit les activités Qweekle depuis booking_activities, les regroupe
par order_id et reconstruit des objets Reservation pour le dashboard.
"""
import datetime
import logging
from collections import defaultdict

try:
    from zoneinfo import ZoneInfo
    TZ_LOCAL = ZoneInfo("Europe/Brussels")
    TZ_UTC = ZoneInfo("UTC")
except Exception:
    # Fallback si zoneinfo/tzdata absent
    TZ_LOCAL = datetime.timezone(datetime.timedelta(hours=2))  # CEST
    TZ_UTC = datetime.timezone.utc

import requests
import streamlit as st

from config import Reservation

logger = logging.getLogger(__name__)

# Catégories Qweekle à afficher dans le planning anniversaires
BIRTHDAY_CATEGORIES = [
    "anniversaire",
    "événement",
    "evenement",
]


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
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _utc_to_local(iso_str: str) -> datetime.datetime:
    """Convertit un timestamp ISO UTC en datetime local (Belgique)."""
    # Qweekle envoie : "2026-08-28T15:00:00.000000Z"
    clean = iso_str.replace("Z", "+00:00")
    dt_utc = datetime.datetime.fromisoformat(clean)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=TZ_UTC)
    return dt_utc.astimezone(TZ_LOCAL)


def get_booking_activities(target_date: datetime.date) -> list[dict]:
    """
    Récupère toutes les activités Qweekle pour une date donnée.

    Filtre sur start_at dans la plage [date 00:00, date+1 00:00] UTC.
    """
    creds = _get_credentials()
    if not creds:
        return []

    url, key = creds

    # Construire les bornes de date en UTC
    # On cherche les activités dont le start_at local tombe sur target_date.
    # Pour couvrir toute la journée belge en UTC : on prend une marge large.
    date_start_utc = f"{target_date.isoformat()}T00:00:00Z"
    date_end_utc = f"{(target_date + datetime.timedelta(days=1)).isoformat()}T23:59:59Z"

    try:
        response = requests.get(
            f"{url}/rest/v1/booking_activities",
            headers=_headers(key),
            params=[
                ("start_at", f"gte.{date_start_utc}"),
                ("start_at", f"lt.{date_end_utc}"),
                ("order", "order_id,pack_step.asc"),
            ],
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error("Erreur lecture Supabase booking_activities : %s", e)
        return []


def _is_birthday_category(category: str) -> bool:
    """Vérifie si la catégorie correspond à un anniversaire/événement."""
    cat_lower = category.lower()
    return any(kw in cat_lower for kw in BIRTHDAY_CATEGORIES)


def activities_to_reservations(
    activities: list[dict],
    target_date: datetime.date,
    birthday_only: bool = True,
) -> list[Reservation]:
    """
    Regroupe les activités par order_id et construit des Reservations.

    Chaque order_id = une réservation complète (accueil + jeux + table).
    On reconstruit le texte d'activité à partir des labels individuels.
    """
    # Regrouper par order_id
    groups: dict[str, list[dict]] = defaultdict(list)
    for act in activities:
        oid = act.get("order_id", "")
        if oid:
            groups[oid].append(act)

    reservations = []

    for order_id, acts in groups.items():
        # Trier par pack_step
        acts.sort(key=lambda a: a.get("pack_step", 0))

        # Filtrer : uniquement les anniversaires si demandé
        if birthday_only:
            categories = [a.get("category", "") for a in acts]
            if not any(_is_birthday_category(c) for c in categories):
                continue

        # ── Infos client (chercher dans TOUTES les activités) ──
        firstname = ""
        lastname = ""
        for a in acts:
            fn = (a.get("client_firstname") or "").strip()
            ln = (a.get("client_lastname") or "").strip()
            if fn or ln:
                firstname = fn
                lastname = ln
                break
        client_name = f"{lastname} {firstname}".strip()
        if not client_name:
            # Afficher un identifiant partiel pour repérer la résa
            short_id = order_id[-8:] if len(order_id) > 8 else order_id
            client_name = f"⚠️ Client inconnu ({short_id})"

        # ── Plage horaire globale ─────────────────────────────
        start_times = [a["start_at"] for a in acts if a.get("start_at")]
        end_times = [a["end_at"] for a in acts if a.get("end_at")]

        if not start_times or not end_times:
            continue

        earliest_local = _utc_to_local(min(start_times))
        latest_local = _utc_to_local(max(end_times))

        # Vérifier que ça tombe bien sur la date demandée
        if earliest_local.date() != target_date:
            continue

        # ── Reconstruire le texte d'activité ──────────────────
        laser_count = 0
        has_team = False
        quiz_minutes = 0
        table_start_local = None  # Heure de la pause gâteau

        for a in acts:
            label = (a.get("label", "") or "").lower()
            cat = (a.get("category", "") or "").lower()
            subcat = (a.get("subcategory", "") or "").lower()
            dur = a.get("duration", 0) or 0

            if "laser" in label or "laser" in cat:
                # Ignorer si c'est la catégorie "Anniversaire" avec location laser
                if "partie" in subcat or "laser" in subcat or "laser" in label:
                    laser_count += 1
            elif "team" in label or "team" in cat:
                has_team = True
            elif "quiz" in label or "quiz" in cat:
                quiz_minutes += dur

            # Détecter l'activité "Table réservée" = pause gâteau
            if ("table" in label and "réservée" in label) or \
               ("table" in label and "reserv" in label) or \
               ("anniversaire" in cat and "table" in label):
                if a.get("start_at"):
                    table_start_local = _utc_to_local(a["start_at"])

        parts = []
        if has_team:
            parts.append("1H")
        if laser_count > 0:
            parts.append(f"{laser_count} partie{'s' if laser_count > 1 else ''}")
        if quiz_minutes > 0:
            parts.append(f"{quiz_minutes} min Quiz")

        activities_str = " + ".join(parts) if parts else "Anniversaire"

        # ── Pause gâteau (heure de début de la table) ─────────
        break_time_str = ""
        if table_start_local:
            h = table_start_local.hour
            m = table_start_local.minute
            break_time_str = f"{h}h{m:02d}"

        # ── Nombre de participants (max parmi toutes les activités) ─
        nb_persons = max((a.get("qty", 0) or 0 for a in acts), default=0)

        # ── Statut ────────────────────────────────────────────
        status = acts[0].get("global_status", "")

        # ── Construire la Reservation ─────────────────────────
        reservation = Reservation(
            id=order_id,
            reservation_number=order_id[:12],
            client_name=client_name,
            date=target_date,
            start_time=earliest_local.time().replace(tzinfo=None),
            end_time=latest_local.time().replace(tzinfo=None),
            activities=activities_str,
            nb_persons=nb_persons,
            child_name="",      # Pas dans les données Qweekle
            child_age="",       # Pas dans les données Qweekle
            break_time=break_time_str,
            comment=f"Status: {status}" if status else "",
        )
        reservations.append(reservation)

    # Trier par heure de début
    reservations.sort(key=lambda r: (r.start_time.hour, r.start_time.minute))
    return reservations


def get_reservations_for_date(
    target_date: datetime.date,
    birthday_only: bool = True,
) -> list[Reservation]:
    """
    Point d'entrée principal : récupère les réservations Qweekle
    depuis Supabase pour une date donnée.
    """
    activities = get_booking_activities(target_date)
    return activities_to_reservations(activities, target_date, birthday_only)


def get_webhook_logs(limit: int = 20) -> list[dict]:
    """Récupère les derniers logs de webhooks (debug)."""
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
