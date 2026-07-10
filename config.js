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
        "2026-07-11": [
            { id: 4, type: "team", title: "Team Building - Société Beta", startHour: "10:30", endHour: "12:30", court: "Zone Team Game", notes: "Challenge par équipe" },
            { id: 5, type: "anniversaire", title: "Anniversaire Chloé (8 ans)", startHour: "15:00", endHour: "17:30", court: "Salle 2", notes: "Formule bonbons + boissons" }
        ]
    }
};

if (typeof module !== "undefined") {
    module.exports = CONFIG;
}
