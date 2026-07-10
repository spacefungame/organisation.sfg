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
        this.isAuthenticated = this.hasSessionStorage() ? (sessionStorage.getItem("auth_token_sfg") === "authenticated") : false;

        // Écouteurs d'événements pour les changements de date
        this.dateChangeListeners = [];
        this.authChangeListeners = [];

        // Initialisation de la base de données locale (si vide, on charge les données de démonstration)
        this.initStore();
    }

    hasLocalStorage() {
        return typeof localStorage !== "undefined" && typeof localStorage.getItem === "function";
    }

    hasSessionStorage() {
        return typeof sessionStorage !== "undefined" && typeof sessionStorage.getItem === "function";
    }

    initStore() {
        if (!this.hasLocalStorage()) return;
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
        if (this.hasSessionStorage()) {
            if (status) {
                sessionStorage.setItem("auth_token_sfg", "authenticated");
            } else {
                sessionStorage.removeItem("auth_token_sfg");
            }
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
        const store = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}") : {};
        const events = store[dateStr] || [];
        if (filterType) {
            return events.filter(ev => ev.type === filterType);
        }
        return events.sort((a, b) => a.startHour.localeCompare(b.startHour));
    }

    addEvent(dateStr, eventObj) {
        const store = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}") : {};
        if (!store[dateStr]) {
            store[dateStr] = [];
        }
        // Attribuer un ID unique
        eventObj.id = Date.now();
        store[dateStr].push(eventObj);
        if (this.hasLocalStorage()) localStorage.setItem("SFG_EVENTS_STORE", JSON.stringify(store));
        this.notifyDateChange(); // Rafraîchir les vues
        return eventObj;
    }

    deleteEvent(dateStr, eventId) {
        const store = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_EVENTS_STORE") || "{}") : {};
        if (store[dateStr]) {
            store[dateStr] = store[dateStr].filter(ev => ev.id !== eventId);
            if (this.hasLocalStorage()) localStorage.setItem("SFG_EVENTS_STORE", JSON.stringify(store));
            this.notifyDateChange();
        }
    }

    // Accès et modification des Post-Its
    getPostIts(scope = "general") {
        // scope peut être "general" ou une date YYYY-MM-DD
        const store = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_POSTITS_STORE") || "{}") : {};
        return store[scope] || [];
    }

    addPostIt(scope, postItObj) {
        const store = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_POSTITS_STORE") || "{}") : {};
        if (!store[scope]) {
            store[scope] = [];
        }
        postItObj.id = Date.now();
        store[scope].push(postItObj);
        if (this.hasLocalStorage()) localStorage.setItem("SFG_POSTITS_STORE", JSON.stringify(store));
        this.notifyDateChange();
        return postItObj;
    }

    deletePostIt(scope, postItId) {
        const store = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_POSTITS_STORE") || "{}") : {};
        if (store[scope]) {
            store[scope] = store[scope].filter(p => p.id !== postItId);
            if (this.hasLocalStorage()) localStorage.setItem("SFG_POSTITS_STORE", JSON.stringify(store));
            this.notifyDateChange();
        }
    }

    // =========================================================================
    // GESTION ET SYNCHRONISATION DE L'API QWEEKLE
    // =========================================================================
    getQweekleReservationsForDate(dateStr) {
        // 1. Vérifier si des données Qweekle synchronisées ou en cache sont disponibles pour cette date
        const cachedStore = this.hasLocalStorage() ? JSON.parse(localStorage.getItem("SFG_QWEEKLE_STORE") || "{}") : {};
        if (cachedStore[dateStr] && cachedStore[dateStr].length > 0) {
            return cachedStore[dateStr];
        }
        // 2. Repli vers les données structurées officielles de la configuration
        if (typeof CONFIG !== "undefined" && CONFIG.QWEEKLE_RESERVATIONS_DATA && CONFIG.QWEEKLE_RESERVATIONS_DATA[dateStr]) {
            return CONFIG.QWEEKLE_RESERVATIONS_DATA[dateStr];
        }
        return [];
    }

    async fetchAndSyncQweekleReservations(dateStr) {
        if (typeof CONFIG === "undefined" || !CONFIG.QWEEKLE_API_KEY) {
            return { status: "fallback", data: this.getQweekleReservationsForDate(dateStr) };
        }

        const url = `${CONFIG.QWEEKLE_API_URL}/bookings?filter[agenda.starts_between]=${dateStr}T00:00:00,${dateStr}T23:59:59&withOrder=true`;
        try {
            const response = await fetch(url, {
                method: "GET",
                headers: {
                    "Authorization": `Bearer ${CONFIG.QWEEKLE_API_KEY}`,
                    "Accept": "application/json"
                }
            });

            if (!response.ok) {
                throw new Error(`Erreur HTTP Qweekle (${response.status})`);
            }

            const json = await response.json();
            const parsedList = this.parseRawQweekleBookings(json.data || [], dateStr);
            
            // Mettre en cache dans le stockage local
            if (this.hasLocalStorage()) {
                const cachedStore = JSON.parse(localStorage.getItem("SFG_QWEEKLE_STORE") || "{}");
                cachedStore[dateStr] = parsedList;
                localStorage.setItem("SFG_QWEEKLE_STORE", JSON.stringify(cachedStore));
            }

            return { status: "success", data: parsedList };
        } catch (error) {
            console.warn("⚠️ Mode démo activé pour Qweekle (ou erreur réseau/CORS) :", error.message);
            return { status: "fallback", data: this.getQweekleReservationsForDate(dateStr) };
        }
    }

    parseRawQweekleBookings(rawBookings, dateStr) {
        // Transformation des données brutes Qweekle vers notre format complet multi-occurrences
        const bookingsMap = {};

        rawBookings.forEach(item => {
            const orderId = item.sale_item_id || item.id;
            if (!bookingsMap[orderId]) {
                // Déduire les informations client
                let nom = "Client";
                let prenom = "Qweekle";
                let societe = "";
                
                if (item.client) {
                    nom = (item.client.lastname || item.client.society || "Client").toUpperCase();
                    prenom = item.client.firstname || "";
                    societe = item.client.society || "";
                } else if (item.order && item.order.client) {
                    nom = (item.order.client.lastname || item.order.client.society || "Client").toUpperCase();
                    prenom = item.order.client.firstname || "";
                    societe = item.order.client.society || "";
                }

                // Déduire le nom du pack
                let nomPack = item.activity || "Réservation Qweekle";
                if (item.order && item.order.label) {
                    nomPack = item.order.label;
                } else if (item.agenda && item.agenda.short_description) {
                    nomPack = item.agenda.short_description;
                }

                // Heures d'arrivée et de départ globales par défaut pour ce dossier
                let heureArrivee = "10:00";
                let heureDepart = "12:00";
                if (item.agenda) {
                    if (item.agenda.convoc_start_at) {
                        heureArrivee = new Date(item.agenda.convoc_start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    } else if (item.agenda.start_at) {
                        heureArrivee = new Date(item.agenda.start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    }
                    if (item.agenda.convoc_end_at) {
                        heureDepart = new Date(item.agenda.convoc_end_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    } else if (item.agenda.end_at) {
                        heureDepart = new Date(item.agenda.end_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    }
                }

                const detectedCats = this.detectQweekleCategories(nom, societe, nomPack, item.activity);
                const enfantInfo = this.extractBirthdayChildInfo(item, detectedCats);

                bookingsMap[orderId] = {
                    id: `QW-${item.id || orderId}`,
                    nom: nom,
                    prenom: prenom,
                    societe: societe,
                    heureArrivee: heureArrivee,
                    heureDepart: heureDepart,
                    nbPersonnes: item.qty || (item.agenda ? item.agenda.qty_pax : 1),
                    nomPack: nomPack,
                    typeActivite: item.type || "Activité",
                    categories: detectedCats,
                    enfantAnniversaire: enfantInfo,
                    activites: [],
                    options: []
                };
            }

            // Si l'information anniversaire enfant n'a pas été trouvée sur la première occurrence, tenter sur la courante
            if (!bookingsMap[orderId].enfantAnniversaire && bookingsMap[orderId].categories.includes("anniversaire")) {
                bookingsMap[orderId].enfantAnniversaire = this.extractBirthdayChildInfo(item, bookingsMap[orderId].categories);
            }

            // Ajouter chaque activité (occurrence) du dossier
            let hDebut = "10:00";
            let hFin = "11:00";
            let actName = item.activity || "Activité";
            let actZone = item.agenda && item.agenda.location ? (item.agenda.location.label || item.agenda.location) : "Zone Générale";
            
            if (item.agenda) {
                if (item.agenda.start_at) {
                    hDebut = new Date(item.agenda.start_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                }
                if (item.agenda.end_at) {
                    hFin = new Date(item.agenda.end_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                }
            }

            bookingsMap[orderId].activites.push({
                heureDebut: hDebut,
                heureFin: hFin,
                nom: actName,
                zone: typeof actZone === "string" ? actZone : (actZone.label || "Salle / Arène")
            });

            // Extraire les options/produits supplémentaires si présents
            if (item.order && item.order.items) {
                item.order.items.forEach(oi => {
                    if (oi.label && !bookingsMap[orderId].options.includes(oi.label)) {
                        bookingsMap[orderId].options.push(oi.label);
                    }
                });
            }
        });

        return Object.values(bookingsMap);
    }

    extractBirthdayChildInfo(item, categories) {
        if (!categories.includes("anniversaire")) return null;

        // 1. Chercher directement un sous-compte dans l'objet de réservation / commande
        const sc = item.sub_client || item.child || item.beneficiary || (item.order && (item.order.sub_client || item.order.beneficiary || item.order.child));
        if (sc) {
            let age = sc.age || sc.age_years || "";
            if (!age && sc.birthdate) {
                const bYear = new Date(sc.birthdate).getFullYear();
                if (!isNaN(bYear)) age = new Date().getFullYear() - bYear;
            }
            return {
                prenom: sc.firstname || sc.prenom || sc.name || "Enfant fêté",
                age: age || "Âge non précisé",
                dateNaissance: sc.birthdate || sc.date_naissance || null,
                sousCompteId: sc.id || sc.client_id || sc.sub_client_id || null
            };
        }

        // 2. Chercher dans la liste des sous-comptes du client principal (sub_clients / children)
        const parentClient = item.client || (item.order && item.order.client);
        if (parentClient && (parentClient.sub_clients || parentClient.children || parentClient.contacts)) {
            const list = parentClient.sub_clients || parentClient.children || parentClient.contacts;
            if (Array.isArray(list) && list.length > 0) {
                const firstChild = list[0];
                let age = firstChild.age || "";
                if (!age && firstChild.birthdate) {
                    const bYear = new Date(firstChild.birthdate).getFullYear();
                    if (!isNaN(bYear)) age = new Date().getFullYear() - bYear;
                }
                return {
                    prenom: firstChild.firstname || firstChild.prenom || firstChild.name || "Enfant",
                    age: age || "10",
                    dateNaissance: firstChild.birthdate || firstChild.date_naissance || null,
                    sousCompteId: firstChild.id || firstChild.client_id || null
                };
            }
        }

        // 3. Extraction depuis les métadonnées, notes ou libellés
        const textToSearch = `${item.order && item.order.notes ? item.order.notes : ''} ${item.activity || ''} ${item.agenda && item.agenda.title ? item.agenda.title : ''}`;
        const matchAge = textToSearch.match(/\b(\d{1,2})\s*ans?\b/i);
        const matchName = textToSearch.match(/Anniversaire\s+([A-ZÉÈÀa-zéèà-]+)/i);
        if (matchName || matchAge) {
            return {
                prenom: matchName ? matchName[1] : "Enfant fêté",
                age: matchAge ? parseInt(matchAge[1], 10) : "Non précisé",
                dateNaissance: null,
                sousCompteId: null
            };
        }

        return null;
    }

    detectQweekleCategories(nom, societe, pack, activity) {
        const fullStr = `${nom} ${societe} ${pack} ${activity}`.toLowerCase();
        const cats = [];
        if (fullStr.includes("enfant") || fullStr.includes("7-12") || fullStr.includes("junior")) cats.push("enfant");
        if (fullStr.includes("ado") || fullStr.includes("13-18") || fullStr.includes("teen")) cats.push("ado");
        if (fullStr.includes("adulte") || fullStr.includes("+18") || fullStr.includes("18+") || fullStr.includes("senior")) cats.push("adulte");
        if (fullStr.includes("anniversaire") || fullStr.includes("birthday")) cats.push("anniversaire");
        if (fullStr.includes("team") || fullStr.includes("challenge") || fullStr.includes("entreprise") || fullStr.includes("collaborateur") || fullStr.includes("séminaire")) cats.push("team building");
        if (fullStr.includes("évènement") || fullStr.includes("evenement") || fullStr.includes("soirée") || fullStr.includes("privé") || fullStr.includes("gala") || fullStr.includes("cocktail")) cats.push("évènement adulte");
        if (fullStr.includes("asbl") || fullStr.includes("association") || fullStr.includes("école") || fullStr.includes("ecole") || fullStr.includes("centre") || fullStr.includes("jeunesse")) cats.push("asbl");
        
        if (cats.length === 0) {
            cats.push("adulte"); // Par défaut si non spécifié
        }
        return cats;
    }
}

// Instance globale singleton
const appState = new AppStateManager();

if (typeof module !== "undefined") {
    module.exports = appState;
}
