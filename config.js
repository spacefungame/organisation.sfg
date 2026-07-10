/**
 * Fichier de Configuration - Organisation Space Fun Games
 * Thème : Beige Chaleureux, Mode Clair & Sobre (Aucun Gris)
 */

const CONFIG = {
    // Nom officiel du site
    SITE_NAME: "Organisation Space Fun Games",

    // Mot de passe pour accéder au site (vous pouvez changer facilement ce texte ou le hash SHA-256 ci-dessous)
    RAW_PASSWORD: "1503",
    // Hachage SHA-256 précalculé pour 1503 (pour validation sécurisée en local)
    PASSWORD_HASH_SHA256: "45fcf3f6c8d76ffef5406dcc4a9bbf629ab1db42bb709774deff11c7ce2fc4ab",

    // Amplitude horaire par défaut pour le "planning classique"
    HOURS_START: 10, // 10h00
    HOURS_END: 23,   // 23h00
    HOURS_STEP: 60,  // Pas de 60 minutes par défaut (ou 30 min)

    // Définition des onglets / pages du site
    TABS: [
        { id: "home", label: "Accueil / Calendrier", icon: "📅" },
        { id: "complet", label: "Planning Complet", icon: "📋" },
        { id: "anniversaire", label: "Planning Anniversaire", icon: "🎂" },
        { id: "laser", label: "Planning Laser Game", icon: "🔫" },
        { id: "team", label: "Planning Team Game", icon: "🤝" },
        { id: "quiz", label: "Planning Quiz Game", icon: "🧠" },
        { id: "postit", label: "Post It", icon: "📌" }
    ],

    // Types d'activités avec palette de couleurs chaudes (Beige, Chocolat, Terracotta, Ambre, Saphir, Émeraude) - STRICTEMENT SANS GRIS
    ACTIVITIES: {
        anniversaire: {
            label: "Anniversaire",
            colorBg: "#FDF0D5",
            colorBorder: "#D4A373",
            colorText: "#5E3A1C"
        },
        laser: {
            label: "Laser Game",
            colorBg: "#FCE8E6",
            colorBorder: "#D9534F",
            colorText: "#6A1E1A"
        },
        team: {
            label: "Team Game",
            colorBg: "#E8F4F8",
            colorBorder: "#3182CE",
            colorText: "#1A4971"
        },
        quiz: {
            label: "Quiz Game",
            colorBg: "#F3E8FF",
            colorBorder: "#805AD5",
            colorText: "#442A75"
        },
        autre: {
            label: "Divers / Maintenance",
            colorBg: "#F0EBE3",
            colorBorder: "#A89F91",
            colorText: "#3D362D"
        }
    },

    // Données de démonstration réalistes pour que le planning ne soit pas vide au premier lancement
    DEMO_DATA: {
        "2026-07-10": [
            { id: 1, type: "anniversaire", title: "Anniversaire Lucas (10 ans) - Formule VIP", startHour: "14:00", endHour: "16:30", court: "Salle 1", notes: "Gâteau chocolat + 12 enfants" },
            { id: 2, type: "laser", title: "Session Laser Game - Groupe Entreprise Alpha", startHour: "18:00", endHour: "20:00", court: "Arène Laser", notes: "20 joueurs" },
            { id: 3, type: "quiz", title: "Quiz Tournoi - Famille Martin", startHour: "15:00", endHour: "16:00", court: "Plateau Quiz A", notes: "8 joueurs" }
        ],
    },

    // Configuration officielle de l'API Qweekle & Base de Données Live (Supabase Webhooks)
    QWEEKLE_API_KEY: "a712eb126838aeb58223d70725227d84",
    QWEEKLE_API_URL: "https://api.qweekle.io/api",
    SUPABASE_URL: "https://uyptbypqzfkdsvpdvwyz.supabase.co",
    SUPABASE_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV5cHRieXBxemZrZHN2cGR2d3l6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAxNTA1ODAsImV4cCI6MjA5NTcyNjU4MH0.ZEZxlWA9H0u6iP3IHn97XjqNABUEl3kqVcsecx9GPKg",

    // Données de réservations détaillées Qweekle (Structure officielle 100% complète et réaliste)
    // Utilisées en synchronisation directe ou en repli si l'appel API est bloqué (hors-ligne/CORS en local)
    QWEEKLE_RESERVATIONS_DATA: {
        "2026-07-10": [
            {
                id: "QW-90102",
                nom: "DUPONT",
                prenom: "Marc (Parent)",
                heureArrivee: "13:30",
                heureDepart: "16:30",
                nbPersonnes: 14,
                nomPack: "Pack Anniversaire Sensation Double (Laser + Quiz)",
                typeActivite: "Multi-Activités Enfant",
                categories: ["anniversaire", "enfant"],
                enfantAnniversaire: {
                    prenom: "Lucas",
                    age: 10,
                    dateNaissance: "12/07/2016",
                    sousCompteId: "SC-8410"
                },
                activites: [
                    { heureDebut: "14:00", heureFin: "14:45", nom: "Session Laser Game - Arène Galactique", zone: "Arène Laser 1" },
                    { heureDebut: "15:00", heureFin: "15:45", nom: "Partie Quiz Game TV - Tournoi des Champions", zone: "Plateau Quiz A" }
                ],
                options: [
                    "🍰 Gâteau au chocolat Maison (16 parts)",
                    "🥤 4x Pichets Boissons gazeuses & jus",
                    "🍬 14x Pochettes surprises bonbons",
                    "📸 Photo souvenir imprimée de l'équipe"
                ]
            },
            {
                id: "QW-90145",
                nom: "MARTIN",
                prenom: "Sophie",
                societe: "Entreprise NexaTech Solutions",
                heureArrivee: "17:30",
                heureDepart: "21:00",
                nbPersonnes: 24,
                nomPack: "Formule Challenge Collaborateurs VIP",
                typeActivite: "Team Building d'Entreprise",
                categories: ["team building", "adulte"],
                activites: [
                    { heureDebut: "18:00", heureFin: "19:15", nom: "Challenge Team Game - Mission spatiale & Défis", zone: "Zone Team Game Alpha" },
                    { heureDebut: "19:30", heureFin: "20:30", nom: "Tournoi Laser Game en équipes", zone: "Arène Laser 1 & 2" }
                ],
                options: [
                    "🍾 Buffet Cocktail Traiteur Adulte (24 personnes)",
                    "🥂 Forfait Boissons & Softs Prestige",
                    "🏆 Trophée personnalisable Équipe gagnante",
                    "🎙️ Animation par un Game Master privatisé"
                ]
            },
            {
                id: "QW-90188",
                nom: "LEFEVRE",
                prenom: "Thomas",
                societe: "ASBL Jeunesse Active & Loisirs",
                heureArrivee: "10:00",
                heureDepart: "13:00",
                nbPersonnes: 18,
                nomPack: "Pack Sortie Groupe ASBL Ado",
                typeActivite: "Sortie Association & Jeunes",
                categories: ["asbl", "ado"],
                activites: [
                    { heureDebut: "10:30", heureFin: "11:30", nom: "Session Laser Game Ado Extrême", zone: "Arène Laser 2" },
                    { heureDebut: "11:45", heureFin: "12:45", nom: "Quiz Culture Pop & Gaming", zone: "Plateau Quiz B" }
                ],
                options: [
                    "🥤 Boissons softs rafraîchissantes x18",
                    "🍕 Formule Pizzas & Snacks du midi (18 portions)"
                ]
            },
            {
                id: "QW-90210",
                nom: "MOREAU",
                prenom: "Alexandre",
                heureArrivee: "20:30",
                heureDepart: "23:30",
                nbPersonnes: 30,
                nomPack: "Soirée Évènement Adulte Prestige & Karaoké/Quiz",
                typeActivite: "Évènement Privé Adulte",
                categories: ["évènement adulte", "adulte"],
                activites: [
                    { heureDebut: "21:00", heureFin: "22:00", nom: "Quiz Musical & Blind Test sur plateau TV", zone: "Plateau Quiz A" },
                    { heureDebut: "22:15", heureFin: "23:15", nom: "Laser Game Nocturne VIP", zone: "Arène Laser Complexe" }
                ],
                options: [
                    "🍸 Espace Bar Privatisé avec Bartender",
                    "🎧 Sonorisation Lounge & Éclairage VIP",
                    "🍕 Assortiment Tapas & Petits Fours (30 convives)"
                ]
            },
            {
                id: "QW-90240",
                nom: "BERNARD",
                prenom: "Éric (Parent)",
                heureArrivee: "14:30",
                heureDepart: "17:00",
                nbPersonnes: 12,
                nomPack: "Pack Anniversaire Ado Laser Intense",
                typeActivite: "Anniversaire Ado",
                categories: ["anniversaire", "ado"],
                enfantAnniversaire: {
                    prenom: "Chloé",
                    age: 14,
                    dateNaissance: "09/07/2012",
                    sousCompteId: "SC-8922"
                },
                activites: [
                    { heureDebut: "15:00", heureFin: "16:00", nom: "Tournoi Laser Game 3 Manches", zone: "Arène Laser 1" },
                    { heureDebut: "16:15", heureFin: "16:45", nom: "Espace Goûter Anniversaire Ado", zone: "Salle Lounge 2" }
                ],
                options: [
                    "🎂 Gâteau Ice Cream & Bougies étincelantes",
                    "🥤 3x Pichets Cocktails sans alcool Ado",
                    "🎮 Jeton Jeux d'Arcade x24"
                ]
            }
        ],
        "2026-07-11": [
            {
                id: "QW-90312",
                nom: "ROUSSEAU",
                prenom: "Céline (Parent)",
                heureArrivee: "11:00",
                heureDepart: "14:00",
                nbPersonnes: 10,
                nomPack: "Pack Anniversaire Enfant Évasion Quiz",
                typeActivite: "Anniversaire Enfant",
                categories: ["anniversaire", "enfant"],
                enfantAnniversaire: {
                    prenom: "Emma",
                    age: 8,
                    dateNaissance: "11/07/2018",
                    sousCompteId: "SC-9104"
                },
                activites: [
                    { heureDebut: "11:30", heureFin: "12:15", nom: "Partie Quiz Enfants Junior", zone: "Plateau Quiz A" },
                    { heureDebut: "12:30", heureFin: "13:30", nom: "Goûter & Cadeaux Salle VIP", zone: "Salle 1" }
                ],
                options: [
                    "🍰 Gâteau Framboisine (12 parts)",
                    "🧃 Jus de fruits bio x10"
                ]
            },
            {
                id: "QW-90350",
                nom: "GARCIA",
                prenom: "Nicolas",
                societe: "Comité d'Entreprise Innovate SA",
                heureArrivee: "15:30",
                heureDepart: "19:00",
                nbPersonnes: 35,
                nomPack: "Grand Challenge Team Building Multi-Zones",
                typeActivite: "Team Building Prestige",
                categories: ["team building", "adulte"],
                activites: [
                    { heureDebut: "16:00", heureFin: "17:15", nom: "Epreuves Team Challenge", zone: "Zone Team Game Alpha & Beta" },
                    { heureDebut: "17:30", heureFin: "18:30", nom: "Tournoi Royal Laser Game", zone: "Arène Laser 1 & 2" }
                ],
                options: [
                    "🥂 Buffet Apéritif Dînatoire & Softs",
                    "📸 Couverture Photo & Vidéo par Drone"
                ]
            }
        ]
    }
};

if (typeof module !== "undefined") {
    module.exports = CONFIG;
}
