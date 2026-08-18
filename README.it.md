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
*è sullo schermo e dove si trova*. Armature fornisce esattamente questo: una mesh del personaggio standard viene posizionata e animata in Blender senza interfaccia grafica, e il rendering diventa una sequenza di controllo per ogni fotogramma che il modello video deve seguire; quindi, i video generati dall'IA possono presentare un personaggio principale coerente la cui posizione e postura sono note in ogni fotogramma.

**Armature è la trasformazione da immagine a video con un file GLB al posto di un'immagine.** Tutto ciò che riguarda lo spazio viene creato, e il modello aggiunge vita ad esso. Il risultato finale è un filmato: scene cinematografiche, animazioni dei personaggi, movimenti, qualsiasi tipo di inquadratura. Un gioco è solo uno degli utilizzi possibili di questo filmato, non il limite dello strumento.

Posiziona il tuo personaggio in Blender. Esegui il rendering della sequenza di controllo. Lascia che il modello video aggiunga vita ad essa. La struttura deriva dalla geometria che possiedi; la vita proviene dal modello; l'identità è un elemento denominato e versionato che si trova nel prompt e nello stack di riferimento, e non è mai frutto del caso o di una fortuita combinazione di fotogrammi.

## Installazione

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
```

Il pacchetto installabile è **`armature_core`**: i sistemi per definire l'inquadratura, gli strumenti per risolvere i problemi di orientamento e rotazione, il contratto che specifica le inquadrature, la matematica dei canali e i generatori di payload. Ognuno di essi viene importato tramite un semplice interprete CPython, il che consente di testarli e impacchettarli senza dover avere Blender installato.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Gli script di rendering non sono punti di ingresso della console, ed è una scelta deliberata.**
`render_turnaround.py`, `stage_render.py` e i loro elementi correlati vengono eseguiti all'interno dell'**interprete di Blender**: uno script della console sul tuo sistema Python non potrebbe importare `bpy` e fallirebbe alla prima riga, quindi includerlo sarebbe una promessa che il pacchetto non può mantenere:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Rimangono qui nel repository, dove l'invocazione che funziona è quella scritta.
`armature_core.blender_scene` è il singolo modulo che importa `bpy`; `armature check` lo segnala come `needs-blender` piuttosto che come un difetto.

Il pacchetto npm è un **lanciatore, non una porta**: reimplementare una soglia in un secondo linguaggio è ciò che fa sì che la soglia si sposti, quindi reindirizza al Python che contiene la verità e rifiuta (in modo esplicito, con un codice di errore diverso da zero, tramite l'unico comando che lo risolve) invece di installare qualcosa per tuo conto.

---

## Stato: la tesi viene misurata a livello del prodotto

Fondato il **10-08-2026**. Tredici esperimenti sono stati completati e la tesi è passata da *in fase di test* a **misurata a livello del prodotto**: il personaggio ha ballato sullo schermo, animato tramite il suo rig e libero di muoversi; un mondo creato manualmente si mantiene fino all'ultimo fotogramma con due seed (E12), e **l'identità ora sopravvive a una fase ospitata, addestrata da esseri umani, alimentata solo con riferimenti creati dall'utente** (E13); tutto è giudicato dall'occhio del regista. L'audit dell'arco di fondazione è disponibile all'indirizzo [docs/audit-first-arc.md](docs/audit-first-arc.md); l'approccio a partire dal 2026-08-12 è un monorepositorio in fase di apprendimento: gli esperimenti dimostrano i percorsi, nessun percorso diventa canonico per inerzia (CLAUDE.md).

| | |
|---|---|
| Esperimenti | **E01–E14 completati** (E05 ritirato a causa di una premessa falsa); l'arco di controllo (E01–E06), la riparazione del rig + l'approvazione dello scheletro (E07), **la prima inquadratura animata** (E08), la baseline della catena pulita (E09), l'adozione di un sistema di controllo più denso (E10), il percorso senza controllo, tre fasi che portano a un fallimento istruttivo (E11), **il percorso libero ottiene un mondo** e la baseline 6.0 / uni_pc (E12), **il percorso composto risponde alla sua domanda** (E13: inviato, interrotto con zero costi, riparato da un arco di supporto, riarmato, eseguito e completato in una sola data: l'identità si mantiene secondo il giudizio del regista; i riferimenti guidano i mondi decisi dal modello), **la scena LoRA con prezzo live** (E14: la prova finale: entrambi gli stili LoRA vengono applicati ai pesi derivati; il personaggio si mantiene su `technically_color` e fallisce sulla coppia fotorealistica; il vincitore ha un livello di file servito irrisolvibile e un obbligo di credito, entrambi registrati). |
| Percorsi | **tre, misurati**: il **percorso guidato** (i bastoncini AAPose renderizzati dal rig → Animate; dimostrato a livello di inquadratura, messo in pausa e con licenza chiara per la sua riattivazione), il **percorso libero** (il fotogramma iniziale creato con GLB → livello della telecamera alla baseline 6.0 / uni_pc; l'identità si mantiene non ancorata, un mondo creato manualmente si mantiene su due seed, e il livello della scena LoRA viene misurato in tempo reale: E14), il **percorso composto** (riferimenti creati in una fase di blocco dell'identità ospitata: completato con E13: identità bloccata, cinematografia decisa dal modello con mondi guidati da ciò che i riferimenti contengono; nota sulla divulgazione nelle sue specifiche). |
| Costi | 22 prove nell'arco di fondazione a 4 crediti ciascuna; l'arco E08–E12 ha comportato **0 crediti** (fatturazione per ora di GPU) in base ai limiti per esperimento; **le quattro generazioni di E13 rappresentano la prima spesa con crediti partner del repository, all'interno dell'intervallo predefinito di 424–844**; le due generazioni di E14 hanno comportato **0 crediti partner** con un limite di due generazioni, raggiunto esattamente. |
| Mappa delle licenze | ogni dipendenza adottata ha un **documento di licenza recuperato**; NON VERIFICATO viene trattato come NO; i percorsi attraverso livelli di terze parti includono anche una **divulgazione per percorso** (regolamentata dal regista il 2026-08-12); lo scopo dichiarato del sistema è la pubblicazione dell'arte dello studio. |
| Sistemi di controllo dei costi | **Il sistema CANON** rifiuta un invio a pagamento il cui soggetto non può essere identificato rispetto a un canone leggibile da una macchina: la superficie è la riga, un elemento nullo è un **vuoto piuttosto che un'assenza**, e entrambe le direzioni vengono verificate (il prompt copre il canone; tutto ciò che si trova nel prompt *è* canone). Si attiva **prima** della creazione della directory di output, all'interno di ciascuno dei sette generatori di payload, perché il passaggio irreversibile di cui questo repository è responsabile è la scrittura di un payload. L'alternativa è supportata da dati: `--no-canon` su un soggetto che *ha* un canone viene rifiutato, non accettato. |
| Test | **1351: passaggio sulla piattaforma di ripresa** (14 ripetizioni, misurato il 2026-08-18), identico sotto `-O`; CI verifica ciò che un operatore può fare onestamente: le risorse locali della piattaforma di ripresa **vengono saltate visibilmente**. |
| Stato | **v0.3.0** — il record ottiene una soglia di spesa e un indice che si verifica autonomamente. `armature_core` viene distribuito su PyPI come `armature-studio` e su npm come `@mcptoolshop/armature-studio`, pubblicato da un tag tramite OIDC senza token a lunga durata. |

### Cosa viene misurato (l'arco corrente)

- **L'identità è mantenuta** — guidata (E08: il volto appare come quello del gemello nella ripresa) *e*
non ancorata (E11, onda 1: ogni elemento fino all'ultimo fotogramma senza riferimento, senza visione ravvicinata,
senza segnale di guida). L'occhio del regista è l'arbitro che valuta il record in entrambi i casi.
- **La telecamera obbedisce a un controllo esplicito su un singolo pixel** sui pesi della telecamera (E11, onda 3) —
e si muove senza comando quando non riceve istruzioni (E11, onda 1).
- **La densità influenza il segnale, non le prestazioni** (E10) — il ricampionamento attenua i passaggi del 41%,
le prestazioni dell'8,6%; comunque adottato in base alla valutazione visiva: più fps equivalgono a risultati migliori.
- **Una serie di licenze non è una richiesta di cablaggio** (E11, onda 2) — un modello mappato Apache e un grafico che
non lo ha mai caricato hanno prodotto 65 fotogrammi di rumore con ogni soglia verde. La coppia di soglie ora esiste.
- **La composizione della scena è volatile in base al seme** (E10 / E11) — lo stesso testo ricomposto ha trasformato completamente il mondo
in base ai semi. **Un'affermazione sulla scena richiede due semi prima che diventi una proprietà.**
- **Un mondo coerente è mantenuto** (E12) — una stanza reale nel fotogramma iniziale sopravvive fino all'ultimo fotogramma
su due semi sul livello della telecamera, con un singolo attributo variabile associato all'immagine iniziale tramite la differenza dei campi.
Lo stesso livello ha mantenuto un vuoto di previzualizzazione (E11, onda 3): i mondi vengono creati e poi conservati.
- **Il catalogo 6.0 / uni_pc è il valore di riferimento del livello della telecamera** (E12) — la premessa ereditaria
3.5 / euler è scesa al suo livello: nelle impostazioni del catalogo, gli stessi semi che hanno perso una
parte del corpo e ne hanno fatta crescere un'altra mantengono la figura fino a f80. Il costo è definito: una maggiore aderenza ha imposto
la **clausola di identità non definita** sul gruppo su uno dei due semi; il prompt con ambito soggetto è la leva promossa.
- **L'identità sopravvive a un livello ospitato alimentato solo da riferimenti creati** (E13) — nel riferimento video wan2.7, entrambi i bracci, entrambi i semi, l'artista di legno stilizzato è apparso come
lo stesso personaggio agli occhi del regista tramite un modello addestrato con dati reali. Tre previsioni alla cieca su due sedute si aspettavano che il livello sovrascrivesse la struttura non umana; nessuna era corretta:
il pessimismo unidirezionale su questi modelli è ora registrato come dottrina di calibrazione.
- **I riferimenti guidano i mondi decisi dal modello e dominano il caos dei semi a tale livello**
(E13) — le piastre grigie hanno generato uno studio grigio, un breve video di un bar caldo ha generato un interno caldo e entrambi
i semi per braccio sono stati d'accordo. L'attribuzione del meccanismo (sanguinamento della piastra rispetto al valore predefinito dello studio) è onestamente visibile
in quattro generazioni; un'affermazione di livello di proprietà viene eseguita in base alla legge dei due semi in una fase successiva progettata.
- **Un VIDEO costruito raggiunge i socket VIDEO** (E13) — non esiste alcun percorso di caricamento per le clip, ma
81 fotogrammi creati sono stati assemblati nel grafico (`CreateVideo`) e accettati su un socket video di riferimento. Ogni input di tipo VIDEO sulla piattaforma è in linea di principio raggiungibile dai fotogrammi creati.

### Cosa non lo è

- **Braccia e mani a velocità elevata.** Ancora con problemi a f80 su entrambi i semi e con entrambe le impostazioni (E12).
La leva viene ridefinita come **prima la presentazione** — posizionamento del polso e della telecamera, in base alla
diagnosi dello stesso regista sul file GLB (l'artiglio è un artefatto di proiezione, non un danno alla mesh) —
con una riparazione della mesh come soluzione alternativa, mai come prima mossa.
- **L'affermazione sulla telecamera sui mondi fotografici.** 0/81 rilevamenti dell'orizzonte su tutte e quattro le clip E12 indicano che il rilevatore desidera un punto di giunzione che questo mondo non ha: registrato alla cieca prima
dell'invio, mai convertito in un risultato della telecamera. Uno **strumento per la telecamera senza punti di giunzione** è necessario
prima che venga letto qualsiasi numero di telecamera su una stanza reale.
- **La libreria delle narrazioni** (consultare #7): punti finali della sequenza, prompt per ogni sezione, condizionamento dell'area temporale del video, embedding della telecamera: adottato, con licenza ove necessario, non testato.

Una risposta negativa rimane un successo completo qui: il fallimento di E11 ha portato a tre soglie, due leggi e la forma esatta del lavoro successivo, e la tabella di marcia lo prevedeva prima che arrivassero le prove.

## Come funziona questo repository

- [CLAUDE.md](CLAUDE.md) — come lavorare qui: i tre ruoli, le regole a cui ogni sede deve attenersi e gli elementi non negoziabili (la soglia di licenza, crediti limitati, l'identità viene valutata visivamente).
- [docs/ROADMAP.md](docs/ROADMAP.md) — l'intero processo, sessione per sessione, con i punti critici definiti in anticipo.
- `docs/experiments/` — ogni modifica non banale viene eseguita come un esperimento numerato:
**specifiche prima del lavoro → relazione dopo → valutazione finale dell'esperto.**
- `docs/license-map.md` — la mappa verificata per l'uso commerciale. Nulla entra nella pipeline senza
un documento di licenza recuperato.

Il metodo è ereditato da [facet](../facet), dove è stato pagato: nella sessione iniziale di facet, sei affermazioni ereditarie sono state falsificate, ciascuna in pochi minuti, perché ciascuna era accanto a un codice eseguibile. armature è a valle di facet: facet taglia e dipinge la figura; armature la mette in scena e la esegue.

## Come eseguirlo

`armature_core` si installa da PyPI (sopra); il **registro degli esperimenti e gli strumenti di rendering** sono questo repository, clonati ed eseguiti: nessun servizio, nessun daemon. Ogni strumento viene invocato direttamente:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Piattaforma | Windows 11 sulla piattaforma di ripresa (Omen 45L, RTX 5090). I test ermetici vengono eseguiti anche su `ubuntu-latest` in CI; i test dipendenti da Blender **vengono saltati visibilmente** quando Blender è assente anziché passare silenziosamente. |
| Python | 3.13+ — CI esegue la versione 3.13, l'ambiente virtuale della piattaforma di ripresa esegue la versione 3.14. Le dipendenze dei test sono numpy, pillow, pytest, opencv (fissate alla versione della piattaforma di ripresa, perché i test di rasterizzazione della posa affermano una rasterizzazione stabile nel tempo) e matplotlib |
| Blender | 5.  2, solo versione senza interfaccia grafica. Una sessione GUI attiva produce artefatti senza parametri registrati e una procedura che non riproduce il suo output non è una procedura valida. |
| Nodo | 22, solo per il sito in `site/` |
| Generazione | viene eseguita su Comfy Cloud e inviata dall'operatore; il rendering e la misurazione vengono eseguiti localmente. |

I percorsi assoluti degli strumenti sono incorporati in molti strumenti e documenti: non si tratta di segreti, ma ciò significa che la maggior parte degli strumenti non funzionerà senza modifiche su un'altra macchina.

## Regole fondamentali che definiscono tutto ciò che accade qui

**Non sono ammessi modelli non commerciali, in nessun caso, anche negli esperimenti.** Le licenze CC-BY-NC, esclusivamente per la ricerca e solo per uso accademico, sono esplicitamente vietate. Una conclusione tratta da un modello vietato è una conclusione che deve essere scartata, quindi non può iniziare.

**Le metriche sono strumenti diagnostici; il Direttore giudica.** Che la figura sullo schermo rappresenti lo stesso personaggio è un dato di fatto e nessuna metrica lo approssima. Ogni esperimento di generazione crea una scheda **controllo | output | riferimento | provenienza** prima che venga citato un singolo numero.

**I crediti cloud sono limitati prima di essere utilizzati.** I crediti spesi non possono essere annullati, quindi ogni specifica indica il limite massimo per ciascuna operazione in anticipo.

**Le rotte rivelano cosa le accompagna** (la decisione del Direttore, 2026-08-12). Qualsiasi percorso che attraversa un livello di terze parti documenta l'utilizzo dei dati e la politica di addestramento dei suoi fornitori, i suoi obblighi di divulgazione dei contenuti AI e la sua politica sui watermark, basati sui documenti recuperati dalla mappa delle licenze. Le rotte completamente locali indicano che nulla lascia il sistema. Una rotta senza la relativa nota di divulgazione è incompleta: la prima applicazione utilizza le specifiche E13.

## Modello di fiducia e minacce

La politica completa è [SECURITY.md](SECURITY.md), valutata rispetto all'albero piuttosto che semplicemente affermata. La versione breve:

- **Dati elaborati:** mesh, rendering, video, immagini e JSON su disco locale, nei percorsi specificati nella riga di comando, più `docs/index/armature.db`, un indice SQLite *derivato* dal markdown di questo repository. Le risorse canoniche vengono utilizzate in sola lettura da alberi secondari e non vengono mai scritte.
- **Dati NON elaborati:** nessuna credenziale di alcun tipo: nessuna viene letta, archiviata o trasmessa e una scansione di tutti i file tracciati per chiavi, token, blocchi di chiavi private e assegnazioni di segreti prefissati dai fornitori restituisce zero corrispondenze. **Non vengono raccolti né inviati dati di telemetria, analisi o conteggio dell'utilizzo;** non è prevista alcuna opzione di esclusione perché non c'è nulla da cui escludersi.
- **Traffico di rete in uscita:** nessuna libreria di rete Python viene importata in `tools/` o `tests/`. Due strumenti eseguono comandi esterni su `curl.exe` per scaricare i file elencati in un dump *che si incolla*, da una generazione *inviata*. Nient'altro qui effettua chiamate di rete.
- **Autorizzazioni:** autorizzazioni utente ordinarie. Nessun aumento dei privilegi, nessuna installazione del servizio, nessuna scrittura nel registro o nelle impostazioni di sistema.
- **Gli aspetti critici, divulgati piuttosto che nascosti:** le operazioni sui file non sono eseguite in un ambiente isolato; uno strumento scrive ovunque indichino i suoi argomenti. I fallimenti imprevisti stampano una traccia di errore completa. I rifiuti intenzionali no: ogni controllo genera un errore tipizzato contenente la misurazione che lo ha attivato e **nessuno di essi è un `assert`:** la suite viene eseguita una seconda volta in CI con `-O` per dimostrare che continuano a generare errori.
- **Stato del supporto:** `main` è l'unico stato supportato. Nessun canale di rilascio, nessuna politica di backport, nessun SLA.

**Controllo finale prima della pubblicazione.** [SHIP_GATE.md](SHIP_GATE.md) contiene i controlli rigorosi A–D così come sono effettivamente definiti, con ogni riga verificata insieme alle prove o saltata con la relativa motivazione. Gli elementi di identità del controllo flessibile sono elencati in modo onesto, incluso quello ancora aperto.

## Licenza

MIT: vedere [LICENSE](LICENSE). La licenza di qualsiasi *modello* utilizzato tramite questo strumento è una questione separata, tracciata in `docs/license-map.md`.
