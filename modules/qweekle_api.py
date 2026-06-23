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
import re

import requests
import streamlit as st

from config import QWEEKLE_API_KEY, QWEEKLE_BASE_URL, Reservation

logger = logging.getLogger(__name__)

# Timeout global pour tous les appels API (en secondes)
_API_TIMEOUT = 10

# ── Mapping labels Qweekle → champs option de la Reservation ──
# Chaque règle : (mots-clés requis, mots-clés exclus, champ Reservation)
# Le premier match gagne, donc les règles plus spécifiques sont en premier.
_OPTIONS_RULES = [
    # Gâteau de crêpes AVANT crêpes (plus spécifique)
    (["gateau de crepe", "gâteau de crêpe"],  [],     "gateau_crepes"),
    (["brownie"],                              [],     "brownie"),
    (["donut"],                                [],     "donuts"),
    (["bonbon"],                               [],     "bonbons"),
    (["kidibul", "champagne pour enfant"],      [],     "kidibul"),
    (["chips"],                                [],     "chips"),
    # Crêpes simples (exclure "gâteau")
    (["crêpe", "crepe"],                       ["gateau", "gâteau"],  "crepes"),
    # Granités : distinguer 200 et 350
    (["granit"],                               ["350", "yard"],       "granite_200"),
    (["granit"],                               ["200", "gobelet"],    "granite_350"),
]


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
            lambda: st.secrets["QWEEKLE_API_KEY"],
            lambda: st.secrets["qweekle_api_key"],
            lambda: st.secrets["qweekle"]["api_key"],
            lambda: st.secrets["qweekle"]["QWEEKLE_API_KEY"],
            lambda: st.secrets["supabase"]["QWEEKLE_API_KEY"],
            lambda: st.secrets["supabase"]["qweekle_api_key"],
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
        """Vérifie si la clé API est renseignée et valide."""
        if not self.api_key or not self.api_key.strip():
            return False
        if self.api_key == "dummy_key_qweekle":
            return False
        return True

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

    def get_client_subs(self, client_id: str) -> list[dict]:
        """
        Récupère les sous-comptes (enfants) d'un client.

        GET /clientsubs?filter[client_id]=...
        Retourne une liste de dicts avec firstname, lastname, birthday_at.
        """
        try:
            response = self._fetch_from_api(
                "/clientsubs",
                params={"filter[client_id]": client_id},
            )
            subs = response.get("data", [])
            if isinstance(subs, list):
                logger.info(
                    "Client %s : %d sous-compte(s) trouvé(s).",
                    client_id, len(subs),
                )
                return subs
            return []
        except Exception as e:
            # 404 = pas de sous-comptes, c'est normal
            logger.debug("Pas de sous-comptes pour %s : %s", client_id, e)
            return []

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

                # Fallback : nom de société (clients entreprise)
                if not full_name:
                    full_name = (client.get("society") or "").strip()

                # Fallback ultime : partie avant @ de l'email
                if not full_name:
                    email = (client.get("email") or "").strip()
                    if email and "@" in email:
                        full_name = email.split("@")[0].replace(".", " ").title()

                if full_name:
                    old_name = reservation.client_name
                    reservation.client_name = full_name
                    if old_name != full_name:
                        logger.info("Nom : '%s' → '%s'", old_name, full_name)

                # ── Étape 4 : nb_persons + catégorie d'âge + is_birthday ──
                items = order.get("items", [])
                
                # Variables pour reconstruire les horaires
                valid_starts = []
                valid_ends = []
                
                # Variables pour reconstruire les activités réelles
                q_activities = []
                laser_count = 0
                has_team = False
                quiz_minutes = 0

                for item in items:
                    item_type = (item.get("type") or "").upper()
                    parent_id = item.get("parent_id")
                    item_label = (item.get("label") or "").lower()
                    
                    # Récupérer les horaires
                    if item.get("start_at"):
                        valid_starts.append(item["start_at"])
                    if item.get("end_at"):
                        valid_ends.append(item["end_at"])

                    # Reconstruire les activités réelles
                    if "laser" in item_label:
                        laser_count += 1
                    elif "team" in item_label:
                        has_team = True
                    elif "quiz" in item_label:
                        dur = item.get("duration") or 30
                        quiz_minutes += dur

                    # Check for birthday keywords in ANY item
                    if "anniversaire" in item_label or "événement" in item_label or "evenement" in item_label:
                        reservation.is_birthday = True

                    # Détecter la catégorie d'âge depuis n'importe quel label
                    if not reservation.age_category:
                        if re.search(r"7\s*[-–]\s*12", item_label):
                            reservation.age_category = "enfant"
                        elif re.search(r"13\s*[-–]\s*18", item_label):
                            reservation.age_category = "ado"
                        elif ("+18" in item_label
                              or "adulte" in item_label
                              or "adult" in item_label):
                            reservation.age_category = "adulte"

                    # Prendre le PACK principal (sans parent) pour le nb_persons
                    if item_type == "PACK" and not parent_id:
                        qty = item.get("qty") or 0
                        if qty and qty > 0:
                            reservation.nb_persons = int(qty)

                # Mettre à jour les horaires
                if valid_starts and valid_ends:
                    from dateutil import parser
                    try:
                        earliest = min(parser.parse(s) for s in valid_starts)
                        latest = max(parser.parse(s) for s in valid_ends)
                        # Conversion locale basique ou fallback
                        reservation.start_time = earliest.time()
                        reservation.end_time = latest.time()
                    except Exception as e:
                        logger.error("Erreur parsing horaires Qweekle: %s", e)
                        
                # Mettre à jour les activités si on a trouvé quelque chose (et si Supabase n'avait mis que "Anniversaire")
                # Ou si Supabase a raté des parties.
                parts = []
                if has_team:
                    parts.append("1H")
                if laser_count > 0:
                    parts.append(f"{laser_count} partie{'s' if laser_count > 1 else ''}")
                if quiz_minutes > 0:
                    parts.append(f"{quiz_minutes} min Quiz")
                
                if parts:
                    reservation.activities = " + ".join(parts)

                # ── Étape 5 : prénom et âge de l'enfant ───────────
                if client_id and not reservation.child_name:
                    subs = self.get_client_subs(client_id)
                    if subs:
                        # S'il y a un seul enfant, c'est lui
                        # S'il y en a plusieurs, choisir celui dont
                        # l'anniversaire est le plus proche de la date
                        best_sub = subs[0]
                        if len(subs) > 1:
                            ref = reservation.date
                            best_dist = 999
                            for s in subs:
                                bday_str = s.get("birthday_at", "")
                                if bday_str:
                                    try:
                                        bd = datetime.date.fromisoformat(
                                            bday_str[:10]
                                        )
                                        # Distance entre le jour/mois de
                                        # naissance et la date de résa
                                        d = abs(
                                            (ref.month - bd.month) * 30
                                            + (ref.day - bd.day)
                                        )
                                        if d < best_dist:
                                            best_dist = d
                                            best_sub = s
                                    except (ValueError, TypeError):
                                        pass

                        # Mettre à jour prénom
                        child_fn = (best_sub.get("firstname") or "").strip()
                        if child_fn:
                            reservation.child_name = child_fn

                        # Calculer l'âge à la date de la réservation
                        bday_str = best_sub.get("birthday_at", "")
                        if bday_str:
                            try:
                                bd = datetime.date.fromisoformat(
                                    bday_str[:10]
                                )
                                age = (
                                    reservation.date.year - bd.year
                                    - (
                                        (reservation.date.month, reservation.date.day)
                                        < (bd.month, bd.day)
                                    )
                                )
                                reservation.child_age = str(age)
                                logger.info(
                                    "Enfant : %s, %s ans",
                                    child_fn, age,
                                )
                            except (ValueError, TypeError):
                                pass

                # ── Étape 6 : options / produits achetés ──────────
                items = order.get("items", [])
                for item in items:
                    itype = (item.get("type") or "").upper()
                    # Ignorer dépôts, vouchers, et items sans label
                    if itype in ("DEPOSIT", "G_DEPOSIT", "PAID_DEPOSIT", "VOUCHER"):
                        continue
                    label = (item.get("label") or "").lower()
                    if not label:
                        continue
                    qty = item.get("qty") or 0
                    if qty <= 0:
                        continue

                    # Ignorer les packs d'activité principaux
                    skip_activity = [
                        "laser", "team", "quiz", "accueil",
                        "acompte", "deduction", "déduction",
                        "nourriture externe", "anniversaire",
                        "table réserv", "table reserv",
                        "a deduire", "à déduire",
                    ]
                    # Un item est une activité s'il contient un mot-clé
                    # d'activité ET qu'il ne matche aucune règle food
                    is_activity = any(kw in label for kw in skip_activity)

                    # Chercher un match dans les règles options
                    matched_field = None
                    for keywords, excludes, field in _OPTIONS_RULES:
                        if any(kw in label for kw in keywords):
                            # Vérifier les exclusions
                            if excludes and any(ex in label for ex in excludes):
                                continue
                            matched_field = field
                            break

                    if matched_field:
                        # Pour gâteau de crêpes, extraire la taille
                        # depuis le label au lieu de qty
                        effective_qty = int(qty)
                        raw_label = item.get("label", "")

                        if matched_field == "gateau_crepes":
                            # "Gâteau 20 Crêpes" → 20
                            m = re.search(r"(\d+)\s*cr[êe]pe", raw_label, re.I)
                            if m:
                                effective_qty = int(m.group(1))

                        current = getattr(reservation, matched_field, 0)
                        setattr(reservation, matched_field, effective_qty)
                        if effective_qty != current:
                            logger.info(
                                "Option %s = %d (label: %s)",
                                matched_field, effective_qty, raw_label[:60],
                            )

            except Exception as e:
                logger.error(
                    "Erreur enrichissement réservation %s : %s",
                    reservation.id, e,
                )
                continue

        logger.info("Enrichissement terminé.")
        return reservations

    # ──────────────────────────────────────────────────────────
    #  Créer une Reservation à partir d'un order_id Qweekle
    # ──────────────────────────────────────────────────────────

    def order_to_reservation(self, order_id: str) -> "Reservation | None":
        """
        Récupère un order par ID Qweekle et le convertit en Reservation.
        
        Utile pour les commandes absentes de Supabase (webhook raté).
        Retourne None si l'order n'existe pas ou en cas d'erreur.
        """
        order = self.get_order_details(order_id)
        if not order:
            return None

        items = order.get("items", [])
        if not items:
            return None

        # ── Client ──
        client_id = order.get("client_id")
        client_name = "Inconnu"
        if client_id:
            client = self.get_client(client_id)
            if client:
                fn = (client.get("firstname") or "").strip()
                ln = (client.get("lastname") or "").strip()
                client_name = f"{fn} {ln}".strip() or "Inconnu"

        # ── Horaires, activités, birthday ──
        from dateutil import parser as dtparser
        valid_starts = []
        valid_ends = []
        laser_count = 0
        has_team = False
        quiz_minutes = 0
        is_birthday = False
        age_category = ""
        nb_persons = 0
        break_time_str = ""

        for item in items:
            label = (item.get("label") or "").lower()
            
            if item.get("start_at"):
                valid_starts.append(item["start_at"])
            if item.get("end_at"):
                valid_ends.append(item["end_at"])

            if "laser" in label:
                laser_count += 1
            elif "team" in label:
                has_team = True
            elif "quiz" in label:
                quiz_minutes += item.get("duration") or 30

            if "anniversaire" in label or "événement" in label or "evenement" in label:
                is_birthday = True

            if not age_category:
                if re.search(r"7\s*[-–]\s*12", label):
                    age_category = "enfant"
                elif re.search(r"13\s*[-–]\s*18", label):
                    age_category = "ado"
                elif "+18" in label or "adulte" in label:
                    age_category = "adulte"

            # Table réservée = pause gâteau
            if "table" in label and "réserv" in label and item.get("start_at"):
                try:
                    t = dtparser.parse(item["start_at"])
                    break_time_str = f"{t.hour}h{t.minute:02d}"
                except Exception:
                    pass

            itype = (item.get("type") or "").upper()
            if itype == "PACK" and not item.get("parent_id"):
                qty = item.get("qty") or 0
                if qty > 0:
                    nb_persons = int(qty)

        if not valid_starts or not valid_ends:
            return None

        try:
            earliest = min(dtparser.parse(s) for s in valid_starts)
            latest = max(dtparser.parse(s) for s in valid_ends)
        except Exception:
            return None

        # ── Activités texte ──
        parts = []
        if has_team:
            parts.append("1H")
        if laser_count > 0:
            parts.append(f"{laser_count} partie{'s' if laser_count > 1 else ''}")
        if quiz_minutes > 0:
            parts.append(f"{quiz_minutes} min Quiz")
        activities_str = " + ".join(parts) if parts else "Anniversaire"

        reservation = Reservation(
            id=order_id,
            reservation_number=order.get("number", order_id[:12]),
            client_name=client_name,
            date=earliest.date(),
            start_time=earliest.time(),
            end_time=latest.time(),
            activities=activities_str,
            nb_persons=nb_persons,
            is_birthday=is_birthday,
            age_category=age_category,
            break_time=break_time_str,
        )

        # ── Options (brownie, gâteau, etc.) ──
        for item in items:
            itype = (item.get("type") or "").upper()
            if itype in ("DEPOSIT", "G_DEPOSIT", "PAID_DEPOSIT", "VOUCHER"):
                continue
            label = (item.get("label") or "").lower()
            if not label:
                continue
            qty = item.get("qty") or 0
            if qty <= 0:
                continue

            for keywords, excludes, matched_field in _OPTIONS_RULES:
                if any(kw in label for kw in keywords):
                    if excludes and any(ex in label for ex in excludes):
                        continue
                    effective_qty = int(qty)
                    if matched_field == "gateau_crepes":
                        m = re.search(r"(\d+)\s*cr[êe]pe", item.get("label", ""), re.I)
                        if m:
                            effective_qty = int(m.group(1))
                    setattr(reservation, matched_field, effective_qty)
                    break

        # ── Enfant ──
        if client_id:
            subs = self.get_client_subs(client_id)
            if subs:
                best_sub = subs[0]
                child_fn = (best_sub.get("firstname") or "").strip()
                if child_fn:
                    reservation.child_name = child_fn
                bday_str = best_sub.get("birthday_at", "")
                if bday_str:
                    try:
                        bd = datetime.date.fromisoformat(bday_str[:10])
                        age = (
                            reservation.date.year - bd.year
                            - ((reservation.date.month, reservation.date.day) < (bd.month, bd.day))
                        )
                        reservation.child_age = str(age)
                    except (ValueError, TypeError):
                        pass

        logger.info("Reservation créée depuis Qweekle order %s : %s", order_id, client_name)
        return reservation

    # ──────────────────────────────────────────────────────────
    #  Découverte automatique des commandes manquantes
    # ──────────────────────────────────────────────────────────

    def discover_missing_orders(
        self,
        target_date: datetime.date,
        known_order_ids: set[str],
        known_client_ids: set[str] | None = None,
    ) -> list[str]:
        """
        Découvre les order_ids Qweekle absents de Supabase pour une date donnée.

        Stratégie rapide (~20 appels API) :
        1. Pour chaque client_id connu (déjà enrichi), appelle
           /orders?filter[client_id]=... pour lister TOUTES ses commandes
        2. Pour chaque order inconnu, vérifie s'il concerne target_date
           via order_to_reservation()
        3. Retourne les order_ids manquants
        """
        if not self.is_configured():
            return []

        # Collecter les client_ids depuis les orders enrichis
        if not known_client_ids:
            known_client_ids = set()
            for oid in known_order_ids:
                order = self.get_order_details(oid)
                if order:
                    cid = order.get("client_id")
                    if cid:
                        known_client_ids.add(cid)

        headers = {"Authorization": f"Bearer {self.api_key}"}
        candidate_oids = set()

        for cid in known_client_ids:
            try:
                r = requests.get(
                    f"{self.base_url}/orders?filter[client_id]={cid}",
                    headers=headers, timeout=15,
                )
                if r.status_code == 200:
                    for order in r.json().get("data", []):
                        oid = order.get("id", "")
                        if oid and oid not in known_order_ids:
                            candidate_oids.add(oid)
            except Exception as e:
                logger.error("Erreur listing orders client %s: %s", cid, e)

        # Vérifier chaque candidat : est-ce qu'il concerne target_date ?
        missing_ids = []
        for oid in candidate_oids:
            try:
                res = self.order_to_reservation(oid)
                if res and res.date == target_date:
                    missing_ids.append(oid)
            except Exception as e:
                logger.error("Erreur check order %s: %s", oid, e)

        logger.info(
            "Qweekle cross-check: %d clients vérifiés, %d orders manquants",
            len(known_client_ids), len(missing_ids),
        )
        return missing_ids

    def run_full_sync(self, progress_callback=None) -> int:
        """
        Récupère les dernières pages de réservations (où se trouvent les plus récentes)
        et les insère/met à jour dans Supabase.
        Renvoie le nombre de réservations insérées.
        """
        from modules.supabase_client import upsert_booking_activities
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}", 
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Déterminer la pagination
            r_init = requests.get(
                f"{self.base_url}/bookings?page=1&per_page=100",
                headers=headers,
                timeout=10
            )
            r_init.raise_for_status()
            json_data = r_init.json()
            
            # Qweekle use 'metadata' or 'meta'
            meta = json_data.get("metadata") or json_data.get("meta") or {}
            
            # Chercher total_pages ou last_page
            total_pages = 1
            if "pagination" in meta:
                total_pages = meta["pagination"].get("total_pages", 1)
            elif "total_pages" in meta:
                total_pages = meta["total_pages"]
            elif "last_page" in meta:
                total_pages = meta["last_page"]
            
            # On va récupérer les 100 dernières pages (les bookings les plus récents)
            # pour remonter suffisamment loin dans le temps et rattraper les vieilles réservations.
            pages_to_fetch = min(total_pages, 100)
            start_page = total_pages - pages_to_fetch + 1
            
            total_upserted = 0
            
            for i, page in enumerate(range(start_page, total_pages + 1)):
                if progress_callback:
                    progress_callback(i / pages_to_fetch, f"Récupération page {page}/{total_pages}...")
                    
                r = requests.get(
                    f"{self.base_url}/bookings?page={page}&per_page=100",
                    headers=headers,
                    timeout=_API_TIMEOUT
                )
                if r.status_code == 200:
                    bookings = r.json().get("data", [])
                    # Formater comme le webhook
                    rows = []
                    for b in bookings:
                        # Gérer le format imbriqué de l'API /bookings
                        order_item = b.get("order_item") or {}
                        activity = b.get("activity") or {}
                        agenda = b.get("agenda") or {}
                        client = b.get("client") or {}
                        
                        # Essayer de trouver un label qui pourrait servir de catégorie
                        cat_label = order_item.get("label", "")
                        if not cat_label:
                            cat_label = activity.get("label", "")
                            
                        # Mettre par défaut l'order_id sur l'id s'il est manquant
                        o_id = order_item.get("order_id") or b.get("order_id") or b.get("id", "")
                        
                        rows.append({
                            "qweekle_booking_id": b.get("id", ""),
                            "order_id": o_id,
                            "order_item_id": order_item.get("id") or b.get("order_item_id", ""),
                            "pack_step": b.get("pack_step", 0),
                            "label": activity.get("label") or b.get("label", ""),
                            "category": cat_label or b.get("category", ""),
                            "subcategory": b.get("subcategory", ""),
                            "location": agenda.get("location", {}).get("label") if agenda.get("location") else b.get("location", ""),
                            "duration": activity.get("duration") or b.get("duration", 0),
                            "qty": b.get("qty", 0),
                            "start_at": agenda.get("start_at") or b.get("start_at"),
                            "end_at": agenda.get("end_at") or b.get("end_at"),
                            "client_firstname": client.get("firstname", ""),
                            "client_lastname": client.get("lastname", ""),
                            "client_email": client.get("email", ""),
                            "client_phone": client.get("phone", ""),
                            "source": b.get("source", ""),
                            "global_status": b.get("state") or b.get("global_status", ""),
                            "event_type": "manual_sync",
                            "raw_payload": b
                        })
                    if rows:
                        success = upsert_booking_activities(rows)
                        if success:
                            total_upserted += len(rows)
                            
            if progress_callback:
                progress_callback(1.0, f"Terminé ! {total_upserted} réservations synchronisées.")
                
            return total_upserted
            
        except Exception as e:
            logger.error("Erreur run_full_sync: %s", e)
            return 0

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
