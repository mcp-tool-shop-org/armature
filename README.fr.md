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

Un modèle vidéo peut produire du mouvement, de la lumière et de la vie que aucun moteur de rendu ne peut reproduire. On ne peut pas savoir *qui se trouve à l’écran et où il est*. Armature fournit exactement cela : un modèle de personnage standard est mis en scène et animé dans Blender sans interface graphique, et le rendu devient une **séquence de contrôle** par image que le modèle vidéo doit respecter — ainsi, la vidéo générée par l’IA peut présenter un personnage principal constant dont la position et la pose sont connues à chaque image.

**Armature est une transformation d’image en vidéo avec un fichier GLB au lieu d’une image.** Tout ce qui concerne l’espace est créé, et le modèle y ajoute de la vie. Le résultat final est un montage — des scènes de film, des cinématiques, des poses et des mouvements de personnages, n’importe quelle scène. Un jeu vidéo est l’un des consommateurs de ces images, mais il ne définit pas les limites de l’outil.

Mettez en scène votre personnage dans Blender. Effectuez le rendu de la séquence de contrôle. Laissez le modèle vidéo y ajouter de la vie. La structure provient de la géométrie que vous possédez ; la vie provient du modèle ; l’identité est une entité nommée et versionnée qui se trouve dans l’invite et la pile de références — ce n’est jamais un hasard dû à une image réussie.

