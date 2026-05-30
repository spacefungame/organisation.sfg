"""
Connecteur Gmail API - Gravity Center
=======================================
Ce module gère la connexion à l'API Gmail pour détecter les emails
de modification liés aux réservations d'anniversaire.

CONFIGURATION :
    1. Créez un projet dans Google Cloud Console
    2. Activez l'API Gmail
    3. Créez des identifiants OAuth 2.0 (type "Application de bureau")
    4. Téléchargez le fichier credentials.json dans le dossier de l'application
    5. Au premier lancement, une fenêtre de navigateur s'ouvrira pour
       autoriser l'accès à votre compte Gmail

Le module recherche les emails contenant des mots-clés de modification
(définis dans config.py) et les associe aux réservations concernées.
"""

import base64
import datetime
import logging
import os
from email.utils import parsedate_to_datetime

from config import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES,
    GMAIL_KEYWORDS,
    GMAIL_SEARCH_DAYS_BACK,
    GmailAlert,
)

# Configuration du logger pour ce module
logger = logging.getLogger(__name__)

# Imports conditionnels pour Google API (peuvent ne pas être installés)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    _GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    _GOOGLE_LIBS_AVAILABLE = False
    logger.warning(
        "Les bibliothèques Google ne sont pas installées. "
        "Exécutez : pip install google-api-python-client "
        "google-auth-httplib2 google-auth-oauthlib"
    )


