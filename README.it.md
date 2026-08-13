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

---

## Stato: la tesi viene valutata a livello del prodotto

Fondato il **10 agosto 2026**. Tredici esperimenti sono stati conclusi e la tesi è passata dalla fase di *test* a quella di **misurazione a livello di prodotto**: il personaggio ha "ballato" sullo schermo, guidato dal suo sistema di controllo interno ed essendo libero; un mondo creato manualmente si mantiene fino all'ultimo fotogramma su due immagini iniziali (E12), e l'**identità ora sopravvive in una versione ospitata, addestrata da esseri umani, alimentata esclusivamente con riferimenti creati appositamente** (E13) — il tutto giudicato dall'occhio del Direttore. L'audit dell'arco iniziale è disponibile all'indirizzo
[docs/audit-first-arc.md](docs/audit-first-arc.md); l'approccio adottato dal 12 agosto 2026 è un repository monolitico in cui si apprendono nuove tecniche: gli esperimenti dimostrano possibili percorsi, ma nessuno di essi diventa uno standard definitivo (CLAUDE.md).

| | |
|---|---|
| Esperimenti | **E01–E14 conclusi** (E05 ritirato a causa di una premessa falsa) — l'arco di controllo (E01–E06) · riparazione del sistema di controllo + approvazione dello scheletro (E07) · **la prima scena renderizzata** (E08) · la base di riferimento della catena pulita (E09) · adozione di un sistema di guida più denso (E10) · il percorso senza controllo, tre fasi che portano a un fallimento istruttivo (E11) · **il percorso libero ottiene un mondo** e la base 6.0 / uni_pc (E12) · **il percorso composto risponde alla sua domanda** (E13 — inviato, interrotto con spesa pari a zero, riparato da un arco di supporto, riattivato, eseguito e concluso entro una data: l'identità si mantiene secondo il giudizio del Direttore; i riferimenti di base guidano i mondi decisi dal modello) · **la scena LoRA con prezzo dinamico** (E14 — la prova finale: entrambi gli stili LoRA vengono applicati ai pesi derivati; il personaggio si mantiene su `technically_color` e fallisce sulla coppia fotorealistica; il vincitore ottiene una versione irrisolvibile del file e un obbligo di credito, entrambi registrati). |
| Percorsi | **tre, misurati** — il **percorso guidato** (i bastoncini AAPose renderizzati dal sistema di controllo → Animate; dimostrato a livello di scena, messo in pausa e autorizzato per la sua riattivazione) · il **percorso libero** (immagine iniziale creata con GLB → livello della telecamera alla base 6.0 / uni_pc; l'identità si mantiene non ancorata, un mondo creato manualmente si mantiene su due immagini iniziali e la scena LoRA viene misurata in tempo reale — E14) · il **percorso composto** (riferimenti creati appositamente inseriti in una versione ospitata con blocco dell'identità — completato da E13: identità bloccata, cinematografia decisa dal modello con mondi guidati da ciò che contengono i riferimenti; nota di divulgazione nelle sue specifiche). |
| Spesa | 22 prove nell'arco iniziale a 4 crediti ciascuna; l'arco E08–E12 ha registrato **0 crediti** (fatturazione per ora di GPU) entro i limiti stabiliti per ogni esperimento; le **quattro generazioni di E13 rappresentano la prima spesa in crediti da parte di un partner nel repository, all'interno dell'intervallo predefinito di 424–844**; le due generazioni di E14 hanno registrato **0 crediti del partner** con un limite di due generazioni, raggiunto esattamente. |
| Mappa delle licenze | ogni dipendenza adottata include un **documento di licenza recuperato**: NON VERIFICATO viene trattato come NO; i percorsi attraverso gli strati di terze parti includono anche una **divulgazione per ogni percorso** (regolamentata dal direttore il 12-08-2026); lo scopo dichiarato del sistema è la pubblicazione delle opere dello studio |
| Test | **1005 superati sul rig** (13 saltati, misurati il 13-08-2026), entro i limiti di `-O`; i test CI simulano ciò che un esecutore può fare onestamente: le risorse locali del rig **vengono visibilmente saltate** |
| Stato | **v0.1.1 rilasciata il 13 agosto 2026** — lo stato attuale della registrazione, che include la conclusione di E14 (v0.1.0, la prima versione contrassegnata, è stata pubblicata all'inizio della stessa giornata); la registrazione è l'albero dei documenti ed è completa. |

### Cosa viene misurato (l'arco corrente)

- **L'identità si mantiene** — guidata (E08: il volto appare come quello del gemello durante la scena) *e* non ancorata (E11, fase 1: ogni caratteristica fino all'ultimo fotogramma senza riferimenti, senza visione di clip, senza segnale di guida). L'occhio del Direttore è l'arbitro definitivo per entrambi.
- **La telecamera obbedisce a un controllo esplicito su un singolo pixel** sui pesi del livello della telecamera (E11, fase 3) — e si muove in modo non comandato senza di esso (E11, fase 1).
- **La densità influenza il segnale, non le prestazioni** (E10) — il ricampionamento uniforma i passaggi del 41%, mentre le prestazioni del 8,6%; comunque adottato visivamente: più fotogrammi al secondo appaiono meglio.
- **Una controversia sulle licenze non è una pretesa di cablaggio** (E11, fase 2) — un modello mappato su Apache e un grafico che non lo ha mai caricato hanno prodotto 65 fotogrammi di rumore con ogni gate verde. Il Gate PAIR ora esiste.
- **La composizione della scena è volatile rispetto all'immagine iniziale** (E10 / E11) — lo stesso testo ricomposto interamente il mondo tra le diverse immagini iniziali. **Un'affermazione sulla scena richiede due immagini iniziali prima che diventi una proprietà.**
- **Un mondo creato manualmente si mantiene** (E12) — una stanza reale nell'immagine iniziale sopravvive fino all'ultimo fotogramma su due immagini iniziali nel livello della telecamera, con un singolo attributo variabile attribuito all'immagine iniziale tramite la differenza dei campi. Lo stesso livello ha mostrato un vuoto di previz che ha mantenuto il vuoto (E11, fase 3): i mondi vengono creati e poi preservati.
- **La base 6.0 / uni_pc del catalogo è la base di riferimento del livello della telecamera** (E12) — la premessa ereditaria 3.5 / euler è scesa al suo livello: con le impostazioni del catalogo, le stesse immagini iniziali che hanno perso una testa e fatto crescere un arto mantengono la figura fino a f80. Il costo è noto: una maggiore aderenza ha imposto la **clausola di identità non definita** alla folla su una delle due immagini iniziali; il prompt con ambito sul soggetto è la leva promossa.
- **L'identità sopravvive in un livello ospitato alimentato solo da riferimenti creati appositamente** (E13) — sull'esempio wan2.7 di riferimento a video, entrambi i bracci, entrambe le immagini iniziali, l'artista stilizzato in legno è apparso come lo stesso personaggio agli occhi del Direttore. Tre previsioni alla cieca su due sedute si aspettavano che il livello sovrascrivesse la struttura non umana; nessuna aveva ragione: il pessimismo unidirezionale su questi modelli è ora scritto come dottrina di calibrazione.
- **I riferimenti di base guidano i mondi decisi dal modello e dominano il caos delle immagini iniziali in quel livello** (E13) — le piastre grigie hanno generato uno studio grigio, una clip di un bar caldo ha generato un interno caldo ed entrambe le immagini iniziali per braccio sono state d'accordo. L'attribuzione del meccanismo (sanguinamento della piastra rispetto all'impostazione predefinita dello studio) è onestamente aperta in quattro generazioni; un'affermazione di livello di proprietà si basa sulla legge delle due immagini iniziali in un follow-up progettato.
- **Un VIDEO costruito raggiunge i socket VIDEO** (E13) — non esiste alcun percorso di caricamento per le clip, ma 81 fotogrammi creati appositamente assemblati nel grafico (`CreateVideo`) sono stati accettati in un socket video di riferimento. Ogni input di tipo VIDEO sulla piattaforma è, in linea di principio, raggiungibile dai fotogrammi creati appositamente.

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