## Installation

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
```

Le paquet installable est **`armature_core`** : les portes, les solveurs d’encadrement et de rotation, le contrat de spécification des scènes, les calculs des canaux et les générateurs de données. Chacun d’eux s’importe dans un environnement CPython standard, ce qui permet de les tester et de les empaqueter sans que Blender soit présent.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Les scripts de rendu ne sont pas des points d’entrée de la console, et c’est intentionnel.** `render_turnaround.py`, `stage_render.py` et leurs dérivés s’exécutent dans **l’interpréteur propre à Blender** — un script de console sur votre Python ne pourrait pas importer `bpy` et échouerait dès sa première ligne. Par conséquent, l’inclure serait une promesse que le paquet ne peut pas tenir :

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Ils restent ici, dans le dépôt, où l’invocation qui fonctionne est celle qui est écrite. `armature_core.blender_scene` est le module unique qui importe `bpy` ; `armature check` le signale comme `needs-blender` plutôt que comme un défaut.

Le paquet npm est un **lanceur, pas un portage** : réimplémenter un seuil dans un deuxième langage est la façon dont un seuil dérive. Il transmet donc les informations au Python qui contient la vérité et refuse — de manière audible, avec une valeur non nulle, en utilisant la commande unique qui le corrige — plutôt que d’installer quoi que ce soit pour vous.

---

## État : la thèse est mesurée au niveau du produit

Fondé le **10 août 2026**. Treize expériences ont été menées et la thèse est passée de *« en cours de test »* à **« mesurée au niveau du produit »** : le personnage a dansé à l’écran, animé par son propre squelette et libre. Un monde créé manuellement persiste jusqu’à la dernière image sur deux ensembles de données (E12), et **l’identité survit désormais à une couche hébergée, entraînée par des humains, alimentée uniquement par des références créées** (E13) — le tout est jugé par l’œil du réalisateur. L’audit de la phase initiale se trouve sur [docs/audit-first-arc.md](docs/audit-first-arc.md) ; depuis le 12 août 2026, il s’agit d’un monoréférentiel d’apprentissage — les expériences prouvent des pistes, aucune n’est canonique par inertie (CLAUDE.md).

| | |
|---|---|
| Expériences | **E01–E14 terminées** (E05 retirée sur la base d’une prémisse erronée) — la séquence de contrôle (E01–E06) ; réparation du squelette et approbation (E07) ; **la première scène animée** (E08) ; la ligne de base à chaîne propre (E09) ; adoption d’un système d’animation plus dense (E10) ; la voie sans contrôle, trois vagues menant à un échec instructif (E11) ; **la voie libre acquiert un monde** et la ligne de base 6.0 / uni_pc (E12) ; **la voie composée répond à sa question** (E13 — envoyée, arrêtée avec zéro dépense, réparée par une séquence de support, réarmée, exécutée et terminée en une seule date : l’identité est maintenue selon le point de vue du réalisateur ; les références servent de guide pour les mondes décidés par le modèle) ; **la scène LoRA avec tarification en direct** (E14 — la comparaison : les deux modèles LoRA s’appliquent aux poids dérivés ; le personnage est maintenu sur `technically_color` et échoue sur la paire photoréaliste ; le gagnant comporte une couche de fichiers servie non résolvable et une obligation de crédit, toutes deux enregistrées). |
| Voies | **trois, mesurées** — la **voie animée** (squelettes AAPose rendus → Animate ; prouvée au niveau de la scène, mise en pause et autorisée pour sa réactivation) ; la **voie libre** (image GLB créée → couche caméra à la ligne de base 6.0 / uni_pc ; l’identité est maintenue sans ancrage, un monde créé manuellement persiste sur deux ensembles de données, et la scène LoRA est mesurée en direct — E14) ; la **voie composée** (références créées dans une couche d’identité hébergée — validée par E13 : identité verrouillée, cinématographie décidée par le modèle avec des mondes guidés par ce que les références contiennent ; note de divulgation dans sa spécification). |
| Dépenses | 22 tests dans la phase initiale à 4 crédits chacun ; la séquence E08–E12 a nécessité **0 crédit** (facturation horaire du GPU) en vertu des plafonds par expérience ; les quatre générations de E13 représentent les premières dépenses en crédits partenaires du dépôt, dans leur fourchette prédéfinie de 424 à 844 ; les deux générations de E14 ont nécessité **0 crédit partenaire** avec un plafond de deux générations, atteint exactement. |
| Carte des licences | chaque dépendance adoptée comporte un **document de licence récupéré** ; NON VÉRIFIÉ est traité comme AUCUNE ; les parcours à travers les couches tierces comportent également une **divulgation par parcours** (décidée par le réalisateur le 12 août 2026) ; l’objectif déclaré de la porte est de publier l’art du studio. |
| Portes de contrôle des dépenses | **La porte CANON refuse une soumission payante dont le sujet ne peut pas être nommé par rapport à un canon lisible par machine** — la surface est la ligne, un occupant nul est un **trou plutôt qu’une absence**, et les deux directions sont vérifiées (l’invite couvre le canon ; tout ce qui se trouve dans l’invite *est* canon). Elle se déclenche **avant** que le répertoire de sortie ne soit créé, dans chacune des sept générateurs de données, car l’étape irréversible dont ce dépôt est responsable est l’écriture d’une donnée. La solution consiste en une vérification : `--no-canon` sur un sujet qui *a* un canon est refusé, et non honoré. |
| Tests | **1351 images générées sur le système** (14 essais, mesurés le 2026-08-18), identiques sous `-O` ; les tests CI évaluent ce qu’un artiste peut réaliser honnêtement — les éléments locaux du système **sautent visiblement**. |
| État | **v0.3.0** — l’enregistrement reçoit une validation de coût et un index qui s’auto-vérifie. `armature_core` est publié sur PyPI sous la forme `armature-studio` et sur npm sous la forme `@mcptoolshop/armature-studio`, à partir d’une balise par OIDC sans jeton persistant. |

### Ce qui est mesuré (l’arc actuel)

- **L’identité est maintenue** — guidée (E08 : le visage correspond à celui du jumeau dans la séquence) *et* non ancrée (séquence 1 E11 : chaque élément jusqu’à la dernière image, sans référence, sans vision de clip, sans signal de contrôle). Le point de vue du réalisateur est le verdict final pour les deux.
- **La caméra obéit à un contrôle explicite sur un seul pixel** sur les poids de la caméra (séquence 3 E11) — et effectue un zoom non commandé sans cela (séquence 1 E11).
- **La densité influence le signal, pas la performance** (E10) — le rééchantillonnage lisse les étapes de 41 %, la performance de 8,6 % ; adopté malgré tout par jugement visuel : plus d’images par seconde donne un meilleur résultat.
- **Une ligne de licence n’est pas une revendication de câblage** (séquence 2 E11) — un modèle mappé Apache et un graphique qui ne l’a jamais chargé ont produit 65 images de bruit avec chaque image validée. La paire d’images est désormais disponible.
- **La composition de la scène est volatile en fonction de la graine** (E10 / E11) — le même texte recomposé a complètement modifié le monde en fonction des différentes graines. **Une revendication de scène nécessite deux graines avant de devenir une propriété.**
- **Un monde cohérent est maintenu** (E12) — une pièce réelle dans l’image de départ survit jusqu’à la dernière image sur deux graines sur la couche caméra, avec un seul attribut variable attribué à l’image de départ par différence de champ. La même couche a permis d’obtenir une prévisualisation vide qui est restée vide (séquence 3 E11) : les mondes sont créés, puis conservés.
- **Le catalogue 6.0 / uni_pc est la base de référence de la couche caméra** (E12) — la prémisse héritée 3.5 / euler a chuté à son propre niveau : dans les paramètres du catalogue, les mêmes graines qui ont perdu une tête et fait pousser un membre maintiennent la figure jusqu’à f80. Le coût est nommé : une adhérence plus forte a imposé la **clause d’identité non définie** sur le groupe sur une seule des deux graines ; l’invite axée sur le sujet est le levier privilégié.
- **L’identité survit à une couche hébergée alimentée uniquement par des références créées** (E13) — sur wan2.7, la référence vers la vidéo, les deux bras, les deux graines, l’artiste en bois stylisé a traversé un modèle entraîné par un humain et est apparu comme le même personnage du point de vue du réalisateur. Trois prédictions aveugles sur deux sièges s’attendaient à ce que la couche écrase une structure non humaine ; aucune n’était correcte — le pessimisme unidirectionnel concernant ces modèles est désormais consigné sous forme de doctrine d’étalonnage.
- **Les références guident les mondes décidés par le modèle et dominent le chaos des graines sur cette couche** (E13) — les plaques grises ont donné naissance à un studio gris, une séquence vidéo d’un bar chaleureux a donné naissance à un intérieur chaleureux, et les deux graines par bras étaient en accord. L’attribution du mécanisme (débordement de la plaque par rapport à la valeur par défaut du studio) est honnêtement visible après quatre générations ; une revendication de qualité s’applique dans le cadre de la loi des deux graines lors d’un suivi conçu.
- **Une VIDÉO construite atteint les sockets VIDÉO** (E13) — il n’existe pas de chemin de téléchargement pour les séquences vidéo, mais 81 images créées ont été assemblées dans le graphique (`CreateVideo`) et acceptées sur un socket de référence vidéo. Chaque entrée de type VIDÉO sur la plateforme est en principe accessible à partir des images créées.

### Ce qui n’est pas

- **Bras et mains en mouvement.** Échec toujours constaté à f80 sur les deux graines avec les deux paramètres (E12). Le levier est redéfini pour être **axé sur la présentation** — positionnement du poignet et de la caméra, d’après le propre diagnostic du réalisateur sur le fichier GLB (la griffe est un artefact de projection, pas une dégradation du maillage) — avec une chirurgie du maillage comme solution de secours, jamais comme première étape.
- **La revendication de la caméra sur les mondes photographiques.** 0/81 détections d’horizon dans les quatre séquences E12 est un détecteur qui recherche une couture que ce monde n’a pas — enregistré en aveugle avant la soumission, jamais converti en résultat de caméra. Un **instrument de caméra sans couture** doit être disponible avant qu’un nombre de caméra ne soit lu sur une pièce réelle.
- **La bibliothèque de narration** (voir #7) : points d’arrêt, invites par segment, conditionnement de la zone temporelle vidéo, intégrations de caméra — adoptées, sous licence si nécessaire, non testées.

Une réponse négative reste un succès total ici — l’échec cuisant de E11 a permis d’obtenir trois images validées, deux lois et la forme exacte du prochain travail, et la feuille de route indiquait que cela se produirait avant même que des preuves n’apparaissent.

## Comment ce dépôt fonctionne

- [CLAUDE.md](CLAUDE.md) — comment travailler ici : les trois rôles, les règles auxquelles chaque siège est soumis et les éléments non négociables (la validation de la licence, les crédits limités, l’identité est jugée par jugement visuel).
- [docs/ROADMAP.md](docs/ROADMAP.md) — l’ensemble du processus, session par session, avec les points de basculement nommés à l’avance.
- `docs/experiments/` — chaque modification non triviale s’exécute comme une expérience numérotée : **spécification avant le travail → rapport après → décision finale de l’examinateur.**
- `docs/license-map.md` — la carte vérifiée pour un usage commercial. Rien n’entre dans le pipeline sans qu’un document de licence soit récupéré.

La méthode est héritée de [facet](../facet), où elle a été payée : lors de la session fondatrice de facet, six revendications héritées ont été invalidées, chacune en quelques minutes, car chacune était à côté d’un code exécutable. armature est en aval de facet — facet découpe et peint la figure ; armature met en scène et l’exécute.

## Comment l’exécuter

`armature_core` s’installe à partir de PyPI (ci-dessus) ; l’**enregistrement des expériences et les instruments de rendu** sont dans ce dépôt, qui est cloné et exécuté — pas de service, pas de démon. Chaque instrument est invoqué directement :

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Plateforme | Windows 11 sur le système (Omen 45L, RTX 5090). Les tests hermétiques s’exécutent également sur `ubuntu-latest` dans CI ; les tests dépendants de Blender **sautent visiblement** lorsque Blender est absent plutôt que de passer silencieusement. |
| Python | 3.13+ — CI exécute la version 3.13, l’environnement virtuel du système exécute la version 3.14. Les dépendances de test sont numpy, pillow, pytest, opencv (épinglées à la version du système, car les tests de rasterisation de pose affirment une rasterisation stable en termes d’octets) et matplotlib |
| Blender | 5.2, uniquement en mode sans interface graphique. Une session d’interface graphique active génère des artefacts sans paramètres enregistrés, et une recette qui ne reproduit pas son résultat n’est pas une recette valide. |
| Nœud | 22, uniquement pour le site situé à `site/` |
| Génération | s’exécute sur Comfy Cloud et est soumis par l’opérateur ; le rendu et la mesure s’effectuent localement. |

Les chemins d’accès absolus aux équipements sont intégrés à de nombreux outils et documents ; ils ne sont pas secrets, mais cela signifie que la plupart des instruments ne fonctionneront pas sans modification sur une autre machine.

## Règles générales qui définissent tout ici

**Aucun modèle non commercial, jamais, y compris dans les expériences.** Les licences CC-BY-NC, réservées à la recherche et aux usages académiques, sont formellement interdites. Une conclusion tirée sur un modèle interdit est une conclusion qui doit être rejetée, elle ne peut donc pas servir de point de départ.

**Les métriques servent de diagnostics ; c’est le responsable qui juge.** Que la figure affichée à l’écran représente ou non le même personnage est un élément canonique, et aucune métrique n’en est une approximation. Chaque expérience de génération crée une feuille **contrôle | résultat | référence | provenance** avant qu’un seul chiffre ne soit mentionné.

**Les crédits cloud sont limités avant d’être utilisés.** Les crédits dépensés ne peuvent pas être annulés, chaque spécification indique donc son plafond par branche à l’avance.

**Les itinéraires révèlent ce qu’ils contiennent** (décision du responsable, 2026-08-12). Tout itinéraire passant par une couche tierce documente les pratiques de ses fournisseurs en matière d’utilisation des données et de formation, leurs obligations en matière de divulgation du contenu IA et leur politique de filigrane, le tout étant basé sur les documents récupérés dans la carte des licences. Les itinéraires entièrement locaux indiquent que rien n’est envoyé hors de l’environnement. Un itinéraire sans sa note de divulgation est incomplet ; la première application utilise la spécification E13.

## Modèle de confiance et de menace

La politique complète se trouve dans le fichier [SECURITY.md](SECURITY.md), elle est évaluée par rapport à l’arborescence plutôt que simplement affirmée. La version abrégée :

- **Données concernées** : maillages, rendus, vidéos, images et fichiers JSON sur le disque local, aux chemins d’accès que vous spécifiez dans la ligne de commande, ainsi que `docs/index/armature.db`, un index SQLite *dérivé* du fichier markdown de ce dépôt. Les ressources canoniques sont consommées en lecture seule à partir des arborescences sœurs et ne sont jamais écrites.
- **Données non concernées** : aucune donnée d’identification de quelque nature que ce soit : aucune n’est lue, stockée ou transmise, et une analyse de tous les fichiers suivis pour détecter les clés, jetons, blocs de clé privée et affectations de secrets préfixés par le fournisseur ne donne aucun résultat. **Aucune télémétrie, analyse ou comptage d’utilisation** n’est collectée ni envoyée ; il n’y a pas d’option de désactivation car il n’y a rien à désactiver.
- **Échange réseau** : aucune bibliothèque de mise en réseau Python n’est importée dans `tools/` ou `tests/`. Deux outils exécutent des commandes shell vers `curl.exe` pour télécharger les fichiers répertoriés dans un fichier que *vous* collez, à partir d’une génération que *vous* avez soumise. Rien d’autre ici n’effectue d’appel réseau.
- **Autorisations** : autorisations utilisateur standard. Aucune élévation de privilèges, aucune installation de service, aucun enregistrement ou écriture dans les paramètres système.
- **Les aspects délicats, divulgués plutôt que dissimulés** : les opérations sur les fichiers ne sont pas exécutées dans un environnement isolé ; un outil écrit à l’endroit indiqué par ses arguments. Les erreurs inattendues affichent une trace d’exécution brute. Les refus délibérés n’en affichent pas : chaque porte déclenche une erreur typée qui contient la mesure qui l’a déclenchée, et **aucune d’entre elles n’est une `assert`** ; la suite s’exécute une deuxième fois dans `-O` en CI pour prouver qu’elles se produisent toujours.
- **État de prise en charge** : `main` est le seul état pris en charge. Aucun canal de publication, aucune politique de rétroportage, aucun SLA.

**Porte de validation finale.** Le fichier [SHIP_GATE.md](SHIP_GATE.md) contient les portes A à D telles qu’elles sont réellement définies, chaque ligne étant soit vérifiée avec ses preuves, soit ignorée avec la justification correspondante. Les éléments d’identité de la porte souple sont répertoriés honnêtement, y compris celui qui est encore ouvert.

## Licence

MIT : voir [LICENSE](LICENSE). La licence de tout *modèle* utilisé avec cet outil est une question distincte, suivie dans `docs/license-map.md`.
