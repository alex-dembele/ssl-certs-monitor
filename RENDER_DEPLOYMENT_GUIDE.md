# Guide Complet: Déploiement SSL Cert Monitor sur Render.com

## 📋 Table des matières
1. [Création du compte Render](#création-du-compte-render)
2. [Déploiement via Blueprint (Méthode 1-Click)](#déploiement-via-blueprint-méthode-1-click)
3. [Déploiement Manuel (Méthode Complète)](#déploiement-manuel-méthode-complète)
4. [Configuration des variables d'environnement](#configuration-des-variables-denvironnement)
5. [Vérification et tests](#vérification-et-tests)
6. [Dépannage](#dépannage)

---

## Création du compte Render

### Étape 1: Aller sur Render.com
1. Ouvrir [https://render.com](https://render.com)
2. Cliquer sur **"Sign up"** en haut à droite
3. Choisir **"GitHub"** comme méthode de connexion

### Étape 2: Autoriser Render à accéder à GitHub
1. GitHub va demander l'autorisation
2. Cliquer **"Authorize render-oss"**
3. Choisir votre compte utilisateur (alex-dembele)
4. Sélectionner **"Only select repositories"** pour plus de sécurité
5. Chercher et sélectionner **"ssl-certs-monitor"**
6. Cliquer **"Install"**

### Étape 3: Revenir sur Render
- Vous serez redirigé sur votre dashboard Render
- Vous devriez voir votre compte créé

---

## Déploiement via Blueprint (Méthode 1-Click) ⭐ RECOMMANDÉE

### La plus rapide (5 minutes)

### Étape 1: Utiliser le lien 1-Click Deploy
1. **Cliquer directement sur ce lien:**
   ```
   https://render.com/deploy?repo=https://github.com/alex-dembele/ssl-certs-monitor
   ```
   (Assurez-vous que vous êtes connecté à Render)

### Étape 2: Vérifier les paramètres
Une page apparaîtra avec les détails pré-remplis:

```
Source Code:  alex-dembele/ssl-certs-monitor
Name:         ssl-certs-monitor
Language:     Docker
Branch:       main ⚠️ CHANGE EN "develop"
Region:       Oregon (US West)
Root Dir:     (vide)
Dockerfile:   (vide)
```

**IMPORTANT**: Changer la branche de **main** à **develop** car c'est là que se trouvent les corrections!

### Étape 3: Créer le Blueprint
1. Cliquer **"Deploy"**
2. Render va créer automatiquement 3 services:
   - `ssl-cert-monitor-api`
   - `ssl-cert-monitor-frontend`
   - `ssl-cert-monitor-cron`

### Étape 4: Attendre le déploiement
- Ça prend environ 5-10 minutes
- Vous verrez les logs défiler en direct
- Une fois terminé, vous aurez 3 URLs

---

## Déploiement Manuel (Méthode Complète)

### Plus de contrôle (10 minutes)

### Partie 1: Créer le service Backend API

#### Étape 1: Nouveau Web Service
1. Sur le dashboard Render, cliquer **"New +"** en haut à droite
2. Sélectionner **"Web Service"**

#### Étape 2: Configurer la source
1. **Source Code:**
   - Sélectionner: `alex-dembele/ssl-certs-monitor`
   - Cliquer **"Connect"**

#### Étape 3: Paramètres du service

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `ssl-cert-monitor-api` |
| **Language** | Docker |
| **Branch** | `develop` |
| **Root Directory** | `backend` |
| **Region** | Oregon (US West) |
| **Instance Type** | Free (512 MB RAM) |

#### Étape 4: Build Command
Dans les paramètres avancés (Advanced):
```bash
pip install -r requirements.txt
```

#### Étape 5: Start Command
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Étape 6: Healthcheck Path
```
/health
```

#### Étape 7: Variables d'environnement
Cliquer **"Add Environment Variable"**

| Clé | Valeur |
|-----|--------|
| `PYTHONUNBUFFERED` | `1` |

Optionnel (pour les emails):
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_SENDER_EMAIL=votre-email@gmail.com
SMTP_PASSWORD=app-password-générée
ALERT_RECIPIENTS=recipient@example.com
```

#### Étape 8: Déployer
Cliquer **"Deploy Web Service"**
- Temps: ~5-7 minutes
- Une URL sera générée: `https://ssl-cert-monitor-api.onrender.com`

---

### Partie 2: Créer le service Frontend

#### Étape 1: Nouveau Web Service
1. Cliquer **"New +"** → **"Web Service"**
2. Sélectionner `alex-dembele/ssl-certs-monitor`

#### Étape 2: Paramètres du service

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `ssl-cert-monitor-frontend` |
| **Language** | Docker |
| **Branch** | `develop` |
| **Root Directory** | `frontend` |
| **Region** | Oregon (US West) |
| **Instance Type** | Free (512 MB RAM) |

#### Étape 3: Build Command
```bash
npm install && npm run build
```

#### Étape 4: Start Command
```bash
npm start
```

#### Étape 5: Variables d'environnement
**⚠️ CRUCIAL:** Lier l'API déployée

Cliquer **"Add Environment Variable"**

| Clé | Valeur |
|-----|--------|
| `NEXT_PUBLIC_API_URL` | Laisser vide pour le moment |

Après le déploiement du frontend:
- Modifier cette variable
- Mettre: `https://ssl-cert-monitor-api.onrender.com`

#### Étape 6: Déployer
Cliquer **"Deploy Web Service"**
- Temps: ~5-7 minutes
- Une URL sera générée: `https://ssl-cert-monitor-frontend.onrender.com`

---

### Partie 3: Créer le service Cron (Background Worker)

#### Étape 1: Nouveau Background Worker
1. Cliquer **"New +"** → **"Background Worker"**
2. Sélectionner `alex-dembele/ssl-certs-monitor`

#### Étape 2: Paramètres du service

| Paramètre | Valeur |
|-----------|--------|
| **Name** | `ssl-cert-monitor-cron` |
| **Language** | Docker |
| **Branch** | `develop` |
| **Root Directory** | `backend` |
| **Region** | Oregon (US West) |
| **Instance Type** | Free (512 MB RAM) |

#### Étape 3: Build Command
```bash
pip install -r requirements.txt
```

#### Étape 4: Start Command
```bash
python cron_job.py
```

#### Étape 5: Variables d'environnement
Ajouter les mêmes que le backend API:

```
PYTHONUNBUFFERED=1
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_SENDER_EMAIL=votre-email@gmail.com
SMTP_PASSWORD=app-password-générée
ALERT_RECIPIENTS=recipient@example.com
```

#### Étape 6: Déployer
Cliquer **"Deploy"**
- Pas d'URL publique (c'est un worker de fond)
- Tournera en arrière-plan

---

## Configuration des variables d'environnement

### Pour le Frontend (IMPORTANT!)

Après avoir déployé l'API:

1. Aller sur le dashboard Render
2. Cliquer sur **`ssl-cert-monitor-frontend`**
3. Cliquer sur l'onglet **"Environment"**
4. Trouver la variable `NEXT_PUBLIC_API_URL`
5. Modifier sa valeur:
   ```
   https://ssl-cert-monitor-api.onrender.com
   ```
6. Cliquer **"Save Changes"**
7. Le service va se redéployer automatiquement

### Pour les emails (Optionnel)

Si vous voulez activer les alertes email:

#### Obtenir un mot de passe d'application Gmail:
1. Aller sur [myaccount.google.com/apppasswords](https://myaccount.google.com/app-passwords)
2. Sélectionner:
   - App: **Mail**
   - Device: **Other (custom name)** → `ssl-cert-monitor`
3. Google génère un mot de passe (16 caractères)
4. Copier ce mot de passe

#### Ajouter aux variables d'environnement de tous les services:

Pour chaque service (API + Cron):
1. Aller dans **"Environment"**
2. Ajouter:
   ```
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_SENDER_EMAIL=votre-email@gmail.com
   SMTP_PASSWORD=16-caractères-générés
   ALERT_RECIPIENTS=email1@example.com,email2@example.com
   ```
3. Cliquer **"Save Changes"**

---

## Vérification et tests

### Vérifier que l'API fonctionne
1. Ouvrir dans le navigateur:
   ```
   https://ssl-cert-monitor-api.onrender.com/health
   ```
2. Vous devriez voir:
   ```json
   {"status": "healthy"}
   ```

### Vérifier le frontend
1. Ouvrir:
   ```
   https://ssl-cert-monitor-frontend.onrender.com
   ```
2. Vous devriez voir le dashboard avec le formulaire pour ajouter des domaines

### Tester l'ajout d'un domaine
1. Sur le frontend, entrer un domaine (ex: `google.com`)
2. Cliquer "Ajouter"
3. Vérifier que ça fonctionne

### Vérifier les logs
Pour chaque service:
1. Aller dans le service sur Render
2. Cliquer sur l'onglet **"Logs"**
3. Vérifier qu'il n'y a pas d'erreurs

---

## Dépannage

### Problème: "Build failed"

**Solution 1:** Vérifier les logs
- Aller sur le service → "Logs"
- Chercher l'erreur exacte

**Solution 2:** Vérifier le Root Directory
- Vérifier que `Root Directory` est correct:
  - Backend: `backend`
  - Frontend: `frontend`
  - Cron: `backend`

**Solution 3:** Vérifier la branche
- Assurez-vous que c'est **`develop`** et pas `main`
- Les corrections sont sur `develop`

### Problème: Frontend ne communique pas avec l'API

**Solution:**
1. Vérifier `NEXT_PUBLIC_API_URL` sur le frontend
2. Elle doit être: `https://ssl-cert-monitor-api.onrender.com`
3. Pas `http://` mais `https://`
4. Sauvegarder et attendre le redéploiement

### Problème: "Port already in use"

**Solution:** Render gère les ports automatiquement
- Vous n'avez rien à faire
- Les logs devraient montrer le port réel utilisé

### Problème: Cron ne tourne pas

**Solution 1:** Vérifier les logs du worker
- Les workers de fond s'arrêtent automatiquement après 30 min d'inactivité
- Pour un vrai cron qui tourne 24/7, il faudrait une instance payante

**Solution 2:** Créer un trigger manuel pour tester
- Vous pouvez redéployer et voir les logs

### Problème: "502 Bad Gateway"

**Solution:**
- L'API n'est peut-être pas prête
- Attendre 1-2 minutes après le déploiement
- Rafraîchir la page (Ctrl+Shift+R pour vider le cache)

### Problème: Les domaines ne se sauvegardent pas

**Solution:**
- Les instances Free de Render n'ont pas de stockage persistant
- Les données disparaissent lors des redéploiements
- **Solution:** Ajouter une base de données (voir section suivante)

---

## Ajouter une base de données (Optionnel)

Pour persister les données entre les redéploiements:

### Option 1: PostgreSQL gratuit via Supabase

1. Aller sur [supabase.com](https://supabase.com)
2. Créer un compte
3. Créer un nouveau projet (Free tier)
4. Copier la connection string
5. Ajouter à vos variables d'environnement:
   ```
   DATABASE_URL=postgresql://...
   ```

### Option 2: MongoDB Atlas gratuit

1. Aller sur [mongodb.com/cloud/atlas](https://mongodb.com/cloud/atlas)
2. Créer un cluster gratuit (500 MB)
3. Copier la connection string
4. Ajouter à vos variables d'environnement:
   ```
   MONGODB_URL=mongodb+srv://...
   ```

---

## Récapitulatif des URLs finales

Une fois déployé, vous aurez:

| Service | URL | Accès |
|---------|-----|-------|
| **Frontend** | `https://ssl-cert-monitor-frontend.onrender.com` | Navigateur |
| **Backend API** | `https://ssl-cert-monitor-api.onrender.com` | API interne |
| **Health Check** | `https://ssl-cert-monitor-api.onrender.com/health` | Vérification |
| **Cron Worker** | (pas d'URL) | Arrière-plan |

---

## Support et aide

### Si quelque chose ne fonctionne pas:

1. **Vérifier les logs:**
   - Dashboard Render → Service → "Logs"
   
2. **Redéployer:**
   - Dashboard Render → Service → "Manual Deploy"
   
3. **Vérifier le code:**
   - Chercher l'erreur spécifique dans les logs
   - Généralement les erreurs Python/Node.js sont claires

4. **Ouvrir une issue GitHub:**
   - [https://github.com/alex-dembele/ssl-certs-monitor/issues](https://github.com/alex-dembele/ssl-certs-monitor/issues)

---

## Félicitations! 🎉

Votre SSL Cert Monitor est maintenant déployé en ligne et accessible à tous!

**Prochaines étapes:**
- Partager l'URL du frontend avec d'autres
- Ajouter des domaines à surveiller
- Configurer les alertes email (optionnel)
- Améliorer l'application avec plus de fonctionnalités
