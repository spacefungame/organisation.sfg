"""
Données de démonstration — Gravity Center
==========================================
Génère des réservations fictives réalistes basées sur le format
exact du planning Excel (colonnes A→T).
"""
import datetime
from config import Reservation, GmailAlert


def generate_demo_reservations(target_date: datetime.date) -> list:
    """
    Génère des réservations fictives pour le mode démonstration.
    Calquées sur le format réel du planning Excel (Samedi 3005, etc.).
    """
    demos = [
        Reservation(
            id="demo-001",
            reservation_number="GRV-2025-0501",
            client_name="Janssen Anne-Sophie",
            date=target_date,
            start_time=datetime.time(10, 0),
            end_time=datetime.time(12, 0),
            activities="3 parties",
            nb_persons=20,
            assigned_table=None,
            child_name="Giulia",
            child_age="11",
            bonbons=6,
            break_time="11h00",
            paid=True,
        ),
        Reservation(
            id="demo-002",
            reservation_number="GRV-2025-0502",
            client_name="Noirot Olivier",
            date=target_date,
            start_time=datetime.time(11, 40),
            end_time=datetime.time(14, 0),
            activities="1H + 1 partie",
            nb_persons=8,
            assigned_table=None,
            child_name="Antoine",
            child_age="10",
            brownie=1,
            break_time="brownie à 13h00",
            paid=True,
        ),
        Reservation(
            id="demo-003",
            reservation_number="GRV-2025-0503",
            client_name="Khadmi Farah",
            date=target_date,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(14, 0),
            activities="1H",
            nb_persons=10,
            assigned_table=None,
            child_name="Sara",
            child_age="10",
            break_time="13h20",
            paid=False,
        ),
        Reservation(
            id="demo-004",
            reservation_number="GRV-2025-0504",
            client_name="Assanvo Wennah",
            date=target_date,
            start_time=datetime.time(12, 0),
            end_time=datetime.time(13, 40),
            activities="2 parties",
            nb_persons=7,
            assigned_table=None,
            child_name="Wennah",
            child_age="14",
            break_time="13h00",
            paid=True,
        ),
        Reservation(
            id="demo-005",
            reservation_number="GRV-2025-0505",
            client_name="Almeida Marlene",
            date=target_date,
            start_time=datetime.time(14, 0),
            end_time=datetime.time(16, 0),
            activities="3 parties",
            nb_persons=12,
            assigned_table=None,
            child_name="Clara",
            child_age="11",
            gateau_crepes=24,
            break_time="gâteau de crêpes à 15h00",
            paid=True,
        ),
        Reservation(
            id="demo-006",
            reservation_number="GRV-2025-0506",
            client_name="Dewinter Renald",
            date=target_date,
            start_time=datetime.time(14, 0),
            end_time=datetime.time(16, 20),
            activities="1H + 1 partie",
            nb_persons=8,
            assigned_table=None,
            child_name="Lily",
            child_age="11",
            break_time="15h20",
            comment="Demande table près de la fenêtre",
            paid=False,
            gmail_alerts=[
                GmailAlert(
                    subject="Modification réservation GRV-2025-0506",
                    sender="renald.dewinter@email.com",
                    date="27/05/2025 09:14",
                    snippet="Bonjour, je souhaite ajouter 2 enfants supplémentaires. On sera donc 10 au lieu de 8...",
                    confidence="high",
                    keywords_found=["modification", "ajouter", "enfants"],
                ),
            ],
        ),
        Reservation(
            id="demo-007",
            reservation_number="GRV-2025-0507",
            client_name="Emily Woitchik",
            date=target_date,
            start_time=datetime.time(14, 40),
            end_time=datetime.time(17, 20),
            activities="1H + 2 parties",
            nb_persons=7,
            assigned_table=None,
            child_name="Sofia",
            child_age="9",
            break_time="16h00",
            paid=True,
        ),
        Reservation(
            id="demo-008",
            reservation_number="GRV-2025-0508",
            client_name="Marziali Valentina",
            date=target_date,
            start_time=datetime.time(15, 0),
            end_time=datetime.time(17, 20),
            activities="1H + 1 partie",
            nb_persons=12,
            assigned_table=None,
            child_name="Flora",
            child_age="10",
            gateau_crepes=16,
            break_time="gâteau de crêpes à 16h20",
            gmail_alerts=[
                GmailAlert(
                    subject="Question sur l'horaire de Flora",
                    sender="valentina.m@email.com",
                    date="26/05/2025 18:30",
                    snippet="Est-il possible de décaler à 15h20 au lieu de 15h00 ?",
                    confidence="medium",
                    keywords_found=["horaire", "décaler"],
                ),
            ],
            paid=True,
        ),
        Reservation(
            id="demo-009",
            reservation_number="GRV-2025-0509",
            client_name="Wang An-An",
            date=target_date,
            start_time=datetime.time(15, 0),
            end_time=datetime.time(17, 40),
            activities="1H + 2 parties",
            nb_persons=8,
            assigned_table=None,
            child_name="?",
            child_age="?",
            break_time="16h20",
            paid=False,
        ),
        Reservation(
            id="demo-010",
            reservation_number="GRV-2025-0510",
            client_name="Addoun Linda",
            date=target_date,
            start_time=datetime.time(15, 20),
            end_time=datetime.time(18, 0),
            activities="1H + 2 parties",
            nb_persons=10,
            assigned_table=None,
            child_name="?",
            child_age="?",
            chips=1,
            bonbons=4,
            granite_200=8,
            break_time="16h40",
            comment="⚠️ Allergie arachides — 1 enfant",
            gmail_alerts=[
                GmailAlert(
                    subject="Confirmation allergie - anniv Linda",
                    sender="linda.addoun@email.com",
                    date="27/05/2025 07:45",
                    snippet="Un enfant est allergique aux arachides, merci de bien vouloir en tenir compte pour les chips et bonbons.",
                    confidence="high",
                    keywords_found=["allergie", "arachides", "bonbons"],
                ),
            ],
            paid=True,
        ),
    ]
    return demos


def generate_demo_gmail_alerts(reservations: list) -> dict:
    """
    Retourne les alertes déjà intégrées dans les réservations démo,
    indexées par id de réservation.
    """
    alerts = {}
    for r in reservations:
        if r.gmail_alerts:
            alerts[r.id] = r.gmail_alerts
    return alerts
