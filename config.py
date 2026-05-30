"""
Configuration de l'application Gravity Center - Gestion des Anniversaires
=========================================================================
Modifiez les variables ci-dessous selon votre configuration.

FORMAT FIDÈLE AU PLANNING EXCEL EXISTANT :
  Colonnes : Heure | Nom+prénom | Activités | Nombre | Table | Prénom | Âge
             | Brownie | Gât.crêpes | Donuts | Bonbons | Kidibul | Chips
             | Crêpes | Granité 200ml | Granité 350ml | Pause gâteau
             | Commentaire | Arrivé | Payé
"""
from dataclasses import dataclass, field
from typing import Optional
import datetime


# ╔══════════════════════════════════════════════════════════════╗
# ║                    CONFIGURATION DES TABLES                  ║
# ╚══════════════════════════════════════════════════════════════╝
# Format : {"nom_table": capacité_max}
# Modifiez cette variable pour refléter votre plan de salle.

TABLES = {
    "T1": 17,
    "T2": 12,
    "T3": 12,
    "T4": 12,
    "T5": 8,
    "T6": 8,
    "STG-": 17,
    "STG+": 22,
    "R1": 10,
    "R2": 6,
    "R3": 6,
    "R4": 12,
}


# ╔══════════════════════════════════════════════════════════════╗
# ║                    ACTIVITÉS DISPONIBLES                     ║
# ╚══════════════════════════════════════════════════════════════╝
# Les activités telles qu'elles apparaissent dans vos plannings :
#   - "X parties" = X parties de Laser Game
#   - "1H" = 1 heure de Team Game (ou jeu libre)
#   - "30 min QUIZ" / "30 min Quiz" = Quiz Game
# Exemples réels : "3 parties", "1H + 1 partie", "1H + 2 parties",
#                  "1H + 1 partie + 30 min QUIZ", "2 parties + 30 min Quiz"
ACTIVITIES = [
    "Laser Game",
    "Team Game",
    "Quiz Game",
]


# ╔══════════════════════════════════════════════════════════════╗
# ║               FORMULES ANNIVERSAIRES & DURÉES                ║
# ╚══════════════════════════════════════════════════════════════╝
# Chaque formule est identifiée par le texte tel qu'il apparaît
# dans la colonne C du planning Excel (col "Activités").
#
# Format : {
#   "clé_normalisée": {
#       "label": "Nom affiché",
#       "duration_min": durée totale en minutes,
#       "steps": [("Étape", durée_min), ...]
#   }
# }
#
# La clé est normalisée (minuscules, espaces réduits) pour matcher
# les variations du planning ("QUIZ" vs "Quiz", etc.)

FORMULAS = {
    "2 parties": {
        "label": "2 parties de Laser Game",
        "duration_min": 100,
        "steps": [
            ("Accueil", 20),
            ("1ère partie de Laser Game", 20),
            ("2ème partie de Laser Game", 20),
            ("Table", 40),
        ],
    },
    "3 parties": {
        "label": "3 parties de Laser Game",
        "duration_min": 120,
        "steps": [
            ("Accueil", 20),
            ("1ère partie de Laser Game", 20),
            ("2ème partie de Laser Game", 20),
            ("Table", 40),
            ("3ème partie de Laser Game", 20),
        ],
    },
    "1h": {
        "label": "1H de Team Game",
        "duration_min": 120,
        "steps": [
            ("Accueil", 20),
            ("Team Game", 60),
            ("Table", 40),
        ],
    },
    "1h + 1 partie": {
        "label": "1H de Team Game + 1 Partie de Laser Game",
        "duration_min": 140,
        "steps": [
            ("Accueil", 20),
            ("Team Game", 60),
            ("Table", 40),
            ("Laser Game", 20),
        ],
    },
    "1h + 2 parties": {
        "label": "1H de Team Game + 2 Parties de Laser Game",
        "duration_min": 160,
        "steps": [
            ("Accueil", 20),
            ("Team Game", 60),
            ("Table", 40),
            ("1ère partie de Laser Game", 20),
            ("2ème partie de Laser Game", 20),
        ],
    },
    "2 parties + 30 min quiz": {
        "label": "2 parties de Laser Game + 30 min de Quiz Game",
        "duration_min": 130,
        "steps": [
            ("Accueil", 20),
            ("1ère partie de Laser Game", 20),
            ("2ème partie de Laser Game", 20),
            ("Table", 40),
            ("Quiz Game", 30),
        ],
    },
    "2 parties + 60 min quiz": {
        "label": "2 parties de Laser Game + 60 min de Quiz Game",
        "duration_min": 160,
        "steps": [
            ("Accueil", 20),
            ("1ère partie de Laser Game", 20),
            ("2ème partie de Laser Game", 20),
            ("Table", 40),
            ("1ère partie de Quiz Game", 30),
            ("2ème partie de Quiz Game", 30),
        ],
    },
    "1h + 30 min quiz": {
        "label": "1H de Team Game + 30 min de Quiz Game",
        "duration_min": 150,
        "steps": [
            ("Accueil", 20),
            ("Team Game", 60),
            ("Table", 40),
            ("Quiz Game", 30),
        ],
    },
    "1h + 60 min quiz": {
        "label": "1H de Team Game + 60 min de Quiz Game",
        "duration_min": 180,
        "steps": [
            ("Accueil", 20),
            ("Team Game", 60),
            ("Table", 40),
            ("1ère partie de Quiz Game", 30),
            ("2ème partie de Quiz Game", 30),
        ],
    },
    "1 partie + 1h + 30 min quiz": {
        "label": "1 Partie LG + 1H Team Game + 30 min Quiz",
        "duration_min": 170,
        "steps": [
            ("Accueil", 20),
            ("Team Game", 60),
            ("Table", 40),
            ("Laser Game", 20),
            ("Quiz Game", 30),
        ],
    },
}


