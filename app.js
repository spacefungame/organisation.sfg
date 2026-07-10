/**
 * Logique Principale de l'Application - Organisation Space Fun Games
 * Thème Beige Chaleureux / Mode Clair (Aucun Gris)
 * Plannings Classiques & Synchronisation Globale
 */

// Mois en français pour affichage convivial
const MONTHS_FR = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
];

const DAYS_FR = [
    "Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"
];

// Mois courant affiché sur le calendrier central de l'accueil
let calendarDisplayYear = new Date().getFullYear();
let calendarDisplayMonth = new Date().getMonth();

// Onglet actif actuel
let currentActiveTab = "home";

// ============================================================================
// 1. INITIALISATION AU CHARGEMENT DE LA PAGE
// ============================================================================
document.addEventListener("DOMContentLoaded", () => {
    initAuth();
    initNavigation();
    initDateController();
    initModals();

    // S'abonner aux changements d'état
    appState.onDateChange((newDate) => {
        updateHeaderDateDisplay(newDate);
        renderCalendar();
        renderCurrentView();
    });

    appState.onAuthChange((isAuth) => {
        if (isAuth) {
            document.getElementById("login-modal").style.display = "none";
            document.getElementById("app-header").style.display = "flex";
            document.getElementById("app-content").style.display = "block";
            updateHeaderDateDisplay(appState.currentDate);
            renderCalendar();
            renderCurrentView();
        } else {
            document.getElementById("login-modal").style.display = "flex";
            document.getElementById("app-header").style.display = "none";
            document.getElementById("app-content").style.display = "none";
        }
    });

    // Vérifier l'état initial
    if (appState.isAuthenticated) {
        appState.notifyAuthChange();
    } else {
        document.getElementById("password-input").focus();
    }
});

// ============================================================================
// 2. AUTHENTIFICATION SÉCURISÉE (Web Crypto API & Mot de passe 1503)
// ============================================================================
function initAuth() {
    const loginForm = document.getElementById("login-form");
    const passwordInput = document.getElementById("password-input");
    const loginError = document.getElementById("login-error");
    const logoutBtn = document.getElementById("btn-logout");

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const pwd = passwordInput.value.trim();
        if (!pwd) return;

        // Vérification directe avec RAW_PASSWORD (1503) ou vérification SHA-256
        if (pwd === CONFIG.RAW_PASSWORD) {
            loginError.textContent = "";
            passwordInput.value = "";
            appState.setAuthenticated(true);
            return;
        }

        // Calcul du hash SHA-256 si la vérification directe échoue
        try {
            const encoder = new TextEncoder();
            const data = encoder.encode(pwd);
            const hashBuffer = await crypto.subtle.digest("SHA-256", data);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

            if (hashHex === CONFIG.PASSWORD_HASH_SHA256) {
                loginError.textContent = "";
                passwordInput.value = "";
                appState.setAuthenticated(true);
            } else {
                loginError.textContent = "❌ Mot de passe incorrect. Veuillez réessayer.";
                passwordInput.select();
            }
        } catch (err) {
            loginError.textContent = "❌ Erreur de vérification. Essayez de retaper le mot de passe.";
        }
    });

    logoutBtn.addEventListener("click", () => {
        if (confirm("Voulez-vous vraiment verrouiller la session ?")) {
            appState.setAuthenticated(false);
        }
    });
}

// ============================================================================
// 3. NAVIGATION ENTRE LES ONGLET & ROUTAGE SPA
// ============================================================================
function initNavigation() {
    const tabButtons = document.querySelectorAll(".nav-tab");
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });
}

function switchTab(tabId) {
    currentActiveTab = tabId;

    // Mise à jour des boutons
    document.querySelectorAll(".nav-tab").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Mise à jour des sections de vue
    document.querySelectorAll(".view-section").forEach(sec => {
        if (sec.id === `view-${tabId}`) {
            sec.classList.add("active");
        } else {
            sec.classList.remove("active");
        }
    });

    // Rendu spécifique de la vue
    renderCurrentView();
}

