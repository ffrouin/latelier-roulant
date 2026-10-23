# L’Atelier Roulant

> Réparer plutôt que remplacer

Page de présentation d’un service de réparations, dépannages et débarras à domicile.

## Positionnement

**L’Atelier Roulant** intervient chez les particuliers pour :

- diagnostiquer et réparer l’électroménager ;
- aider au diagnostic et à la réparation de matériel informatique et électronique ;
- remettre en état meubles, murs, sols et plafonds ;
- débarrasser les encombrants et favoriser le réemploi lorsque c’est possible.

## Lancer le site en local

Le site utilise Three.js depuis un module CDN et se sert avec Python :

```bash
python3 app.py
```

Puis ouvrir [http://127.0.0.1:8000](http://127.0.0.1:8000).

Le port peut être modifié :

```bash
PORT=8080 python3 app.py
```

### Envoi des demandes

Après la confirmation humaine, le serveur génère un PDF de synthèse et
l’envoie uniquement à `OWNER_EMAIL` pour la notification backend. Le PDF est
également renvoyé au navigateur pour être consulté ou téléchargé par l’usager.
Configurez
les variables SMTP avant de lancer le serveur :

```bash
export OWNER_EMAIL="me@my.mail"
export SMTP_HOST="smtp.my.mail"
export SMTP_PORT="587"
export SMTP_USERNAME="me@my.mail"
export SMTP_PASSWORD="mot-de-passe-fourni-par-le-fournisseur"
export SMTP_FROM="me@my.mail"
export SMTP_STARTTLS="1"
export PUBLIC_BASE_URL="https://atelier-roulant.linuxtribe.fr"
export REQUEST_STORAGE_DIR="/opt/latelier-roulant/requests"
export GEOIP_LEGACY_DB_PATH="/opt/GeoIPv2/GeoLiteCity.dat"
export LEGAL_BUSINESS_NAME="L'Atelier Roulant"
export LEGAL_CONTACT_NAME=""
export LEGAL_PHONE=""
export LEGAL_REGISTRATION=""
export LEGAL_EMAIL="me@my.mail"
export ADMIN_USERNAME="admin"
export ADMIN_PASSWORD="mot-de-passe-admin-fort-et-hors-du-depot"
python3 app.py
```

`SMTP_PASSWORD` ne doit pas être inscrit dans le dépôt. Sans configuration
SMTP complète, l’interface signale que l’envoi n’est pas disponible et permet
de réessayer après configuration du serveur.

En production, si le dépôt est installé dans `/opt/latelier-roulant` et que les
PDF sont stockés dans `/opt/latelier-roulant/requests`, définissez explicitement
`REQUEST_STORAGE_DIR=/opt/latelier-roulant/requests`. À défaut, l’application
utilise automatiquement le dossier `requests/` s’il existe à côté de `app.py`,
et conserve `data/requests/` comme repli pour le développement local historique.

### Administration

La page `/admin` est protégée par une authentification HTTP Basic. Elle est
désactivée si `ADMIN_PASSWORD` n’est pas défini. Elle affiche les compteurs web
depuis le démarrage du processus et analyse les PDF présents dans
`REQUEST_STORAGE_DIR` pour présenter le nombre de demandes, les répartitions
par besoin/disponibilité/urgence/statut, le tri de chaque colonne et la liste des documents. Chaque ligne permet d’ouvrir le PDF, de modifier son suivi ou de le supprimer après confirmation. Une modification de statut ou une observation est ajoutée comme nouvelle page dans le PDF lui-même ; aucun fichier de métadonnées séparé n’est créé. Les nouvelles références PDF utilisent 32 caractères hexadécimaux aléatoires (les anciennes références de 12 caractères restent lisibles). La suppression et la mise à jour sont protégées par l’authentification administrateur et agissent uniquement sur le fichier PDF runtime. Le mot de passe administrateur doit rester dans l’environnement systemd ou nginx, jamais dans Git. Les compteurs web sont remis à zéro lors d’un redémarrage du service. La référence du commit est récupérée automatiquement par `app.py` depuis le dépôt Git local, y compris sans exécuter la commande `git` lorsque les métadonnées `.git` sont accessibles.

Le port `587` est utilisé avec STARTTLS par défaut. Le port `465` est aussi
possible avec `SMTP_SSL="1"`.

La section **Menaces** suit les erreurs 4xx par adresse IP pendant la durée de
vie du processus. Elle signale les sondes de chemins sensibles, trois erreurs
4xx consécutives sur plusieurs chemins, ou un volume élevé d’erreurs 4xx en une
minute. Les erreurs 5xx sont affichées dans le trafic mais ne sont pas
considérées seules comme une attaque. La géolocalisation est facultative et
utilise en priorité une base GeoIP2 `.mmdb`, puis accepte les anciennes bases GeoLite City `.dat` via `GEOIP_LEGACY_DB_PATH` (par exemple `/opt/GeoIPv2/GeoLiteCity.dat`) ; sans bibliothèque ou base compatible, le pays et la ville restent affichés comme non disponibles.

La génération du PDF enrichi utilise Pillow et `qrencode` pour intégrer la
photo envoyée et le QR code. Le suivi PDF utilise également `pdfunite`
(paquet `poppler-utils`) afin d’ajouter chaque entrée au document existant.
Le compte du service doit pouvoir écrire dans
`REQUEST_STORAGE_DIR`, qui contient les PDF accessibles par leur référence.
Avec un service systemd utilisant `ProtectSystem=strict`, ajoutez également
`ReadWritePaths=/opt/latelier-roulant/requests` dans la section
`[Service]`.

## Structure

```text
.
├── app.py          # Serveur HTTP Python minimal
├── index.html      # Structure et styles de la page d’accueil
├── admin.html      # Tableau de bord protégé des statistiques
└── js/main.js      # Scène Three.js et interactions visuelles
```

## État du prototype

Cette première version présente l’identité, la promesse et les grandes familles de services. Les coordonnées, zones d’intervention, tarifs, formulaire de contact et mentions légales restent à compléter avant la mise en production.

## Mise en production

Le service Python peut être placé derrière Nginx. Pour un usage public, prévoir notamment :

- un service supervisé (systemd, Docker ou équivalent) ;
- le bind du serveur sur l’interface appropriée ;
- HTTPS et les en-têtes de sécurité côté reverse proxy ;
- les informations légales et les coordonnées commerciales.