def match_formula(activity_text: str) -> dict | None:
    """
    Cherche la formule correspondant au texte d'activité.

    Normalise le texte (minuscules, espaces réduits) et compare
    avec les clés de FORMULAS. Gère les variations du planning
    comme "QUIZ" vs "Quiz", "1 Partie" vs "1 partie", etc.

    Args:
        activity_text: Le texte de la colonne C du planning.

    Returns:
        Le dict de la formule trouvée, ou None.
    """
    if not activity_text:
        return None

    import re

    # Normaliser : minuscules, espaces multiples → un seul
    normalized = " ".join(activity_text.lower().split())

    # ── Correspondance directe ────────────────────────────────
    if normalized in FORMULAS:
        return FORMULAS[normalized]

    # ── Parsing par composants (ordre indifférent) ────────────
    # Séparer par " + " et identifier chaque bloc
    parts = [p.strip() for p in normalized.split("+")]

    laser_count = 0
    has_team = False
    quiz_minutes = 0

    for part in parts:
        part = part.strip()
        # Laser Game : "X partie(s)" ou "X parties"
        m = re.match(r"(\d+)\s*partie", part)
        if m:
            laser_count += int(m.group(1))
            continue
        # Team Game : "1h"
        if re.match(r"1\s*h\b", part):
            has_team = True
            continue
        # Quiz Game : "30 min quiz" ou "60 min quiz"
        m = re.match(r"(\d+)\s*min", part)
        if m:
            quiz_minutes += int(m.group(1))
            continue

    # Table de correspondance (laser, team, quiz) → clé formule
    _COMPONENT_MAP = {
        (2, False, 0):  "2 parties",
        (3, False, 0):  "3 parties",
        (0, True, 0):   "1h",
        (1, True, 0):   "1h + 1 partie",
        (2, True, 0):   "1h + 2 parties",
        (2, False, 30): "2 parties + 30 min quiz",
        (2, False, 60): "2 parties + 60 min quiz",
        (0, True, 30):  "1h + 30 min quiz",
        (0, True, 60):  "1h + 60 min quiz",
        (1, True, 30):  "1 partie + 1h + 30 min quiz",
    }

    key = (laser_count, has_team, quiz_minutes)
    formula_key = _COMPONENT_MAP.get(key)
    if formula_key and formula_key in FORMULAS:
        return FORMULAS[formula_key]

    # ── Fallback : correspondance partielle ───────────────────
    for fkey, formula in FORMULAS.items():
        if fkey in normalized or normalized in fkey:
            return formula

    return None


# ╔══════════════════════════════════════════════════════════════╗
# ║                     OPTIONS (Colonnes H → P)                 ║
# ╚══════════════════════════════════════════════════════════════╝
# Liste ordonnée des options telles qu'elles apparaissent dans
# les colonnes H à P du fichier Excel.
OPTIONS_COLUMNS = [
    "Brownie",           # Col H — quantité (généralement 0 ou 1)
    "Gât. crêpes",       # Col I — nombre de parts
    "Donuts",            # Col J — quantité
    "Bonbons",           # Col K — nombre de sachets
    "Kidibul",           # Col L — quantité
    "Chips",             # Col M — quantité
    "Crêpes",            # Col N — nombre d'assiettes
    "Granité 200ml",     # Col O — quantité
    "Granité 350ml",     # Col P — quantité
]