function renderCurrentView() {
    switch (currentActiveTab) {
        case "home":
            renderHomeDashboard();
            break;
        case "complet":
            renderClassicPlanning(null, "tbody-complet", "subtitle-complet");
            break;
        case "anniversaire":
            renderClassicPlanning("anniversaire", "tbody-anniversaire", "subtitle-anniversaire");
            break;
        case "laser":
            renderClassicPlanning("laser", "tbody-laser", "subtitle-laser");
            break;
        case "team":
            renderClassicPlanning("team", "tbody-team", "subtitle-team");
            break;
        case "quiz":
            renderClassicPlanning("quiz", "tbody-quiz", "subtitle-quiz");
            break;
        case "postit":
            renderPostIts();
            break;
    }
}

// ============================================================================
// 4. CONTRÔLE DE LA DATE ET DU CALENDRIER
// ============================================================================
function initDateController() {
    const prevBtn = document.getElementById("date-prev-btn");
    const nextBtn = document.getElementById("date-next-btn");
    const todayBtn = document.getElementById("date-today-btn");
    const dateInput = document.getElementById("header-date-input");

    const calPrevMonth = document.getElementById("cal-prev-month");
    const calNextMonth = document.getElementById("cal-next-month");

    prevBtn.addEventListener("click", () => changeDateByDays(-1));
    nextBtn.addEventListener("click", () => changeDateByDays(1));
    todayBtn.addEventListener("click", () => {
        const todayStr = new Date().toISOString().split("T")[0];
        appState.setDate(todayStr);
        calendarDisplayYear = new Date().getFullYear();
        calendarDisplayMonth = new Date().getMonth();
        renderCalendar();
    });

    dateInput.addEventListener("change", (e) => {
        if (e.target.value) {
            appState.setDate(e.target.value);
            const chosenDate = new Date(e.target.value);
            calendarDisplayYear = chosenDate.getFullYear();
            calendarDisplayMonth = chosenDate.getMonth();
            renderCalendar();
        }
    });

    calPrevMonth.addEventListener("click", () => {
        calendarDisplayMonth--;
        if (calendarDisplayMonth < 0) {
            calendarDisplayMonth = 11;
            calendarDisplayYear--;
        }
        renderCalendar();
    });

    calNextMonth.addEventListener("click", () => {
        calendarDisplayMonth++;
        if (calendarDisplayMonth > 11) {
            calendarDisplayMonth = 0;
            calendarDisplayYear++;
        }
        renderCalendar();
    });
}

function changeDateByDays(daysDelta) {
    const parts = appState.currentDate.split("-");
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    d.setDate(d.getDate() + daysDelta);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    appState.setDate(`${yyyy}-${mm}-${dd}`);

    calendarDisplayYear = yyyy;
    calendarDisplayMonth = d.getMonth();
    renderCalendar();
}

function updateHeaderDateDisplay(dateStr) {
    const parts = dateStr.split("-");
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    const dayName = DAYS_FR[d.getDay()];
    const monthName = MONTHS_FR[d.getMonth()];
    
    document.getElementById("header-date-text").textContent = `${dayName} ${d.getDate()} ${monthName} ${d.getFullYear()}`;
    document.getElementById("header-date-input").value = dateStr;
    
    // Mettre à jour aussi l'intitulé du tableau de bord d'accueil
    const dashTitle = document.getElementById("dashboard-date-title");
    if (dashTitle) {
        dashTitle.textContent = `Synthèse du ${dayName.toLowerCase()} ${d.getDate()} ${monthName.toLowerCase()}`;
    }
}

