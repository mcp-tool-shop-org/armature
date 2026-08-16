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
pip install armature-previz
```

```bash
npm install -g @mcptoolshop/armature   # the same command, as a launcher
```

```bash
armature check
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

Questi rimangono qui, nel repository, dove l'invocazione che funziona è quella scritta.
`armature_core.blender_scene` è il singolo modulo che importa `bpy`; `armature check` lo segnala come `needs-blender` anziché come un difetto.

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
| Test | **1311 superati sul sistema di animazione** (13 saltati, misurati il 2026-08-15 alla versione v0.2.0), anche sotto `-O`; CI esegue ciò che un runner può fare onestamente: le risorse locali del sistema di animazione **vengono saltate in modo visibile** |
| Stato | **v0.2.0 rilasciata il 15-08-2026** — il record diventa una cassetta degli attrezzi installabile: `armature_core` su PyPI come `armature-previz` e su npm come `@mcptoolshop/armature`, pubblicata da un tag tramite OIDC senza token a lunga durata. Il record è ancora l'albero dei documenti ed è ancora completo |

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

Non c'è nulla da installare. Questo è un repository che si clona ed esegue: nessun pacchetto su alcun registro, nessun servizio, nessun demone. Ogni strumento viene invocato direttamente:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Piattaforma | Windows 11 sulla macchina (Omen 45L, RTX 5090). I test ermetici vengono eseguiti anche su `ubuntu-latest` in CI; i test dipendenti da Blender **vengono saltati** quando Blender è assente anziché essere eseguiti silenziosamente. |
| Python | 3.13+ — CI esegue la versione 3.13, l'ambiente virtuale della macchina esegue la versione 3.14. Le dipendenze di test sono numpy, pillow, pytest, opencv (fissate alla versione della macchina, perché i test di rasterizzazione della posa richiedono una rasterizzazione stabile) e matplotlib |
| Blender | 5.2, solo in modalità headless. Una sessione GUI attiva produce artefatti senza parametri registrati e una ricetta che non riproduce il suo output non è una ricetta. |
| Node | 22, solo per il sito su `site/` |
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

- **Dati interessati** — mesh, rendering, video, immagini e file JSON sul disco locale, nei percorsi specificati tramite la riga di comando, più `docs/index/armature.db`, un indice SQLite *derivato* dal markdown del presente repository. Le risorse principali vengono utilizzate in modalità sola lettura da directory correlate e non vengono mai scritte.
- **Dati NON interessati** — nessuna credenziale di alcun tipo: non vengono lette, archiviate o trasmesse e una scansione di tutti i file tracciati alla ricerca di chiavi, token, blocchi di chiave privata e assegnazioni di segreti con prefisso del fornitore restituisce zero corrispondenze. **Non vengono raccolti né inviati dati di telemetria, analisi o conteggio dell'utilizzo**; non è prevista alcuna opzione per disattivare la raccolta dei dati perché non c'è nulla da disattivare.
- **Comunicazione in uscita dalla rete** — nessuna libreria di rete Python viene importata in `tools/` o `tests/`. Due strumenti eseguono comandi esterni su `curl.exe` per scaricare i file elencati in un dump che *voi* incollate, da una versione che *voi* avete inviato. Nient'altro qui effettua chiamate di rete.
- **Autorizzazioni** — autorizzazioni utente standard. Nessun aumento dei privilegi, nessuna installazione di servizi, nessuna scrittura nel registro di sistema o nelle impostazioni di sistema.
- **Aspetti critici, resi noti anziché nascosti** — le operazioni sui file non sono eseguite in un ambiente isolato; uno strumento scrive ovunque lo indichino i suoi argomenti. In caso di errori imprevisti, viene visualizzata una traccia di errore completa. I rifiuti intenzionali non vengono segnalati: ogni controllo genera un errore tipizzato che contiene la misurazione che l'ha attivato e **nessuno di essi è un `assert`**; la suite viene eseguita una seconda volta in `-O` nell'ambiente CI per dimostrare che continuano a generare errori.
- **Stato del supporto** — `main` è l'unico stato supportato. Nessun canale di rilascio, nessuna politica di backport, nessun SLA.

**Controllo finale prima della pubblicazione.** [SHIP_GATE.md](SHIP_GATE.md) contiene i controlli rigorosi A–D così come sono effettivamente definiti, con ogni riga verificata insieme alle prove o saltata in base alla sua validità. Gli elementi di identità del controllo meno rigido sono elencati in modo trasparente, incluso quello ancora aperto.

## Licenza

MIT — vedere [LICENSE](LICENSE). La licenza di qualsiasi *modello* utilizzato tramite questo strumento è una questione separata, tracciata in `docs/license-map.md`.