# ╔══════════════════════════════════════════════════════════════╗
# ║                    CONFIGURATION API QWEEKLE                 ║
# ╚══════════════════════════════════════════════════════════════╝
QWEEKLE_API_KEY = ""  # Renseignez votre clé API Qweekle ici
QWEEKLE_BASE_URL = "https://api.qweekle.com/v1"  # URL de base


# ╔══════════════════════════════════════════════════════════════╗
# ║                    CONFIGURATION GMAIL                       ║
# ╚══════════════════════════════════════════════════════════════╝
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

GMAIL_KEYWORDS = [
    "modification", "anniversaire", "annulation", "changement",
    "participants", "heure", "annuler", "reporter", "décaler",
    "ajouter", "supprimer", "nombre",
]
GMAIL_SEARCH_DAYS_BACK = 7


# ╔══════════════════════════════════════════════════════════════╗
# ║                    MODÈLES DE DONNÉES                        ║
# ╚══════════════════════════════════════════════════════════════╝

@dataclass
class GmailAlert:
    """Alerte email détectée pour une réservation."""
    subject: str
    sender: str
    date: str
    snippet: str
    confidence: str  # "high", "medium", "low"
    keywords_found: list = field(default_factory=list)


@dataclass
class Reservation:
    """
    Réservation d'anniversaire — calquée sur le format Excel.

    Les champs correspondent directement aux colonnes du planning :
      A=heure, B=nom, C=activités, D=nombre, E=table,
      F=prénom enfant, G=âge, H-P=options, Q=pause, R=commentaire,
      S=arrivé, T=payé
    """
    id: str
    reservation_number: str
    client_name: str                          # Col B — Nom + prénom du parent
    date: datetime.date                       # Ligne 1 — date du jour
    start_time: datetime.time                 # Col A — heure début
    end_time: datetime.time                   # Col A — heure fin
    activities: str                           # Col C — texte libre ("1H + 2 parties")
    nb_persons: int                           # Col D — nombre total de participants
    assigned_table: Optional[str] = None      # Col E — table attribuée
    child_name: str = ""                      # Col F — prénom de l'enfant
    child_age: str = ""                       # Col G — âge (str car parfois "?")

    # Options individuelles (colonnes H → P)
    brownie: int = 0                          # Col H
    gateau_crepes: int = 0                    # Col I — nombre de parts
    donuts: int = 0                           # Col J
    bonbons: int = 0                          # Col K — nombre de sachets
    kidibul: int = 0                          # Col L
    chips: int = 0                            # Col M
    crepes: int = 0                           # Col N — nombre d'assiettes
    granite_200: int = 0                      # Col O
    granite_350: int = 0                      # Col P

    # Timing & statut
    break_time: str = ""                      # Col Q — "11h00" ou "brownie à 13h00"
    comment: str = ""                         # Col R — commentaire libre
    arrived: bool = False                     # Col S
    paid: bool = False                        # Col T

    # Alertes Gmail (ajoutées par l'application)
    gmail_alerts: list = field(default_factory=list)

    @property
    def total_persons(self) -> int:
        """Nombre total de personnes."""
        return self.nb_persons

    @property
    def duration_hours(self) -> float:
        """Durée du créneau calculée à partir des heures de début et fin."""
        start_m = self.start_time.hour * 60 + self.start_time.minute
        end_m = self.end_time.hour * 60 + self.end_time.minute
        return (end_m - start_m) / 60

    @property
    def options_summary(self) -> dict:
        """Retourne les options non nulles sous forme de dictionnaire."""
        opts = {}
        if self.brownie:     opts["Brownie"] = self.brownie
        if self.gateau_crepes: opts["Gât. crêpes"] = self.gateau_crepes
        if self.donuts:      opts["Donuts"] = self.donuts
        if self.bonbons:     opts["Bonbons"] = self.bonbons
        if self.kidibul:     opts["Kidibul"] = self.kidibul
        if self.chips:       opts["Chips"] = self.chips
        if self.crepes:      opts["Crêpes"] = self.crepes
        if self.granite_200: opts["Granité 200"] = self.granite_200
        if self.granite_350: opts["Granité 350"] = self.granite_350
        return opts