// Rendu du Calendrier Interactif sur l'Accueil
function renderCalendar() {
    const monthYearEl = document.getElementById("cal-month-year");
    const gridEl = document.getElementById("calendar-dates-grid");
    if (!monthYearEl || !gridEl) return;

    monthYearEl.textContent = `${MONTHS_FR[calendarDisplayMonth]} ${calendarDisplayYear}`;
    gridEl.innerHTML = "";

    // Premier jour du mois (ajustement lundi = 0)
    const firstDay = new Date(calendarDisplayYear, calendarDisplayMonth, 1);
    let startDayOfWeek = firstDay.getDay() - 1;
    if (startDayOfWeek === -1) startDayOfWeek = 6; // Dimanche devient index 6

    // Nombre de jours dans le mois
    const daysInMonth = new Date(calendarDisplayYear, calendarDisplayMonth + 1, 0).getDate();

    // Remplir les espaces vides avant le premier jour
    for (let i = 0; i < startDayOfWeek; i++) {
        const emptyCell = document.createElement("div");
        gridEl.appendChild(emptyCell);
    }

    // Récupérer toutes les dates qui ont des événements dans localStorage pour mettre un point de repère
    const store = JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}");

    for (let day = 1; day <= daysInMonth; day++) {
        const cell = document.createElement("div");
        cell.className = "calendar-day-cell";
        cell.textContent = day;

        const dateStr = `${calendarDisplayYear}-${String(calendarDisplayMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

        if (dateStr === appState.currentDate) {
            cell.classList.add("selected");
        }

        if (store[dateStr] && store[dateStr].length > 0) {
            cell.classList.add("has-events");
        }

        cell.addEventListener("click", () => {
            appState.setDate(dateStr);
        });

        gridEl.appendChild(cell);
    }
}

// ============================================================================
// 5. RENDU DU TABLEAU DE BORD ACCUEIL
// ============================================================================
function renderHomeDashboard() {
    const listEl = document.getElementById("dashboard-summary-list");
    const countEl = document.getElementById("dashboard-event-count");
    if (!listEl) return;

    const events = appState.getEventsForDate(appState.currentDate);
    const totalCount = events.length;
    const anniversaireCount = events.filter(ev => ev.type === "anniversaire").length;

    if (countEl) {
        countEl.style.display = "none"; // Masqué car affiché dans les encarts ci-dessous
    }

    listEl.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-top: 10px;">
            <div style="background: var(--bg-main); border: 2px solid var(--border-color); border-radius: var(--radius-md); padding: 24px; text-align: center; box-shadow: var(--shadow-sm);">
                <div style="font-size: 3rem; font-weight: 700; color: var(--text-main); line-height: 1.2;">${totalCount}</div>
                <div style="font-size: 1.05rem; font-weight: 600; color: var(--text-muted); margin-top: 8px;">Réservation${totalCount > 1 ? 's' : ''} au total</div>
            </div>
            <div style="background: #FDF0D5; border: 2px solid #D4A373; border-radius: var(--radius-md); padding: 24px; text-align: center; box-shadow: var(--shadow-sm);">
                <div style="font-size: 3rem; font-weight: 700; color: #5E3A1C; line-height: 1.2;">${anniversaireCount}</div>
                <div style="font-size: 1.05rem; font-weight: 600; color: #5E3A1C; margin-top: 8px;">Réservation${anniversaireCount > 1 ? 's' : ''} Anniversaire${anniversaireCount > 1 ? 's' : ''}</div>
            </div>
        </div>
    `;
}