class GmailClient:
    """
    Client pour l'API Gmail.

    Permet de rechercher des emails de modification liés aux
    réservations d'anniversaire et de les transformer en alertes.
    """

    def __init__(self):
        """
        Initialise le client Gmail.
        Le service reste None jusqu'à l'appel de authenticate().
        """
        self._service = None
        self._authenticated = False

    def is_configured(self) -> bool:
        """
        Vérifie si le fichier credentials.json existe.

        Returns:
            True si le fichier est présent ET les libs Google
            sont installées, False sinon.
        """
        if not _GOOGLE_LIBS_AVAILABLE:
            return False
        return os.path.exists(GMAIL_CREDENTIALS_FILE)

    def authenticate(self) -> bool:
        """
        Gère le flux OAuth2 pour se connecter à Gmail.

        1. Vérifie si un token.json valide existe déjà
        2. Si le token est expiré mais rafraîchissable, le rafraîchit
        3. Sinon, lance le flux d'autorisation dans le navigateur

        Returns:
            True si l'authentification a réussi, False sinon.
        """
        if not self.is_configured():
            logger.warning(
                "Gmail non configuré : le fichier '%s' est introuvable.",
                GMAIL_CREDENTIALS_FILE,
            )
            return False

        try:
            creds = None

            # ── Étape 1 : charger le token existant ──────────────
            if os.path.exists(GMAIL_TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(
                    GMAIL_TOKEN_FILE, GMAIL_SCOPES
                )
                logger.debug("Token existant chargé depuis '%s'.", GMAIL_TOKEN_FILE)

            # ── Étape 2 : rafraîchir ou créer le token ───────────
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Rafraîchissement du token Gmail...")
                    creds.refresh(Request())
                else:
                    logger.info(
                        "Lancement du flux d'autorisation Gmail dans le navigateur..."
                    )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Sauvegarder le token pour les prochaines exécutions
                with open(GMAIL_TOKEN_FILE, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
                logger.info("Token Gmail sauvegardé dans '%s'.", GMAIL_TOKEN_FILE)

            # ── Étape 3 : construire le service Gmail ────────────
            self._service = build("gmail", "v1", credentials=creds)
            self._authenticated = True
            logger.info("Authentification Gmail réussie.")
            return True

        except Exception as e:
            logger.error("Erreur lors de l'authentification Gmail : %s", e)
            self._authenticated = False
            return False

    def search_for_reservation(
        self,
        client_name: str,
        reservation_number: str,
        date: datetime.date,
    ) -> list:
        """
        Recherche dans Gmail les emails liés à une réservation.

        Construit une requête de recherche combinant le nom du client,
        le numéro de réservation et les mots-clés de modification,
        puis analyse les résultats pour créer des alertes.

        Args:
            client_name: Nom du client (ex. "Famille Dupont").
            reservation_number: Numéro de réservation (ex. "QWK-20260527-001").
            date: Date de la réservation.

        Returns:
            Liste d'objets GmailAlert correspondant aux emails trouvés.
        """
        # ── Mode non authentifié : retourner des alertes de démo ─
        if not self._authenticated or not self._service:
            logger.info(
                "Gmail non authentifié — pas d'alertes disponibles pour %s.",
                client_name,
            )
            return []

        try:
            # Construire la requête de recherche
            query = self._build_query(client_name, reservation_number, date)
            logger.debug("Requête Gmail : %s", query)

            # Exécuter la recherche
            results = (
                self._service.users()
                .messages()
                .list(userId="me", q=query, maxResults=10)
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                logger.info("Aucun email trouvé pour '%s'.", client_name)
                return []

            # Parser chaque message trouvé
            alerts = []
            for msg_info in messages:
                alert = self._parse_message(msg_info["id"])
                if alert:
                    alerts.append(alert)

            logger.info(
                "%d alerte(s) trouvée(s) pour '%s'.", len(alerts), client_name
            )
            return alerts

        except Exception as e:
            logger.error(
                "Erreur lors de la recherche Gmail pour '%s' : %s",
                client_name,
                e,
            )
            return []

    # ──────────────────────────────────────────────────────────────
    #  Méthodes internes
    # ──────────────────────────────────────────────────────────────

    def _build_query(
        self,
        client_name: str,
        reservation_number: str,
        date: datetime.date,
    ) -> str:
        """
        Construit la chaîne de requête pour la recherche Gmail.

        La requête combine :
        - Le nom du client OU le numéro de réservation
        - Les mots-clés de modification (en OR)
        - Une limite temporelle (derniers N jours)

        Args:
            client_name: Nom du client.
            reservation_number: Numéro de réservation.
            date: Date de la réservation.

        Returns:
            La chaîne de requête Gmail (format q parameter).
        """
        # Extraire le nom de famille du client (sans "Famille" ni prénom)
        # "Famille Dupont (Lucas)" -> "Dupont"
        nom_parts = client_name.replace("Famille ", "").split("(")[0].strip()

        # Bloc identité : nom du client OU numéro de réservation
        identity_query = f'("{nom_parts}" OR "{reservation_number}")'

        # Bloc mots-clés : au moins un mot-clé de modification
        keywords_query = " OR ".join(f'"{kw}"' for kw in GMAIL_KEYWORDS)
        keywords_query = f"({keywords_query})"

        # Limite temporelle : emails reçus dans les N derniers jours
        date_limit = datetime.date.today() - datetime.timedelta(
            days=GMAIL_SEARCH_DAYS_BACK
        )
        after_query = f"after:{date_limit.strftime('%Y/%m/%d')}"

        # Requête combinée
        return f"{identity_query} {keywords_query} {after_query}"

    def _parse_message(self, msg_id: str) -> GmailAlert:
        """
        Récupère et parse un message Gmail par son identifiant.

        Args:
            msg_id: Identifiant unique du message Gmail.

        Returns:
            Un objet GmailAlert, ou None si le parsing échoue.
        """
        try:
            # Récupérer le message complet
            message = (
                self._service.users()
                .messages()
                .get(userId="me", id=msg_id, format="full")
                .execute()
            )

            headers = message.get("payload", {}).get("headers", [])

            # Extraire les en-têtes utiles
            subject = ""
            sender = ""
            date_str = ""
            for header in headers:
                name = header.get("name", "").lower()
                if name == "subject":
                    subject = header.get("value", "")
                elif name == "from":
                    sender = header.get("value", "")
                elif name == "date":
                    date_str = header.get("value", "")

            # Extraire le texte brut du corps de l'email
            body = self._extract_body(message.get("payload", {}))

            # Snippet fourni par Gmail (résumé court)
            snippet = message.get("snippet", "")

            # Détecter les mots-clés dans le sujet et le corps
            texte_complet = f"{subject} {body}".lower()
            keywords_found = [
                kw for kw in GMAIL_KEYWORDS if kw.lower() in texte_complet
            ]

            # Calculer le niveau de confiance
            confidence = self._calculate_confidence(subject, body, keywords_found)

            # Formater la date si possible
            try:
                parsed_date = parsedate_to_datetime(date_str)
                date_formatted = parsed_date.strftime("%d/%m/%Y %H:%M")
            except Exception:
                date_formatted = date_str

            return GmailAlert(
                subject=subject,
                sender=sender,
                date=date_formatted,
                snippet=snippet[:200],  # Limiter la longueur du snippet
                confidence=confidence,
                keywords_found=keywords_found,
            )

        except Exception as e:
            logger.warning("Impossible de parser le message %s : %s", msg_id, e)
            return None

    def _extract_body(self, payload: dict) -> str:
        """
        Extrait le texte brut du corps d'un email Gmail.

        Gère les différentes structures possibles (simple, multipart).

        Args:
            payload: Le payload du message Gmail.

        Returns:
            Le texte brut du corps de l'email.
        """
        body = ""

        if "body" in payload and payload["body"].get("data"):
            # Corps simple
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                "utf-8", errors="replace"
            )
        elif "parts" in payload:
            # Corps multipart — chercher la partie text/plain
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8", errors="replace")
                    break
                elif "parts" in part:
                    # Récursion pour les structures imbriquées
                    body = self._extract_body(part)
                    if body:
                        break

        return body

    def _calculate_confidence(
        self,
        subject: str,
        body: str,
        keywords_found: list,
    ) -> str:
        """
        Évalue le niveau de confiance d'une alerte.

        Le niveau dépend du nombre de mots-clés trouvés :
        - 3+ mots-clés → "high"
        - 1-2 mots-clés → "medium"
        - 0 mot-clé → "low"

        Args:
            subject: Sujet de l'email.
            body: Corps de l'email.
            keywords_found: Liste des mots-clés détectés.

        Returns:
            Niveau de confiance : "high", "medium" ou "low".
        """
        nb_keywords = len(keywords_found)

        if nb_keywords >= 3:
            return "high"
        elif nb_keywords >= 1:
            return "medium"
        else:
            return "low"
