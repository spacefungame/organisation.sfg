"""
┌──────────────────────────────────────────────────────┐
│  GRAVITY CENTER — Gestion des Anniversaires          │
│  Dashboard Streamlit · Format fidèle au planning Excel│
│  Auteur : Gravity Dev · v1.0                         │
└──────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import datetime
import pathlib
import traceback
import logging

# Configuration basique du logger
logging.basicConfig(level=logging.INFO)

import streamlit as st
import requests

from config import (
    TABLES,
    OPTIONS_COLUMNS,
    FORMULAS,
    match_formula,
    Reservation,
    GmailAlert,
)
from modules.qweekle_api import QweekleClient
from modules.gmail_api import GmailClient
from modules.table_allocator import TableAllocator
from modules import supabase_client

# ── Configuration de la page ──────────────────────────────────
st.set_page_config(
    page_title="Gravity Center — Anniversaires",
    page_icon="🎂",
    layout="wide",
)

# ══════════════════════════════════════════════════════════════
# CONSTANTES & HELPERS
# ══════════════════════════════════════════════════════════════

ROOT = pathlib.Path(__file__).resolve().parent

JOURS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS_FR = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
]

# Couleurs cycliques pour la timeline (une par réservation)
TIMELINE_COLORS = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444",
    "#7C3AED", "#EC4899", "#06B6D4", "#F97316",
    "#8B5CF6", "#14B8A6", "#D946EF", "#84CC16",
]

TIMELINE_START = 9   # 09h00
TIMELINE_END = 20    # 20h00
TIMELINE_SLOTS: list[str] = []
for _h in range(TIMELINE_START, TIMELINE_END):
    TIMELINE_SLOTS.append(f"{_h:02d}h00")
    TIMELINE_SLOTS.append(f"{_h:02d}h30")


def _fmt_date_fr(d: datetime.date) -> str:
    """'Mardi 27 Mai 2025'"""
    return f"{JOURS_FR[d.weekday()]} {d.day} {MOIS_FR[d.month]} {d.year}"


def _fmt_time(t: datetime.time) -> str:
    """'14h00'"""
    return f"{t.hour:02d}h{t.minute:02d}"


def _fmt_heure_col(r: Reservation) -> str:
    """'14h00 - 16h20' comme dans l'Excel."""
    return f"{_fmt_time(r.start_time)} - {_fmt_time(r.end_time)}"


def _alert_badge(alerts: list[GmailAlert]) -> str:
    """Badge HTML d'alerte Gmail."""
    if not alerts:
        return ""
    levels = {"high": 3, "medium": 2, "low": 1}
    max_a = max(alerts, key=lambda a: levels.get(a.confidence, 0))
    return (
        f'<span class="alert-badge alert-{max_a.confidence}">'
        f'📧 {len(alerts)}</span>'
    )


def _opt_cell(value: int) -> str:
    """Cellule d'option : affiche la valeur si > 0, sinon vide."""
    if value:
        return f'<span class="opt-value">{value}</span>'
    return ""


def _get_tables() -> dict:
    """Retourne la config des tables (session_state → Supabase → config.py)."""
    if "tables_config" not in st.session_state:
        # Essayer de charger depuis Supabase
        loaded = _load_tables_from_supabase()
        st.session_state["tables_config"] = loaded if loaded else dict(TABLES)
    return st.session_state["tables_config"]


def _load_tables_from_supabase() -> dict | None:
    """Charge la config tables depuis Supabase app_settings."""
    try:
        creds = supabase_client._get_credentials()
        if not creds:
            return None
        url, key = creds
        r = requests.get(
            f"{url}/rest/v1/app_settings",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={"key": "eq.tables", "select": "value"},
            timeout=5,
        )
        if r.ok and r.json():
            data = r.json()[0]["value"]
            # Convertir les valeurs en int (JSONB peut les stocker en float)
            return {k: int(v) for k, v in data.items()}
    except Exception:
        pass
    return None


