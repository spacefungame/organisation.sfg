# 🎯 Guide d'Installation — Gravity Center Anniversaires

## Prérequis

- **Python 3.10+** installé sur votre ordinateur
- **Accès internet** (pour installer les dépendances)

---

## 1. Installation rapide

Ouvrez un terminal (PowerShell ou Invite de commandes) dans le dossier du projet :

```bash
# Installer les dépendances Python
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse : **http://localhost:8501**

---

## 2. Mode Démo vs Mode Production

### Mode Démo (par défaut)
- **Aucune configuration nécessaire** — l'application fonctionne immédiatement
- Affiche des réservations fictives pour tester l'interface
- Idéal pour découvrir l'application

### Mode Production
Pour passer en production, il faut configurer :
1. L'API Qweekle (récupération des réservations)
2. L'API Gmail (détection des modifications)

---

## 3. Configuration de l'API Qweekle

1. Contactez le support Qweekle pour obtenir votre **clé API**
2. Ouvrez le fichier `config.py`
3. Renseignez votre clé :

```python
QWEEKLE_API_KEY = "votre-clé-api-ici"
QWEEKLE_BASE_URL = "https://api.qweekle.com/v1"  # À adapter selon Qweekle
```

> ⚠️ **Note** : Une fois la clé API renseignée, il faudra peut-être adapter le fichier `modules/qweekle_api.py` pour correspondre au format exact des réponses de l'API Qweekle. Des commentaires dans le code vous guident.

---

## 4. Configuration de Gmail (détection des modifications)

### Étape 1 : Créer un projet Google Cloud

1. Allez sur **https://console.cloud.google.com/**
2. Cliquez sur **"Sélectionner un projet"** en haut → **"Nouveau projet"**
3. Donnez un nom (ex: "Gravity Anniversaires") → **Créer**

### Étape 2 : Activer l'API Gmail

1. Dans le menu de gauche → **"API et Services"** → **"Bibliothèque"**
2. Cherchez **"Gmail API"**
3. Cliquez dessus → **"Activer"**

### Étape 3 : Configurer l'écran de consentement OAuth

1. Menu gauche → **"API et Services"** → **"Écran de consentement OAuth"**
2. Choisissez **"Externe"** → **Créer**
3. Remplissez :
   - Nom de l'application : "Gravity Anniversaires"
   - Email d'assistance : votre email
   - Email du développeur : votre email
4. Cliquez **"Enregistrer et continuer"** pour les étapes suivantes
5. À l'étape **"Utilisateurs tests"**, ajoutez votre adresse Gmail

### Étape 4 : Créer les identifiants OAuth

1. Menu gauche → **"API et Services"** → **"Identifiants"**
2. Cliquez **"+ Créer des identifiants"** → **"ID client OAuth"**
3. Type d'application : **"Application de bureau"**
4. Nom : "Gravity Desktop"
5. **Téléchargez** le fichier JSON
6. **Renommez-le** en `credentials.json`
7. **Placez-le** dans le dossier du projet (à côté de `app.py`)

### Étape 5 : Première connexion

1. Lancez l'application : `streamlit run app.py`
2. Dans la barre latérale, cliquez sur **"🔗 Connecter Gmail"**
3. Votre navigateur s'ouvrira pour vous connecter à Google
4. Autorisez l'accès en lecture seule
5. Un fichier `token.json` sera créé automatiquement (vous n'aurez plus à vous reconnecter)

---

## 5. Personnalisation des tables

Ouvrez `config.py` et modifiez le dictionnaire `TABLES` :

```python
TABLES = {
    "T1": 17,    # Table 1 — 17 places
    "T2": 12,    # Table 2 — 12 places
    "T3": 12,    # Table 3 — 12 places
    "T4": 12,    # Table 4 — 12 places
    "T5": 8,     # Table 5 — 8 places
    "T6": 8,     # Table 6 — 8 places
    "STG-": 17,  # Stage petit — 17 places
    "STG+": 22,  # Stage grand — 22 places
    "R1": 10,    # Salle R1 — 10 places
    "R2": 6,     # Salle R2 — 6 places
    "R3": 6,     # Salle R3 — 6 places
    "R4": 12,    # Salle R4 — 12 places
}
```

Pour ajouter une table, ajoutez simplement une ligne. Pour en supprimer, retirez la ligne.

---

## 6. Structure du projet

```
📁 Automatisation anniversaires/
├── 📄 app.py                    ← Application principale
├── 📄 config.py                 ← Configuration (tables, API, etc.)
├── 📄 requirements.txt          ← Dépendances Python
├── 📄 SETUP_GUIDE.md            ← Ce guide
├── 📁 modules/
│   ├── __init__.py
│   ├── demo_data.py             ← Données fictives pour les tests
│   ├── qweekle_api.py           ← Connecteur API Qweekle
│   ├── gmail_api.py             ← Connecteur API Gmail
│   └── table_allocator.py       ← Algorithme d'attribution des tables
├── 📁 assets/
│   └── style.css                ← Styles CSS du dashboard
└── 📁 .streamlit/
    └── config.toml              ← Thème Streamlit (couleurs)
```

---

## Dépannage

| Problème | Solution |
|----------|----------|
| `ModuleNotFoundError` | Exécutez `pip install -r requirements.txt` |
| L'app ne s'ouvre pas | Vérifiez que le port 8501 n'est pas utilisé |
| Gmail ne se connecte pas | Vérifiez que `credentials.json` est dans le bon dossier |
| Token expiré | Supprimez `token.json` et reconnectez-vous |
