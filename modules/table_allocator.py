"""
Algorithme d'allocation de tables - Gravity Center
====================================================
Utilise un algorithme Best-Fit pour attribuer la plus petite table
disponible qui peut accueillir le groupe, en évitant les chevauchements
de créneaux horaires.

Intervalles semi-ouverts [start, end) : une réservation qui finit à 14h00
ne chevauche PAS une réservation qui commence à 14h00 (back-to-back OK).
"""

import datetime
import logging
from typing import Optional

from config import TABLES, Reservation

logger = logging.getLogger(__name__)


class TableAllocator:
    """
    Gestionnaire d'allocation de tables pour les réservations.

    Utilise start_time et end_time de chaque Reservation
    (calculés à partir de la colonne "Heure" du planning Excel).
    """

    def __init__(self, tables: dict = None):
        """
        Args:
            tables: Dictionnaire {nom_table: capacité_max}.
                    Si None, utilise la configuration de config.py.
        """
        self.tables = tables or dict(TABLES)
        # Carte d'occupation : table_name -> [(start_time, end_time, reservation)]
        self._occupancy: dict[str, list] = {name: [] for name in self.tables}
        self._conflicts: list[str] = []

    def allocate(self, reservations: list) -> list:
        """
        Attribue une table à chaque réservation pour une journée.

        Algorithme :
        1. Trier les réservations par heure de début
        2. Pour chaque réservation :
           a. Trouver les tables libres sur [start_time, end_time)
           b. Parmi celles avec capacité >= nb_persons, choisir la plus petite
           c. Sinon → marquer comme conflit

        Returns:
            Liste des réservations avec assigned_table mis à jour.
        """
        self._occupancy = {name: [] for name in self.tables}
        self._conflicts = []

        sorted_reservations = sorted(
            reservations, key=lambda r: (r.start_time.hour, r.start_time.minute)
        )

        for reservation in sorted_reservations:
            start_time = reservation.start_time
            end_time = reservation.end_time

            logger.debug(
                "Allocation pour '%s' : %s–%s, %d personnes",
                reservation.client_name,
                start_time.strftime("%H:%M"),
                end_time.strftime("%H:%M"),
                reservation.nb_persons,
            )

            available = self._get_available_tables(start_time, end_time)
            best_table = self._find_best_table(reservation.nb_persons, available)

            if best_table:
                reservation.assigned_table = best_table
                self._occupancy[best_table].append(
                    (start_time, end_time, reservation)
                )
                logger.info(
                    "✓ '%s' → Table %s (cap. %d, groupe de %d)",
                    reservation.client_name,
                    best_table,
                    self.tables[best_table],
                    reservation.nb_persons,
                )
            else:
                conflit_msg = (
                    f"{reservation.client_name} "
                    f"({reservation.nb_persons} pers., "
                    f"{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}) : "
                    f"aucune table disponible avec capacité suffisante."
                )
                reservation.assigned_table = None
                self._conflicts.append(conflit_msg)
                logger.warning("CONFLIT — %s", conflit_msg)

        return sorted_reservations

    def _get_available_tables(
        self,
        time_start: datetime.time,
        time_end: datetime.time,
    ) -> list:
        """
        Retourne les tables libres pour un créneau donné.

        Returns:
            Liste de tuples (nom_table, capacité) triée par capacité croissante.
        """
        available = []

        for table_name, capacity in self.tables.items():
            is_free = True
            for occ_start, occ_end, _ in self._occupancy[table_name]:
                if self._check_time_overlap(time_start, time_end, occ_start, occ_end):
                    is_free = False
                    break
            if is_free:
                available.append((table_name, capacity))

        available.sort(key=lambda t: t[1])
        return available

    def _find_best_table(
        self,
        total_persons: int,
        available_tables: list,
    ) -> Optional[str]:
        """
        Best-fit : plus petite table disponible avec capacité >= total_persons.
        """
        for table_name, capacity in available_tables:
            if capacity >= total_persons:
                return table_name
        return None

    @staticmethod
    def _check_time_overlap(
        start1: datetime.time, end1: datetime.time,
        start2: datetime.time, end2: datetime.time,
    ) -> bool:
        """
        Vérifie le chevauchement de deux créneaux semi-ouverts [start, end).
        """
        return start1 < end2 and start2 < end1

    def get_conflicts(self) -> list:
        """Retourne la liste des conflits détectés."""
        return list(self._conflicts)

    def get_occupancy_map(self) -> dict:
        """Retourne la carte d'occupation : {table: [(start, end, reservation), ...]}."""
        return {
            name: list(occs)
            for name, occs in self._occupancy.items()
            if occs
        }
