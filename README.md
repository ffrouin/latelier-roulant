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

## Structure

```text
.
├── app.py          # Serveur HTTP Python minimal
├── index.html      # Structure et styles de la page d’accueil
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
