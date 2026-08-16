<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.md">English</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

**Bloqueas el disparo. El modelo lo realiza.**

**[Página de destino y manual →](https://mcp-tool-shop-org.github.io/armature/)**

Un modelo de vídeo puede generar movimiento, luz y vida que ningún motor de renderizado puede lograr. No se puede determinar *quién está en la pantalla y dónde está*. Armature proporciona exactamente eso: un modelo de personaje canónico se coloca y anima en Blender sin interfaz gráfica, y el renderizado se convierte en una
**secuencia de control** por fotograma a la que el modelo de vídeo debe obedecer; de este modo, el vídeo generado por IA puede presentar un personaje principal persistente cuya posición y pose se conocen en cada fotograma.

**Armature es imagen a vídeo con un archivo GLB en lugar de una imagen.** Todo lo espacial está diseñado, y el modelo le da vida. El resultado final es metraje: película, escenas, poses y movimientos de personajes, cualquier toma. Un juego es uno de los consumidores de ese metraje, nunca el límite de la herramienta.

Coloca tu personaje en Blender. Renderiza la secuencia de control. Deja que el modelo de vídeo le dé vida. La estructura proviene de la geometría que posees; la vida proviene del modelo; la identidad es algo con nombre y versión que se incluye en el mensaje y la pila de referencias, nunca un accidente de un fotograma afortunado.

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

El paquete instalable es **`armature_core`**: las puertas, el entramado y los solucionadores de recorrido, el contrato de especificación de la toma, las matemáticas del canal y los generadores de carga útil. Cada uno de ellos importa desde un CPython estándar, lo que permite probarlos y empaquetarlos sin necesidad de tener Blender instalado.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Los scripts de renderizado no son puntos de entrada de la consola, y esto es intencional.**
`render_turnaround.py`, `stage_render.py` y sus derivados se ejecutan dentro del **intérprete propio de Blender**: un script de consola en tu Python no podría importar `bpy` y fallaría en su primera línea, por lo que incluir uno sería una promesa que el paquete no puede cumplir:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Permanecen aquí, en el repositorio, donde la invocación que funciona es la que está escrita.
`armature_core.blender_scene` es el único módulo que importa `bpy`; `armature check` lo informa como `needs-blender` en lugar de como un defecto.

El paquete npm es un **lanzador, no un puerto**: volver a implementar un umbral en un segundo lenguaje es la forma en que un umbral se desvía, por lo que redirige al Python que contiene la verdad y se niega (de manera sonora, con un valor distinto de cero, mediante el único comando que lo soluciona) en lugar de instalar nada en tu nombre.

---

## Estado: la tesis se mide a nivel de producto

Fundado el **10 de agosto de 2026**. Trece experimentos cerrados y la tesis ha pasado de estar *en fase de prueba* a ser **medida a nivel de producto**: el personaje ha bailado en la pantalla, controlado por su propio sistema de animación y libre; un mundo creado manualmente se mantiene hasta el último fotograma con dos semillas (E12), y **la identidad ahora sobrevive a una capa alojada, entrenada por humanos, alimentada únicamente con referencias creadas** (E13); todo ello juzgado por la mirada del director. La auditoría del arco fundacional está en
[docs/audit-first-arc.md](docs/audit-first-arc.md); la postura desde el 12 de agosto de 2026 es un monorepositorio de aprendizaje: los experimentos demuestran caminos, ningún camino es canónico por inercia (CLAUDE.md).

| | |
|---|---|
| Experimentos | **E01–E14 cerrados** (E05 retirado debido a una premisa falsa); el arco de control (E01–E06) · reparación del sistema de animación + aprobación del esqueleto (E07) · **la primera toma renderizada** (E08) · la línea base de cadena limpia (E09) · se adopta un sistema de control más denso (E10) · la ruta sin control, tres fases hacia una falla instructiva (E11) · **la ruta libre gana un mundo** y la línea base 6.0 / uni_pc (E12) · **la ruta compuesta responde a su pregunta** (E13: enviada, detenida con cero gasto, reparada por un arco de soporte, rearmada, ejecutada y cerrada en una sola fecha: la identidad se mantiene según la mirada del director; las referencias sirven como base para los mundos decididos por el modelo) · **la escena LoRA con precio en vivo** (E14: la prueba final: ambos estilos LoRA se unen a los pesos derivados; el personaje se mantiene en `technically_color` y falla en el par fotorrealista; el ganador tiene una capa de archivo servido irresoluble y una obligación crediticia, ambas registradas). |
| Rutas | **tres, medidos**: la **ruta controlada** (sistemas de animación renderizados AAPose → Animate; probados a nivel de toma, estacionados y con licencia clara para su reactivación) · la **ruta libre** (fotograma inicial creado en GLB → capa de cámara en la línea base 6.0 / uni_pc; la identidad se mantiene sin anclar, un mundo creado manualmente se mantiene con dos semillas, y la escena LoRA se mide en vivo — E14) · la **ruta compuesta** (referencias creadas en una capa de bloqueo de identidad alojada — graduada por E13: cinematografía con identidad bloqueada, mundos decididos por el modelo y guiados por lo que llevan las referencias; nota de divulgación en su especificación). |
| Gasto | 22 pruebas en el arco fundacional a 4 créditos cada una; el arco E08–E12 midió **0 créditos** (facturación por hora de GPU) bajo límites por experimento; **las cuatro generaciones de E13 son el primer gasto con créditos de socios del repositorio, dentro de su rango preestablecido de 424 a 844**; las dos generaciones de E14 midieron **0 créditos de socios** en un límite de dos generaciones, alcanzado exactamente. |
| Mapa de licencias | cada dependencia adoptada lleva un **documento de licencia recuperado**; NO VERIFICADO se trata como SI; las rutas a través de capas de terceros también llevan una **divulgación por ruta** (establecida por el director el 12 de agosto de 2026); el propósito declarado de la puerta es publicar el arte del estudio. |
| Pruebas | **1311 aprobados en el sistema de animación** (13 omisiones, medido el 15 de agosto de 2026 en la versión v0.2.0), también bajo `-O`; CI ejerce lo que un ejecutor puede hacer honestamente: los activos locales del sistema de animación **se omiten visiblemente**. |
| Estado | **v0.2.0 lanzado el 15 de agosto de 2026**: el registro se convierte en un conjunto de herramientas instalable: `armature_core` en PyPI como `armature-previz` y en npm como `@mcptoolshop/armature`, publicado desde una etiqueta por OIDC sin ninguna ficha de larga duración. El registro sigue siendo el árbol de documentos y sigue estando completo. |

### Qué se mide (el arco actual)

- **La identidad se mantiene** — mediante el control (E08: la imagen muestra el rostro del gemelo a lo largo de la secuencia) *y* sin control (E11, fase 1: cada detalle hasta el último fotograma, sin referencias, sin visión basada en clips, sin señal de control). El criterio del director es definitivo en ambos casos.
- **La cámara obedece al control explícito a nivel de un solo píxel** en los parámetros de la cámara (E11, fase 3) y se desplaza sin que se le ordene hacerlo (E11, fase 1).
- **La densidad mueve la señal, no el rendimiento** (E10): el remuestreo suaviza las transiciones en un 41 %, mientras que el rendimiento mejora en un 8,6 %; aun así, se adoptó visualmente: más fotogramas por segundo dan como resultado una mejor imagen.
- **Un problema de licencia no es un problema de cableado** (E11, fase 2): un modelo Apache asignado y un gráfico que nunca lo cargó produjeron 65 fotogramas de ruido con cada puerta en verde. Ahora existe el par de puertas.
- **La composición de la escena es volátil según la semilla** (E10 / E11): el mismo texto reconstruyó por completo el mundo a través de diferentes semillas. **Una afirmación sobre la escena requiere dos semillas antes de que se convierta en una propiedad.**
- **Un mundo definido se mantiene** (E12): una habitación real en el fotograma inicial sobrevive hasta el último fotograma con dos semillas en el nivel de la cámara, y un atributo variable asignado a la imagen inicial mediante la diferencia de campo. El mismo nivel que mostró una previsualización vacía mantuvo el vacío (E11, fase 3): los mundos se crean y luego se conservan.
- **El catálogo 6.0 / uni_pc es la línea base del nivel de la cámara** (E12): la premisa heredada de 3.5 / euler cayó a su propio nivel: en la configuración del catálogo, las mismas semillas que perdieron una cabeza y desarrollaron una extremidad mantienen la figura hasta f80. El costo se denomina: un mayor grado de adherencia impuso la **cláusula de identidad no limitada** al grupo con una de las dos semillas; el indicador con ámbito en el sujeto es la palanca principal.
- **La identidad sobrevive a un nivel alojado alimentado solo por referencias creadas** (E13): en la referencia a video de wan2.7, ambos brazos, ambas semillas, el estilizado intérprete de madera apareció como el mismo personaje según el criterio del director, a través de un modelo entrenado por humanos. Tres predicciones ciegas en dos asientos diferentes esperaban que el nivel sobrescribiera la estructura no humana; ninguna acertó: el pesimismo unidireccional sobre estos modelos ahora se registra como doctrina de calibración.
- **Las referencias sirven de guía para los mundos decididos por el modelo y dominan el caos de las semillas en ese nivel** (E13): las placas grises dieron lugar a un estudio gris, un clip de un bar cálido dio lugar a un interior cálido, y ambas semillas por brazo coincidieron. La atribución del mecanismo (difusión de la placa frente al valor predeterminado del estudio) es honestamente evidente en cuatro generaciones; una afirmación de nivel de propiedad se rige por la ley de las dos semillas en una secuencia diseñada.
- **Un VIDEO construido llega a los conectores de VIDEO** (E13): no existe ninguna ruta de carga para los clips, pero 81 fotogramas creados se ensamblaron en el gráfico (`CreateVideo`) y se aceptaron en un conector de video de referencia. En principio, todos los datos de entrada de tipo VIDEO en la plataforma son accesibles a partir de los fotogramas creados.

### Qué no

- **Brazos y manos en movimiento rápido.** Sigue fallando en f80 con ambas semillas y ambos ajustes (E12).
La palanca se ha rediseñado, priorizando la **presentación** — posicionamiento de la muñeca y la cámara, a partir del
diagnóstico del Director sobre el GLB (la garra es un artefacto de proyección, no daño en la malla) —
con una reparación de la malla como último recurso, nunca como la primera opción.
- **La afirmación sobre la cámara en los mundos fotográficos.** 0/81 detecciones de horizonte en los cuatro clips E12
indican que el detector necesita una discontinuidad que este mundo no tiene — se registra como un punto ciego antes de
la presentación, y nunca se convierte en un resultado de la cámara. Se debe proporcionar un **instrumento de cámara sin discontinuidades**
antes de que se lea cualquier número de cámara en una habitación real.
- **La sección de narración** (consulte #7): puntos finales de las secuencias, indicaciones por fragmento, condicionamiento del área de tiempo de video,
incrustaciones de la cámara — adoptado, con licencia cuando sea necesario, sin probar.

Una respuesta negativa sigue siendo un éxito total aquí: el fracaso contundente de E11 generó tres puertas, dos leyes y
la forma exacta del próximo trabajo, y el plan indicó que así sería antes de que llegaran las pruebas.

## Cómo funciona este repositorio

- [CLAUDE.md](CLAUDE.md) — cómo trabajar aquí: los tres roles, las reglas bajo las cuales opera cada puesto y
los aspectos innegociables (la puerta de la licencia, créditos limitados, la identidad se juzga a simple vista).
- [docs/ROADMAP.md](docs/ROADMAP.md) — toda la estructura, sesión por sesión, con los puntos críticos definidos por adelantado.
- `docs/experiments/` — cada cambio no trivial se ejecuta como un experimento numerado:
**especificación antes del trabajo → informe después → decisión final del asesor.**
- `docs/license-map.md` — el mapa verificado para uso comercial. Nada entra en la cadena de procesamiento sin
un documento de licencia recuperado.

El método se hereda de [facet](../facet), donde se pagó por él: en la sesión fundacional de facet, seis afirmaciones heredadas fueron falsificadas, cada una en minutos, porque cada una estaba junto a un código ejecutable. armature es posterior a facet; facet corta y pinta la figura; armature la prepara y
la ejecuta.

## Cómo ejecutarlo

No hay nada que instalar. Este es un repositorio que se clona y se ejecuta: no hay ningún paquete en ningún
registro, ni servicio, ni demonio. Cada instrumento se invoca directamente:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Plataforma | Windows 11 en el equipo (Omen 45L, RTX 5090). Las pruebas herméticas también se ejecutan en `ubuntu-latest` en CI; las pruebas dependientes de Blender **se omiten visiblemente** cuando no está presente, en lugar de pasar silenciosamente. |
| Python | 3.13+ — CI ejecuta la versión 3.13, el entorno virtual del equipo ejecuta la versión 3.14. Las dependencias de prueba son numpy, pillow, pytest, opencv (fijadas a la versión del equipo, porque las pruebas de rasterización de pose afirman una rasterización estable en bytes) y matplotlib |
| Blender | 5.2, solo en modo sin cabeza. Una sesión GUI activa produce artefactos sin parámetros registrados, y una receta que no reproduce su salida no es una receta. |
| Node | 22, solo para el sitio bajo `site/` |
| Generación | se ejecuta en Comfy Cloud y se envía por el operador; la renderización y la medición se ejecutan localmente. |

Las rutas absolutas del equipo están integradas en muchas herramientas y documentos: no son secretos, pero sí
significan que la mayoría de los instrumentos no se ejecutarán sin modificar en otra máquina.

## Reglas permanentes que dan forma a todo aquí

**Nunca modelos no comerciales, ni siquiera en experimentos.** Las licencias CC-BY-NC, solo para investigación y
solo para uso académico están prohibidas por completo. Una conclusión obtenida de un modelo prohibido es una
conclusión que debe descartarse, por lo que nunca comienza.

**Las métricas son diagnósticos; el Director juzga.** Si la figura en la pantalla es el mismo
personaje es canon, y ninguna métrica se acerca a ello. Cada experimento de generación crea una
hoja **control | salida | referencia | procedencia** antes de que se cite un solo número.

**Los créditos en la nube están limitados antes de que se gasten.** Los créditos gastados no tienen deshacer, por lo que cada especificación
indica su límite por brazo con anticipación.

**Las rutas revelan qué las acompaña** (la decisión del Director, 2026-08-12). Cualquier ruta
a través de un nivel de terceros documenta el uso de datos y la postura de capacitación de sus proveedores, sus
obligaciones de divulgación de contenido con IA y su política de marca de agua, basadas en los documentos recuperados del mapa de licencias. Las rutas totalmente locales indican que nada sale del equipo. Una ruta sin su
nota de divulgación no está completa: la primera aplicación utiliza la especificación de E13.

## Modelo de confianza y amenazas

La política completa se encuentra en [SECURITY.md](SECURITY.md), medida con respecto al árbol en lugar de afirmada.
En resumen:

- **Datos afectados** — mallas, renderizados, vídeos, imágenes y archivos JSON en el disco local, en las rutas que se especifican en la línea de comandos, además de `docs/index/armature.db`, un índice SQLite *derivado* del propio archivo markdown de este repositorio. Los recursos canónicos se consumen en modo de solo lectura desde los árboles hermanos y nunca se escriben en ellos.
- **Datos NO afectados** — no se utilizan credenciales de ningún tipo: no se leen, almacenan ni transmiten, y un análisis de cada archivo rastreado para detectar claves, tokens, bloques de clave privada y asignaciones de secretos con prefijo del proveedor devuelve cero coincidencias. **No se recopila ni envía telemetría, analítica o información sobre el uso**; no hay opción de exclusión porque no hay nada de lo que excluirse.
- **Comunicación de red** — no se importa ninguna biblioteca de redes Python en `tools/` o `tests/`. Dos herramientas ejecutan comandos externos a `curl.exe` para descargar los archivos enumerados en un archivo *que usted* pega, procedentes de una versión *que usted* ha enviado. Nada más aquí realiza una llamada de red.
- **Permisos** — permisos de usuario normales. No se elevan privilegios, no se instala ningún servicio, no se realizan escrituras en el registro ni en la configuración del sistema.
- **Los aspectos críticos, que se revelan en lugar de ocultarse** — las operaciones con archivos no están aisladas; una herramienta escribe donde sus argumentos lo indican. Los fallos inesperados muestran un rastreo completo sin procesar. Las denegaciones deliberadas no: cada puerta levanta un error tipificado que contiene la medición que la activó, y **ninguno de ellos es un `assert`** — el conjunto se ejecuta una segunda vez bajo `-O` en CI para demostrar que siguen levantándose.
- **Estado del soporte** — `main` es el único estado compatible. No hay canal de lanzamiento, no hay política de compatibilidad con versiones anteriores, no hay SLA.

**Barrera de envío.** [SHIP_GATE.md](SHIP_GATE.md) contiene las barreras estrictas A–D tal como son en realidad, con cada línea verificada con su evidencia o omitida con la razón correspondiente. Los elementos de identidad de la barrera flexible se enumeran honestamente, incluido el que aún está abierto.

## Licencia

MIT — consulte [LICENSE](LICENSE). La licencia de cualquier *modelo* utilizado a través de esta herramienta es una cuestión independiente, rastreada en `docs/license-map.md`.