// ============================================================================
// 6. RENDU DES PLANNINGS CLASSIQUES (GRILLES DE TABLEAU HORAIRES)
// ============================================================================
function renderClassicPlanning(filterType, tbodyId, subtitleId) {
    const tbody = document.getElementById(tbodyId);
    const subtitle = document.getElementById(subtitleId);
    if (!tbody) return;

    const events = appState.getEventsForDate(appState.currentDate, filterType);

    if (subtitle) {
        const parts = appState.currentDate.split("-");
        const d = new Date(parts[0], parts[1] - 1, parts[2]);
        subtitle.textContent = `Planning du ${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]} (${events.length} réservation${events.length > 1 ? 's' : ''})`;
    }

    tbody.innerHTML = "";

    // Générer les lignes horaires classiques (de 10h00 à 23h00 par pas de 1h ou demi-heure selon événements)
    for (let hour = CONFIG.HOURS_START; hour <= CONFIG.HOURS_END; hour++) {
        const hourStr = `${String(hour).padStart(2, '0')}:00`;
        const nextHourStr = `${String(hour + 1).padStart(2, '0')}:00`;

        // Trouver les événements qui commencent dans cette tranche horaire
        const matchingEvents = events.filter(ev => {
            const evHour = parseInt(ev.startHour.split(":")[0], 10);
            return evHour === hour;
        });

        const tr = document.createElement("tr");
        
        // Colonne Horaire
        const tdTime = document.createElement("td");
        tdTime.className = "time-cell";
        tdTime.textContent = hourStr;
        tr.appendChild(tdTime);

        // Colonne Activités
        const tdContent = document.createElement("td");
        if (matchingEvents.length === 0) {
            tdContent.innerHTML = `<span style="color: rgba(107, 94, 81, 0.4); font-size: 0.85rem; font-style: italic;">Créneau disponible</span>`;
        } else {
            matchingEvents.forEach(ev => {
                const actInfo = CONFIG.ACTIVITIES[ev.type] || CONFIG.ACTIVITIES.autre;
                const div = document.createElement("div");
                div.className = "activity-card";
                div.style.borderLeftColor = actInfo.colorBorder;
                div.style.backgroundColor = actInfo.colorBg;
                div.style.marginBottom = "8px";

                div.innerHTML = `
                    <div class="activity-info" style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                            <span class="activity-badge" style="background: var(--bg-card); border-color: ${actInfo.colorBorder}; color: ${actInfo.colorText}; font-size: 0.8rem;">${actInfo.label}</span>
                            <strong style="color: ${actInfo.colorText}; font-size: 1.05rem;">${ev.title}</strong>
                        </div>
                        <p style="margin-top: 4px; color: var(--text-main); font-weight: 500;">⏱ ${ev.startHour} à ${ev.endHour} ${ev.court ? `| 📍 <strong>${ev.court}</strong>` : ''}</p>
                        ${ev.notes ? `<p style="margin-top: 4px; font-size: 0.88rem; color: var(--text-muted); background: rgba(255,255,255,0.6); padding: 4px 8px; border-radius: 4px; display: inline-block;">💬 ${ev.notes}</p>` : ''}
                    </div>
                    <div>
                        <button class="btn-action" onclick="deleteEventItem(${ev.id})" title="Supprimer">🗑️</button>
                    </div>
                `;
                tdContent.appendChild(div);
            });
        }
        tr.appendChild(tdContent);
        tbody.appendChild(tr);
    }
}

// ============================================================================
// 7. RENDU ET GESTION DES POST-IT
// ============================================================================
function renderPostIts() {
    const containerDate = document.getElementById("postits-date-container");
    const containerGeneral = document.getElementById("postits-general-container");
    const dateLabel = document.getElementById("postit-date-label");
    const modalDateLabel = document.getElementById("postit-modal-date-label");

    if (!containerDate || !containerGeneral) return;

    const parts = appState.currentDate.split("-");
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    const formattedDate = `${DAYS_FR[d.getDay()]} ${d.getDate()} ${MONTHS_FR[d.getMonth()]}`;
    
    if (dateLabel) dateLabel.textContent = formattedDate;
    if (modalDateLabel) modalDateLabel.textContent = formattedDate;

    // Post-It pour la date sélectionnée
    const datePostIts = appState.getPostIts(appState.currentDate);
    containerDate.innerHTML = "";
    if (datePostIts.length === 0) {
        containerDate.innerHTML = `<p style="color: var(--text-muted); font-style: italic; grid-column: 1 / -1;">Aucun Post-It spécifique pour le ${formattedDate}. Cliquez sur + Nouveau Post-It pour en ajouter un.</p>`;
    } else {
        datePostIts.forEach(p => {
            containerDate.appendChild(createPostItCard(p, appState.currentDate));
        });
    }

    // Post-It généraux (permanents)
    const genPostIts = appState.getPostIts("general");
    containerGeneral.innerHTML = "";
    if (genPostIts.length === 0) {
        containerGeneral.innerHTML = `<p style="color: var(--text-muted); font-style: italic; grid-column: 1 / -1;">Aucune consigne générale.</p>`;
    } else {
        genPostIts.forEach(p => {
            containerGeneral.appendChild(createPostItCard(p, "general"));
        });
    }
}