def _save_tables_to_supabase(tables: dict) -> bool:
    """Sauvegarde la config tables dans Supabase app_settings."""
    try:
        creds = supabase_client._get_credentials()
        if not creds:
            return False
        url, key = creds
        r = requests.post(
            f"{url}/rest/v1/app_settings",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json={"key": "tables", "value": tables},
            timeout=5,
        )
        return r.ok
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
# CHARGEMENT DES DONNÉES
# ══════════════════════════════════════════════════════════════

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_reservations(date_start: datetime.date, data_source: str, tables_hash: str = "") -> list[dict]:
    """
    Récupère et alloue les tables. Renvoie une liste de dicts (cache-safe).
    data_source: 'supabase', 'qweekle', ou 'demo'
    tables_hash: hash de la config tables pour invalider le cache si modifiée
    """
    if data_source == "supabase":
        reservations = supabase_client.get_reservations_for_date(date_start, birthday_only=False)
    elif data_source == "qweekle":
        reservations = QweekleClient().get_reservations(date_start, date_start)
    else:
        from modules.demo_data import generate_demo_reservations
        reservations = generate_demo_reservations(date_start)

    # ── Enrichissement Qweekle : compléter    # On enrichit avec l'API Qweekle (si dispo)
    try:
        qweekle = QweekleClient()
        if qweekle.is_configured():
            reservations = qweekle.enrich_reservations(reservations)
    except Exception as e:
        import logging
        logging.error("Erreur enrich_reservations: %s", e)

    # Filtrer uniquement les anniversaires APRÈS enrichissement
    # car l'enrichissement trouve les mots-clés "anniversaire" dans Qweekle !
    reservations = [r for r in reservations if r.is_birthday]

    tables = _get_tables()
    allocator = TableAllocator(tables=tables)
    reservations = allocator.allocate(reservations)

    result = []
    for r in reservations:
        result.append({
            "id": r.id,
            "reservation_number": r.reservation_number,
            "client_name": r.client_name,
            "date": r.date.isoformat(),
            "start_time": r.start_time.strftime("%H:%M"),
            "end_time": r.end_time.strftime("%H:%M"),
            "activities": r.activities,
            "nb_persons": r.nb_persons,
            "assigned_table": r.assigned_table,
            "child_name": r.child_name,
            "child_age": r.child_age,
            "brownie": r.brownie,
            "gateau_crepes": r.gateau_crepes,
            "donuts": r.donuts,
            "bonbons": r.bonbons,
            "kidibul": r.kidibul,
            "chips": r.chips,
            "crepes": r.crepes,
            "granite_200": r.granite_200,
            "granite_350": r.granite_350,
            "break_time": r.break_time,
            "comment": r.comment,
            "arrived": r.arrived,
            "paid": r.paid,
            "age_category": r.age_category,
            "gmail_alerts": [
                {"subject": a.subject, "sender": a.sender, "date": a.date,
                 "snippet": a.snippet, "confidence": a.confidence,
                 "keywords_found": a.keywords_found}
                for a in r.gmail_alerts
            ],
        })
    return result


def _to_reservation(d: dict) -> Reservation:
    """Reconstruit un Reservation depuis un dict (cache)."""
    dp = d["date"].split("-")
    st_p = d["start_time"].split(":")
    et_p = d["end_time"].split(":")
    return Reservation(
        id=d["id"],
        reservation_number=d["reservation_number"],
        client_name=d["client_name"],
        date=datetime.date(int(dp[0]), int(dp[1]), int(dp[2])),
        start_time=datetime.time(int(st_p[0]), int(st_p[1])),
        end_time=datetime.time(int(et_p[0]), int(et_p[1])),
        activities=d["activities"],
        nb_persons=d["nb_persons"],
        assigned_table=d["assigned_table"],
        child_name=d["child_name"],
        child_age=d["child_age"],
        brownie=d["brownie"],
        gateau_crepes=d["gateau_crepes"],
        donuts=d["donuts"],
        bonbons=d["bonbons"],
        kidibul=d["kidibul"],
        chips=d["chips"],
        crepes=d["crepes"],
        granite_200=d["granite_200"],
        granite_350=d["granite_350"],
        break_time=d["break_time"],
        comment=d["comment"],
        arrived=d["arrived"],
        paid=d["paid"],
        age_category=d.get("age_category", ""),
        gmail_alerts=[GmailAlert(**a) for a in d["gmail_alerts"]],
    )


