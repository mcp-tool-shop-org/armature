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

Un modèle vidéo peut produire du mouvement, de la lumière et de la vie que aucun moteur de rendu ne peut reproduire. On ne peut pas déterminer *qui est à l’écran et où il se trouve*. Armature fournit exactement cela : un maillage de personnage standard est mis en scène et animé dans Blender sans interface graphique, et le rendu devient une **séquence de contrôle** par image que le modèle vidéo doit respecter. Ainsi, la vidéo générée par l’IA peut présenter un personnage principal constant dont la position et la pose sont connues à chaque image.

**Armature est une transformation d’image en vidéo avec un fichier GLB au lieu d’une image.** Tout ce qui concerne l’espace est créé, et le modèle y ajoute de la vie. Le résultat est un montage : film, cinématiques, poses et mouvements de personnages, toute scène imaginable. Un jeu n’est qu’un utilisateur de ces séquences vidéo, et non une limite à cet outil.

Mettez en scène votre personnage dans Blender. Effectuez le rendu de la séquence de contrôle. Laissez le modèle vidéo y ajouter de la vie. La structure provient de la géométrie que vous possédez ; la vie provient du modèle ; l’identité est une entité nommée et versionnée qui se trouve dans l’invite et la pile de références, et non un simple hasard d’une image réussie.

