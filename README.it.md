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

Creato il **10-08-2026**. Dodici esperimenti sono stati completati e la tesi è passata da *in fase di test*
a **valutata a livello del prodotto**: il personaggio ha ballato sullo schermo due volte, una volta guidato dal suo rig originale e una volta in modo libero; un mondo creato manualmente ora mantiene l'ultimo fotogramma su due set di dati (E12), tutto valutato dall'occhio del direttore. L'audit dell'arco iniziale è disponibile all'indirizzo
[docs/audit-first-arc.md](docs/audit-first-arc.md); la strategia a partire dal 12-08-2026 è un repository monolitico per l'apprendimento: gli esperimenti dimostrano i possibili percorsi, ma nessuno di essi diventa canonico semplicemente per inerzia (CLAUDE.md).

| | |
|---|---|
| Esperimenti | **E01–E12 completati** (E05 ritirato a causa di una premessa falsa); l'arco di controllo (E01–E06), la riparazione del rig e l'approvazione dello scheletro (E07), **la prima inquadratura animata** (E08), la base della catena pulita (E09), l'adozione di un sistema di guida più denso (E10), il percorso senza controllo, con tre fasi che hanno portato a un fallimento istruttivo (E11), **il percorso libero ottiene un mondo**, e le impostazioni di base vengono ridotte al catalogo 6.0 / uni_pc (E12), **E13 avviato il 13-08-2026**: la sonda del percorso composto, con riferimenti creati per lo strato wan2.7 di riferimento-to-video |
| Percorsi | **due, più uno in fase di test**: il **percorso guidato** (rig renderizzato AAPose → Animate; dimostrato a livello di inquadratura, pronto per la creazione di animazioni AI), il **percorso libero** (fotogramma iniziale creato con GLB → strati I2V / camera alla base 6.0 / uni_pc; l'identità rimane non ancorata e un mondo creato manualmente si mantiene su due set di dati), il **percorso composto** (riferimenti creati per uno strato di blocco dell'identità ospitato: la sonda E13; le note sulla divulgazione sono incluse nelle specifiche in base alla legge sulla divulgazione per ogni percorso) |
| Spesa | 22 sonde nell'arco iniziale, con un costo di 4 crediti ciascuna; l'arco E08–E12 ha richiesto **0 crediti** per ogni invio (fatturazione per ora di GPU) entro i limiti massimi per esperimento: E12 ha utilizzato 4 dei suoi 6 invii consentiti, mentre il resto è rimasto inutilizzato |
| Mappa delle licenze | ogni dipendenza adottata include un **documento di licenza recuperato**: NON VERIFICATO viene trattato come NO; i percorsi attraverso gli strati di terze parti includono anche una **divulgazione per ogni percorso** (regolamentata dal direttore il 12-08-2026); lo scopo dichiarato del sistema è la pubblicazione delle opere dello studio |
| Test | **1005 superati sul rig** (13 saltati, misurati il 13-08-2026), entro i limiti di `-O`; i test CI simulano ciò che un esecutore può fare onestamente: le risorse locali del rig **vengono visibilmente saltate** |
| Stato | **di nuovo pubblico a partire dal 13-08-2026** (privato per scelta dall'11 al 13-08-2026); in fase di organizzazione per il rilascio della **v0.1.0**: la documentazione è completa |

### Cosa viene misurato (l'arco corrente)

- **L'identità si mantiene** — guidata (E08: il volto appare come quello del gemello durante l'inquadratura) *e*
non ancorata (E11, fase 1: ogni caratteristica fino all'ultimo fotogramma senza riferimenti, senza visione ravvicinata, senza segnale di guida). Il giudizio del direttore è la prova definitiva per entrambi.
- **La telecamera obbedisce al controllo esplicito con una precisione di un pixel** sui pesi dello strato della telecamera (E11, fase 3) —
e si muove senza comando quando non riceve istruzioni (E11, fase 1).
- **La densità influenza il segnale, non le prestazioni** (E10): il ricampionamento attenua i passaggi del 41%, mentre le prestazioni del 8,6%; comunque adottato in base al giudizio visivo: un numero maggiore di fotogrammi al secondo risulta migliore.
- **Una riga della licenza non è una rivendicazione sui collegamenti** (E11, fase 2): un modello mappato con licenza Apache e un grafico che non l'ha caricata hanno prodotto 65 fotogrammi di rumore con tutti i controlli verdi. Il sistema Gate PAIR ora esiste.
- **La composizione della scena è volatile in base al set di dati** (E10 / E11): lo stesso testo ha ricomposto il mondo completamente tra diversi set di dati. **Un'affermazione sulla scena richiede due set di dati prima che diventi una proprietà.**
- **Un mondo creato manualmente si mantiene** (E12): una stanza reale nel fotogramma iniziale sopravvive fino all'ultimo fotogramma su due set di dati nello strato della telecamera, con un solo attributo variabile attribuito all'immagine iniziale tramite confronto dei campi. Lo stesso strato che ha mostrato un ambiente vuoto ha mantenuto il vuoto (E11, fase 3): i mondi vengono creati e poi preservati.
- **Il catalogo 6.0 / uni_pc è la base dello strato della telecamera** (E12): la premessa ereditaria 3.5 / euler è stata ridotta al suo livello: con le impostazioni del catalogo, gli stessi set di dati che hanno perso una testa e fatto crescere un arto mantengono la figura fino al fotogramma 80. Il costo è noto: una maggiore aderenza ha imposto la **clausola sull'identità non definita** a un elemento casuale in uno dei due set di dati; il prompt con ambito sul soggetto è la leva promossa.

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
