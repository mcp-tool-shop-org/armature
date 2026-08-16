<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.md">English</a>
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

**Você bloqueia o disparo. O modelo realiza o disparo.**

**[Página inicial e manual →](https://mcp-tool-shop-org.github.io/armature/)**

Um modelo de vídeo pode produzir movimento, luz e vida que nenhum renderizador consegue. Não se pode determinar *quem está na tela e onde está posicionado*. O armature fornece exatamente isso: uma malha de personagem canônica é preparada e animada no Blender sem interface gráfica, e o render se torna uma **sequência de controle** por quadro que o modelo de vídeo deve obedecer — para que o vídeo gerado por IA possa apresentar um personagem principal consistente cuja posição e pose sejam conhecidas em cada quadro.

**O armature é a conversão de imagem para vídeo com um arquivo GLB em vez de uma imagem.** Tudo relacionado ao espaço é criado, e o modelo adiciona vida a ele. O resultado final é uma filmagem — filme, cenas, poses e movimentos de personagens, qualquer tipo de cena. Um jogo é apenas um dos consumidores dessa filmagem, nunca o limite da ferramenta.

Prepare seu personagem no Blender. Renderize a sequência de controle. Deixe o modelo de vídeo adicionar vida a ela. A estrutura vem da geometria que você possui; a vida vem do modelo; a identidade é algo nomeado e versionado que está presente no prompt e na pilha de referências — nunca um acidente em um quadro sortudo.

## Instalar

```bash
pip install armature-previz
```

```bash
npm install -g @mcptoolshop/armature   # the same command, as a launcher
```

```bash
armature check
```

O pacote instalável é **`armature_core`** — os módulos de definição, os módulos de enquadramento e resolução de inversão, o contrato de especificação de cena, as operações matemáticas dos canais e os criadores de carga. Cada um deles é importado usando CPython padrão, o que permite que sejam testados e empacotados sem a necessidade do Blender.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Os scripts de renderização não são pontos de entrada para o console, e isso é intencional.**
`render_turnaround.py`, `stage_render.py` e seus módulos relacionados são executados dentro do **próprio interpretador do Blender** — um script de console no seu Python não conseguiria importar `bpy` e falharia na primeira linha; portanto, incluir um seria uma promessa que o pacote não poderia cumprir:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Eles permanecem aqui, no repositório, onde a invocação que funciona é aquela que está escrita. `armature_core.blender_scene` é o único módulo que importa `bpy`; `armature check` relata isso como `needs-blender`, em vez de um defeito.

O pacote npm é um **lançador, não uma porta**: reimplementar um limite em uma segunda linguagem é a forma como um limite se desvia, então ele encaminha para o Python que contém a verdade e recusa — de forma clara, com um código de erro diferente de zero, usando o único comando que o corrige — em vez de instalar qualquer coisa em seu nome.

---

## Estado: a tese é medida no nível do produto

Fundada em **10 de agosto de 2026**. Treze experimentos foram concluídos e a tese passou de *em teste* para **medida no nível do produto**: o personagem dançou na tela, controlado por seu próprio sistema, e livre; um mundo construído mantém-se até o último quadro em duas amostras (E12), e **a identidade agora sobrevive a uma camada hospedada, treinada por humanos, alimentada apenas com referências autorais** (E13) — tudo avaliado pelo olhar do Diretor. A auditoria do arco inicial está em
[docs/audit-first-arc.md](docs/audit-first-arc.md); a postura desde 12 de agosto de 2026 é um monorepositorio de aprendizado — os experimentos comprovam caminhos, nenhum caminho é canônico por impulso (CLAUDE.md).

| | |
|---|---|
| Experimentos | **E01–E14 concluídos** (E05 retirado com base em uma premissa falsa) — o arco de controle (E01–E06) · reparo do sistema + aprovação do esqueleto (E07) · **a primeira cena renderizada** (E08) · a linha de base limpa (E09) · direção densificada adotada (E10) · o caminho sem controle, três ondas para uma falha instrutiva (E11) · **o caminho livre ganha um mundo** e a linha de base 6.0 / uni_pc (E12) · **o caminho composto responde à sua pergunta** (E13 — enviado, interrompido com gasto zero, reparado por um arco de suporte, reativado, executado e concluído dentro de uma data: a identidade mantém-se sob o olhar do Diretor; as referências orientam os mundos decididos pelo modelo) · **a cena LoRA com preço dinâmico** (E14 — o teste comparativo: ambas as LoRAs de estilo são vinculadas aos pesos derivados; o personagem mantém-se em `technically_color` e falha no par fotorrealista; o vencedor carrega uma camada de arquivo servido irresolvível e uma obrigação de crédito, ambos registrados) |
| Caminhos | **três, medidos** — o **caminho direcionado** (palitos AAPose renderizados pelo sistema → Animate; comprovado no nível da cena, pausado e com licença liberada para sua retomada) · o **caminho livre** (quadro inicial criado em GLB → camada de câmera na linha de base 6.0 / uni_pc; a identidade mantém-se sem ancoragem, um mundo construído mantém-se em duas amostras, e a cena LoRA é medida dinamicamente — E14) · o **caminho composto** (referências autorais em uma camada de identidade hospedada — graduado por E13: identidade bloqueada, cinematografia decidida pelo modelo com mundos orientados pelo que as referências carregam; nota de divulgação em suas especificações) |
| Gastos | 22 sondas no arco inicial a 4 créditos cada; o arco E08–E12 mediu **0 créditos** (cobrança por hora de GPU) sob tetos por experimento; **as quatro gerações de E13 são os primeiros gastos com créditos de parceiro do repositório, dentro da faixa pré-definida de 424–844**; as duas gerações de E14 mediram **0 créditos de parceiro** em um teto de duas gerações, atingido exatamente |
| Mapa de licenças | cada dependência adotada possui um **documento de licença recuperado**; NÃO VERIFICADO é tratado como NÃO; caminhos através de camadas de terceiros também possuem **divulgação por caminho** (regra do Diretor, 12 de agosto de 2026); o propósito declarado da porta de entrada é a publicação da arte do estúdio. |
| Testes | **1311 testes aprovados no conjunto de animação** (13 saltos, medidos em 2026-08-15 na versão v0.2.0), também sob `-O`; os testes automatizados simulam o que um executor pode fazer honestamente — os recursos locais do conjunto de animação **são ignorados visivelmente**. |
| Status | **v0.2.0 lançado em 2026-08-15** — o registro se torna um kit de ferramentas instalável: `armature_core` no PyPI como `armature-previz` e no npm como `@mcptoolshop/armature`, publicado a partir de uma tag por OIDC sem nenhum token de longa duração em lugar algum. O registro ainda é a árvore de documentação e continua completo. |

### O que é medido (o arco atual)

- **A identidade mantém-se** — direcionada (E08: o rosto se assemelha ao do gêmeo ao longo da cena) *e* não ancorada (onda 1 de E11: cada característica até o último quadro sem referência, sem visão de recorte, sem sinal de direção). O olhar do Diretor é o veredicto registrado em ambos.
- **A câmera obedece a um controle explícito para um único pixel** nos pesos da camada da câmera (onda 3 de E11) — e se move não solicitado sem ele (onda 1 de E11).
- **A densidade move o sinal, não o desempenho** (E10) — o reamostragem suaviza os passos em 41%, o desempenho em 8,6%; adotado mesmo assim pelo olhar: mais fps resulta melhor.
- **Uma disputa de licença não é uma reivindicação de fiação** (onda 2 de E11) — um modelo mapeado Apache e um gráfico que nunca o carregou produziram 65 quadros de ruído com cada porta verde. A porta PAIR agora existe.
- **A composição da cena é volátil em relação à semente** (E10 / E11) — texto idêntico recompôs o mundo por completo entre as sementes. **Uma reivindicação de cena precisa de duas sementes antes que seja uma propriedade.**
- **Um mundo construído mantém-se** (E12) — uma sala real no quadro inicial sobrevive até o último quadro em duas sementes na camada da câmera, com um único atributo variável atribuído à imagem inicial por diferença de campo. A mesma camada apresentou um vazio de pré-visualização que manteve um vazio (onda 3 de E11): os mundos são autorais e depois mantidos.
- **O catálogo 6.0 / uni_pc é a linha de base da camada da câmera** (E12) — a premissa herdada 3.5 / euler caiu em seu próprio nível: nas configurações do catálogo, as mesmas sementes que perderam uma cabeça e cresceram um membro mantêm a figura até f80. O custo é nomeado — uma maior adesão impulsionou a **cláusula de identidade não definida** para o público em uma das duas sementes; o prompt com escopo no assunto é a alavanca promovida.
- **A identidade sobrevive a uma camada hospedada alimentada apenas com referências autorais** (E13) — na referência wan2.7 para vídeo, ambos os braços, ambas as sementes, o artista de madeira estilizado surgiu como o mesmo personagem sob o olhar do Diretor através de um modelo treinado por humanos. Três previsões cegas em duas sessões esperavam que a camada sobrescrevesse estruturas não humanas; nenhuma estava certa — o pessimismo unidirecional sobre esses modelos agora está registrado como doutrina de calibração.
- **As referências orientam os mundos decididos pelo modelo e dominam o caos da semente nessa camada** (E13) — placas cinzas geraram um estúdio cinza, um clipe de bar quente gerou um interior quente e ambas as sementes por braço concordaram. A atribuição do mecanismo (sangramento da placa vs. padrão do estúdio) está honestamente aberta em quatro gerações; uma reivindicação de nível de propriedade é executada sob a lei das duas sementes em um acompanhamento projetado.
- **Um VÍDEO construído atinge os sockets de VÍDEO** (E13) — não existe um caminho de upload para clipes, mas 81 quadros autorais montados no gráfico (`CreateVideo`) foram aceitos em um socket de vídeo de referência. Cada entrada do tipo VÍDEO na plataforma é, em princípio, acessível a partir de quadros autorais.

### O que não

- **Braços e mãos em alta velocidade.** Ainda com falhas em f80 em ambas as amostras, em ambos os ajustes (E12).
A alavanca é redefinida com foco na **apresentação** — posicionamento do pulso e da câmera, a partir do
diagnóstico do Diretor no GLB (a "garra" é um artefato de projeção, não dano à malha) —
com correção da malha como último recurso, nunca o primeiro passo.
- **A reivindicação da câmera nos mundos fotográficos.** 0/81 detecções de horizonte em todos os quatro clipes E12
indicam que o detector precisa de uma "costura" que este mundo não tem — registrado como cego antes do
envio, nunca convertido em um resultado da câmera. Um **instrumento de câmera sem costuras** é necessário
antes que qualquer número de câmera seja lido em um ambiente real.
- **A prateleira de narração** (consulte #7): pontos finais dos trechos, prompts por trecho, condicionamento da área de tempo do vídeo,
incorporações da câmera — adotado, licenciado quando necessário, não testado.

Uma resposta negativa ainda é um sucesso total aqui — a falha crítica do E11 gerou três "gates", duas leis e
a forma exata do próximo trabalho, e o roteiro dizia que isso aconteceria antes de qualquer evidência surgir.

## Como este repositório funciona

- [CLAUDE.md](CLAUDE.md) — como trabalhar aqui: os três papéis, as regras sob as quais cada um opera e
os pontos não negociáveis (o "gate" da licença, créditos limitados, a identidade é avaliada visualmente).
- [docs/ROADMAP.md](docs/ROADMAP.md) — todo o processo de construção, sessão por sessão, com os gatilhos de desvio nomeados antecipadamente.
- `docs/experiments/` — cada alteração não trivial é executada como um experimento numerado:
**especificação antes do trabalho → relatório após → decisão final do consultor.**
- `docs/license-map.md` — o mapa verificado para uso comercial. Nada entra no pipeline sem
um documento de licença recuperado.

O método é herdado de [facet](../facet), onde foi pago: na sessão inaugural do "facet", seis reivindicações herdadas foram falsificadas, cada uma em minutos, porque cada um estava ao lado de
código executável. "armature" está a jusante de "facet" — "facet" corta e pinta a figura; "armature" a organiza e
a executa.

## Executando-o

Não há nada para instalar. Este é um repositório que você clona e executa — nenhum pacote em qualquer
repositório, nenhum serviço, nenhum daemon. Cada instrumento é invocado diretamente:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Plataforma | Windows 11 na máquina (Omen 45L, RTX 5090). Os testes herméticos também são executados em `ubuntu-latest` no CI; os testes dependentes do Blender **são ignorados visivelmente** quando o Blender está ausente, em vez de serem executados silenciosamente. |
| Python | 3.13+ — o CI executa a versão 3.13, e o ambiente virtual da máquina executa a versão 3.14. As dependências de teste são numpy, pillow, pytest, opencv (fixadas na versão da máquina, porque os testes de rasterização de pose afirmam uma rasterização estável em termos de bytes) e matplotlib |
| Blender | 5.2, apenas no modo "headless". Uma sessão GUI ativa produz artefatos sem parâmetros registrados, e uma receita que não reproduz sua saída não é uma receita. |
| Node | 22, apenas para o site em `site/` |
| Geração | executado no Comfy Cloud e enviado pelo operador; a renderização e a medição são executadas localmente. |

Caminhos absolutos da máquina estão incorporados em muitas ferramentas e documentos — eles não são segredos, mas significam que a maioria dos instrumentos não será executada sem modificações em outra máquina.

## Regras permanentes que moldam tudo aqui

**Nenhum modelo não comercial, nunca — incluindo em experimentos.** Licenças CC-BY-NC, apenas para pesquisa e
uso acadêmico são proibidas de forma explícita. Uma conclusão tirada com base em um modelo proibido é uma
conclusão que deve ser descartada, portanto, ela nunca começa.

**As métricas são diagnósticos; o Diretor julga.** Se a figura na tela é o mesmo
personagem, isso é canônico, e nenhuma métrica se aproxima disso. Cada experimento de geração cria uma
folha **controle | saída | referência | proveniência** antes que um único número seja citado.

**Os créditos da nuvem são limitados antes de serem gastos.** Os créditos gastos não podem ser desfeitos, portanto, cada especificação
indica seu limite por "braço" com antecedência.

**As rotas revelam o que as acompanha** (a decisão do Diretor, 2026-08-12). Qualquer rota
através de uma camada de terceiros documenta o uso de dados e a postura de treinamento de seus provedores, suas
obrigações de divulgação de conteúdo de IA e sua política de marca d'água, com base nos documentos recuperados do mapa de licenças. As rotas totalmente locais afirmam que nada sai da máquina. Uma rota sem sua
nota de divulgação não está completa — a primeira aplicação usa a especificação do E13.

## Modelo de confiança e ameaças

A política completa está em [SECURITY.md](SECURITY.md), medida em relação à árvore, e não apenas afirmada.
Na forma resumida:

- **Dados acessados** — modelos, renderizações, vídeos, imagens e JSON no disco local, nos caminhos que você especifica na linha de comando, mais `docs/index/armature.db`, um índice SQLite *derivado* do próprio arquivo Markdown deste repositório. Os recursos canônicos são consumidos em modo somente leitura a partir de árvores adjacentes e nunca são gravados.
- **Dados NÃO acessados** — nenhuma credencial de qualquer tipo: nenhuma é lida, armazenada ou transmitida, e uma verificação de todos os arquivos rastreados para identificar chaves, tokens, blocos de chave privada e atribuições de segredos com prefixo do provedor retorna zero correspondências. **Nenhuma telemetria, análise ou contagem de uso** é coletada ou enviada; não há opção de desativação porque não há nada para desativar.
- **Comunicação de rede** — nenhuma biblioteca de rede Python é importada em nenhum lugar em `tools/` ou `tests/`. Duas ferramentas executam comandos externos para `curl.exe` a fim de baixar os arquivos listados em um arquivo *que você* cola, de uma geração *que você* enviou. Nada mais aqui faz uma chamada de rede.
- **Permissões** — permissões de usuário comuns. Sem elevação de privilégios, sem instalação de serviço, sem gravações no registro ou nas configurações do sistema.
- **Os pontos críticos, divulgados em vez de ocultados** — as operações de arquivo não são executadas em um ambiente isolado; uma ferramenta grava onde seus argumentos indicam. Falhas inesperadas imprimem um rastreamento bruto. Recusas deliberadas não: cada barreira gera um erro tipificado que contém a medição que a acionou, e **nenhuma delas é `assert`** — o conjunto de testes é executado uma segunda vez sob `-O` no CI para provar que ainda geram erros.
- **Status de suporte** — `main` é o único estado suportado. Sem canal de lançamento, sem política de retrocompatibilidade, sem SLA.

**Barreira de envio.** [SHIP_GATE.md](SHIP_GATE.md) contém as barreiras rígidas A–D conforme estão na realidade, com cada linha sendo verificada com sua evidência ou ignorada com a justificativa correspondente. Os itens de identidade da barreira flexível são listados honestamente, incluindo o que ainda está pendente.

## Licença

MIT — consulte [LICENSE](LICENSE). A licença de qualquer *modelo* usado por meio desta ferramenta é uma questão separada, rastreada em `docs/license-map.md`.
