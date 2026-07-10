/**
 * Gestionnaire d'État (AppStateManager) - Organisation Space Fun Games
 * Gère la date active sélectionnée, la synchronisation entre les vues,
 * et la persistance des données dans le stockage local.
 */

class AppStateManager {
    constructor() {
        // Date active sélectionnée (par défaut aujourd'hui ou la date courante)
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        this.currentDate = `${yyyy}-${mm}-${dd}`;

        // État d'authentification
        this.isAuthenticated = sessionStorage.getItem("auth_token_sfg") === "authenticated";

        // Écouteurs d'événements pour les changements de date
        this.dateChangeListeners = [];
        this.authChangeListeners = [];

        // Initialisation de la base de données locale (si vide, on charge les données de démonstration)
        this.initStore();
    }

    initStore() {
        if (!localStorage.getItem("SFG_EVENTS_STORE")) {
            localStorage.setItem("SFG_EVENTS_STORE", JSON.stringify(typeof CONFIG !== "undefined" ? CONFIG.DEMO_DATA : {}));
        }
        if (!localStorage.getItem("SFG_POSTITS_STORE")) {
            const initialPostIts = {
                "general": [
                    { id: 1, title: "Note d'équipe", content: "Penser à vérifier les batteries des pistolets Laser Game avant le week-end.", color: "#FDF0D5" },
                    { id: 2, title: "Livraison boissons", content: "Réception de la commande sodas & jus prévue mardi après-midi.", color: "#E8F4F8" }
                ],
                "2026-07-10": [
                    { id: 3, title: "Consigne Salle 1", content: "Préparer la table VIP pour l'anniversaire de Lucas à 13h30.", color: "#FCE8E6" }
                ]
            };
            localStorage.setItem("SFG_POSTITS_STORE", JSON.stringify(initialPostIts));
        }
    }

    // Gestion de la date active
    setDate(newDateStr) {
        if (this.currentDate !== newDateStr) {
            this.currentDate = newDateStr;
            this.notifyDateChange();
        }
    }

    getDate() {
        return this.currentDate;
    }

    onDateChange(callback) {
        this.dateChangeListeners.push(callback);
    }

    notifyDateChange() {
        this.dateChangeListeners.forEach(cb => cb(this.currentDate));
    }

    // Gestion de l'authentification
    setAuthenticated(status) {
        this.isAuthenticated = status;
        if (status) {
            sessionStorage.setItem("auth_token_sfg", "authenticated");
        } else {
            sessionStorage.removeItem("auth_token_sfg");
        }
        this.notifyAuthChange();
    }

    onAuthChange(callback) {
        this.authChangeListeners.push(callback);
    }

    notifyAuthChange() {
        this.authChangeListeners.forEach(cb => cb(this.isAuthenticated));
    }

    // Accès et modification des événements de planning
    getEventsForDate(dateStr, filterType = null) {
        const store = JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}");
        const events = store[dateStr] || [];
        if (filterType) {
            return events.filter(ev => ev.type === filterType);
        }
        return events.sort((a, b) => a.startHour.localeCompare(b.startHour));
    }

    addEvent(dateStr, eventObj) {
        const store = JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}");
        if (!store[dateStr]) {
            store[dateStr] = [];
        }
        // Attribuer un ID unique
        eventObj.id = Date.now();
        store[dateStr].push(eventObj);
        localStorage.setItem("SFG_EVENTS_STORE", JSON.stringify(store));
        this.notifyDateChange(); // Rafraîchir les vues
        return eventObj;
    }

    deleteEvent(dateStr, eventId) {
        const store = JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}");
        if (store[dateStr]) {
            store[dateStr] = store[dateStr].filter(ev => ev.id !== eventId);
            localStorage.setItem("SFG_EVENTS_STORE", JSON.stringify(store));
            this.notifyDateChange();
        }
    }

    // Accès et modification des Post-Its
    getPostIts(scope = "general") {
        // scope peut être "general" ou une date YYYY-MM-DD
        const store = JSON.parse(localStorage.getItem("SFG_POSTITS_STORE") || "{}");
        return store[scope] || [];
    }

    addPostIt(scope, postItObj) {
        const store = JSON.parse(localStorage.getItem("SFG_POSTITS_STORE") || "{}");
        if (!store[scope]) {
            store[scope] = [];
        }
        postItObj.id = Date.now();
        store[scope].push(postItObj);
        localStorage.setItem("SFG_POSTITS_STORE", JSON.stringify(store));
        this.notifyDateChange();
        return postItObj;
    }

    deletePostIt(scope, postItId) {
        const store = JSON.parse(localStorage.getItem("SFG_POSTITS_STORE") || "{}");
        if (store[scope]) {
            store[scope] = store[scope].filter(p => p.id !== postItId);
            localStorage.setItem("SFG_POSTITS_STORE", JSON.stringify(store));
            this.notifyDateChange();
        }
    }
}

// Instance globale singleton
const appState = new AppStateManager();

if (typeof module !== "undefined") {
    module.exports = appState;
}
