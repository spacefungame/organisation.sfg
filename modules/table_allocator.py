"""
Algorithme d'allocation de tables - Gravity Center
====================================================
Priorité : MINIMISER LES CHANGEMENTS DE TABLE en cours de journée.

On préfère utiliser une table encore inutilisée dans la journée (même si
elle est trop grande pour le groupe) plutôt que de réutiliser une table
qui a déjà servi. Cela évite au staff de devoir débarrasser et redresser
une table en plein rush.

Ordre de préférence pour chaque réservation :
  1. Table non utilisée aujourd'hui, capacité ≥ groupe (on choisit la plus petite possible pour économiser les grandes tables).
  2. Table déjà utilisée aujourd'hui, libre sur le créneau, capacité ≥ groupe (on choisit celle avec le plus grand écart temporel).
  3. Aucune table de capacité suffisante disponible → conflit.

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

            best_table = self._find_best_table_spread(
                reservation.nb_persons, start_time, end_time
            )

            if best_table:
                reservation.assigned_table = best_table
                self._occupancy[best_table].append(
                    (start_time, end_time, reservation)
                )
                nb_uses = len(self._occupancy[best_table])
                logger.info(
                    "✓ '%s' → Table %s (cap. %d, groupe de %d, usage n°%d)",
                    reservation.client_name,
                    best_table,
                    self.tables[best_table],
                    reservation.nb_persons,
                    nb_uses,
                )
            else:
                conflit_msg = (
                    f"{reservation.client_name} "
                    f"({reservation.nb_persons} pers., "
                    f"{start_time.strftime('%H:%M')}–{end_time.strftime('%H:%M')}) : "
                    f"aucune table disponible."
                )
                reservation.assigned_table = None
                self._conflicts.append(conflit_msg)
                logger.warning("CONFLIT — %s", conflit_msg)

        return sorted_reservations

    def _find_best_table_spread(
        self,
        nb_persons: int,
        start_time: datetime.time,
        end_time: datetime.time,
    ) -> Optional[str]:
        """
        Choisit la meilleure table en MINIMISANT les changements de table.

        Catégorise les tables disponibles (sans chevauchement) :
          - unused_fit : jamais utilisée + capacité suffisante
          - reused_fit : déjà utilisée + capacité suffisante
        """
        unused_fit = []    # (nom, capacité)
        reused_fit = []    # (nom, capacité, gap_minutes)

        for table_name, capacity in self.tables.items():
            # Ne jamais utiliser une table trop petite
            if capacity < nb_persons:
                continue

            # Vérifier que le créneau est libre
            if not self._is_free(table_name, start_time, end_time):
                continue

            used_today = len(self._occupancy[table_name]) > 0

            if not used_today:
                unused_fit.append((table_name, capacity))
            else:
                gap = self._min_gap_minutes(
                    table_name, start_time, end_time
                )
                reused_fit.append((table_name, capacity, gap))

        # 1. Table non utilisée, capacité OK → plus petite en premier
        if unused_fit:
            unused_fit.sort(key=lambda t: t[1])
            return unused_fit[0][0]

        # 2. Table réutilisée, capacité OK → plus grand gap en premier
        if reused_fit:
            reused_fit.sort(key=lambda t: -t[2])
            return reused_fit[0][0]

        # 3. Aucune table libre et de taille suffisante → conflit
        return None

    def _is_free(
        self,
        table_name: str,
        start_time: datetime.time,
        end_time: datetime.time,
    ) -> bool:
        """Vérifie qu'une table est libre sur le créneau [start, end)."""
        for occ_start, occ_end, _ in self._occupancy[table_name]:
            if start_time < occ_end and occ_start < end_time:
                return False
        return True

    def _min_gap_minutes(
        self,
        table_name: str,
        start_time: datetime.time,
        end_time: datetime.time,
    ) -> int:
        """
        Calcule le plus petit écart (en minutes) entre le nouveau créneau
        et les créneaux existants de cette table. Plus le gap est grand,
        plus le staff a du temps pour préparer.
        """
        min_gap = 9999
        for occ_start, occ_end, _ in self._occupancy[table_name]:
            # Écart = temps entre fin d'un créneau et début de l'autre
            gap1 = self._time_diff_min(occ_end, start_time)   # occ finit avant
            gap2 = self._time_diff_min(end_time, occ_start)   # occ commence après
            gap = max(0, min(gap1, gap2))
            if gap < min_gap:
                min_gap = gap
        return min_gap

    @staticmethod
    def _time_diff_min(t1: datetime.time, t2: datetime.time) -> int:
        """Différence t2 - t1 en minutes (peut être négatif)."""
        return (t2.hour * 60 + t2.minute) - (t1.hour * 60 + t1.minute)

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
