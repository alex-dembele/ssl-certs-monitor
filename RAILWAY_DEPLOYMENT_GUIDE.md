# Guide Complet: Déploiement sur Railway.app

## 📋 État actuel
Tu as déjà 2 services créés:
- ✅ `ssl-cert-monitor-api` (Backend)
- ✅ `ssl-cert-monitor-frontend` (Frontend)

Les deux sont en erreur "Build failed" - c'est normal, on va corriger ça avec les variables.

---

## 🔧 Variables à configurer

### Service 1: Backend API (`ssl-cert-monitor-api`)

**Où aller:** Dashboard Railway → ssl-cert-monitor-api → Variables

**Variables à ajouter:**

| Clé | Valeur | Explication |
|-----|--------|-------------|
| `PYTHONUNBUFFERED` | `1` | Affiche les logs en temps réel |
| `PORT` | `8000` | Port d'écoute de l'API |

**Optionnel (pour les alertes email):**

| Clé | Valeur |
|-----|--------|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_SENDER_EMAIL` | `votre-email@gmail.com` |
| `SMTP_PASSWORD` | `votre-app-password` |
| `ALERT_RECIPIENTS` | `email1@example.com,email2@example.com` |

**Comment ajouter les variables:**
1. Cliquer sur le service `ssl-cert-monitor-api`
2. Aller à l'onglet **"Variables"** (ou "Environment")
3. Cliquer **"+ New Variable"**
4. Remplir les champs Key et Value
5. Cliquer **"Add"**

---

### Service 2: Frontend (`ssl-cert-monitor-frontend`)

**Où aller:** Dashboard Railway → ssl-cert-monitor-frontend → Variables

**Variables à ajouter:**

| Clé | Valeur | Explication |
|-----|--------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://ssl-cert-monitor-api.onrender.com` (ou l'URL Railway si déployée là) | URL de l'API |
| `PORT` | `3000` | Port d'écoute du frontend |
| `NODE_ENV` | `production` | Environnement de production |

**Attention:** 
- Si l'API est aussi sur Railway, utilise l'URL Railway (elle sera dans le dashboard Railway)
- Si l'API est ailleurs, mets son URL complète

**Comment ajouter les variables:**
1. Cliquer sur le service `ssl-cert-monitor-frontend`
2. Aller à l'onglet **"Variables"**
3. Cliquer **"+ New Variable"**
4. Remplir les champs
5. Cliquer **"Add"**

---

## 🔍 Où trouver les URL des services

### Pour connaître l'URL API sur Railway:

1. Aller dans **Dashboard Railway**
2. Cliquer sur le projet **"production"**
3. Cliquer sur le service **`ssl-cert-monitor-api`**
4. Aller à l'onglet **"Settings"** ou **"Deployments"**
5. Tu verras l'URL comme: `https://ssl-cert-monitor-api-xxx.railway.app`

**Copie cette URL** et mets-la dans la variable `NEXT_PUBLIC_API_URL` du frontend.

### Pour connaître l'URL Frontend sur Railway:

1. Cliquer sur le service **`ssl-cert-monitor-frontend`**
2. Tu verras l'URL comme: `https://ssl-cert-monitor-frontend-xxx.railway.app`

---

## 📋 Checklist complète

### ✅ Étape 1: Configurer Backend API
- [ ] Aller dans `ssl-cert-monitor-api`
- [ ] Aller à l'onglet Variables
- [ ] Ajouter `PYTHONUNBUFFERED` = `1`
- [ ] Ajouter `PORT` = `8000`
- [ ] Cliquer "Save" ou "Deploy"
- [ ] Attendre le déploiement (3-5 min)
- [ ] Vérifier que le build réussit

### ✅ Étape 2: Copier l'URL de l'API
- [ ] Aller dans les paramètres du service API
- [ ] Copier l'URL générée (exemple: `https://ssl-cert-monitor-api-xxx.railway.app`)

### ✅ Étape 3: Configurer Frontend
- [ ] Aller dans `ssl-cert-monitor-frontend`
- [ ] Aller à l'onglet Variables
- [ ] Ajouter `NEXT_PUBLIC_API_URL` = `https://ssl-cert-monitor-api-xxx.railway.app` (l'URL copiée)
- [ ] Ajouter `PORT` = `3000`
- [ ] Ajouter `NODE_ENV` = `production`
- [ ] Cliquer "Save" ou "Deploy"
- [ ] Attendre le déploiement (3-5 min)
- [ ] Vérifier que le build réussit

### ✅ Étape 4: Tester
- [ ] Ouvrir l'URL du frontend
- [ ] Vérifier que le dashboard s'affiche
- [ ] Tester l'ajout d'un domaine (exemple: google.com)
- [ ] Vérifier que ça communique avec l'API

---

## 🚀 Redéployer après changement de variables

Quand tu changes une variable:

1. **Option 1:** Railway redéploie automatiquement (attendre 2-3 min)
2. **Option 2:** Forcer le redéploiement:
   - Cliquer sur le service
   - Aller à **"Deployments"**
   - Cliquer sur le bouton **"Redeploy"** (flèche)

---

## ❌ Si ça ne marche pas

### Problème: "Build failed"

**Solution 1:** Vérifier les logs
- Cliquer sur le service → "Logs"
- Chercher le message d'erreur
- Le message dirà ce qui ne va pas

**Solution 2:** Vérifier les variables
- Assurez-vous que toutes les variables sont bien remplies
- Pas d'espaces inutiles avant/après les valeurs

**Solution 3:** Vérifier la branche
- Aller dans "Settings" du service
- Vérifier que la branche est **`develop`** et pas `main`

### Problème: Frontend ne communique pas avec l'API

**Solution:**
1. Vérifier que `NEXT_PUBLIC_API_URL` est correctement remplie
2. S'assurer que c'est en `https://` et pas `http://`
3. Copier-coller l'URL directement sans erreur de typage
4. Redéployer le frontend

### Problème: "Port already in use"

**Solution:** Railroad gère les ports automatiquement
- Tu peux laisser PORT vide ou mettre la valeur
- Railway assignera automatiquement un port disponible

---

## 📝 Exemple complet de configuration

### Backend API - Variables finales
```
PYTHONUNBUFFERED=1
PORT=8000
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_SENDER_EMAIL=mon-email@gmail.com
SMTP_PASSWORD=abcd efgh ijkl mnop
ALERT_RECIPIENTS=mon-email@gmail.com
```

### Frontend - Variables finales
```
NEXT_PUBLIC_API_URL=https://ssl-cert-monitor-api-xxx.railway.app
PORT=3000
NODE_ENV=production
```

---

## 🎯 Résumé rapide

**3 étapes:**
1. Ajouter variables au Backend → Attendre déploiement
2. Copier URL de l'API
3. Ajouter variables au Frontend avec l'URL de l'API → Attendre déploiement

**Coût:** Gratuit ($5/mois crédit)

**Temps total:** ~10-15 minutes

---

## 💡 Tips

- Garde l'onglet Railway ouvert dans un navigateur
- Ouvre les logs en parallèle pour suivre les déploiements
- Les variables changent à chaud, pas besoin de redéployer manuellement (sauf parfois)
- Les erreurs les plus courantes sont dans les logs (toujours vérifier là)

---

## 📞 Support

Si tu as des problèmes:
1. Vérifier les logs du service (Dashboard → Service → Logs)
2. Lire les messages d'erreur (ils sont généralement clairs)
3. Vérifier que les variables sont bien configurées
4. Redéployer manuellement si nécessaire
