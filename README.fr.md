<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.md">English</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/brand/main/logos/armature/readme.png" alt="armature — you block the shot, the model shoots it" width="820">
</p>

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/armature/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/armature/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/armature/"><img src="https://img.shields.io/badge/Landing_Page-live-blue" alt="Landing Page"></a>
</p>

#

**Vous bloquez le tir. Le modèle effectue le tir.**

**[Page d’accueil et manuel →](https://mcp-tool-shop-org.github.io/armature/)**

Un modèle vidéo peut produire du mouvement, de la lumière et de la vie que aucun moteur de rendu ne peut reproduire. On ne peut pas déterminer *qui se trouve à l’écran et où il est*. Armature fournit exactement cela : un maillage de personnage standard est mis en scène et animé dans Blender sans interface graphique, et le rendu devient une **séquence de contrôle** par image que le modèle vidéo doit respecter. Ainsi, la vidéo générée par l’IA peut présenter un personnage principal constant dont la position et la pose sont connues à chaque image.

**Armature est une transformation d’image en vidéo avec un fichier GLB au lieu d’une image.** Tout ce qui est spatial est créé, et le modèle y ajoute de la vie. Le résultat final est un montage : film, cinématiques, poses et mouvements de personnages, toute scène imaginable. Un jeu n’est qu’un utilisateur possible de ces séquences vidéo, et non une limite à l’outil.

Mettez en scène votre personnage dans Blender. Effectuez le rendu de la séquence de contrôle. Laissez le modèle vidéo y ajouter de la vie. La structure provient de la géométrie que vous possédez ; la vie provient du modèle ; l’identité est une entité nommée et versionnée qui se trouve dans l’invite et la pile de références, et non un simple hasard d’une image réussie.

---

## État : la thèse est mesurée au niveau du produit

Fondé le **10 août 2026**. Douze expériences ont été menées, et la thèse est passée de l’état *en cours de test* à l’état **mesuré au niveau du produit** : le personnage a dansé à l’écran deux fois (une fois en étant contrôlé par son propre squelette, une fois en étant libre), et un monde cohérent conserve la dernière image sur deux ensembles de données (E12), le tout jugé par le regard du réalisateur. Le rapport d’audit de la phase initiale se trouve à l’adresse [docs/audit-first-arc.md](docs/audit-first-arc.md) ; depuis le 12 août 2026, il s’agit d’un dépôt unique pour l’apprentissage : les expériences prouvent les voies possibles, aucune voie n’est canonique par inertie (CLAUDE.md).

| | |
|---|---|
| Expériences | **E01 à E12 terminées** (E05 retirée en raison d’une prémisse erronée) : la séquence de contrôle (E01 à E06) ; réparation du squelette et approbation (E07) ; **la première scène animée** (E08) ; la base de référence avec une chaîne propre (E09) ; adoption d’un système de contrôle plus dense (E10) ; la voie sans contrôle, trois vagues menant à un échec instructif (E11) ; **la voie libre obtient un monde**, et la base de référence des paramètres passe au catalogue 6.0 / uni_pc (E12) ; **E13 lancée le 13 août 2026** : la sonde à voie composée, avec des références créées dans la couche wan2.7 de référence vers vidéo. |
| Voies | **deux, plus une en cours d’étude** : la **voie contrôlée** (bâtonnets AAPose rendus par le squelette → Animer ; prouvée au niveau de la scène, mise en attente pour la création d’animations IA) ; la **voie libre** (première image créée avec un fichier GLB → couches I2V / caméra à la base 6.0 / uni_pc ; l’identité reste non ancrée, et un monde cohérent est maintenu sur deux ensembles de données) ; la **voie composée** (références créées dans une couche d’identité hébergée verrouillée : la sonde E13 ; sa note explicative se trouve dans les spécifications conformément à la loi sur la divulgation par voie). |
| Dépenses | 22 sondes dans la phase initiale, chacune coûtant 4 crédits ; la séquence E08 à E12 a entraîné des dépenses de **0 crédit** à chaque soumission (facturation horaire du GPU) en respectant les plafonds par expérience : E12 a dépensé 4 de ses 6 soumissions autorisées, le reste n’ayant pas été utilisé. |
| Carte des licences | chaque dépendance adoptée est accompagnée d’un **document de licence récupéré** ; NON VÉRIFIÉ est traité comme AUCUNE ; les voies passant par des couches tierces sont également accompagnées d’une **divulgation par voie** (décidée par le réalisateur le 12 août 2026) ; l’objectif déclaré de la passerelle est de publier l’art du studio. |
| Tests | **1 005 tests réussis sur le squelette** (13 sauts, mesurés le 13 août 2026), sous `-O` également ; les tests CI simulent ce qu’un moteur peut réellement faire : les actifs locaux du squelette **sautent visiblement**. |
| État | **de nouveau accessible au public à partir du 13 août 2026** (privé par choix du 11 au 13 août) : organisation en vue d’une **version 0.1.0** ; le registre est l’arborescence des documents, et il est complet. |

### Ce qui est mesuré (la phase actuelle)

- **L’identité est maintenue** : contrôlée (E08 : le visage ressemble à celui du jumeau tout au long de la scène) *et* non ancrée (vague 1 d’E11 : chaque caractéristique jusqu’à la dernière image, sans référence, sans vision par découpage, sans signal de contrôle). Le regard du réalisateur est le verdict officiel pour les deux.
- **La caméra obéit à un contrôle explicite au pixel près** sur les poids de la couche caméra (vague 3 d’E11) et se déplace de manière non commandée sans cela (vague 1 d’E11).
- **La densité fait bouger le signal, pas la performance** (E10) : le rééchantillonnage lisse les étapes de 41 %, la performance de 8,6 %. Adopté malgré tout par jugement visuel : plus d’images par seconde donne une meilleure impression.
- **Une ligne de licence n’est pas une revendication de câblage** (vague 2 d’E11) : un modèle mappé Apache et un graphique qui ne l’a jamais chargé ont produit 65 images de bruit avec chaque porte ouverte. La porte PAIR existe maintenant.
- **La composition de la scène est volatile en fonction des ensembles de données** (E10 / E11) : le même texte a recomposé le monde entièrement entre les ensembles de données. **Une revendication sur une scène nécessite deux ensembles de données avant de devenir une propriété.**
- **Un monde cohérent est maintenu** (E12) : une pièce réelle dans l’image de départ survit jusqu’à la dernière image sur deux ensembles de données dans la couche caméra, avec un seul attribut variable attribué à l’image de départ par différence de champ. La même couche a permis à un espace vide de prévisualisation de rester vide (vague 3 d’E11) : les mondes sont créés, puis maintenus.
- **La base 6.0 / uni_pc du catalogue est la base de référence de la couche caméra** (E12) : la prémisse héritée 3.5 / euler a chuté à son propre niveau : avec les paramètres du catalogue, les mêmes ensembles de données qui ont perdu une tête et fait pousser un membre maintiennent la figure jusqu’à l’image 80. Le coût est connu : une adhérence plus forte a imposé la **clause d’identité non limitée** au groupe sur un des deux ensembles de données ; l’invite à portée du sujet est le levier privilégié.

### Ce qui n’est pas

- **Mouvements des bras et des mains.** Échec persistant à f80 pour les deux ensembles de données et les deux configurations (E12).
Le levier est repensé en mettant l’accent sur la **présentation** : positionnement du poignet et de la caméra, à partir du diagnostic du directeur sur le GLB (la « griffe » est un artefact de projection, pas une dégradation du maillage) — avec une correction du maillage comme solution de repli, jamais comme première étape.
- **L’importance de la caméra dans les mondes photographiques.** 0/81 détections d’horizon sur les quatre clips E12 indique que le détecteur recherche une discontinuité que ce monde n’a pas — il est enregistré comme étant aveugle avant la soumission, et ne sera jamais converti en un résultat de caméra. Un **instrument de caméra sans discontinuité** doit être disponible avant qu’un numéro de caméra ne soit utilisé dans un environnement réel.
- **La bibliothèque des narrations** (voir #7) : points de terminaison, invites par segment, conditionnement de la zone temporelle vidéo, intégrations de caméra — adoptées, sous licence si nécessaire, non testées.

Une réponse négative reste un succès total ici — l’échec flagrant d’E11 a permis d’obtenir trois portes, deux lois et la forme exacte du prochain travail, et le plan prévoyait cela avant que des preuves ne soient disponibles.

## Comment ce dépôt fonctionne

- [CLAUDE.md](CLAUDE.md) — comment travailler ici : les trois rôles, les règles auxquelles chaque personne est soumise et les éléments non négociables (la porte de la licence, les crédits limités, l’identité est jugée visuellement).
- [docs/ROADMAP.md](docs/ROADMAP.md) — l’ensemble du processus, session par session, avec les points de contrôle définis à l’avance.
- `docs/experiments/` — chaque modification non triviale est exécutée comme une expérience numérotée :
**spécification avant le travail → rapport après → décision finale de l’expert.**
- `docs/license-map.md` — la carte vérifiée pour un usage commercial. Rien ne pénètre dans le processus sans qu’un document de licence soit récupéré.

La méthode est héritée de [facet](../facet), où elle a été payée : lors de la session initiale de facet, six affirmations ont été falsifiées en quelques minutes, car chacune était à côté d’un code exécutable. armature est une étape ultérieure de facet — facet découpe et peint la figure ; armature met en scène et l’exécute.

## Comment l’utiliser

Il n’y a rien à installer. Il s’agit d’un dépôt que vous clonez et exécutez — aucun paquet sur un registre, aucun service, aucun démon. Chaque instrument est invoqué directement :

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Plateforme | Windows 11 sur la machine (Omen 45L, RTX 5090). Les tests hermétiques sont également exécutés sur `ubuntu-latest` en CI ; les tests dépendants de Blender **sont visiblement ignorés** lorsque Blender est absent plutôt que d’être exécutés silencieusement. |
| Python | 3.13+ — le CI exécute 3.13, l’environnement virtuel de la machine exécute 3.14. Les dépendances des tests sont numpy, pillow, pytest, opencv (fixées à la version de la machine, car les tests de rasterisation de pose affirment une rasterisation stable en termes d’octets) et matplotlib |
| Blender | 5.2, uniquement en mode sans interface graphique. Une session GUI active produit des artefacts sans paramètres enregistrés, et une recette qui ne reproduit pas sa sortie n’est pas une recette. |
| Node | 22, uniquement pour le site sous `site/` |
| Génération | s’exécute sur Comfy Cloud et est soumise par l’opérateur ; le rendu et la mesure s’effectuent localement. |

Les chemins absolus de la machine sont intégrés dans de nombreux outils et documents — ce ne sont pas des secrets, mais cela signifie que la plupart des instruments ne fonctionneront pas sans modification sur une autre machine.

## Règles permanentes qui façonnent tout ici

**Aucun modèle non commercial, jamais — y compris dans les expériences.** Les licences CC-BY-NC, uniquement pour la recherche et uniquement pour le milieu universitaire sont purement et simplement interdites. Une conclusion tirée sur un modèle interdit est une conclusion qui doit être rejetée, elle ne peut donc pas commencer.

**Les métriques sont des diagnostics ; c’est le directeur qui juge.** Que la figure à l’écran soit le même personnage est canonique, et aucune métrique n’y ressemble. Chaque expérience de génération crée une feuille **contrôle | sortie | référence | provenance** avant qu’un seul nombre ne soit cité.

**Les crédits cloud sont limités avant d’être dépensés.** Les crédits dépensés ne peuvent pas être annulés, donc chaque spécification indique son plafond par branche à l’avance.

**Les itinéraires révèlent ce qui les accompagne** (décision du directeur, 2026-08-12). Tout itinéraire passant par un tiers documente la politique d’utilisation des données et de formation de ses fournisseurs, ses obligations en matière de divulgation du contenu IA et sa politique de filigrane, sur la base des documents récupérés dans la carte des licences. Les itinéraires entièrement locaux indiquent que rien ne quitte la machine. Un itinéraire sans sa note de divulgation est incomplet — la première application utilise les spécifications d’E13.

## Modèle de confiance et de menace

La politique complète se trouve dans [SECURITY.md](SECURITY.md), mesurée par rapport à l’arborescence plutôt que simplement affirmée. La version courte :

- **Données concernées** : maillages, rendus, vidéos, images et fichiers JSON sur le disque local, aux chemins que vous spécifiez dans la ligne de commande, ainsi que `docs/index/armature.db`, un index SQLite *dérivé* du fichier markdown de ce dépôt. Les ressources principales sont utilisées en lecture seule à partir des répertoires frères et ne sont jamais écrites.
- **Données non concernées** : aucune donnée d’identification de quelque nature que ce soit : aucune n’est lue, stockée ou transmise, et une analyse de tous les fichiers suivis pour détecter les clés, jetons, blocs de clé privée et affectations de secrets préfixés par le fournisseur ne donne aucun résultat. **Aucune télémétrie, analyse ou comptage d’utilisation** n’est collectée ni envoyée ; il n’y a pas d’option de désactivation car il n’y a rien à désactiver.
- **Communication réseau** : aucune bibliothèque réseau Python n’est importée dans `tools/` ou `tests/`. Deux outils exécutent une commande externe vers `curl.exe` pour télécharger les fichiers répertoriés dans un fichier *que vous* collez, provenant d’une version *que vous* avez soumise. Rien d’autre ici ne génère de communication réseau.
- **Autorisations** : autorisations utilisateur standard. Pas d’élévation de privilèges, pas d’installation de service, pas d’écriture dans le registre ou les paramètres système.
- **Les aspects délicats, révélés plutôt que dissimulés** : les opérations sur les fichiers ne sont pas exécutées dans un environnement isolé ; un outil écrit à l’endroit indiqué par ses arguments. Les erreurs inattendues affichent une trace d’exécution brute. Les refus délibérés n’envoient pas de message : chaque contrôle déclenche une erreur typée qui contient la mesure qui l’a déclenchée, et **aucune d’entre elles n’est une `assert`** : la suite s’exécute une deuxième fois sous `-O` dans l’environnement CI pour prouver qu’elles se produisent toujours.
- **État de prise en charge** : `main` est le seul état pris en charge. Pas de canal de publication, pas de politique de rétroportage, pas d’accord sur les niveaux de service (SLA).

**Barrière de validation avant la mise en production.** Le fichier [SHIP_GATE.md](SHIP_GATE.md) contient les critères stricts A à D tels qu’ils sont réellement définis, chaque ligne étant soit vérifiée avec ses preuves, soit ignorée avec une justification basée sur son mérite. Les éléments d’identité de la barrière souple sont répertoriés honnêtement, y compris celui qui est encore ouvert.

## Licence

MIT — voir [LICENSE](LICENSE). La licence de tout *modèle* utilisé via cet outil est une question distincte, suivie dans `docs/license-map.md`.