## Installer

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
armature canon --help
armature verify --help
```

Le paquet installable est **`armature_core`** : les modules de gestion des points d’entrée et de sortie, les solveurs pour le calcul du trajet, le contrat de spécification des plans, les fonctions mathématiques pour les canaux et les générateurs de données. Chacun d’eux est importé dans un environnement CPython standard, ce qui permet de les tester et de les empaqueter sans avoir besoin de Blender.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Les scripts de rendu ne sont pas des points d’entrée pour la console, et c’est intentionnel.**
`render_turnaround.py`, `stage_render.py` et leurs modules associés s’exécutent dans l’**interpréteur propre à Blender** ; un script de console Python sur votre système ne pourrait pas importer `bpy` et échouerait dès la première ligne. Par conséquent, inclure un tel script serait une promesse que le paquet ne pourrait pas tenir :

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Ils restent ici, dans le dépôt, où l’invocation qui fonctionne est celle qui est écrite.
`armature_core.blender_scene` est le module unique qui importe `bpy` ; `armature check` le signale comme `needs-blender` plutôt que comme un défaut. `check` indique ce qui est vrai de l’installation à partir de laquelle vous l’avez exécutée, et pas seulement ce qui est importé : il résout également les importations locales à la fonction, de sorte qu’une extraction de code source ou une installation `--no-deps` qui manque d’OpenCV, de Pillow ou de matplotlib signale `needs-cv2` / `needs-PIL` lignes, affiche `UNRESOLVED:` et se termine avec le code 1 — alors qu’auparavant, il affichait « tous les modules résolus » lors d’une installation dont les fonctions de dessin ne pouvaient pas s’exécuter. Une ligne qui échoue affiche le type et le message de l’exception ; `--json` contient les mêmes lignes sous `module_rows`.

Le paquet npm est un **lanceur, et non une porte d’entrée** : réimplémenter un seuil dans un deuxième langage est la façon dont un seuil dérive. Il transmet donc les données au Python qui contient la vérité et refuse – de manière claire, avec un code d’erreur différent de zéro, en utilisant la seule commande qui le corrige – plutôt que d’installer quoi que ce soit pour vous.

---

## État : la thèse est mesurée au niveau du produit

Fondé le **10 août 2026**. Treize expériences ont été menées à bien et la thèse est passée de *« en cours d’évaluation »* à **« mesurée au niveau du produit »** : le personnage a dansé à l’écran, animé par son propre squelette, et il est libre. Un monde créé manuellement reste intact jusqu’à la dernière image sur deux ensembles de données (E12), et **l’identité survit désormais grâce à une couche hébergée, entraînée par des humains et alimentée uniquement par des références créées** (E13) — le tout étant jugé par l’œil du réalisateur. L’audit de la phase initiale se trouve sur [docs/audit-first-arc.md](docs/audit-first-arc.md) ; depuis le 12 août 2026, il s’agit d’un monoreposo d’apprentissage : les expériences prouvent les voies possibles, aucune voie n’est canonique par inertie (CLAUDE.md).

| | |
|---|---|
| Expériences | **E01 à E14 terminées** (E05 retirée en raison d’une prémisse erronée) : la phase de contrôle (E01 à E06) ; réparation du squelette et approbation (E07) ; **la première scène animée** (E08) ; la base de référence propre (E09) ; adoption d’un système d’animation plus dense (E10) ; la voie sans contrôle, trois phases menant à un échec instructif (E11) ; **la voie libre acquiert un monde** et la base de référence 6.0 / uni_pc (E12) ; **la voie composée répond à sa question** (E13 : envoyée, arrêtée avec zéro dépense, réparée par une phase de support, réarmée, exécutée et terminée en une seule date : l’identité est préservée selon les critères du réalisateur ; les références servent de base pour orienter les mondes décidés par le modèle) ; **la scène LoRA avec un prix au niveau de la scène** (E14 : la comparaison : les deux modèles LoRA s’appliquent aux poids dérivés ; le personnage est conservé sur `technically_color` et échoue sur la paire photoréaliste ; le gagnant présente une couche de fichiers servie non résolvable et une obligation de crédit, toutes deux enregistrées). |
| Voies | **trois, mesurées** : la **voie animée** (squelette AAPose rendu → Animate ; prouvée au niveau de la scène, mise en pause et autorisée pour sa réactivation) ; la **voie libre** (première image créée avec un fichier GLB → couche caméra à la base de référence 6.0 / uni_pc ; l’identité est conservée sans ancrage, un monde créé manuellement reste intact sur deux ensembles de données, et la scène LoRA est mesurée en direct — E14) ; la **voie composée** (références créées dans une couche d’identité hébergée : graduée par E13 ; identité verrouillée, cinématographie décidée par le modèle avec des mondes orientés par ce que les références contiennent ; note de divulgation dans ses spécifications). |
| Dépenses | 22 tests dans la phase initiale à 4 crédits chacun ; la phase E08 à E12 a entraîné **0 crédit** (facturation horaire du GPU) en vertu des plafonds par expérience ; les **quatre générations de E13 représentent les premières dépenses en crédits partenaires du dépôt, dans la fourchette prédéfinie de 424 à 844** ; les deux générations de E14 ont entraîné **0 crédit partenaire** avec un plafond de deux générations, atteint exactement. |
| Carte des licences | chaque dépendance adoptée comporte un **document de licence récupéré** ; NON VÉRIFIÉ est traité comme AUCUNE ; les voies à travers les couches tierces comportent également une **divulgation par voie** (règle du réalisateur, 12 août 2026) ; l’objectif déclaré de la porte d’entrée est de publier l’art du studio. |
| Points de contrôle | **La porte CANON** refuse une soumission payante dont le sujet ne peut pas être associé à un canon lisible par une machine — la ligne est la surface, un occupant nul est un **trou plutôt qu’une absence**, et les deux directions sont vérifiées (l’invite couvre le canon ; tout ce qui se trouve dans l’invite *est* canon). Elle se déclenche **avant** la création du répertoire de sortie, dans chacun des sept générateurs de charge utile, car l’étape irréversible que ce dépôt gère est l’écriture d’une charge utile. La solution est basée sur un recensement : `--no-canon` pour un sujet qui *a* un canon est refusé, et non accepté — et depuis le premier contrôle de conformité, elle est **très claire pour chaque transaction** : chaque générateur affiche `[canon] ARMED: <subject>`, et lors de la validation du recensement, `[canon] UNGATED: <subject> — <the census row's reason>`, de sorte qu’un journal de construction distingue un trou validé d’un sujet dont le canon n’a jamais été écrit ; et enregistre le verdict sous `gates.CANON`, de sorte qu’aucun enregistrement ne puisse laisser la question de savoir si le canon a été activé ou désactivé sans réponse. |
| Tests | **8051 en cours d’exécution sur le banc d’essai** (59 sauts, mesuré le 2026-09-07 après la correction du problème de la broche feature-execute — 7 538 à la version 0.4.0, 7 811 après l’étape D), identique sous `-O` lors de la répétition qui a enregistré STATUS ; les tests CI simulent ce qu’un exécuteur peut honnêtement faire — les actifs locaux du banc d’essai **sautent visiblement**. |
| État | **v0.5.0** — Amélioration de l’aspect visuel de la phase D et ajout de nouvelles fonctionnalités, en complément de la version v0.4.0. Validation du système de soumission intégré (`build_submit_payload.py`, exécution à titre d’essai), installation de l’interface en ligne de commande `canon` / `verify` / `spec` / `donor`, 8051 tests. Ce n’est pas la version 1.0.0 : le problème concernant la fonctionnalité « filled » est toujours en cours de résolution. |

