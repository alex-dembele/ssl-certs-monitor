# Guide de Déploiement Gratuit - SSL Cert Monitor

## Options de déploiement recommandées

### 1. **Render.com** (Recommandé) ⭐
**Avantages:**
- Service gratuit avec 750h/mois par instance
- Support natif Docker
- Hébergement côté serveur et client
- Base de données gratuite
- Redéploiement automatique à chaque git push
- Plan gratuit suffisant pour une petite utilisation

**Comment déployer:**
1. Créer un compte sur [render.com](https://render.com)
2. Connecter votre repository GitHub (alex-dembele/ssl-certs-monitor)
3. Créer un nouveau service Web (Blueprint ou manuel)
4. Configurer:
   - Build Command: `npm install && npm run build` (pour le frontend)
   - Start Command: `npm start`
   - Environment: `BACKEND_API_URL=https://votre-api.onrender.com`
5. Pour le backend, créer un autre service avec:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port 8000`

**Temps de déploiement:** 5-10 minutes
**Coût:** Gratuit (750h/mois)

---

### 2. **Railway.app** 🚂
**Avantages:**
- $5/mois gratuit au démarrage
- Interface très intuitive
- Support Docker Compose natif
- Parfait pour les microservices

**Comment déployer:**
1. Aller sur [railway.app](https://railway.app)
2. Se connecter avec GitHub
3. Créer un nouveau project
4. Connecter le repository
5. Railway détectera automatiquement les Dockerfiles
6. Configurer les variables d'environnement

**Temps de déploiement:** 5 minutes
**Coût:** Gratuit ($5/mois crédit)

---

### 3. **Fly.io** 🚀
**Avantages:**
- Toujours gratuit (limite de 3 instances)
- Performance élevée
- Support global
- IPv6 natif

**Comment déployer:**
1. Installer `flyctl`: `curl -L https://fly.io/install.sh | sh`
2. Créer un app: `flyctl apps create`
3. Initialiser: `flyctl launch`
4. Déployer: `flyctl deploy`

**Temps de déploiement:** 10 minutes
**Coût:** Gratuit

---

### 4. **Vercel** (Frontend uniquement)
**Avantages:**
- Meilleure performance pour Next.js
- Déploiement en 1 clic
- Gratuitement jusqu'à 100GB bande passante/mois

**Comment déployer le frontend:**
1. Pousser sur GitHub
2. Aller sur [vercel.com](https://vercel.com)
3. Importer le project
4. Configurer: `BACKEND_API_URL=https://votre-api.fly.io`
5. Déployer

**Temps de déploiement:** 2 minutes
**Coût:** Gratuit

---

## Déploiement complet avec Render (Solution complète gratuite)

### Étape 1: Préparer le repository
```bash
git push origin develop  # ✅ Déjà fait
```

### Étape 2: Créer le service Frontend sur Render
1. Sur render.com, cliquer "New +" → "Web Service"
2. Sélectionner votre repository
3. Configurer:
   - **Name:** ssl-cert-monitor-frontend
   - **Environment:** Docker
   - **Root Directory:** frontend
   - **Environment Variables:**
     - `BACKEND_API_URL=https://ssl-cert-monitor-api.onrender.com`

### Étape 3: Créer le service Backend API sur Render
1. Cliquer "New +" → "Web Service"
2. Sélectionner votre repository
3. Configurer:
   - **Name:** ssl-cert-monitor-api
   - **Environment:** Docker
   - **Root Directory:** backend
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0`

### Étape 4: Créer le service Backend Cron sur Render
1. Clicker "New +" → "Background Worker"
2. Sélectionner votre repository
3. Configurer:
   - **Name:** ssl-cert-monitor-cron
   - **Environment:** Docker
   - **Root Directory:** backend
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python cron_job.py`
   - **Environment Variables:** (copier du fichier .env)

---

## Configuration d'une base de données gratuite (optionnel)

Pour persister les données:

### Supabase PostgreSQL (Gratuit)
- 500MB storage
- Connexion à partir du backend
- Très simple à intégrer

### MongoDB Atlas (Gratuit)
- 512MB storage
- Parfait pour JSON
- Très facile à mettre en place

---

## Domaine gratuit

### Option 1: Render gratuit
Render fournit un domaine: `https://ssl-cert-monitor.onrender.com`

### Option 2: Freenom (domaines gratuits)
Domaines gratuits (.tk, .ml, .ga) sur [freenom.com](https://freenom.com)

### Option 3: GitHub Pages + Cloudflare
- Cloudflare offre DNS gratuit avec domaine personnel

---

## Résumé des coûts
| Service | Coût | Limite |
|---------|------|--------|
| Render Frontend | Gratuit | 750h/mois |
| Render Backend API | Gratuit | 750h/mois |
| Render Cron | Gratuit | 750h/mois |
| **Total** | **Gratuit** | **Services multiples** |

---

## ⚠️ Recommandations importantes

1. **Variables d'environnement:** 
   - Ne jamais commit `.env`
   - Utiliser le panel de chaque service pour les secrets
   - Bien configurer `BACKEND_API_URL`

2. **Partage des volumes:**
   - Render n'a pas de partage de volume persistent entre services
   - Solution: Utiliser une base de données (PostgreSQL, MongoDB)

3. **Monitoring:**
   - Chaque service doit avoir un healthcheck
   - ✅ Backend API a déjà un `/health`

4. **Scaling future:**
   - Render peut monter jusqu'à plusieurs instances payantes
   - Votre code est prêt pour ça

---

## Prochaines étapes

1. Choisir Render ou Railway pour démarrer
2. Créer un compte
3. Connecter le repository
4. Configurer les variables d'environnement
5. Observer les logs de déploiement
6. Tester l'application déployée

**Besoin d'aide?** Les logs de chaque service montreront les erreurs éventuelles.
