<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.md">English</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

**Blocchi l'inquadratura. Il modello la esegue.**

**[Pagina di destinazione e manuale →](https://mcp-tool-shop-org.github.io/armature/)**

Un modello video può produrre movimento, luce e vita che nessun motore di rendering è in grado di fare. Non si può stabilire *chi*
*è sullo schermo e dove si trova*. Armature fornisce esattamente questo: una mesh del personaggio canonica viene posizionata e animata in Blender senza interfaccia grafica, e il rendering diventa una sequenza di controllo per ogni fotogramma che il modello video deve seguire; quindi, un video generato dall'IA può presentare un personaggio principale coerente la cui posizione e postura sono note in ogni fotogramma.

**Armature è la trasformazione da immagine a video con un file GLB al posto di un'immagine.** Tutto ciò che riguarda lo spazio viene creato, e il modello vi aggiunge vita. Il risultato finale è un filmato: scene cinematografiche, sequenze d'azione, pose e movimenti dei personaggi, qualsiasi tipo di inquadratura. Un gioco è solo uno degli utilizzi possibili di questo filmato, non il limite dello strumento.

Posiziona il tuo personaggio in Blender. Esegui il rendering della sequenza di controllo. Lascia che il modello video aggiunga vita al risultato. La struttura deriva dalla geometria che possiedi; la vita proviene dal modello; l'identità è un elemento nominato e con versioni, presente nel prompt e nello stack di riferimento: non si tratta mai di una coincidenza fortuita in un singolo fotogramma.

## Installa

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

Il pacchetto installabile è **`armature_core`** — i gate, il sistema di inquadratura e gli algoritmi di calcolo dei movimenti della telecamera, lo script che definisce le specifiche delle riprese, la matematica dei canali e i moduli per la creazione del contenuto. Ognuno di essi importa elementi da un ambiente CPython standard, il che consente di testarli e impacchettarli senza dover avere Blender installato.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Gli script di rendering non sono punti di ingresso della console, ed è una scelta intenzionale.**
`render_turnaround.py`, `stage_render.py` e i loro elementi correlati vengono eseguiti all'interno dell'**interprete di Blender**. Uno script della console Python sul tuo sistema non potrebbe importare `bpy` e fallirebbe alla prima riga; quindi, includerne uno nel pacchetto sarebbe una promessa che il pacchetto non potrebbe mantenere:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

They stay here in the repository, where the invocation that works is the one written down.
`armature_core.blender_scene` is the single module that imports `bpy`; `armature check` reports
it as `needs-blender` rather than as a defect. `check` states what is true of the install you
ran it from, not merely what imports: it resolves the function-local imports too, so a source
checkout or a `--no-deps` install missing OpenCV, Pillow or matplotlib reports `needs-cv2` /
`needs-PIL` rows, prints `UNRESOLVED:` and exits 1 — where it once printed "all modules
resolved" on an install whose drawing functions could not run. A failing row prints the
exception type and message; `--json` carries the same rows under `module_rows`.

Il pacchetto npm è un **lanciatore, non una porta**: reimplementare una soglia in un secondo linguaggio è ciò che fa sì che la soglia si sposti; quindi, indirizza verso il Python che contiene la verità e rifiuta — in modo evidente, con un valore diverso da zero, tramite l'unico comando che lo risolve — invece di installare qualcosa per tuo conto.

---

## Stato: la tesi viene valutata a livello del prodotto

Fondato il **10-08-2026**. Tredici esperimenti sono stati completati e la tesi è passata dallo stato di *in fase di test* a **misurata a livello di prodotto**: il personaggio ha eseguito una danza sullo schermo, guidato dal suo sistema di animazione e libero; un mondo creato manualmente si mantiene fino all'ultimo fotogramma su due configurazioni (E12) e **l'identità ora sopravvive in un ambiente ospitato, addestrato da esseri umani, alimentato solo con riferimenti creati dall'autore** (E13); tutto è valutato dallo sguardo del regista. L'audit dell'arco di fondazione è disponibile all'indirizzo [docs/audit-first-arc.md](docs/audit-first-arc.md); l'approccio a partire dal 2026-08-12 è un monorepository per l'apprendimento: gli esperimenti dimostrano i percorsi; nessun percorso è canonico per inerzia (CLAUDE.md).

| | |
|---|---|
| Esperimenti | **E01–E14 completati** (E05 ritirato a causa di una premessa falsa) — l'arco di controllo (E01–E06) · riparazione del sistema di animazione + approvazione dello scheletro (E07) · **la prima ripresa renderizzata** (E08) · la base della catena pulita (E09) · guida densificata adottata (E10) · il percorso senza controllo, tre fasi che portano a un fallimento istruttivo (E11) · **il percorso libero ottiene un mondo** e la base 6.0 / uni_pc (E12) · **il percorso composto risponde alla sua domanda** (E13 — inviato, interrotto con spesa pari a zero, riparato da un arco di supporto, riarmato, eseguito e completato entro una data: l'identità si mantiene sotto lo sguardo del regista; i riferimenti guidano i mondi decisi dal modello) · **la scena LoRA con prezzo dinamico** (E14 — il test comparativo: entrambi gli stili LoRA si applicano ai pesi derivati; il personaggio si mantiene su `technically_color` e fallisce sulla coppia fotorealistica; il vincitore ha una quota di file serviti irrisolvibile e un obbligo di credito, entrambi registrati) |
| Percorsi | **tre, misurati** — il **percorso guidato** (i bastoncini AAPose renderizzati dal sistema di animazione → Animate; dimostrato a livello di ripresa, messo in pausa e con licenza valida per la sua riattivazione) · il **percorso libero** (fotogramma iniziale creato con GLB → livello della telecamera alla base 6.0 / uni_pc; l'identità si mantiene non ancorata, un mondo creato manualmente si mantiene su due configurazioni e la scena LoRA viene misurata in tempo reale — E14) · il **percorso composto** (riferimenti creati dall'autore inseriti in un ambiente di blocco dell'identità ospitato — completato da E13: identità bloccata, cinematografia decisa dal modello con mondi guidati da ciò che contengono i riferimenti; nota sulla divulgazione nelle sue specifiche) |
| Spesa | 22 prove nell'arco di fondazione a 4 crediti ciascuna; l'arco E08–E12 ha registrato **0 crediti** (addebito per ora di GPU) entro i limiti per esperimento; **le quattro generazioni di E13 rappresentano la prima spesa in crediti del partner nel repository, all'interno dell'intervallo predefinito di 424–844**; le due generazioni di E14 hanno registrato **0 crediti del partner** con un limite di due generazioni, raggiunto esattamente |
| Mappa delle licenze | ogni dipendenza adottata include un **documento di licenza recuperato**: NON VERIFICATO viene trattato come NO; i percorsi attraverso gli strati di terze parti includono anche una **divulgazione per ogni percorso** (regolamentata dal direttore il 12-08-2026); lo scopo dichiarato del sistema è la pubblicazione delle opere dello studio |
| Punti di controllo | **Gate CANON** rifiuta un invio a pagamento il cui oggetto non può essere associato a un canone leggibile da una macchina: la superficie è la riga, un elemento nullo è un **buco piuttosto che un'assenza** e entrambe le direzioni vengono verificate (il prompt copre il canone; tutto nel prompt *è* canone). Si attiva **prima** che venga creata la directory di output, all'interno di ciascuno dei sette generatori di payload, perché il passaggio irreversibile di cui questo repository si occupa è la scrittura di un payload. L'escape è supportato da un censimento: `--no-canon` su un oggetto che *ha* un canone viene rifiutato, non accettato, e poiché ha superato il primo controllo di integrità, è **esplicito in ogni operazione**: ogni generatore stampa `[canon] ARMED: <subject>` e, durante l'escape del censimento, stampa `[canon] UNGATED: <subject> — <the census row's reason>`, in modo che un registro di build distingua un buco convalidato da un oggetto il cui canone non è mai stato scritto; e registra il verdetto sotto `gates.CANON`, in modo che nessun record possa lasciare irrisolta la questione se il canone è stato attivato o meno. |
| Test | **Il codice 8051 viene eseguito correttamente sulla piattaforma di test** (59 iterazioni, misurate il 2026-09-07 dopo la correzione del pin per l’esecuzione delle funzionalità — 7538 nella versione 0.4.0, 7811 dopo la fase D), con risultati identici in `-O` durante la simulazione che ha registrato lo stato; i test CI verificano cosa può effettivamente fare un processo — le risorse locali della piattaforma di test **vengono saltate in modo evidente**. |
| Stato | **Versione 0.4.0 sui repository; questa versione è obsoleta.** L’esecuzione di controllo (832 risultati) rappresenta ancora lo stato pubblicato. Da allora: sono stati apportati miglioramenti visivi nella fase D, quindi è stata eseguita una funzionalità che ha aggiunto un sistema di invio approvato al repository (`build_submit_payload.py`, esecuzione di prova, nessun credito attivo nella suite), è stata ampliata l’interfaccia a riga di comando installata (`canon` / `verify` / `spec` / `donor`) ed è stata registrata la simulazione **34098347849**. Non vengono aggiunte nuove etichette finché non si esegue una nuova versione. |

### Cosa viene misurato (l'arco corrente)

- **L'identità viene mantenuta** — attraverso l'inquadratura (E08: il volto corrisponde a quello del gemello) *e* non ancorata (E11, sequenza 1: ogni dettaglio fino all'ultimo fotogramma, senza riferimenti, senza visione di clip, senza segnale guida). L'occhio del regista è l'arbitro definitivo in entrambi i casi.
- **La telecamera risponde a un controllo esplicito su un singolo pixel** sui pesi della telecamera (E11, sequenza 3) — e si sposta anche senza questo comando (E11, sequenza 1).
- **La densità influenza il segnale, non le prestazioni** (E10) — il ricampionamento attenua i passaggi del 41%, mentre le prestazioni migliorano dell'8,6%; comunque, la decisione finale viene presa visivamente: più fotogrammi al secondo producono un risultato migliore.
- **Una controversia sulle licenze non è una richiesta di cablaggio** (E11, sequenza 2) — un modello Apache mappato e un grafico che non lo ha mai caricato hanno prodotto 65 fotogrammi di rumore con ogni segnale verde. Ora esiste la coppia Gate PAIR.
- **La composizione della scena è volatile in base al seme** (E10 / E11) — lo stesso testo ricomposto ha modificato completamente il mondo tra i diversi semi. **Un'affermazione sulla scena richiede due semi prima di poter essere considerata una proprietà.**
- **Un mondo coerente viene mantenuto** (E12) — una stanza reale nel fotogramma iniziale sopravvive fino all'ultimo fotogramma su due semi nella gerarchia della telecamera, con un singolo attributo variabile assegnato all'immagine iniziale tramite la differenza di campo. La stessa gerarchia ha mantenuto un vuoto in una visualizzazione preliminare (E11, sequenza 3): i mondi vengono creati e poi preservati.
- **Il catalogo 6.0 / uni_pc rappresenta il valore di riferimento per la gerarchia della telecamera** (E12) — l'ereditato presupposto 3.5 / euler è sceso al suo livello inferiore: nelle impostazioni del catalogo, gli stessi semi che hanno perso una parte e ne hanno fatta crescere un'altra mantengono la figura fino a f80. Il costo è noto: una maggiore aderenza ha imposto la **clausola di identità non limitata** alla folla su uno dei due semi; il prompt con ambito sul soggetto è la leva principale.
- **L'identità sopravvive in una gerarchia ospitata alimentata solo da riferimenti creati** (E13) — nel riferimento video wan2.7, entrambi i bracci, entrambi i semi: l'artista stilizzato di legno è apparso attraverso un modello addestrato con dati umani come lo stesso personaggio agli occhi del regista. Tre previsioni alla cieca su due set si aspettavano che la gerarchia sovrascrivesse le strutture non umane; nessuna era corretta: il pessimismo unidirezionale riguardo a questi modelli è ora formalizzato come dottrina di calibrazione.
- **I riferimenti fondamentali guidano i mondi decisi dal modello e dominano il caos dei semi in quella gerarchia** (E13) — le piastre grigie hanno generato un set grigio, una clip di un bar caldo ha generato un interno caldo e entrambi i semi per braccio sono stati d'accordo. L'attribuzione del meccanismo (sanguinamento della piastra rispetto al valore predefinito dello studio) è chiaramente visibile in quattro generazioni; un'affermazione di livello di proprietà si basa sulla legge dei due semi in una fase successiva progettata.
- **Un VIDEO costruito raggiunge i socket VIDEO** (E13) — non esiste alcun percorso di caricamento per le clip, ma 81 fotogrammi creati sono stati assemblati nel grafico (`CreateVideo`) e accettati in un socket video di riferimento. In linea di principio, ogni input di tipo VIDEO sulla piattaforma è accessibile dai fotogrammi creati.

### Cosa non

- **Braccia e mani in movimento rapido.** Ancora problemi con f80 su entrambi i set di dati e con entrambe le impostazioni (E12).
La leva viene riprogettata con un approccio che dà la **priorità alla presentazione** — posizionamento del polso e della telecamera, a partire dalla
diagnosi dello stesso Direttore sul GLB (l'artiglio è un artefatto di proiezione, non un danno alla mesh) —
con interventi sulla mesh come soluzione alternativa, mai come prima opzione.
- **L'affermazione sulla telecamera nei mondi fotografici.** 0/81 rilevamenti dell'orizzonte su tutti e quattro i clip E12 indicano che il sistema di rilevamento richiede una discontinuità che questo mondo non ha — registrazione di un punto cieco prima della
sottomissione, mai convertito in un risultato della telecamera. Uno **strumento per la telecamera senza discontinuità** è necessario
prima che venga letto qualsiasi numero di telecamera in un ambiente reale.
- **La libreria delle narrazioni** (consultare #7): punti finali dei segmenti, istruzioni per ogni segmento, condizionamento dell'area temporale del video, embedding della telecamera — adottato, con licenza ove necessario, non testato.

Una risposta negativa rimane un successo completo qui: il fallimento di E11 ha portato a tre gate, due regole e la forma esatta del lavoro successivo, e la tabella di marcia lo prevedeva prima che arrivassero le prove.

## Come funziona questo repository

- [CLAUDE.md](CLAUDE.md) — come lavorare qui: i tre ruoli, le regole a cui è soggetto ogni ruolo e gli aspetti non negoziabili (il gate della licenza, crediti limitati, l'identità viene valutata visivamente).
- [docs/ROADMAP.md](docs/ROADMAP.md) — l'intero processo di sviluppo, sessione per sessione, con i punti critici identificati in anticipo.
- `docs/experiments/` — ogni modifica significativa viene eseguita come un esperimento numerato:
**specifiche prima del lavoro → report dopo → valutazione finale dell'esperto.**
- `docs/license-map.md` — la mappa verificata per l'uso commerciale. Nulla entra nel flusso di lavoro senza
un documento di licenza recuperato.

Il metodo è ereditato da [facet](../facet), dove è stato pagato: nella sessione di fondazione di facet, sei affermazioni ereditarie sono state falsificate, ciascuna in pochi minuti, perché ognuna era accanto a codice eseguibile. armature è a valle di facet — facet taglia e dipinge la figura; armature la mette in scena ed esegue.

## Come eseguirlo

`armature_core` installa da PyPI (sopra); il **registro dell'esperimento e gli strumenti di rendering** sono questo repository, clonati ed eseguiti: nessun servizio, nessun daemon. Ogni strumento viene invocato direttamente:

```
python tools/<name>.py --help                       # the 55 CPython instruments: measurement, sheets, payload builders
blender -b -P tools/<name>.py -- <args>             # the 21 Blender-side instruments (stage_render, the rig_* tools, the
                                                    # sheet composers): headless only; `python tools/<name>.py` on one of
                                                    # these fails with `No module named 'bpy'`
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, package build + two clean installs (wheel + sdist), site build
```

Ogni strumento, in base a come viene eseguito, con la sua descrizione di una riga: [docs/tools.md](docs/tools.md) (generato dalle docstring, 2026-09-05).

### Lettura di un'interruzione

Ogni strumento CPython esce con **0** quando ha fatto ciò che dice, con **2** in caso di rifiuto deliberato (un punto di controllo attivato, una premessa fallita, un argomento rifiutato) e con **1** in caso di errore. Un rifiuto o un errore stampa esattamente una riga del formato `<TOOL>_HALT {json}`, il cui record contiene sei chiavi: `tool`, `outcome`, `gate`, `error`, `message`, `evidence`, dove `outcome` è una delle tre frasi (`HALTED — a gate fired`, `REFUSED — the tool declined to proceed`, `FAILED — un errore non gestito`), `message` è il testo del rifiuto e `evidence.clause` è la parola leggibile dalla macchina su cui si basa un chiamante; il vocabolario delle clausole è mantenuto dalla suite (`tests/test_refusal_clauses.py`). Il successo è un segnale che lo strumento ottiene tramite un effetto (`BUILD_PAYLOAD_OK`, `RIG_OK`, `ENCODE_OK`, …), mai solo il codice di uscita: `blender -b -P` esce con 0 quando un'eccezione di uno script si propaga, motivo per cui gli strumenti lato Blender contengono la stessa riga di interruzione tramite un gestore locale e cinque degli strumenti del sistema di test scrivono anche un `halt.json` accanto agli output che non hanno prodotto. L'unica implementazione del contratto CPython è `armature_core.parts.run_tool_main`; la sua docstring è la specifica. Il record viene stampato come JSON rigoroso, con la prosa dello strumento lasciata come prosa; dove la codifica del terminale non può gestire un carattere, la riga torna a un escape `\uXXXX` per quel carattere anziché non stampare, e il codice di uscita non viene influenzato in alcun modo.

Tre famiglie di rifiuti sono arrivate con il passaggio della fase C (2026-09-06) e si leggono allo stesso modo ovunque:

- **Uno strumento che sovrascriverebbe gli artefatti di un'esecuzione precedente** — il grafico e il record di una build, i fotogrammi di un rendering — rifiuta con la clausola `output_already_exists` e li nomina (una build nomina entrambi i file e entrambi gli hash); `--overwrite` li sostituisce e il record di successo contiene quindi `out_dir_pre_existed` e `overwrote`. L'unico generatore di invii che si trova sotto il `out_dir_not_empty` di Gate CANON rifiuta un `--out` non vuoto un punto di controllo prima e non accetta alcun flag.
- **Uno strumento che attende** — una codifica, una decodifica, un rendering, un download — stampa una riga di avanzamento in minuscolo su stderr, `<tool> <stage> <done>/<total>  elapsed <e>s  bound <b>s`, prima e dopo l'attesa (e per elemento quando il lavoro è quantificabile); stdout contiene ancora solo l'unica riga di successo o di interruzione. Ogni sottoprocesso contiene un limite derivato dal lavoro e un limite che viene raggiunto è un rifiuto per nome (`ffmpeg_exceeded_the_time_bound`, `downloader_exceeded_the_time_bound`) che nomina il lavoro parziale su disco e non riprova mai: nel percorso a pagamento, un tentativo consuma crediti che non hanno un compensatore.
- **Un punto di controllo che si attiva dopo che la directory di output esiste** lo indica: il rifiuto nomina la directory, indica che contiene un lavoro parziale e non è un risultato e indica il passaggio successivo supportato.

### Esecuzione della suite

```
E:\AI\armature\.venv\Scripts\python.exe -m pytest -q            # from the repo root, on the repo venv — never the system Python
```

Tre leve ambientali, tutte opzionali: `PYTHONPATH=E:/AI/record-index` (la copia di lavoro sorella che i test di indice importano; senza di essa, tali test vengono saltati per nome), `ARMATURE_BLENDER` (l'eseguibile Blender che gli strumenti di guida di Blender eseguono; senza di esso, o al di fuori di questo sistema di test, tali test vengono saltati in modo evidente) e `ARMATURE_GIT` (il git che il test di packaging invoca). La ricetta esatta di CI è il lavoro `python-tests` in `.github/workflows/ci.yml`; `verify.ps1` esegue la stessa suite due volte (una volta sotto `-O`) e quindi la build del pacchetto.

Il blocco `ceiling` di una specifica di seme contiene i numeri che vincolano: `submissions`, la suddivisione per braccio o per ondata, `counted_in`, `note`. La cronologia delle correzioni alla base di questi numeri ha una sede in [specs/ceiling-why-machine-readable.md](specs/ceiling-why-machine-readable.md) (spostata lì da otto copie identiche all'interno della specifica il 2026-09-06; `specs/*.json` è passato da 80.321 a 45.585 byte).

| | |
|---|---|
| Piattaforma | Windows 11 sulla macchina (Omen 45L, RTX 5090). I test ermetici vengono eseguiti anche su `ubuntu-latest` in CI; i test dipendenti da Blender **vengono saltati** quando Blender è assente anziché essere eseguiti silenziosamente. |
| Python | `>=3.11,<3.15` per il pacchetto; l’ambiente CI esegue le versioni 3.11 e 3.13, mentre l’ambiente di test esegue la versione 3.14. `pip install armature-studio` installa numpy, opencv-python-headless, Pillow e matplotlib: queste sono le dipendenze di runtime effettivamente importate dal codice (dichiarate a partire dalla versione wave-3; un’installazione pulita veniva utilizzata per importare `armature_core` e quindi fallire al primo tentativo di rendering). pytest è l’unica dipendenza utilizzata esclusivamente per i test; l’ambiente CI fissa la versione di opencv alla versione utilizzata nell’ambiente di test, perché i test pose-raster verificano la stabilità della rasterizzazione. |
| Blender | 5.2, solo in modalità headless. Una sessione GUI attiva produce artefatti senza parametri registrati e una ricetta che non riproduce il suo output non è una ricetta. |
| Node | il launcher `armature` (`npm/`) viene testato sulle versioni 18 e 22 nell’ambiente CI; il sito all’indirizzo `site/` viene compilato sulla versione 22. |
| Generazione | viene eseguita su Comfy Cloud ed è inviata dall'operatore; il rendering e la misurazione vengono eseguiti localmente. |

I percorsi assoluti della macchina sono incorporati in molti strumenti e documenti: non sono segreti, ma ciò significa che la maggior parte degli strumenti non funzionerà senza modifiche su un'altra macchina.

## Regole fondamentali che definiscono tutto qui

**Nessun modello non commerciale, mai — inclusi negli esperimenti.** Le licenze CC-BY-NC, solo per la ricerca e solo per uso accademico sono esplicitamente vietate. Una conclusione tratta da un modello vietato è una
conclusione che deve essere scartata, quindi non inizia mai.

**Le metriche sono diagnostiche; il Direttore giudica.** Se la figura sullo schermo è lo stesso
personaggio è canonico e nessuna metrica lo approssima. Ogni esperimento di generazione crea una
scheda **controllo | output | riferimento | provenienza** prima che venga citato un singolo numero.

**I crediti cloud sono limitati prima di essere spesi.** I crediti spesi non possono essere annullati, quindi ogni specifica indica il suo limite per ogni braccio in anticipo.

**Le rotte rivelano cosa le accompagna** (la decisione del Direttore, 2026-08-12). Qualsiasi percorso attraverso un livello di terze parti documenta l'utilizzo dei dati e la politica di formazione dei suoi fornitori, i suoi
obblighi di divulgazione dei contenuti AI e la sua politica sui watermark, basati sui documenti recuperati dalla mappa delle licenze. I percorsi completamente locali indicano che nulla lascia la macchina. Un percorso senza la sua nota di divulgazione non è completo: la prima applicazione utilizza le specifiche di E13.

## Modello di fiducia e minaccia

La politica completa è [SECURITY.md](SECURITY.md), misurata rispetto all'albero piuttosto che affermata. La versione breve:

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
- **Support status** — `main` is the only supported state. Tagged releases exist (`v0.4.0`
  is current); there is no backport policy and no SLA.

**Controllo finale prima della pubblicazione.** [SHIP_GATE.md](SHIP_GATE.md) contiene i controlli rigorosi A–D così come sono effettivamente definiti, con ogni riga verificata insieme alle prove o saltata in base alla sua validità. Gli elementi di identità del controllo meno rigido sono elencati in modo trasparente, incluso quello ancora aperto.

## Licenza

MIT — vedere [LICENSE](LICENSE). La licenza di qualsiasi *modello* utilizzato tramite questo strumento è una questione separata, tracciata in `docs/license-map.md`.