# ══════════════════════════════════════════════════════════════
# INJECTION CSS
# ══════════════════════════════════════════════════════════════

def _inject_css():
    css_path = ROOT / "assets" / "style.css"
    try:
        css = css_path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    except FileNotFoundError:
        pass


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════

def _render_sidebar() -> datetime.date:
    with st.sidebar:
        st.markdown(
            '<div class="sidebar-logo">🎯 <span class="accent">GRAVITY</span> CENTER</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="sidebar-subtitle">Gestion des Anniversaires</div>',
            unsafe_allow_html=True,
        )
        # ── Navigation par date ──────────────────────────────
        if "nav_date" not in st.session_state:
            st.session_state.nav_date = datetime.date.today()

        # Flèches jour
        col_pd, col_tj, col_nd = st.columns([1, 1, 1])
        with col_pd:
            if st.button("◀", use_container_width=True, key="prev_day", help="Jour précédent"):
                st.session_state.nav_date -= datetime.timedelta(days=1)
                st.rerun()
        with col_tj:
            if st.button("Auj.", use_container_width=True, key="today", help="Aujourd'hui"):
                st.session_state.nav_date = datetime.date.today()
                st.rerun()
        with col_nd:
            if st.button("▶", use_container_width=True, key="next_day", help="Jour suivant"):
                st.session_state.nav_date += datetime.timedelta(days=1)
                st.rerun()

        selected = st.date_input(
            "📅 Date du planning",
            value=st.session_state.nav_date,
            format="DD/MM/YYYY",
        )
        # Synchroniser si l'utilisateur change via le calendrier
        if selected != st.session_state.nav_date:
            st.session_state.nav_date = selected
            st.rerun()

        # Flèches semaine
        col_pw, col_nw = st.columns(2)
        with col_pw:
            if st.button("◀◀ Semaine", use_container_width=True, key="prev_week"):
                st.session_state.nav_date -= datetime.timedelta(weeks=1)
                st.rerun()
        with col_nw:
            if st.button("Semaine ▶▶", use_container_width=True, key="next_week"):
                st.session_state.nav_date += datetime.timedelta(weeks=1)
                st.rerun()

        st.divider()




        st.markdown("##### 🔌 Connexions")
        sbok = supabase_client.is_configured()
        qok = QweekleClient().is_configured()
        gok = GmailClient().is_configured()
        dot_s = "green" if sbok else "red"
        dot_q = "green" if qok else "red"
        dot_g = "green" if gok else "red"
        st.markdown(
            f'<span class="status-dot {dot_s}"></span> **Supabase** — {"Connecté" if sbok else "Non configuré"}',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="status-dot {dot_q}"></span> **Qweekle** — {"Connecté" if qok else "Non configuré"}',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<span class="status-dot {dot_g}"></span> **Gmail** — {"Prêt" if gok else "Non configuré"}',
            unsafe_allow_html=True,
        )
        if gok:
            if st.button("🔗 Connecter Gmail", use_container_width=True):
                try:
                    gc = GmailClient()
                    if gc.authenticate():
                        st.success("✅ Gmail connecté !")
                    else:
                        st.error("❌ Échec de l'authentification.")
                except Exception as e:
                    st.error(f"❌ {e}")

        st.divider()

        with st.expander("⚙️ Configuration des tables", expanded=False):
            tables = _get_tables()
            edited = dict(tables)  # copie de travail
            to_delete = []

            for tname in list(edited.keys()):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.text(tname)
                with c2:
                    new_cap = st.number_input(
                        "cap", value=edited[tname], min_value=1, max_value=50,
                        label_visibility="collapsed", key=f"cap_{tname}",
                    )
                    edited[tname] = new_cap
                with c3:
                    if st.button("🗑️", key=f"del_{tname}"):
                        to_delete.append(tname)

            for t in to_delete:
                edited.pop(t, None)

            # Ajouter une table
            c1, c2 = st.columns([3, 2])
            with c1:
                new_name = st.text_input("Nom", "", key="new_table_name",
                                         placeholder="ex: T7")
            with c2:
                new_cap_val = st.number_input("Places", value=10, min_value=1,
                                              max_value=50, key="new_table_cap")
            if st.button("➕ Ajouter", use_container_width=True):
                if new_name and new_name not in edited:
                    edited[new_name] = new_cap_val

            # Bouton sauvegarder
            if st.button("💾 Enregistrer les tables", use_container_width=True,
                         type="primary"):
                st.session_state["tables_config"] = edited
                if _save_tables_to_supabase(edited):
                    st.success("✅ Tables sauvegardées !")
                else:
                    st.warning("⚠️ Sauvegardé en session uniquement.")
                st.cache_data.clear()
                st.rerun()

        st.markdown(
            '<div class="sidebar-version">v1.0 — Gravity Center</div>',
            unsafe_allow_html=True,
        )
    return selected