### Ce qui est mesuré (la phase actuelle)

- **La cohérence visuelle est maintenue** — grâce à des éléments de référence (E08 : l’image montre le jumeau tout au long de la séquence) *et* à l’absence d’éléments de référence (E11, phase 1 : chaque élément est présent jusqu’à la dernière image, sans point de référence, sans vision par clips, sans signal directeur). Le regard du réalisateur est le juge ultime pour les deux.
- **La caméra obéit à un contrôle explicite au niveau d’un seul pixel** sur les paramètres de la caméra (E11, phase 3) — et effectue un zoom non sollicité en l’absence de ces paramètres (E11, phase 1).
- **La densité influence le signal, pas la performance** (E10) — le rééchantillonnage lisse les étapes de 41 %, tandis que la performance est améliorée de 8,6 %; malgré cela, l’évaluation se fait visuellement : un nombre d’images par seconde plus élevé donne une meilleure impression.
- **Une licence n’est pas une revendication concernant le câblage** (E11, phase 2) — un modèle Apache mappé et un graphique qui ne l’a jamais chargé ont produit 65 images de bruit avec chaque image verte. La paire d’images est désormais disponible.
- **La composition de la scène est volatile** (E10 / E11) — le même texte, recomposé, a modifié complètement le monde dans différentes versions. **Une revendication concernant une scène nécessite deux versions avant de devenir une propriété.**
- **Un monde cohérent est maintenu** (E12) — une pièce réelle présente dans la première image persiste jusqu’à la dernière image sur deux versions au niveau des paramètres de la caméra, avec un seul attribut variable attribué à l’image de départ par différence de champ. Le même ensemble de paramètres, appliqué à un espace vide, a maintenu cet espace vide (E11, phase 3) : les mondes sont créés, puis conservés.
- **Le catalogue 6.0 / uni_pc est la base des paramètres de la caméra** (E12) — le paramètre hérité 3.5 / euler a été réduit à sa propre valeur : dans les paramètres du catalogue, les mêmes versions qui ont perdu une partie et en ont fait apparaître une autre maintiennent la figure jusqu’à f80. Le coût est défini : une adhérence plus forte a imposé la **clause d’identité non limitée** au groupe sur une des deux versions ; l’invite axée sur le sujet est le levier privilégié.
- **L’identité survit à un ensemble de paramètres alimenté uniquement par des références créées** (E13) — sur wan2.7, la référence vidéo montre que les deux bras et les deux versions du personnage stylisé en bois sont identiques au regard du réalisateur. Trois prédictions aveugles sur deux ensembles de paramètres s’attendaient à ce que l’ensemble de paramètres écrase la structure non humaine ; aucune n’a eu raison, ce qui indique un pessimisme excessif concernant ces modèles, désormais considéré comme une doctrine d’étalonnage.
- **Les références guident les mondes décidés par le modèle et dominent le chaos des versions dans cet ensemble de paramètres** (E13) — les plaques grises ont donné naissance à un studio gris, un clip de bar chaleureux a donné naissance à un intérieur chaleureux, et les deux versions par bras étaient d’accord. L’attribution du mécanisme (débordement de la plaque par rapport à la valeur par défaut du studio) est honnêtement visible après quatre générations ; une revendication de qualité s’applique dans le cadre de la loi des deux versions lors d’un suivi conçu.
- **Une VIDÉO construite atteint les sockets VIDÉO** (E13) — il n’existe aucun chemin de téléchargement pour les clips, mais 81 images créées ont été assemblées dans le graphique (`CreateVideo`) et acceptées au niveau d’un socket vidéo de référence. En principe, chaque entrée de type VIDÉO sur la plateforme est accessible à partir des images créées.

### Ce qui n’est pas

