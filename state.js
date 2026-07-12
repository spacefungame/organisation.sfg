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
        if (cachedStore[dateStr] && Array.isArray(cachedStore[dateStr])) {
            // Ne pas utiliser un cache démo ancien (Marc Dupont QW-90102) si la base Supabase est active
            const isDemoCache = cachedStore[dateStr].some(r => r && (r.id === "QW-90102" || r.id === "QW-90145" || r.nom === "DUPONT"));
            if (!isDemoCache || typeof CONFIG === "undefined" || !CONFIG.SUPABASE_URL) {
                return cachedStore[dateStr];
            }
        }
        // 2. Repli vers les données structurées officielles de la configuration uniquement si Supabase n'est pas configuré
        if (typeof CONFIG !== "undefined" && !CONFIG.SUPABASE_URL && CONFIG.QWEEKLE_RESERVATIONS_DATA && CONFIG.QWEEKLE_RESERVATIONS_DATA[dateStr]) {
            return CONFIG.QWEEKLE_RESERVATIONS_DATA[dateStr];
        }
        return [];
    }

    async fetchAndSyncQweekleReservations(dateStr) {
        if (typeof CONFIG === "undefined") {
            return { status: "fallback", data: this.getQweekleReservationsForDate(dateStr) };
        }

        // 1. Tenter en priorité la base de production Live (Webhooks Qweekle -> Supabase booking_activities)
        if (CONFIG.SUPABASE_URL && CONFIG.SUPABASE_KEY) {
            try {
                const nextDate = new Date(dateStr);
                nextDate.setDate(nextDate.getDate() + 1);
                const nextDateStr = nextDate.toISOString().split("T")[0];
                const supaUrl = `${CONFIG.SUPABASE_URL}/rest/v1/booking_activities?select=*&start_at=gte.${dateStr}T00:00:00Z&start_at=lt.${nextDateStr}T23:59:59Z&order=order_id,pack_step.asc`;
                
                const response = await fetch(supaUrl, {
                    method: "GET",
                    headers: {
                        "apikey": CONFIG.SUPABASE_KEY,
                        "Authorization": `Bearer ${CONFIG.SUPABASE_KEY}`,
                        "Accept": "application/json"
                    }
                });

                if (response.ok) {
                    const rows = await response.json();
                    const parsedList = this.parseSupabaseActivitiesToBookings(rows || [], dateStr);
                    
                    if (this.hasLocalStorage()) {
                        const cachedStore = JSON.parse(localStorage.getItem("SFG_QWEEKLE_STORE") || "{}");
                        cachedStore[dateStr] = parsedList;
                        localStorage.setItem("SFG_QWEEKLE_STORE", JSON.stringify(cachedStore));
                    }
                    return { status: "success", data: parsedList, source: "supabase" };
                }
            } catch (error) {
                console.warn("⚠️ Erreur de synchronisation Supabase Live :", error.message);
            }
        }

        // 2. Tenter en direct via l'API REST officielle de Qweekle si disponible
        if (CONFIG.QWEEKLE_API_KEY && CONFIG.QWEEKLE_API_URL) {
            const url = `${CONFIG.QWEEKLE_API_URL}/bookings?filter[agenda.starts_between]=${dateStr}T00:00:00,${dateStr}T23:59:59&withOrder=true`;
            try {
                const response = await fetch(url, {
                    method: "GET",
                    headers: {
                        "Authorization": `Bearer ${CONFIG.QWEEKLE_API_KEY}`,
                        "Accept": "application/json"
                    }
                });

                if (response.ok) {
                    const json = await response.json();
                    const parsedList = this.parseRawQweekleBookings(json.data || [], dateStr);
                    if (this.hasLocalStorage()) {
                        const cachedStore = JSON.parse(localStorage.getItem("SFG_QWEEKLE_STORE") || "{}");
                        cachedStore[dateStr] = parsedList;
                        localStorage.setItem("SFG_QWEEKLE_STORE", JSON.stringify(cachedStore));
                    }
                    return { status: "success", data: parsedList, source: "qweekle_rest" };
                }
            } catch (error) {
                console.warn("⚠️ Mode démo activé pour Qweekle (ou erreur réseau/CORS) :", error.message);
            }
        }

        return { status: "fallback", data: this.getQweekleReservationsForDate(dateStr) };
    }

    parseSupabaseActivitiesToBookings(rows, dateStr) {
        // Filtrer par date locale du dossier (Belgique / fuseau local)
        const filteredRows = rows.filter(r => {
            if (!r.start_at) return false;
            const rowDate = new Date(r.start_at).toLocaleDateString("en-CA", { timeZone: "Europe/Brussels" });
            return rowDate === dateStr;
        });

        // Regrouper par order_id ou par identifiant unique de réservation
        const groups = {};
        filteredRows.forEach(r => {
            const oid = r.order_id || r.qweekle_booking_id || r.id;
            if (!groups[oid]) groups[oid] = [];
            groups[oid].push(r);
        });

        const bookings = [];
        Object.keys(groups).forEach(oid => {
            const group = groups[oid];
            // Tri chronologique des activités au sein du dossier
            group.sort((a, b) => new Date(a.start_at) - new Date(b.start_at));

            // 1. Informations Client
            let nom = "Client Inconnu";
            let prenom = "";
            let societe = "";

            for (const act of group) {
                const fn = act.client_firstname || act.raw_payload?.client?.firstname || "";
                const ln = act.client_lastname || act.raw_payload?.client?.lastname || "";
                const soc = act.raw_payload?.client?.society || "";
                const clientType = act.raw_payload?.client?.type || "";

                if (fn || ln || soc) {
                    prenom = fn;
                    if (clientType === "association" || clientType === "entreprise" || soc) {
                        societe = soc;
                        nom = (ln ? `${ln} (${soc})` : soc).toUpperCase();
                    } else {
                        nom = ln.toUpperCase() || "CLIENT";
                    }
                    break;
                }
            }
            if (nom === "Client Inconnu") {
                const email = group.find(a => a.client_email || a.raw_payload?.client?.email);
                if (email) {
                    const em = email.client_email || email.raw_payload?.client?.email;
                    nom = em.split("@")[0].toUpperCase();
                } else {
                    nom = `CLIENT (${oid.slice(-8)})`;
                }
            }

            // 2. Plage horaire globale (arrivée et départ)
            const earliestDate = new Date(group[0].start_at);
            let maxEndMs = earliestDate.getTime();
            group.forEach(act => {
                const sMs = new Date(act.start_at).getTime();
                const eMs = act.end_at ? new Date(act.end_at).getTime() : sMs + (Number(act.duration) || 60) * 60000;
                if (eMs > maxEndMs) maxEndMs = eMs;
            });
            const latestDate = new Date(maxEndMs);

            const heureArrivee = earliestDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const heureDepart = latestDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            // 3. Nombre de personnes
            const nbPersonnes = Math.max(...group.map(a => Number(a.qty) || 0), 1);

            // 4. Activités détaillées (si plusieurs occurrences, on les affiche toutes)
            const activites = group.map(act => {
                const s = new Date(act.start_at);
                const e = act.end_at ? new Date(act.end_at) : new Date(s.getTime() + (Number(act.duration) || 60) * 60000);
                const actQty = Number(act.qty) || Number(act.raw_payload?.client?.qty) || Number(act.raw_payload?.qty) || nbPersonnes || 1;
                return {
                    heureDebut: s.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    heureFin: e.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    nom: act.label || "Activité Qweekle",
                    zone: act.location || act.category || "Zone Générale",
                    nbPersonnes: actQty
                };
            });

            // 5. Nom du pack (en priorité depuis le titre exact de commande/produit dans Qweekle, sinon calculé depuis les activités)
            let nomPack = "";
            const orderPacks = new Set();
            group.forEach(act => {
                const rp = act.raw_payload || {};
                const itemLabel = rp.order_item?.label || rp.product?.label || rp.pack_label || rp.activity?.product_label || act.pack_label || act.product_label;
                if (itemLabel && typeof itemLabel === 'string' && itemLabel.trim() && !itemLabel.toLowerCase().includes("accueil") && !itemLabel.toLowerCase().includes("table réservée")) {
                    orderPacks.add(itemLabel.trim());
                }
            });
            if (orderPacks.size > 0) {
                // Si on n'a trouvé qu'un seul label dans order_item mais que le groupe a plusieurs types d'activités distinctes (ex: Team Games et Laser Game), on enrichit
                const distinctActTypes = new Set(group.map(a => (a.label || a.nom || "").replace(/▶\s*/g, '').trim()).filter(n => !n.toLowerCase().includes("accueil") && !n.toLowerCase().includes("table réservée")));
                if (distinctActTypes.size > orderPacks.size && orderPacks.size === 1) {
                    nomPack = this.computePackLabelFromActivities(group, Array.from(orderPacks).join(" + "));
                } else {
                    nomPack = Array.from(orderPacks).join(" + ");
                }
            } else {
                // Tenter de prendre le label parent du panier si pas d'order_item spécifique
                const parentOrderLabel = group[0]?.raw_payload?.order?.label || group[0]?.raw_payload?.order?.product_label || group[0]?.raw_payload?.order?.name || "";
                nomPack = this.computePackLabelFromActivities(group, parentOrderLabel);
            }

            // 6. Catégories détectées
            const allTextForCats = `${nom} ${societe} ${nomPack} ${group.map(a => `${a.label || ''} ${a.category || ''} ${a.subcategory || ''} ${a.raw_payload?.client?.type || ''}`).join(" ")}`;
            const categories = this.detectQweekleCategories(nom, societe, nomPack, allTextForCats);

            // 7. Options supplémentaires choisies (produits / gâteaux / options)
            const options = [];
            group.forEach(act => {
                const catLower = (act.category || "").toLowerCase();
                const lblLower = (act.label || "").toLowerCase();
                if (catLower.includes("option") || catLower.includes("produit") || lblLower.includes("gâteau") || lblLower.includes("gateau") || lblLower.includes("kidibul") || lblLower.includes("brownie") || lblLower.includes("donut") || lblLower.includes("bonbon") || lblLower.includes("chips") || lblLower.includes("granit") || lblLower.includes("crêpe") || lblLower.includes("crepe")) {
                    if (!options.includes(act.label)) options.push(act.label);
                }
                if (act.raw_payload?.order?.items && Array.isArray(act.raw_payload.order.items)) {
                    act.raw_payload.order.items.forEach(oi => {
                        if (oi.label && !options.includes(oi.label)) options.push(oi.label);
                    });
                }
            });

            // 8. Sous-compte enfant anniversaire (si réservation anniversaire)
            let enfantAnniversaire = null;
            if (categories.includes("anniversaire")) {
                const allSubclients = [];
                group.forEach(act => {
                    if (act.raw_payload && Array.isArray(act.raw_payload.subclients)) {
                        act.raw_payload.subclients.forEach(sc => allSubclients.push(sc));
                    } else if (act.raw_payload?.client?.sub_clients && Array.isArray(act.raw_payload.client.sub_clients)) {
                        act.raw_payload.client.sub_clients.forEach(sc => allSubclients.push(sc));
                    }
                });

                if (allSubclients.length > 0) {
                    const targetDateObj = new Date(dateStr);
                    let bestChild = allSubclients[0];
                    let bestDist = 9999;

                    allSubclients.forEach(sc => {
                        if (sc.birthday_at || sc.birthdate) {
                            const bDate = new Date(sc.birthday_at || sc.birthdate);
                            const dist = Math.abs((bDate.getMonth() - targetDateObj.getMonth()) * 30 + (bDate.getDate() - targetDateObj.getDate()));
                            if (dist < bestDist) {
                                bestDist = dist;
                                bestChild = sc;
                            }
                        }
                    });

                    let age = bestChild.age || "";
                    if (!age && (bestChild.birthday_at || bestChild.birthdate)) {
                        const bYear = new Date(bestChild.birthday_at || bestChild.birthdate).getFullYear();
                        if (!isNaN(bYear)) age = targetDateObj.getFullYear() - bYear;
                    }

                    enfantAnniversaire = {
                        prenom: bestChild.firstname || bestChild.prenom || bestChild.lastname || "Enfant fêté",
                        age: age ? Number(age) : "Non précisé",
                        dateNaissance: bestChild.birthday_at || bestChild.birthdate || null,
                        sousCompteId: bestChild.id || null
                    };
                } else {
                    for (const act of group) {
                        const ext = this.extractBirthdayChildInfo(act.raw_payload || act, categories);
                        if (ext) {
                            enfantAnniversaire = ext;
                            break;
                        }
                    }
                }
            }

            bookings.push({
                id: `QW-${oid}`,
                nom,
                prenom,
                societe,
                heureArrivee,
                heureDepart,
                nbPersonnes,
                nomPack,
                typeActivite: group[0].category || "Activité Qweekle",
                categories,
                enfantAnniversaire,
                activites,
                options
            });
        });

        // Trier les réservations par heure d'arrivée chronologique puis regrouper les doublons (adulte + enfant même heure)
        bookings.sort((a, b) => a.heureArrivee.localeCompare(b.heureArrivee));
        return this.mergeDuplicateClientBookings(bookings);
    }

    computePackLabelFromActivities(acts, fallbackPack = "") {
        if (!acts || !acts.length) return fallbackPack || "Réservation Qweekle";

        // Filtrer les activités d'accueil ou de table
        const mainActs = acts.filter(a => {
            const l = (a.nom || a.label || "").toLowerCase();
            return !l.includes("accueil") && !l.includes("table réservée");
        });

        if (!mainActs.length) {
            return fallbackPack || (acts[0].nom || acts[0].label || "Réservation Qweekle");
        }

        // Vérifier si toutes les activités principales sont du Laser Game
        const allLaser = mainActs.every(a => {
            const l = (a.nom || a.label || "").toLowerCase();
            return l.includes("laser");
        });

        if (allLaser) {
            let totalMin = 0;
            mainActs.forEach(a => {
                let dur = Number(a.duration);
                if (!dur || isNaN(dur)) {
                    const [sH, sM] = (a.heureDebut || "00:00").split(":").map(Number);
                    const [eH, eM] = (a.heureFin || "00:00").split(":").map(Number);
                    dur = (eH * 60 + eM) - (sH * 60 + sM);
                }
                totalMin += (dur > 0 ? dur : 20);
            });

            if (totalMin > 0) {
                const firstLabel = mainActs[0].nom || mainActs[0].label || fallbackPack || "";
                if (firstLabel.toLowerCase().includes("7-12") || firstLabel.toLowerCase().includes("enfant") || (fallbackPack || "").toLowerCase().includes("enfant")) {
                    return `${totalMin} Min Laser Games | Enfant 7-12ans`;
                } else if (firstLabel.toLowerCase().includes("adulte") || firstLabel.toLowerCase().includes("+18") || (fallbackPack || "").toLowerCase().includes("adulte")) {
                    return `${totalMin} Min Laser Games | Adulte +18ans`;
                } else {
                    return `${totalMin} Min Laser Games`;
                }
            }
        }

        // Si ce n'est pas uniquement du Laser Game (ex: 1 Heure de Team Games + 20 Min Laser Game 7-12 ans)
        // Récupérer les noms distincts
        const distinctNames = [];
        mainActs.forEach(a => {
            let n = (a.nom || a.label || "").replace(/▶\s*/g, '').trim();
            if (n && !distinctNames.includes(n)) {
                distinctNames.push(n);
            }
        });

        if (distinctNames.length > 0) {
            return distinctNames.join(" + ");
        }

        return fallbackPack || "Réservation Qweekle";
    }

    splitBookingsBySessions(list) {
        if (!list || !list.length) return [];
        const splitList = [];

        list.forEach(booking => {
            if (!booking.activites || booking.activites.length <= 1) {
                splitList.push(booking);
                return;
            }

            // Trier les activités par heure chronologique
            const sortedActs = [...booking.activites].sort((a, b) => (a.heureDebut || "").localeCompare(b.heureDebut || ""));
            const sessions = [];
            let currentSession = [sortedActs[0]];

            for (let i = 1; i < sortedActs.length; i++) {
                const prev = currentSession[currentSession.length - 1];
                const curr = sortedActs[i];

                const [pEndH, pEndM] = (prev.heureFin || "00:00").split(":").map(Number);
                const prevEndMin = pEndH * 60 + pEndM;

                const [cStartH, cStartM] = (curr.heureDebut || "00:00").split(":").map(Number);
                const currStartMin = cStartH * 60 + cStartM;

                const gap = currStartMin - prevEndMin;
                const isNewAccueil = (curr.nom || "").toLowerCase().includes("accueil") && gap >= 30;

                // Si l'écart entre la fin de l'activité précédente et le début de la nouvelle est >= 60 min,
                // OU si une nouvelle activité "Accueil" démarre avec au moins 30 min d'écart, c'est un nouveau groupe / nouvelle arrivée !
                if (gap >= 60 || isNewAccueil) {
                    sessions.push(currentSession);
                    currentSession = [curr];
                } else {
                    currentSession.push(curr);
                }
            }
            sessions.push(currentSession);

            if (sessions.length === 1) {
                const newPack = this.computePackLabelFromActivities(booking.activites, booking.nomPack);
                splitList.push({
                    ...booking,
                    nomPack: newPack || booking.nomPack
                });
            } else {
                // Plusieurs sessions distinctes sur la journée sous le même nom
                sessions.forEach((sessActs, idx) => {
                    const firstAct = sessActs[0];
                    const lastAct = sessActs[sessActs.length - 1];
                    const hArr = firstAct.heureDebut || booking.heureArrivee;
                    const hDep = lastAct.heureFin || booking.heureDepart;

                    const sessNbPers = Math.max(...sessActs.map(a => Number(a.nbPersonnes) || 0), Number(booking.nbPersonnes) || 1);
                    const sessionPack = this.computePackLabelFromActivities(sessActs, booking.nomPack);

                    splitList.push({
                        ...booking,
                        id: `${booking.id || 'QW'}-S${idx + 1}`,
                        heureArrivee: hArr,
                        heureDepart: hDep,
                        nbPersonnes: sessNbPers,
                        nomPack: sessionPack || `${booking.nomPack} (Session ${idx + 1})`,
                        activites: sessActs
                    });
                });
            }
        });

        return splitList;
    }

    mergeDuplicateClientBookings(list) {
        if (!list || !list.length) return [];

        // 1. D'abord, séparer en sous-réservations distinctes les dossiers qui ont plusieurs arrivées/sessions dans la journée (écart >= 60 min ou nouvel Accueil > 30 min)
        const splitList = this.splitBookingsBySessions(list);

        // 2. Trier par heure d'arrivée d'abord
        const sorted = [...splitList].sort((a, b) => (a.heureArrivee || "00:00").localeCompare(b.heureArrivee || "00:00"));
        const merged = [];

        sorted.forEach(booking => {
            const cleanNom = (booking.nom || "CLIENT").trim().toUpperCase();
            
            // Chercher si une réservation existante dans merged a le même nom et une heure d'arrivée proche (<= 30 min)
            let match = null;
            if (cleanNom !== "CLIENT" && !cleanNom.startsWith("CLIENT (")) {
                const [bH, bM] = (booking.heureArrivee || "00:00").split(":").map(Number);
                const bookingMin = bH * 60 + bM;

                for (const existing of merged) {
                    const existingNom = (existing.nom || "").trim().toUpperCase();
                    if (existingNom === cleanNom) {
                        const [eH, eM] = (existing.heureArrivee || "00:00").split(":").map(Number);
                        const existingMin = eH * 60 + eM;
                        if (Math.abs(bookingMin - existingMin) <= 30) {
                            match = existing;
                            break;
                        }
                    }
                }
            }

            if (!match) {
                // Pas de doublon trouvé, on ajoute une copie propre de la réservation
                merged.push({
                    ...booking,
                    categories: Array.isArray(booking.categories) ? [...booking.categories] : [],
                    activites: Array.isArray(booking.activites) ? booking.activites.map(a => ({ ...a })) : [],
                    options: Array.isArray(booking.options) ? [...booking.options] : []
                });
            } else {
                // Fusionner avec la réservation existante (match) !
                // 1. Fusion des IDs
                const existingIds = match.id.split(" + ");
                if (!existingIds.includes(booking.id)) {
                    match.id = `${match.id} + ${booking.id}`;
                }

                // 2. Fusion des Prénoms
                const prenomsSet = new Set(match.prenom ? match.prenom.split(" & ").map(p => p.trim()).filter(Boolean) : []);
                if (booking.prenom) {
                    booking.prenom.split(" & ").forEach(p => {
                        const cp = p.trim();
                        if (cp) prenomsSet.add(cp);
                    });
                }
                match.prenom = Array.from(prenomsSet).join(" & ");

                // 3. Fusion des Sociétés
                const socSet = new Set(match.societe ? match.societe.split(" / ").map(s => s.trim()).filter(Boolean) : []);
                if (booking.societe) {
                    booking.societe.split(" / ").forEach(s => {
                        const cs = s.trim();
                        if (cs) socSet.add(cs);
                    });
                }
                match.societe = Array.from(socSet).join(" / ");

                // 4. Heure d'arrivée = le plus tôt, Heure de départ = le plus tard
                if (booking.heureArrivee < match.heureArrivee) {
                    match.heureArrivee = booking.heureArrivee;
                }
                if (booking.heureDepart > match.heureDepart) {
                    match.heureDepart = booking.heureDepart;
                }

                // 5. Somme des personnes
                match.nbPersonnes = (Number(match.nbPersonnes) || 0) + (Number(booking.nbPersonnes) || 0);

                // 6. Fusion des Catégories (badges ex: enfant + adulte)
                const catSet = new Set(match.categories || []);
                if (Array.isArray(booking.categories)) {
                    booking.categories.forEach(c => catSet.add(c));
                }
                match.categories = Array.from(catSet);

                // 7. Fusion des Options
                const optSet = new Set(match.options || []);
                if (Array.isArray(booking.options)) {
                    booking.options.forEach(o => optSet.add(o));
                }
                match.options = Array.from(optSet);

                // 8. Fusion du Nom de Pack et Type Activité
                const packSet = new Set();
                (match.nomPack || "").split(" + ").forEach(p => {
                    const cp = p.trim();
                    if (cp && !cp.toLowerCase().includes("accueil")) packSet.add(cp);
                });
                (booking.nomPack || "").split(" + ").forEach(p => {
                    const cp = p.trim();
                    if (cp && !cp.toLowerCase().includes("accueil")) packSet.add(cp);
                });
                const sortedPacks = Array.from(packSet).sort((a, b) => {
                    if (a.toLowerCase().includes("enfant") && !b.toLowerCase().includes("enfant")) return -1;
                    if (!a.toLowerCase().includes("enfant") && b.toLowerCase().includes("enfant")) return 1;
                    return b.localeCompare(a);
                });
                match.nomPack = sortedPacks.length > 0 ? sortedPacks.join(" + ") : (match.nomPack || booking.nomPack);

                const typeSet = new Set(match.typeActivite ? match.typeActivite.split(" & ").map(t => t.trim()) : []);
                if (booking.typeActivite) {
                    booking.typeActivite.split(" & ").forEach(t => {
                        const ct = t.trim();
                        if (ct) typeSet.add(ct);
                    });
                }
                match.typeActivite = Array.from(typeSet).join(" & ");

                // 9. Enfant anniversaire
                if (!match.enfantAnniversaire && booking.enfantAnniversaire) {
                    match.enfantAnniversaire = booking.enfantAnniversaire;
                }

                // 10. Fusion & Dédoublonnage des Activités
                const existingActs = [...(match.activites || [])];
                if (Array.isArray(booking.activites)) {
                    booking.activites.forEach(newAct => {
                        const existingMatch = existingActs.find(ea => 
                            ea.heureDebut === newAct.heureDebut &&
                            ea.heureFin === newAct.heureFin &&
                            (ea.nom || "").trim().toLowerCase() === (newAct.nom || "").trim().toLowerCase()
                        );
                        if (!existingMatch) {
                            existingActs.push({ ...newAct });
                        } else {
                            existingMatch.nbPersonnes = (Number(existingMatch.nbPersonnes) || 0) + (Number(newAct.nbPersonnes) || 0);
                        }
                    });
                }
                // Tri chronologique des activités après fusion
                existingActs.sort((a, b) => {
                    const cmp = (a.heureDebut || "").localeCompare(b.heureDebut || "");
                    if (cmp !== 0) return cmp;
                    return (a.nom || "").localeCompare(b.nom || "");
                });
                match.activites = existingActs;
            }
        });

        // Regrouper les activités simultanées (ex: adultes et enfants jouant ensemble sur le même créneau)
        merged.forEach(item => {
            item.activites = this.groupSimultaneousActivities(item.activites, item.nbPersonnes);
        });

        return merged;
    }

    groupSimultaneousActivities(activites, fallbackQty = 1) {
        if (!activites || !activites.length) return [];

        const groupedMap = new Map();

        activites.forEach(act => {
            const hDebut = act.heureDebut || "";
            const hFin = act.heureFin || "";
            const zone = (act.zone || "Salle de jeu").trim();
            const key = `${hDebut}_${hFin}_${zone.toLowerCase()}`;

            if (!groupedMap.has(key)) {
                groupedMap.set(key, {
                    heureDebut: hDebut,
                    heureFin: hFin,
                    zone: zone,
                    noms: [(act.nom || "").trim()],
                    nbPersonnes: Number(act.nbPersonnes) || Number(fallbackQty) || 1
                });
            } else {
                const existing = groupedMap.get(key);
                const cleanNom = (act.nom || "").trim();
                if (!existing.noms.includes(cleanNom)) {
                    existing.noms.push(cleanNom);
                }
                existing.nbPersonnes = (Number(existing.nbPersonnes) || 0) + (Number(act.nbPersonnes) || Number(fallbackQty) || 1);
            }
        });

        const result = [];
        groupedMap.forEach(item => {
            let combinedNom = item.noms[0];
            if (item.noms.length > 1) {
                // Si plusieurs noms sur le même créneau ex: "20 Min Laser Game | Adulte +18 ans" et "20 Min Laser Game 7-12 ans"
                const hasAdulte = item.noms.some(n => n.toLowerCase().includes("adulte") || n.toLowerCase().includes("+18"));
                const hasEnfant = item.noms.some(n => n.toLowerCase().includes("7-12") || n.toLowerCase().includes("enfant"));
                const hasLaser = item.noms.some(n => n.toLowerCase().includes("laser"));

                if (hasLaser && hasAdulte && hasEnfant) {
                    combinedNom = "20 Min Laser Game | Adulte & Enfant";
                } else if (hasLaser && item.noms.length > 1) {
                    combinedNom = "20 Min Laser Game (" + item.noms.map(n => n.replace(/20 Min Laser Game\s*(\|\s*)?/i, '').trim()).filter(Boolean).join(" & ") + ")";
                } else {
                    combinedNom = item.noms.join(" + ");
                }
            }
            result.push({
                heureDebut: item.heureDebut,
                heureFin: item.heureFin,
                zone: item.zone,
                nom: combinedNom,
                nbPersonnes: item.nbPersonnes
            });
        });

        result.sort((a, b) => {
            const cmp = (a.heureDebut || "").localeCompare(b.heureDebut || "");
            if (cmp !== 0) return cmp;
            return (a.nom || "").localeCompare(b.nom || "");
        });

        return result;
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
                zone: typeof actZone === "string" ? actZone : (actZone.label || "Salle / Arène"),
                nbPersonnes: Number(item.qty) || Number(item.quantity) || Number(item.client?.qty) || Number(bookingsMap[orderId].nbPersonnes) || 1
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

        return this.mergeDuplicateClientBookings(Object.values(bookingsMap));
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