function createPostItCard(postIt, scope) {
    const card = document.createElement("div");
    card.className = "postit-card";
    card.style.backgroundColor = postIt.color || "#FDF0D5";

    card.innerHTML = `
        <button class="postit-delete" onclick="deletePostItItem('${scope}', ${postIt.id})" title="Supprimer la note">✕</button>
        <h4>${postIt.title}</h4>
        <p>${postIt.content}</p>
    `;
    return card;
}

// ============================================================================
// 8. FENÊTRES MODALES & ACTIONS (SUPPRESSION/AJOUT)
// ============================================================================
function initModals() {
    // Initialiser les listes déroulantes d'horaires
    const startSelect = document.getElementById("event-start");
    const endSelect = document.getElementById("event-end");
    if (startSelect && endSelect) {
        for (let h = 9; h <= 23; h++) {
            for (let m of ["00", "30"]) {
                const timeStr = `${String(h).padStart(2, '0')}:${m}`;
                startSelect.innerHTML += `<option value="${timeStr}">${timeStr}</option>`;
                endSelect.innerHTML += `<option value="${timeStr}">${timeStr}</option>`;
            }
        }
        startSelect.value = "14:00";
        endSelect.value = "16:00";
    }

    // Soumission formulaire Événement
    const formEvent = document.getElementById("form-event");
    if (formEvent) {
        formEvent.addEventListener("submit", (e) => {
            e.preventDefault();
            const newEvent = {
                type: document.getElementById("event-type").value,
                title: document.getElementById("event-title").value.trim(),
                startHour: document.getElementById("event-start").value,
                endHour: document.getElementById("event-end").value,
                court: document.getElementById("event-court").value.trim(),
                notes: document.getElementById("event-notes").value.trim()
            };
            appState.addEvent(appState.currentDate, newEvent);
            closeModal("event-modal");
            formEvent.reset();
        });
    }

    // Soumission formulaire Post-It
    const formPostIt = document.getElementById("form-postit");
    if (formPostIt) {
        formPostIt.addEventListener("submit", (e) => {
            e.preventDefault();
            const scopeVal = document.getElementById("postit-scope").value;
            const targetScope = scopeVal === "date" ? appState.currentDate : "general";

            const newPostIt = {
                title: document.getElementById("postit-title").value.trim(),
                content: document.getElementById("postit-content").value.trim(),
                color: document.getElementById("postit-color").value
            };

            appState.addPostIt(targetScope, newPostIt);
            closeModal("postit-modal");
            formPostIt.reset();
        });
    }
}

function openEventModal(defaultType = null) {
    const modal = document.getElementById("event-modal");
    const typeSelect = document.getElementById("event-type");
    const titleEl = document.getElementById("modal-event-title");

    if (defaultType && typeSelect) {
        typeSelect.value = defaultType;
    } else if (typeSelect) {
        typeSelect.value = "anniversaire";
    }

    const parts = appState.currentDate.split("-");
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    if (titleEl) {
        titleEl.textContent = `Ajouter au planning du ${d.getDate()} ${MONTHS_FR[d.getMonth()]}`;
    }

    modal.style.display = "flex";
    document.getElementById("event-title").focus();
}

function openPostItModal() {
    document.getElementById("postit-modal").style.display = "flex";
    document.getElementById("postit-title").focus();
}

function closeModal(modalId) {
    document.getElementById("modalId" || modalId).style.display = "none";
}

// Global functions accessible from HTML onClick attributes
window.openEventModal = openEventModal;
window.openPostItModal = openPostItModal;
window.closeModal = closeModal;
window.switchTab = switchTab;

window.deleteEventItem = function(eventId) {
    if (confirm("Voulez-vous supprimer cette activité du planning ?")) {
        appState.deleteEvent(appState.currentDate, eventId);
    }
};

window.deletePostItItem = function(scope, postItId) {
    if (confirm("Voulez-vous supprimer ce Post-It ?")) {
        appState.deletePostIt(scope, postItId);
    }
};