# ══════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════

def _render_header(date: datetime.date, demo: bool):
    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown(
            f"""
            <div class="header-gradient fade-in">
                <h1>📋 Planning Anniversaires</h1>
                <div class="header-date">{_fmt_date_fr(date)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        if st.button("🔍 Diagnostic réservations"):
            try:
                activities = supabase_client.get_booking_activities(selected_date)
                from collections import defaultdict
                groups = defaultdict(list)
                for act in activities:
                    oid = act.get("order_id", "")
                    if oid:
                        groups[oid].append(act)
                st.write(f"**{len(groups)} commandes trouvées dans Supabase pour le {selected_date}**")
                for oid, acts in sorted(groups.items()):
                    fn = ""
                    ln = ""
                    for a in acts:
                        fn = (a.get("client_firstname") or "").strip()
                        ln = (a.get("client_lastname") or "").strip()
                        if fn or ln:
                            break
                    cats = list(set(a.get("category", "") for a in acts))
                    is_bday = any(supabase_client._is_birthday_category(c) for c in cats)
                    marker = "🎂" if is_bday else "  "
                    st.text(f"{marker} {ln} {fn} | {oid[:20]}... | {cats}")
            except Exception as e:
                st.error(str(e))

    if demo:
        st.markdown(
            '<div class="demo-banner fade-in">'
            "🎮 Mode Démonstration — Données fictives. "
            "Connectez Supabase + Qweekle pour afficher les vraies réservations."
            "</div>",
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════
# KPI
# ══════════════════════════════════════════════════════════════

def _render_kpis(reservations: list[Reservation]):
    total = len(reservations)
    persons = sum(r.nb_persons for r in reservations)
    capacity = sum(_get_tables().values())
    fill_pct = min(int(persons / capacity * 100), 100) if capacity else 0
    alerts = sum(1 for r in reservations if r.gmail_alerts)

    data = [
        ("🎂", str(total), "Réservations"),
        ("👧", str(persons), "Participants"),
        ("📊", f"{fill_pct}%", "Remplissage"),
        ("⚠️", str(alerts), "Alertes Gmail"),
    ]
    cols = st.columns(4)
    for col, (icon, val, label) in zip(cols, data):
        with col:
            st.markdown(
                f"""
                <div class="kpi-card fade-in">
                    <div class="kpi-icon">{icon}</div>
                    <div class="kpi-value">{val}</div>
                    <div class="kpi-label">{label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ══════════════════════════════════════════════════════════════
# TIMELINE
# ══════════════════════════════════════════════════════════════

def _render_timeline(reservations: list[Reservation]):
    st.markdown(
        '<div class="section-title">🕐 Occupation des tables</div>',
        unsafe_allow_html=True,
    )
    if not reservations:
        return

    # Construire la map couleur par réservation
    color_map = {}
    for i, r in enumerate(reservations):
        color_map[r.id] = TIMELINE_COLORS[i % len(TIMELINE_COLORS)]

    # Toutes les tables du config + celles assignées
    all_tables = list(_get_tables().keys())
    assigned = {r.assigned_table for r in reservations if r.assigned_table}
    tables_to_show = [t for t in all_tables if t in assigned]
    if not tables_to_show:
        st.caption("Aucune table assignée.")
        return

    nb = len(TIMELINE_SLOTS)
    grid_cols = f"100px repeat({nb}, 1fr)"

    # En-tête
    hdr = '<div class="timeline-label" style="font-weight:700;color:#A78BFA;">Table</div>'
    for s in TIMELINE_SLOTS:
        hdr += f'<div class="timeline-header-cell">{s}</div>'

    rows = ""
    for table in tables_to_show:
        rows += f'<div class="timeline-label">{table}</div>'
        for slot_label in TIMELINE_SLOTS:
            sh = int(slot_label[:2])
            sm = int(slot_label[3:5])
            slot_min = sh * 60 + sm

            occupant = None
            for r in reservations:
                if r.assigned_table != table:
                    continue
                s_min = r.start_time.hour * 60 + r.start_time.minute
                e_min = r.end_time.hour * 60 + r.end_time.minute
                if s_min <= slot_min < e_min:
                    occupant = r
                    break

            if occupant:
                color = color_map.get(occupant.id, "#7C3AED")
                occ_start = occupant.start_time.hour * 60 + occupant.start_time.minute
                name = occupant.client_name.split()[-1] if occupant.client_name else ""
                show = slot_min == occ_start
                lbl = name[:8] if show else ""
                rows += (
                    f'<div class="timeline-slot occupied" '
                    f'style="background:{color};" '
                    f'title="{occupant.client_name} — {_fmt_heure_col(occupant)}">'
                    f'{lbl}</div>'
                )
            else:
                rows += '<div class="timeline-slot empty"></div>'

    st.markdown(
        f"""
        <div class="timeline-container fade-in">
            <div class="timeline-grid" style="grid-template-columns:{grid_cols};">
                {hdr}{rows}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
# TABLEAU PRINCIPAL (format Excel fidèle)
# ══════════════════════════════════════════════════════════════

def _render_table(reservations: list[Reservation]):
    st.markdown(
        '<div class="section-title">📋 Réservations du jour</div>',
        unsafe_allow_html=True,
    )

    if not reservations:
        st.markdown(
            """
            <div class="empty-state fade-in">
                <div class="empty-icon">🎈</div>
                <div class="empty-text">Aucune réservation pour cette date</div>
                <div class="empty-sub">Les réservations apparaîtront ici automatiquement.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    sorted_res = sorted(reservations, key=lambda r: (r.start_time.hour, r.start_time.minute))

    # En-têtes
    hdr = """
    <tr>
        <th>Heure</th>
        <th>Nom + prénom</th>
        <th>Activités</th>
        <th style="text-align:center">Nb</th>
        <th>Table</th>
        <th>Prénom</th>
        <th>Âge</th>
        <th class="opt-header">Brownie</th>
        <th class="opt-header">Gât.crêpes</th>
        <th class="opt-header">Donuts</th>
        <th class="opt-header">Bonbons</th>
        <th class="opt-header">Kidibul</th>
        <th class="opt-header">Chips</th>
        <th class="opt-header">Crêpes</th>
        <th class="opt-header">Gr.200</th>
        <th class="opt-header">Gr.350</th>
        <th>Pause gâteau</th>
        <th>Commentaire</th>
        <th class="status-header">Arrivé</th>
        <th class="status-header">Payé</th>
        <th>Alertes</th>
    </tr>
    """

    rows = ""

    # ── Couleur unique par table ────────────────────────────
    _TABLE_PALETTE = [
        ("#dbeafe", "#1e40af"),   # bleu
        ("#d1fae5", "#065f46"),   # vert
        ("#fef3c7", "#92400e"),   # jaune
        ("#fce7f3", "#9d174d"),   # rose
        ("#e0e7ff", "#3730a3"),   # indigo
        ("#fed7aa", "#9a3412"),   # orange
        ("#ccfbf1", "#115e59"),   # teal
        ("#f5d0fe", "#86198f"),   # violet
        ("#fecaca", "#991b1b"),   # rouge
        ("#d9f99d", "#3f6212"),   # lime
    ]
    from collections import Counter
    table_counts = Counter(r.assigned_table for r in sorted_res if r.assigned_table)
    multi_tables = {t for t, c in table_counts.items() if c > 1}
    unique_tables = sorted(set(r.assigned_table for r in sorted_res if r.assigned_table))
    table_colors = {tname: _TABLE_PALETTE[i % len(_TABLE_PALETTE)] for i, tname in enumerate(unique_tables)}

    for r in sorted_res:
        # Table — badge coloré
        if r.assigned_table:
            bg, fg = table_colors.get(r.assigned_table, ("#f1f5f9", "#334155"))
            bold = "700" if r.assigned_table in multi_tables else "600"
            opa = "" if r.assigned_table in multi_tables else "opacity:0.75;"
            table_html = f'<span style="display:inline-block;padding:2px 8px;border-radius:6px;background:{bg};color:{fg};font-weight:{bold};{opa}">{r.assigned_table}</span>'
        else:
            table_html = '<span class="badge badge-conflict">⚠️ CONFLIT</span>'

        # Activités
        act_html = f'<span class="activity-pill">{r.activities}</span>' if r.activities else "—"

        # Statuts
        arrived_html = '<span class="status-ok">✅</span>' if r.arrived else ""
        paid_html = '<span class="status-ok">✅</span>' if r.paid else '<span class="status-wait">⏳</span>'

        # Alertes
        alert_html = _alert_badge(r.gmail_alerts)

        # Commentaire tronqué
        comment_display = r.comment[:30] + "…" if len(r.comment) > 30 else r.comment

        # Badge catégorie d'âge
        age_badge = ""
        if r.age_category == "enfant":
            age_badge = '<span style="display:inline-block;font-size:0.65rem;padding:1px 6px;border-radius:8px;background:#d1fae5;color:#065f46;margin-left:4px;">7-12</span>'
        elif r.age_category == "ado":
            age_badge = '<span style="display:inline-block;font-size:0.65rem;padding:1px 6px;border-radius:8px;background:#fed7aa;color:#9a3412;margin-left:4px;">13-18</span>'
        elif r.age_category == "adulte":
            age_badge = '<span style="display:inline-block;font-size:0.65rem;padding:1px 6px;border-radius:8px;background:#bfdbfe;color:#1e40af;margin-left:4px;">+18</span>'

        rows += f"""
        <tr>
            <td class="col-heure"><strong>{_fmt_heure_col(r)}</strong></td>
            <td class="client-name">{r.client_name} {age_badge}</td>
            <td>{act_html}</td>
            <td style="text-align:center"><strong>{r.nb_persons}</strong></td>
            <td>{table_html}</td>
            <td>{r.child_name}</td>
            <td style="text-align:center">{r.child_age}</td>
            <td class="opt-cell">{_opt_cell(r.brownie)}</td>
            <td class="opt-cell">{_opt_cell(r.gateau_crepes)}</td>
            <td class="opt-cell">{_opt_cell(r.donuts)}</td>
            <td class="opt-cell">{_opt_cell(r.bonbons)}</td>
            <td class="opt-cell">{_opt_cell(r.kidibul)}</td>
            <td class="opt-cell">{_opt_cell(r.chips)}</td>
            <td class="opt-cell">{_opt_cell(r.crepes)}</td>
            <td class="opt-cell">{_opt_cell(r.granite_200)}</td>
            <td class="opt-cell">{_opt_cell(r.granite_350)}</td>
            <td class="col-pause">{r.break_time}</td>
            <td class="col-comment">{comment_display}</td>
            <td style="text-align:center">{arrived_html}</td>
            <td style="text-align:center">{paid_html}</td>
            <td>{alert_html}</td>
        </tr>
        """

    # Lire le CSS pour l'inliner dans st.html (iframe isolé)
    css_path = ROOT / "assets" / "style.css"
    try:
        table_css = css_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        table_css = ""

    st.html(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        body {{ margin: 0; padding: 0; font-family: 'Inter', sans-serif; background: transparent; }}
        {table_css}
        </style>
        <div style="overflow-x:auto;">
        <table class="reservations-table">
            <thead>{hdr}</thead>
            <tbody>{rows}</tbody>
        </table>
        </div>
        """
    )


# ══════════════════════════════════════════════════════════════
# DÉTAILS (expanders)
# ══════════════════════════════════════════════════════════════

def _render_details(reservations: list[Reservation]):
    if not reservations:
        return

    st.markdown(
        '<div class="section-title" style="margin-top:1.5rem;">🔍 Détails des réservations</div>',
        unsafe_allow_html=True,
    )

    sorted_res = sorted(reservations, key=lambda r: (r.start_time.hour, r.start_time.minute))

    for r in sorted_res:
        alert_ind = f" 📧{len(r.gmail_alerts)}" if r.gmail_alerts else ""
        label = f"{_fmt_time(r.start_time)} — {r.client_name}{alert_ind}"

        with st.expander(label, expanded=False):
            c1, c2, c3 = st.columns(3)

            with c1:
                st.markdown("**📋 Informations**")
                st.markdown(f"- **N°** : `{r.reservation_number}`")
                st.markdown(f"- **Horaire** : {_fmt_heure_col(r)}")
                st.markdown(f"- **Durée** : {r.duration_hours:.1f}h")
                st.markdown(f"- **Table** : {r.assigned_table or '⚠️ Non assignée'}")
                st.markdown(f"- **Participants** : {r.nb_persons}")

            with c2:
                st.markdown("**🎂 Enfant**")
                st.markdown(f"- **Prénom** : {r.child_name or '?'}")
                st.markdown(f"- **Âge** : {r.child_age or '?'}")
                st.markdown(f"- **Activités** : {r.activities}")
                st.markdown(f"- **Pause** : {r.break_time or '—'}")

            with c3:
                st.markdown("**🎁 Options**")
                opts = r.options_summary
                if opts:
                    for k, v in opts.items():
                        st.markdown(f"- **{k}** : {v}")
                else:
                    st.caption("Aucune option")

            # Déroulé de la formule
            formula = match_formula(r.activities)
            if formula:
                st.markdown("---")
                st.markdown(f"**🎮 Formule : {formula['label']}** — Durée standard : {formula['duration_min']} min")
                # Barre visuelle du déroulé
                step_colors = {
                    "Accueil": "#64748B",
                    "Table": "#F59E0B",
                }
                laser_color = "#EF4444"
                team_color = "#10B981"
                quiz_color = "#3B82F6"
                total = formula["duration_min"]
                bar_html = '<div style="display:flex;gap:2px;border-radius:8px;overflow:hidden;height:32px;margin:8px 0;">'
                for step_name, step_dur in formula["steps"]:
                    pct = step_dur / total * 100
                    if "laser" in step_name.lower():
                        bg = laser_color
                    elif "team" in step_name.lower():
                        bg = team_color
                    elif "quiz" in step_name.lower():
                        bg = quiz_color
                    else:
                        bg = step_colors.get(step_name, "#7C3AED")
                    bar_html += (
                        f'<div style="width:{pct}%;background:{bg};display:flex;'
                        f'align-items:center;justify-content:center;color:#fff;'
                        f'font-size:0.65rem;font-weight:600;padding:0 2px;" '
                        f'title="{step_name} — {step_dur} min">{step_dur}m</div>'
                    )
                bar_html += '</div>'
                # Légende
                legend = (
                    '<div style="display:flex;gap:12px;flex-wrap:wrap;font-size:0.75rem;color:#94A3B8;">'
                )
                for step_name, step_dur in formula["steps"]:
                    if "laser" in step_name.lower():
                        dot = laser_color
                    elif "team" in step_name.lower():
                        dot = team_color
                    elif "quiz" in step_name.lower():
                        dot = quiz_color
                    else:
                        dot = step_colors.get(step_name, "#7C3AED")
                    legend += (
                        f'<span style="display:inline-flex;align-items:center;gap:4px;">'
                        f'<span style="width:8px;height:8px;border-radius:50%;background:{dot};"></span>'
                        f'{step_name} ({step_dur}min)</span>'
                    )
                legend += '</div>'
                st.markdown(bar_html + legend, unsafe_allow_html=True)

            if r.comment:
                st.markdown(f"**💬 Commentaire** : {r.comment}")

            # Alertes Gmail
            if r.gmail_alerts:
                st.markdown("---")
                st.markdown(f"**📧 Alertes Gmail** ({len(r.gmail_alerts)})")
                for alert in r.gmail_alerts:
                    st.markdown(
                        f"""
                        <div class="gmail-alert {alert.confidence}">
                            <div class="gmail-alert-subject">{alert.subject}</div>
                            <div class="gmail-alert-meta">De : {alert.sender} · {alert.date}</div>
                            <div class="gmail-alert-snippet">« {alert.snippet} »</div>
                            <div style="margin-top:4px;">
                                <span class="alert-badge alert-{alert.confidence}" style="font-size:0.7rem;">
                                    Confiance : {alert.confidence.upper()}
                                </span>
                            </div>
                            <div class="confidence-bar {alert.confidence}"></div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )


# ══════════════════════════════════════════════════════════════
# CONFLITS
# ══════════════════════════════════════════════════════════════

def _render_conflicts(reservations: list[Reservation]):
    alloc = TableAllocator(tables=_get_tables())
    alloc.allocate(reservations)
    conflicts = alloc.get_conflicts()
    if not conflicts:
        return

    st.markdown(
        '<div class="section-title" style="margin-top:1.5rem;">⚠️ Conflits détectés</div>',
        unsafe_allow_html=True,
    )
    for c in conflicts:
        st.markdown(
            f'<div class="conflict-box fade-in">⚠️ {c}</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════
# GMAIL ENRICHMENT
# ══════════════════════════════════════════════════════════════

def _enrich_gmail(reservations: list[Reservation]) -> list[Reservation]:
    """Recherche d'alertes Gmail pour chaque réservation (mode production)."""
    gmail = GmailClient()
    if not gmail.is_configured():
        return reservations
    try:
        gmail.authenticate()
    except Exception:
        return reservations

    for r in reservations:
        if not r.gmail_alerts:
            try:
                r.gmail_alerts = gmail.search_for_reservation(
                    r.client_name, r.reservation_number, r.date
                )
            except Exception:
                pass
    return reservations


# ══════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════

def main():
    _inject_css()
    selected_date = _render_sidebar()

    st.sidebar.markdown("---")
    
    # Déterminer la source de données (priorité : Supabase > Qweekle > Démo)
    if supabase_client.is_configured():
        data_source = "supabase"
    elif QweekleClient().is_configured():
        data_source = "qweekle"
    else:
        data_source = "demo"

    demo = data_source == "demo"
    _render_header(selected_date, demo)

    try:
        tables_hash = str(sorted(_get_tables().items()))
        raw = _fetch_reservations(selected_date, data_source, tables_hash)
        reservations = [_to_reservation(d) for d in raw]
    except Exception as e:
        logging.exception("Erreur lors de l'exécution de l'application")
        st.error(f"❌ Erreur chargement : {e}")
        st.code(traceback.format_exc())
        reservations = []

    if not demo:
        try:
            reservations = _enrich_gmail(reservations)
        except Exception:
            pass

    _render_kpis(reservations)
    st.markdown("<br>", unsafe_allow_html=True)

    try:
        _render_timeline(reservations)
    except Exception as e:
        st.warning(f"⚠️ Timeline : {e}")

    try:
        _render_table(reservations)
    except Exception as e:
        st.warning(f"⚠️ Tableau : {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    try:
        _render_details(reservations)
    except Exception as e:
        st.warning(f"⚠️ Détails : {e}")

    try:
        _render_conflicts(reservations)
    except Exception:
        pass


if __name__ == "__main__":
    main()
