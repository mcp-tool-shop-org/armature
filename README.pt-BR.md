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

---

## Estado: a tese é medida no nível do produto

Fundado em **10 de agosto de 2026**. Doze experimentos foram concluídos e a tese passou de *em teste* para **medida no nível do produto**: o personagem dançou na tela duas vezes — uma vez controlado por seu próprio rig, uma vez livre — e um mundo construído agora se mantém até o último quadro em duas amostras (E12), tudo julgado pelo olhar do Diretor. A auditoria do arco de fundação está em [docs/audit-first-arc.md](docs/audit-first-arc.md); a postura desde 10 de agosto de 2026 é um monorepositorio de aprendizado — os experimentos comprovam caminhos, nenhum caminho é canônico por impulso (CLAUDE.md).

| | |
|---|---|
| Experimentos | **E01–E12 concluídos** (E05 retirado com base em uma premissa falsa) — o arco de controle (E01–E06) · reparo do rig + aprovação do esqueleto (E07) · **a primeira cena renderizada** (E08) · a linha de base da cadeia limpa (E09) · densificação do acionamento adotada (E10) · o caminho sem controle, três ondas para uma falha instrutiva (E11) · **o caminho livre ganha um mundo**, e a linha de base das configurações cai para 6.0 / uni_pc no catálogo (E12) · **E13 iniciado em 13 de agosto de 2026** — a sonda do caminho composto, referências criadas na camada wan2.7 de referência para vídeo |
| Caminhos | **dois, mais um em teste** — o **caminho controlado** (rig renderizado AAPose → Animate; comprovado no nível da cena, reservado para a construção da animação de IA) · o **caminho livre** (quadro inicial criado com GLB → camadas I2V / câmera na linha de base 6.0 / uni_pc; a identidade permanece não ancorada, e um mundo construído se mantém em duas amostras) · o **caminho composto** (referências criadas em uma camada hospedada de bloqueio de identidade — a sonda E13; sua nota de divulgação está presente na especificação de acordo com a lei de divulgação por caminho) |
| Gastos | 22 sondas no arco de fundação, a 4 créditos cada; o arco E08–E12 teve um custo de **0 créditos** em cada envio (cobrança por hora de GPU) sob limites por experimento — E12 gastou 4 de seus 6 envios limitados, o restante não foi utilizado. |
| Mapa de licenças | cada dependência adotada possui um **documento de licença recuperado**; NÃO VERIFICADO é tratado como NÃO; caminhos através de camadas de terceiros também possuem **divulgação por caminho** (regra do Diretor, 12 de agosto de 2026); o propósito declarado da porta de entrada é a publicação da arte do estúdio. |
| Testes | **1005 aprovados no rig** (13 ignorados, medidos em 13 de agosto de 2026), sob `-O` também; o CI executa o que um executor pode fazer honestamente — os ativos locais do rig **são visivelmente ignorados**. |
| Status | **novamente público a partir de 13 de agosto de 2026** (privado por escolha, de 11 a 13 de agosto) — organizando para um lançamento **v0.1.0**; o registro é a árvore de documentos e está completo. |

### O que é medido (o arco atual)

- **A identidade se mantém** — controlada (E08: o rosto parece ser do gêmeo ao longo da cena) *e* não ancorada (onda 1 de E11: cada característica até o último quadro, sem referência, sem visão de recorte, sem sinal de acionamento). O olhar do Diretor é o veredicto registrado em ambos.
- **A câmera obedece a um controle explícito de um pixel** nos pesos da camada da câmera (onda 3 de E11) — e se move não solicitado sem ele (onda 1 de E11).
- **A densidade move o sinal, não o desempenho** (E10) — a reamostragem suaviza os passos em 41%, o desempenho em 8,6%; adotado mesmo assim com base no olhar: mais fps parece melhor.
- **Uma linha de licença não é uma alegação de fiação** (onda 2 de E11) — um modelo mapeado Apache e um gráfico que nunca o carregou produziram 65 quadros de ruído com cada porta verde. A porta PAIR agora existe.
- **A composição da cena é volátil em relação à amostra** (E10 / E11) — o mesmo texto recompôs o mundo completamente entre as amostras. **Uma alegação de cena precisa de duas amostras antes de ser uma propriedade.**
- **Um mundo construído se mantém** (E12) — uma sala real no quadro inicial sobrevive até o último quadro em duas amostras na camada da câmera, com um atributo variável atribuído à imagem inicial por meio de diferença de campo. A mesma camada que apresentou um vazio de pré-visualização manteve um vazio (onda 3 de E11): os mundos são criados e depois mantidos.
- **6.0 / uni_pc do catálogo é a linha de base da camada da câmera** (E12) — a premissa herdada de 3.5 / euler caiu para seu próprio nível: nas configurações do catálogo, as mesmas amostras que perderam uma cabeça e cresceram um membro mantêm a figura até o quadro 80. O custo é nomeado — uma adesão mais forte impôs a **cláusula de identidade não restrita** à multidão em uma das duas amostras; o prompt com escopo no sujeito é a alavanca promovida.

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
