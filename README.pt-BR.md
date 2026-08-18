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

Um modelo de vídeo pode produzir movimento, luz e vida que nenhum renderizador consegue. Não se pode dizer *quem está na tela e onde está posicionado*. O armature fornece exatamente isso: uma malha de personagem canônica é preparada e animada no Blender sem interface gráfica, e o render se torna uma **sequência de controle** por quadro que o modelo de vídeo deve obedecer — para que o vídeo gerado por IA possa apresentar um personagem principal persistente cuja posição e pose sejam conhecidas em cada quadro.

**O armature é imagem para vídeo com um arquivo GLB em vez de uma imagem.** Tudo relacionado ao espaço é criado, e o modelo adiciona vida a ele. O resultado final é uma filmagem — filme, cenas, poses e movimentos de personagens, qualquer tipo de cena. Um jogo é apenas um dos usos dessa filmagem, nunca o limite da ferramenta.

Posicione seu personagem no Blender. Renderize a sequência de controle. Deixe que o modelo de vídeo adicione vida a ela. A estrutura vem da geometria que você possui; a vida vem do modelo; a identidade é algo nomeado e versionado que está presente no prompt e na pilha de referências — nunca um acidente em um quadro sortudo.

## Instalar

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
```

O pacote instalável é **`armature_core`** — os portões, os solucionadores de enquadramento e rotação, o contrato de especificações da cena, as operações matemáticas dos canais e os criadores de carga útil. Cada um deles é importado em um ambiente CPython simples, o que permite que sejam testados e empacotados sem a presença do Blender.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Os scripts de renderização não são pontos de entrada do console, e isso é intencional.**
`render_turnaround.py`, `stage_render.py` e seus derivados são executados dentro do **próprio interpretador do Blender** — um script de console em seu Python não poderia importar `bpy` e falharia na primeira linha, portanto, incluí-lo seria uma promessa que o pacote não pode cumprir:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Eles permanecem aqui no repositório, onde a invocação que funciona é aquela que está escrita. `armature_core.blender_scene` é o único módulo que importa `bpy`; `armature check` relata isso como `needs-blender` em vez de um defeito.

O pacote npm é um **lançador, não uma porta**: reimplementar um limite em uma segunda linguagem é a forma como um limite se desvia, então ele encaminha para o Python que contém a verdade e recusa — de forma clara, com um valor diferente de zero, com o único comando que o corrige — em vez de instalar qualquer coisa em seu nome.

---

## Estado: a tese é medida no nível do produto

Fundado em **10 de agosto de 2026**. Treze experimentos foram concluídos e a tese passou de *em teste* para **medida no nível do produto**: o personagem dançou na tela, controlado por seu próprio sistema de rigging e livre; um mundo criado manualmente permanece até o último quadro em duas sementes (E12), e **a identidade agora sobrevive a uma camada hospedada, treinada por humanos, alimentada apenas com referências criadas** (E13) — tudo julgado pelo olhar do diretor. A auditoria do arco de fundação está em [docs/audit-first-arc.md](docs/audit-first-arc.md); a postura desde 12 de agosto de 2026 é um monorepositorio de aprendizado — os experimentos comprovam caminhos, nenhum caminho é canônico por impulso (CLAUDE.md).

| | |
|---|---|
| Experimentos | **E01–E14 concluídos** (E05 retirado com base em uma premissa falsa) — o arco de controle (E01–E06) · reparo do sistema de rigging + aprovação do esqueleto (E07) · **a primeira cena renderizada** (E08) · a linha de base da cadeia limpa (E09) · direção densificada adotada (E10) · o caminho sem controle, três ondas para uma falha instrutiva (E11) · **o caminho livre ganha um mundo** e a linha de base 6.0 / uni_pc (E12) · **o caminho composto responde à sua pergunta** (E13 — enviado, interrompido com gasto zero, reparado por um arco de suporte, rearmado, executado e concluído em uma única data: a identidade se mantém sob o olhar do diretor; as referências orientam os mundos decididos pelo modelo) · **a cena LoRA com preço ao vivo** (E14 — o teste comparativo: ambas as LoRAs de estilo são vinculadas aos pesos derivados; o personagem se mantém em `technically_color` e falha no par fotorrealista; o vencedor carrega uma camada de arquivo servido irresolvível e uma obrigação de crédito, ambos registrados) |
| Caminhos | **três, medidos** — o **caminho direcionado** (os bastões AAPose renderizados pelo sistema de rigging → Animate; comprovado no nível da cena, pausado e com licença liberada para sua reativação) · o **caminho livre** (quadro inicial criado em GLB → camada de câmera na linha de base 6.0 / uni_pc; a identidade se mantém sem ancoragem, um mundo criado manualmente se mantém em duas sementes, e a cena LoRA é medida ao vivo — E14) · o **caminho composto** (referências criadas em uma camada de bloqueio de identidade hospedada — graduado por E13: cinematografia com identidade bloqueada e mundos decididos pelo modelo, orientados pelo que as referências carregam; nota de divulgação em suas especificações) |
| Gasto | 22 testes no arco de fundação a 4 créditos cada; o arco E08–E12 teve um gasto de **0 créditos** (cobrança por hora de GPU) sob tetos por experimento; **as quatro gerações de E13 são o primeiro gasto com créditos de parceiro do repositório, dentro da faixa pré-definida de 424 a 844**; as duas gerações de E14 tiveram um gasto de **0 créditos de parceiro** em um teto de duas gerações, atingido exatamente |
| Mapa de licenças | cada dependência adotada carrega um **documento de licença recuperado**; NÃO VERIFICADO é tratado como NÃO; os caminhos através de camadas de terceiros também carregam **divulgação por caminho** (regra do diretor, 12 de agosto de 2026); o propósito declarado do portão é publicar a arte do estúdio |
| Portões de gasto | **O Portão CANON** rejeita um envio pago cujo assunto não pode ser nomeado em relação a um cânone legível por máquina — a superfície é a linha, um ocupante nulo é um **buraco em vez de uma ausência**, e ambas as direções são verificadas (o prompt cobre o cânone; tudo no prompt *é* cânone). Ele dispara **antes** que o diretório de saída seja criado, dentro de cada um dos sete criadores de carga útil, porque a etapa irreversível que este repositório possui é escrever uma carga útil. A saída é baseada em dados: `--no-canon` em um assunto que *tem* cânone é rejeitado, não honrado |
| Testes | **1351: transição na plataforma de testes** (14 iterações, medido em 2026-08-18), idêntico sob `-O`; os testes de CI avaliam o que um modelo pode fazer honestamente — ativos locais da plataforma **são omitidos visivelmente**. |
| Status | **v0.3.0** – o registro recebe uma barreira de custo e um índice que se verifica. `armature_core` é enviado para PyPI como `armature-studio` e npm como `@mcptoolshop/armature-studio`, publicado a partir de uma tag por OIDC sem nenhum token de longa duração em lugar algum. |

### O que está sendo medido (o arco atual)

- **A identidade é mantida** – guiada (E08: o rosto é reconhecido como o do gêmeo na imagem) *e* não ancorada (onda 1 de E11: cada característica até o último quadro, sem referência, sem visão de recorte, sem sinal de direção). O olhar do diretor é o veredicto final em ambos os casos.
- **A câmera obedece ao controle explícito para um único pixel** nos pesos da camada da câmera (onda 3 de E11) – e se move não solicitado sem ele (onda 1 de E11).
- **A densidade influencia o sinal, não o desempenho** (E10) – a reamostragem suaviza os passos em 41%, o desempenho em 8,6%; ainda assim, é adotado visualmente: mais fps resulta em melhor qualidade.
- **Uma disputa de licença não é uma alegação de fiação** (onda 2 de E11) – um modelo mapeado Apache e um gráfico que nunca o carregou produziram 65 quadros de ruído com cada porta verde. A porta PAIR agora existe.
- **A composição da cena é volátil em relação à semente** (E10 / E11) – texto idêntico recompôs o mundo inteiro em diferentes sementes. **Uma alegação de cena precisa de duas sementes antes de se tornar uma propriedade.**
- **Um mundo definido é mantido** (E12) – uma sala real no quadro inicial sobrevive até o último quadro em duas sementes na camada da câmera, com um único atributo variável atribuído à imagem inicial por meio da diferença de campo. A mesma camada que definiu um espaço vazio manteve-o (onda 3 de E11): os mundos são criados e depois mantidos.
- **O catálogo 6.0 / uni_pc é a linha de base da camada da câmera** (E12) – a premissa herdada 3.5 / euler caiu para seu próprio nível: nas configurações do catálogo, as mesmas sementes que perderam uma cabeça e ganharam um membro mantêm a figura em f80. O custo é nomeado – uma maior adesão impôs a **cláusula de identidade não delimitada** à multidão em uma das duas sementes; o prompt com escopo no assunto é o gatilho promovido.
- **A identidade sobrevive a uma camada hospedada alimentada apenas por referências criadas** (E13) – na referência wan2.7 para vídeo, ambos os braços, ambas as sementes, o artista de madeira estilizado passou por um modelo treinado por humanos como o mesmo personagem aos olhos do diretor. Três previsões cegas em duas posições esperavam que a camada sobrescrevesse a estrutura não humana; nenhuma estava correta – o pessimismo unidirecional sobre esses modelos agora está registrado como doutrina de calibração.
- **As referências orientam os mundos decididos pelo modelo e dominam o caos da semente nessa camada** (E13) – placas cinzas geraram um estúdio cinza, um clipe de bar quente gerou um interior quente e ambas as sementes por braço concordaram. A atribuição do mecanismo (sangramento da placa versus padrão do estúdio) está honestamente aberta em quatro gerações; uma alegação de nível de propriedade é executada sob a lei das duas sementes em um acompanhamento projetado.
- **Um VÍDEO construído alcança os sockets de VÍDEO** (E13) – não existe nenhum caminho de upload para clipes, mas 81 quadros criados foram montados no gráfico (`CreateVideo`) e aceitos em um socket de vídeo de referência. Todos os inputs do tipo VÍDEO na plataforma são, em princípio, acessíveis a partir dos quadros criados.

### O que não é

- **Braços e mãos em alta velocidade.** Ainda falhando em f80 em ambas as sementes em ambas as configurações (E12). O gatilho tem um escopo redefinido, **priorizando a apresentação** – posicionamento do pulso e da câmera, com base no próprio diagnóstico do diretor sobre o GLB (a garra é um artefato de projeção, não dano à malha) – com cirurgia na malha como último recurso, nunca o primeiro passo.
- **A alegação da câmera em mundos fotográficos.** 0/81 detecções de horizonte em todos os quatro clipes E12 indicam que o detector precisa de uma costura que este mundo não tem – registrado cegamente antes do envio, nunca convertido em um resultado da câmera. Um **instrumento de câmera sem costuras** é necessário antes que qualquer número de câmera seja lido em uma sala real.
- **A prateleira da narração** (consulte #7): pontos finais da cena, prompts por trecho, condicionamento da área do tempo do vídeo, incorporações da câmera – adotado, licenciado quando necessário, não testado.

Uma resposta negativa continua sendo um sucesso total aqui – a falha de E11 gerou três portas, duas leis e a forma exata do próximo trabalho, e o roteiro dizia que isso aconteceria antes mesmo de qualquer evidência surgir.

## Como este repositório funciona

- [CLAUDE.md](CLAUDE.md) – como trabalhar aqui: os três papéis, as regras sob as quais cada posição opera e os pontos não negociáveis (a porta de licença, créditos limitados, a identidade é julgada visualmente).
- [docs/ROADMAP.md](docs/ROADMAP.md) – todo o processo de construção, sessão por sessão, com os gatilhos de desvio nomeados antecipadamente.
- `docs/experiments/` – cada alteração não trivial é executada como um experimento numerado: **especificação antes do trabalho → relatório após → decisão final do consultor.**
- `docs/license-map.md` – o mapa verificado de uso comercial. Nada entra no pipeline sem um documento de licença recuperado.

O método é herdado de [facet](../facet), onde foi pago: na sessão fundadora de facet, seis alegações herdadas foram falsificadas, cada uma em minutos, porque cada uma estava ao lado de código executável. armature está a jusante de facet – facet corta e pinta a figura; armature a encena e executa.

## Executando-o

`armature_core` é instalado a partir do PyPI (acima); o **registro de experimento e os instrumentos de renderização** são este repositório, clonado e executado – sem serviço, sem daemon. Cada instrumento é invocado diretamente:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Plataforma | Windows 11 na plataforma de testes (Omen 45L, RTX 5090). Os testes herméticos também são executados em `ubuntu-latest` no CI; os testes dependentes do Blender **são omitidos visivelmente** onde o Blender está ausente, em vez de serem aprovados silenciosamente. |
| Python | 3.13+ – o CI executa 3.13, o ambiente virtual da plataforma de testes executa 3.14. As dependências de teste são numpy, pillow, pytest, opencv (fixadas na versão da plataforma de testes, porque os testes de rasterização de pose afirmam a rasterização estável em bytes) e matplotlib |
| Blender | 5.  2, apenas em modo "headless". Uma sessão GUI ativa gera artefatos sem parâmetros registrados, e uma receita que não reproduz seu resultado não é uma receita. |
| Nó | 22, apenas para o site em `site/` |
| Geração | executa na Comfy Cloud e é enviada pelo operador; a renderização e a medição são executadas localmente. |

Caminhos absolutos dos equipamentos estão incorporados em muitas ferramentas e documentações — não são segredos, mas significam que a maioria dos instrumentos não funcionará sem modificações em outra máquina.

## Regras básicas que moldam tudo aqui

**Nenhum modelo não comercial, nunca — incluindo em experimentos.** Licenças CC-BY-NC, apenas para pesquisa e apenas para uso acadêmico são expressamente proibidas. Uma conclusão obtida com um modelo proibido é uma conclusão que deve ser descartada, portanto, ela nunca começa.

**As métricas são diagnósticos; o Diretor julga.** Se a imagem na tela for o mesmo personagem, isso é canônico e nenhuma métrica se aproxima disso. Cada experimento de geração cria uma planilha de **controle | saída | referência | proveniência** antes que um único número seja citado.

**Os créditos da nuvem são limitados antes de serem gastos.** Os créditos gastos não podem ser revertidos, portanto, cada especificação indica seu limite por conjunto em antecipação.

**As rotas revelam o que as acompanha** (a decisão do Diretor, 2026-08-12). Qualquer rota através de uma camada de terceiros documenta os dados de uso e a postura de treinamento de seus provedores, suas obrigações de divulgação de conteúdo de IA e sua política de marca d'água, com base nos documentos recuperados do mapa de licenças. As rotas totalmente locais indicam que nada sai do equipamento. Uma rota sem sua nota de divulgação não está completa — a primeira aplicação usa a especificação E13.

## Modelo de confiança e ameaças

A política completa é [SECURITY.md](SECURITY.md), medida em relação à árvore, em vez de ser apenas declarada. A forma resumida:

- **Dados acessados** — malhas, renderizações, vídeos, imagens e JSON no disco local, nos caminhos que você fornece na linha de comando, mais `docs/index/armature.db`, um índice SQLite *derivado* do próprio arquivo markdown deste repositório. Os ativos canônicos são consumidos em modo somente leitura a partir de árvores irmãs e nunca são gravados.
- **Dados NÃO acessados** — nenhuma credencial de qualquer tipo: nenhuma é lida, armazenada ou transmitida, e uma varredura de cada arquivo rastreado para chaves, tokens, blocos de chave privada e atribuições de segredo embutidas com prefixo do provedor retorna zero correspondências. **Nenhuma telemetria, análise ou contagem de uso** é coletada ou enviada; não há opção de desativar porque não há nada para desativar.
- **Saída de rede** — nenhuma biblioteca de rede Python é importada em nenhum lugar em `tools/` ou `tests/`. Duas ferramentas executam comandos na linha de comando para `curl.exe` para baixar os arquivos listados em um arquivo *que você* cola, de uma geração *que você* enviou. Nada mais aqui faz uma chamada de rede.
- **Permissões** — permissões de usuário comuns. Sem elevação, sem instalação de serviço, sem gravações no registro ou nas configurações do sistema.
- **Os pontos críticos, divulgados em vez de ocultados** — as operações de arquivo não são executadas em um ambiente isolado; uma ferramenta grava onde seus argumentos indicam. Falhas inesperadas imprimem um rastreamento bruto. As recusas deliberadas não: cada barreira gera um erro tipificado que contém a medição que a acionou, e **nenhuma delas é uma `assert`** — o conjunto é executado uma segunda vez sob `-O` no CI para provar que elas ainda são geradas.
- **Status de suporte** — `main` é o único estado suportado. Nenhum canal de lançamento, nenhuma política de retrocompatibilidade, nenhum SLA.

**Barreira de envio.** [SHIP_GATE.md](SHIP_GATE.md) contém as barreiras rígidas A–D conforme elas realmente estão, com cada linha sendo verificada com sua evidência ou ignorada com a razão em seus próprios méritos. Os itens de identidade da barreira suave são listados honestamente, incluindo o que ainda está aberto.

## Licença

MIT — veja [LICENSE](LICENSE). A licença de qualquer *modelo* usado por meio desta ferramenta é uma questão separada, rastreada em `docs/license-map.md`.