- **Bras et mains en mouvement.** L’échec persiste à f80 pour les deux versions avec les deux ensembles de paramètres (E12). Le levier est réorienté vers une **approche axée sur la présentation** — positionnement du poignet et de la caméra, basé sur le diagnostic du réalisateur concernant le fichier GLB (la griffe est un artefact de projection, pas un dommage au maillage) — avec une correction du maillage comme solution de secours, jamais comme première étape.
- **La revendication concernant la caméra dans les mondes photographiques.** 0/81 détections d’horizon sur les quatre clips E12 indiquent qu’un détecteur recherche une ligne que ce monde n’a pas — enregistré en aveugle avant la soumission, jamais converti en résultat de caméra. Un **instrument de caméra sans couture** est requis avant qu’aucun numéro de caméra ne soit lu dans une pièce réelle.
- **La bibliothèque de narration** (voir #7) : points de terminaison des séquences, invites par segment, conditionnement temporel vidéo, intégrations de caméra — adoptées, sous licence si nécessaire, non testées.

Une réponse négative reste un succès total ici — l’échec cuisant d’E11 a permis d’obtenir trois images, deux lois et la forme exacte du prochain travail, et le plan de route l’avait annoncé avant que des preuves ne soient disponibles.

## Comment ce dépôt fonctionne

- [CLAUDE.md](CLAUDE.md) — comment travailler ici : les trois rôles, les règles auxquelles chaque poste est soumis et les éléments non négociables (la validation de la licence, les crédits limités, l’identité est jugée visuellement).
- [docs/ROADMAP.md](docs/ROADMAP.md) — l’ensemble du processus, session par session, avec les points de basculement identifiés à l’avance.
- `docs/experiments/` — chaque modification importante est exécutée sous forme d’expérience numérotée : **spécification avant le travail → rapport après → décision finale de l’examinateur.**
- `docs/license-map.md` — la carte vérifiée pour une utilisation commerciale. Rien n’entre dans le pipeline sans un document de licence récupéré.

La méthode est héritée de [facet](../facet), où elle a été financée : lors de la session initiale de facet, six revendications ont été invalidées en quelques minutes, car chacune était à côté d’un code exécutable. Armature est un élément secondaire de facet — facet découpe et peint la figure ; armature met en scène et l’exécute.

## Son exécution

`armature_core` s’installe à partir de PyPI (ci-dessus) ; le **journal d’expériences et les instruments de rendu** sont ce dépôt, cloné et exécuté — pas de service, pas de démon. Chaque instrument est appelé directement :

```
python tools/<name>.py --help                       # the 55 CPython instruments: measurement, sheets, payload builders
blender -b -P tools/<name>.py -- <args>             # the 21 Blender-side instruments (stage_render, the rig_* tools, the
                                                    # sheet composers): headless only; `python tools/<name>.py` on one of
                                                    # these fails with `No module named 'bpy'`
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, package build + two clean installs (wheel + sdist), site build
```

Chaque outil, en fonction de sa manière de fonctionner, avec sa propre description d’une ligne : [docs/tools.md](docs/tools.md) (généré à partir des docstrings, 2026-09-05).

### Lecture d’un arrêt

Chaque instrument CPython se termine avec le code **0** lorsqu’il a fait ce qu’il était censé faire, **2** en cas de refus délibéré (une porte s’est déclenchée, une prémisse a échoué, un argument a été refusé) et **1** en cas de plantage. Un refus ou un plantage affiche exactement une ligne du format `<TOOL>_HALT {json}` dont l’enregistrement contient six clés — `tool`, `outcome`, `gate`, `error`, `message`, `evidence` — où `outcome` est l’une des trois phrases (`HALTED — a gate fired`, `REFUSED — the tool declined to proceed`, `ÉCHEC — une erreur non gérée`), `message` est le texte du refus lui-même, et `evidence.clause` est le mot lisible par une machine sur lequel un appelant se base ; le vocabulaire de la clause est conservé par la suite (`tests/test_refusal_clauses.py`). Le succès est un indicateur que l’outil obtient grâce à un effet (`BUILD_PAYLOAD_OK`, `RIG_OK`, `ENCODE_OK`, …), et non jamais uniquement grâce au code de sortie — `blender -b -P` se termine avec le code 0 lorsqu’une exception d’un script se propage, ce qui explique pourquoi les outils côté Blender contiennent la même ligne d’arrêt via un gestionnaire local et cinq des outils du banc d’essai écrivent également une ligne `halt.json` à côté des résultats qu’ils n’ont pas produits. La seule implémentation du contrat CPython est `armature_core.parts.run_tool_main` ; sa docstring est la spécification. L’enregistrement est affiché sous forme de JSON strict, le propre texte de l’outil étant laissé tel quel ; lorsque l’encodage du terminal ne peut pas prendre en charge un caractère, la ligne revient à un caractère d’échappement `\uXXXX` pour ce caractère plutôt que d’échouer, et le code de sortie n’est affecté d’aucune manière.

Trois familles de refus sont apparues avec l’étape C (2026-09-06) et se lisent de la même manière partout :

- **Un outil qui écrirait sur les artefacts d’une exécution précédente** — le graphique et l’enregistrement d’une construction, les images d’un rendu — refuse avec la clause `output_already_exists` et les nomme (une construction nomme les deux fichiers et les deux hachages) ; `--overwrite` les remplace, et l’enregistrement de succès contient alors `out_dir_pre_existed` et `overwrote`. Le seul générateur de transaction qui se trouve sous la porte CANON `out_dir_not_empty` refuse un `--out` non vide une porte plus tôt et n’accepte aucun indicateur.
- **Un outil qui attend** — un encodage, un décodage, un rendu, un téléchargement — affiche une ligne de progression en minuscules sur stderr, `<tool> <stage> <done>/<total>  elapsed <e>s  bound <b>s`, avant et après l’attente (et par élément lorsque le travail est quantifiable) ; stdout ne contient toujours qu’une seule ligne de succès ou d’arrêt. Chaque sous-processus contient une limite dérivée du travail, et une limite qui est atteinte est un refus par nom (`ffmpeg_exceeded_the_time_bound`, `downloader_exceeded_the_time_bound`) qui nomme le travail partiel sur le disque et ne réessaie jamais — sur le chemin payant, une nouvelle tentative dépense des crédits qui n’ont pas de compensation.
- **Une porte qui se déclenche après l’existence du répertoire de sortie** l’indique : le refus nomme le répertoire, indique qu’il contient un travail partiel et qu’il n’est pas un résultat, et indique la prochaine étape prise en charge.

### Exécution de la suite

```
E:\AI\armature\.venv\Scripts\python.exe -m pytest -q            # from the repo root, on the repo venv — never the system Python
```

Trois leviers d’environnement, tous facultatifs : `PYTHONPATH=E:/AI/record-index` (la copie de travail sœur que les tests d’index importent ; sans cela, ces tests sont ignorés par nom), `ARMATURE_BLENDER` (l’exécutable Blender que les accessoires qui pilotent Blender exécutent ; sans cela, ou en dehors de ce banc d’essai, ces tests sont ignorés visiblement) et `ARMATURE_GIT` (le git que le test d’empaquetage invoque). La recette exacte de CI est la tâche `python-tests` dans `.github/workflows/ci.yml` ; `verify.ps1` exécute la même suite deux fois (une fois sous `-O`), puis construit le package et l’installe dans deux environnements propres (wheel et sdist).

Le bloc `ceiling` des spécifications d’une graine contient les nombres qui lient — `submissions`, la division par bras ou par vague, `counted_in`, `note`. L’historique des corrections qui les sous-tend se trouve à l’adresse [specs/ceiling-why-machine-readable.md](specs/ceiling-why-machine-readable.md) (déplacé là à partir de huit copies identiques dans les spécifications le 2026-09-06 ; `specs/*.json` est passé de 80 321 à 45 585 octets).

| | |
|---|---|
| Plateforme | Windows 11 sur la machine (Omen 45L, RTX 5090). Les tests hermétiques sont également exécutés sur `ubuntu-latest` dans CI ; les tests dépendants de Blender **sautent visiblement** lorsque Blender est absent plutôt que de passer silencieusement. |
| Python | `>=3.11,<3.15`, conformément au paquet ; l’intégration continue exécute les versions 3.11 et 3.13, et l’environnement virtuel du projet exécute la version 3.14. `pip install armature-studio` installe numpy, opencv-python-headless, Pillow et matplotlib, qui sont les dépendances d’exécution réellement importées par le code (déclarées depuis la version 3 du contrôle sanitaire ; une installation propre était utilisée pour importer `armature_core`, puis cela échouait lors du premier appel de dessin). pytest est la seule dépendance utilisée uniquement pour les tests ; l’intégration continue fixe la version d’opencv à celle du projet, car les tests de rasterisation de pose vérifient la stabilité des données rasterisées. |
| Blender | 5.2, uniquement en mode sans tête. Une session GUI active produit des artefacts sans paramètres enregistrés, et une recette qui ne reproduit pas sa sortie n’est pas une recette. |
| Node | Le lanceur `armature` (`npm/`) est testé sur les versions 18 et 22 dans l’intégration continue ; le site situé à l’adresse `site/` est compilé sur la version 22. |
| Génération | s’exécute sur Comfy Cloud et est soumise par l’opérateur ; le rendu et la mesure s’effectuent localement. |

Les chemins d’accès absolus sont intégrés à de nombreux outils et documents ; ils ne sont pas secrets, mais cela signifie que la plupart des modèles ne fonctionneront pas sans modification sur une autre machine.

## Règles fondamentales qui régissent tout ici

**Aucun modèle non commercial, jamais, y compris dans les expériences.** Les licences CC-BY-NC, réservées à la recherche et aux usages universitaires, sont formellement interdites. Une conclusion tirée d’un modèle interdit est une conclusion qui doit être rejetée, elle ne peut donc pas servir de point de départ.

**Les métriques servent de diagnostics ; c’est le responsable qui juge.** Que la figure affichée à l’écran représente ou non le même personnage est un élément canonique, et aucune métrique n’en est une approximation. Chaque expérience de génération crée une feuille **contrôle | sortie | référence | provenance** avant qu’un seul chiffre ne soit mentionné.

**Les crédits cloud sont limités avant d’être utilisés.** Les crédits utilisés ne peuvent pas être annulés, donc chaque spécification indique son plafond par branche à l’avance.

**Les itinéraires indiquent ce qu’ils incluent** (règle du responsable, 2026-08-12). Tout itinéraire passant par une couche tierce documente l’utilisation des données et la politique de formation de ses fournisseurs, ses obligations en matière de divulgation du contenu IA et sa politique de filigrane, le tout étant basé sur les documents récupérés dans la carte des licences. Les itinéraires entièrement locaux indiquent que rien n’est exporté. Un itinéraire sans note de divulgation est incomplet ; la première application utilise la spécification E13.

## Modèle de confiance et de menace

La politique complète se trouve dans [SECURITY.md](SECURITY.md), elle est mesurée par rapport à l’arborescence plutôt que simplement affirmée. La version abrégée :

- **Data touched** — meshes, renders, videos, images and JSON on local disk, at paths you pass
  on the command line, plus `docs/index/armature.db`, a SQLite index *derived* from this repo's
  own markdown. Canonical assets are consumed read-only from sibling trees and never written to.
- **Data NOT touched** — no credentials of any kind: none are read, stored or transmitted, and
  a sweep of every tracked file for provider-prefixed keys, tokens, private-key blocks and
  inline secret assignments returns zero matches. **No telemetry, analytics or usage counting**
  is collected or sent; there is no opt-out because there is nothing to opt out of.
- **Network egress** — no Python networking library is imported anywhere in `tools/` or
  `tests/`. Two tools shell out to `curl.exe` to download the files listed in a dump *you*
  paste in, from a generation *you* submitted. Nothing else here makes a network call.
- **Permissions** — ordinary user permissions. No elevation, no service installation, no
  registry or system-settings writes.
- **The sharp edges, disclosed rather than claimed away** — file operations are not sandboxed;
  a tool writes wherever its arguments say. Unexpected failures print a raw traceback.
  Deliberate refusals do not: every gate raises a typed error carrying the measurement that
  fired it, and **none of them is an `assert`** — the suite runs a second time under `-O` in CI
  to prove they still raise.
- **Support status** — `main` is the only supported state. Tagged releases exist (`v0.5.0`
  is current); there is no backport policy and no SLA.

**Porte de validation finale.** [SHIP_GATE.md](SHIP_GATE.md) contient les portes obligatoires A à D telles qu’elles sont réellement définies, chaque ligne étant soit vérifiée avec ses preuves, soit ignorée avec la justification correspondante. Les éléments d’identité de la porte souple sont répertoriés honnêtement, y compris celui qui est encore ouvert.

## Licence

MIT : voir [LICENSE](LICENSE). La licence de tout *modèle* utilisé via cet outil est une question distincte, suivie dans `docs/license-map.md`.
