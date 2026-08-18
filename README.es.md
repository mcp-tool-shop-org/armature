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

**[Página de inicio y manual →](https://mcp-tool-shop-org.github.io/armature/)**

Un modelo de vídeo puede generar movimiento, luz y vida que ningún motor de renderizado puede lograr. No se puede determinar *quién está en la pantalla y dónde está parado*. Armature proporciona exactamente eso: un modelo de personaje canónico se coloca y anima en Blender sin interfaz gráfica, y el renderizado se convierte en una **secuencia de control** por fotograma a la que el modelo de vídeo debe obedecer; así, el vídeo generado por IA puede presentar un personaje principal persistente cuya posición y pose se conocen en cada fotograma.

**Armature es imagen a vídeo con un archivo GLB en lugar de una imagen.** Todo lo espacial está diseñado, y el modelo le da vida. El resultado final es metraje: película, escenas, poses y movimientos de personajes, cualquier toma. Un juego es uno de los consumidores de ese metraje, nunca el límite de la herramienta.

Coloca a tu personaje en Blender. Renderiza la secuencia de control. Deja que el modelo de vídeo le dé vida. La estructura proviene de la geometría que posees; la vida proviene del modelo; la identidad es algo con nombre y versión que se incluye en el mensaje y la pila de referencias, nunca un accidente de un fotograma afortunado.

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

El paquete instalable es **`armature_core`**: las puertas, los solucionadores de encuadre y rotación, el contrato de especificación de la toma, las matemáticas del canal y los generadores de carga útil. Cada uno de ellos se importa en un entorno CPython estándar, lo que permite probarlos y empaquetarlos sin necesidad de tener Blender instalado.

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**Los scripts de renderizado no son puntos de entrada de la consola, y esto es intencional.**
`render_turnaround.py`, `stage_render.py` y sus derivados se ejecutan dentro del **intérprete propio de Blender**: un script de consola en tu Python no podría importar `bpy` y fallaría en su primera línea, por lo que incluir uno sería una promesa que el paquete no puede cumplir:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

Permanecen aquí, en el repositorio, donde la invocación que funciona es la que está escrita. `armature_core.blender_scene` es el único módulo que importa `bpy`; `armature check` lo informa como `needs-blender` en lugar de como un defecto.

El paquete npm es un **lanzador, no un puerto**: reimplementar un umbral en un segundo lenguaje es la forma en que un umbral se desvía, por lo que redirige al Python que contiene la verdad y se niega (de manera audible, con un valor distinto de cero, con el único comando que lo corrige) en lugar de instalar nada en tu nombre.

---

## Estado: la tesis se mide a nivel de producto

Fundado el **10 de agosto de 2026**. Trece experimentos cerrados y la tesis ha pasado de estar *en fase de prueba* a ser **medida a nivel de producto**: el personaje ha bailado en la pantalla, controlado por su propio esqueleto y libre; un mundo creado manualmente se mantiene hasta el último fotograma con dos semillas (E12), y **la identidad ahora sobrevive a una capa alojada y entrenada por humanos que solo recibe referencias creadas** (E13); todo ello juzgado por la mirada del director. La auditoría del arco fundacional está en [docs/audit-first-arc.md](docs/audit-first-arc.md); la postura desde el 12 de agosto de 2026 es un repositorio monorepo de aprendizaje: los experimentos demuestran caminos, ninguna ruta es canónica por inercia (CLAUDE.md).

| | |
|---|---|
| Experimentos | **E01–E14 cerrados** (E05 retirado debido a una premisa falsa); el arco de control (E01–E06) · reparación del esqueleto + aprobación del esqueleto (E07) · **la primera toma renderizada** (E08) · la línea base de cadena limpia (E09) · se adopta un sistema de control más denso (E10) · la ruta sin control, tres oleadas hacia un fallo instructivo (E11) · **la ruta libre gana un mundo** y la línea base 6.0 / uni_pc (E12) · **la ruta compuesta responde a su pregunta** (E13: enviada, detenida con cero gasto, reparada por un arco de soporte, rearmada, ejecutada y cerrada en una sola fecha: la identidad se mantiene según la mirada del director; las referencias guían los mundos decididos por el modelo) · **la escena LoRA con precio en vivo** (E14: la prueba: ambos LoRA de estilo se vinculan a los pesos derivados; el personaje se mantiene en `technically_color` y falla en la pareja fotorrealista; el ganador tiene una capa de archivo servido irresoluble y una obligación de crédito, ambas registradas) |
| Rutas | **tres, medidas**: la **ruta controlada** (esqueles AAPose renderizados → Animate; probada a nivel de toma, aparcada y con licencia clara para su reapertura) · la **ruta libre** (fotograma inicial diseñado en GLB → capa de cámara en la línea base 6.0 / uni_pc; la identidad se mantiene sin anclar, un mundo creado manualmente se mantiene con dos semillas, y la escena LoRA se mide en vivo — E14) · la **ruta compuesta** (referencias diseñadas en una capa de bloqueo de identidad alojada — graduada por E13: cinematografía con identidad bloqueada y mundos decididos por el modelo, guiados por lo que llevan las referencias; nota de divulgación en su especificación) |
| Gasto | 22 pruebas en el arco fundacional a 4 créditos cada una; el arco E08–E12 gastó **0 créditos** (facturación por hora de GPU) según los límites máximos por experimento; las cuatro generaciones de E13 son el primer gasto con créditos de socios del repositorio, dentro del rango preestablecido de 424 a 844; las dos generaciones de E14 gastaron **0 créditos de socios** con un límite máximo de dos generaciones, alcanzado exactamente |
| Mapa de licencias | cada dependencia adoptada lleva adjunto un **documento de licencia recuperado**: NO VERIFICADO se trata como SI; las rutas a través de capas de terceros también llevan una **divulgación por ruta** (establecida por el director el 12 de agosto de 2026); el propósito declarado de la puerta es publicar el arte del estudio |
| Puertas de gasto | La puerta CANON rechaza un envío pagado cuyo sujeto no se puede nombrar en relación con un canon legible por máquina: la superficie es la fila, un ocupante nulo es un **hueco más que una ausencia**, y ambas direcciones se comprueban (el mensaje cubre el canon; todo lo que hay en el mensaje *es* canon). Se activa **antes** de que se cree el directorio de salida, dentro de cada uno de los siete generadores de carga útil, porque el paso irreversible que posee este repositorio es escribir una carga útil. La vía de escape está respaldada por un censo: `--no-canon` en un sujeto que *tiene* canon se rechaza, no se acepta |
| Pruebas | **1351: transición en el set** (14 iteraciones, medido el 2026-08-18), idéntico bajo `-O`; CI evalúa lo que un operador puede hacer honestamente: los activos locales del set **se omiten visiblemente**. |
| Estado | **v0.3.0**: el registro obtiene una puerta de control de gasto y un índice que se verifica a sí mismo. `armature_core` se envía a PyPI como `armature-studio` y a npm como `@mcptoolshop/armature-studio`, publicado desde una etiqueta mediante OIDC sin ningún token de larga duración en ninguna parte. |

### Qué se mide (el arco actual)

- **La identidad se mantiene**: impulsada (E08: la imagen se interpreta como la del gemelo a lo largo de la toma) *y* sin anclaje (onda E11, 1: cada característica hasta el último fotograma sin ninguna referencia, sin visión de recorte, sin señal de control). El ojo del director es el veredicto final en ambos casos.
- **La cámara obedece un control explícito a un píxel** en las ponderaciones de nivel de cámara (onda E11, 3) y se acerca sin que se le ordene hacerlo (onda E11, 1).
- **La densidad mueve la señal, no el rendimiento** (E10): el remuestreo suaviza los pasos en un 41 %, el rendimiento en un 8,6 %; de todos modos, se adopta visualmente: más fotogramas por segundo se ven mejor.
- **Una fila de licencias no es una reclamación de cableado** (onda E11, 2): un modelo Apache asignado y un gráfico que nunca lo cargó produjeron 65 fotogramas de ruido con cada puerta en verde. Ahora existe la puerta PAIR.
- **La composición de la escena es volátil según la semilla** (E10 / E11): el mismo texto recomponiendo el mundo por completo entre diferentes semillas. **Una reclamación de escena necesita dos semillas antes de que sea una propiedad.**
- **Un mundo definido se mantiene** (E12): una habitación real en el fotograma inicial sobrevive hasta el último fotograma con dos semillas en el nivel de cámara, una variable atribuida a la imagen inicial mediante la diferencia de campo. El mismo nivel definió un espacio vacío que mantuvo el vacío (onda E11, 3): los mundos se crean y luego se mantienen.
- **El catálogo 6.0 / uni_pc es la línea base del nivel de cámara** (E12): la premisa heredada de 3.5 / euler retrocedió a su propio nivel: en la configuración del catálogo, las mismas semillas que perdieron una cabeza y desarrollaron un brazo mantienen la figura hasta f80. El costo se denomina: una mayor adherencia impuso la **cláusula de identidad no delimitada** al grupo con una de dos semillas; el indicador con ámbito de sujeto es la palanca promovida.
- **La identidad sobrevive a un nivel alojado alimentado solo por referencias creadas** (E13): en la referencia wan2.7 a video, ambos brazos, ambas semillas, el estilizado intérprete de madera pasó a través de un modelo entrenado por humanos como el mismo personaje a los ojos del director. Tres predicciones ciegas en dos asientos esperaban que el nivel sobrescribiera una estructura no humana; ninguna acertó: ahora se registra el pesimismo unidireccional sobre estos modelos como doctrina de calibración.
- **Las referencias fundamentales dirigen los mundos decididos por el modelo y dominan el caos de las semillas en ese nivel** (E13): las placas grises generaron un estudio gris, un clip de un bar cálido generó un interior cálido y ambas semillas por brazo estuvieron de acuerdo. La atribución del mecanismo (difusión de la placa frente al valor predeterminado del estudio) se revela honestamente en cuatro generaciones: una reclamación de calidad de propiedad se ejecuta bajo la ley de las dos semillas en una secuencia diseñada.
- **Un VIDEO construido llega a los sockets de VIDEO** (E13): no existe ninguna ruta de carga para los clips, pero 81 fotogramas creados se ensamblaron en el gráfico (`CreateVideo`) y se aceptaron en un socket de video de referencia. En principio, cada entrada de tipo VIDEO en la plataforma es accesible desde los fotogramas creados.

### Qué no lo es

- **Brazos y manos a alta velocidad**. Sigue fallando en f80 con ambas semillas y ambos ajustes (E12). La palanca se vuelve a delimitar como **presentación primero**: posicionamiento de la muñeca y la cámara, según el diagnóstico del propio director sobre el archivo GLB (la garra es un artefacto de proyección, no daño en la malla), con cirugía de malla como último recurso, nunca como el primer movimiento.
- **La reclamación de la cámara en los mundos fotográficos**. 0/81 detecciones de horizonte en todos los cuatro clips E12 indican que el detector necesita una costura que este mundo no tiene; se registró antes del envío y nunca se convirtió en un resultado de la cámara. Se debe una **instrumento de cámara sin costuras** antes de que se lea cualquier número de cámara en una habitación real.
- **El estante de narración** (consulte #7): puntos finales de la secuencia, indicaciones por fragmento, condicionamiento del área de tiempo de video, incrustaciones de cámara: adoptado, con licencia cuando sea necesario, sin probar.

Una respuesta negativa sigue siendo un éxito total aquí: el fallo contundente de E11 obtuvo tres puertas, dos leyes y la forma exacta del siguiente trabajo, y el plan dijo que lo haría antes de que llegaran las pruebas.

## Cómo funciona este repositorio

- [CLAUDE.md](CLAUDE.md): cómo trabajar aquí: los tres roles, las reglas bajo las cuales opera cada asiento y los elementos no negociables (la puerta de licencia, créditos limitados, la identidad se juzga visualmente).
- [docs/ROADMAP.md](docs/ROADMAP.md): toda la construcción, sesión por sesión, con los puntos críticos definidos por adelantado.
- `docs/experiments/`: cada cambio no trivial se ejecuta como un experimento numerado: **especificación antes del trabajo → informe después → decisión final del asesor.**
- `docs/license-map.md`: el mapa verificado de uso comercial. Nada entra en la canalización sin un documento de licencia recuperado.

El método se hereda de [facet](../facet), donde se pagó por él: en la sesión fundacional de facet, seis reclamaciones heredadas fueron refutadas, cada una en minutos, porque cada una estaba junto a un código ejecutable. armature es posterior a facet: facet corta y pinta la figura; armature la escenifica y la interpreta.

## Ejecutándolo

`armature_core` se instala desde PyPI (arriba); el **registro de experimentos y los instrumentos de renderizado** son este repositorio, clonado y ejecutado: no hay servicio, ni demonio. Cada instrumento se invoca directamente:

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| Plataforma | Windows 11 en el set (Omen 45L, RTX 5090). Las pruebas herméticas también se ejecutan en `ubuntu-latest` en CI; las pruebas dependientes de Blender **se omiten visiblemente** donde falta Blender en lugar de pasar silenciosamente. |
| Python | 3.13+: CI ejecuta 3.13, el entorno virtual del set ejecuta 3.14. Las dependencias de prueba son numpy, pillow, pytest, opencv (fijadas a la versión del set, porque las pruebas de rasterización de pose afirman una rasterización estable en bytes) y matplotlib. |
| Blender | 5.  2, solo en modo sin interfaz gráfica. Una sesión de GUI activa genera artefactos sin parámetros registrados, y una receta que no reproduce su resultado no es una receta. |
| Nodo | 22, solo para el sitio bajo `site/` |
| Generación | se ejecuta en Comfy Cloud y la envía el operador; el renderizado y la medición se ejecutan localmente. |

Las rutas absolutas del entorno están integradas en muchas herramientas y documentos; no son secretos, pero sí implican que la mayoría de los instrumentos no funcionarán sin modificaciones en otra máquina.

## Reglas básicas que dan forma a todo aquí

**Nunca se permiten modelos no comerciales, ni siquiera en experimentos.** Las licencias CC-BY-NC, solo para investigación y solo para uso académico están prohibidas por completo. Una conclusión obtenida con un modelo prohibido es una conclusión que debe descartarse, por lo que nunca comienza.

**Las métricas son diagnósticos; el Director juzga.** Si la imagen en pantalla es el mismo personaje, es canónico y ninguna métrica se acerca a ello. Cada experimento de generación crea una hoja de **control | salida | referencia | procedencia** antes de que se cite un solo número.

**Los créditos de la nube están limitados antes de ser utilizados.** Los créditos gastados no se pueden deshacer, por lo que cada especificación indica su límite máximo por rama con antelación.

**Las rutas revelan qué elementos las acompañan** (la decisión del Director, 2026-08-12). Cualquier ruta a través de un nivel de terceros documenta el uso de datos y la postura de capacitación de sus proveedores, sus obligaciones de divulgación de contenido con IA y su política de marcas de agua, basadas en los documentos recuperados del mapa de licencias. Las rutas completamente locales indican que nada sale del entorno. Una ruta sin su nota de divulgación no está completa; la primera aplicación utiliza la especificación E13.

## Modelo de confianza y amenazas

La política completa es [SECURITY.md](SECURITY.md), medida en relación con el árbol, en lugar de afirmada. La versión resumida:

- **Datos accedidos:** mallas, renderizados, vídeos, imágenes y JSON en el disco local, en las rutas que se pasan en la línea de comandos, más `docs/index/armature.db`, un índice SQLite *derivado* del archivo markdown de este repositorio. Los activos canónicos se consumen en modo de solo lectura desde árboles hermanos y nunca se escriben en ellos.
- **Datos NO accedidos:** no hay credenciales de ningún tipo: ninguna se lee, almacena ni transmite, y un análisis de cada archivo rastreado para detectar claves, tokens, bloques de clave privada y asignaciones de secretos en línea con prefijos de proveedor devuelve cero coincidencias. No se recopila ni envía **ninguna telemetría, analítica o recuento de uso**; no hay opción de exclusión porque no hay nada de lo que excluirse.
- **Salida de red:** no se importa ninguna biblioteca de redes Python en `tools/` o `tests/`. Dos herramientas ejecutan comandos a `curl.exe` para descargar los archivos enumerados en un archivo *que usted* pega, desde una generación *que usted* envió. Nada más aquí realiza una llamada de red.
- **Permisos:** permisos de usuario normales. No hay elevación de privilegios, no hay instalación de servicios, no hay escrituras en el registro o en la configuración del sistema.
- **Los aspectos críticos se revelan en lugar de ocultarse:** las operaciones de archivos no están aisladas; una herramienta escribe donde sus argumentos indican. Los fallos inesperados imprimen un rastreo completo. Las denegaciones deliberadas no lo hacen: cada puerta levanta un error tipificado que contiene la medición que la activó, y **ninguno de ellos es un `assert`**: el conjunto se ejecuta una segunda vez bajo `-O` en CI para demostrar que siguen levantándose.
- **Estado de soporte:** `main` es el único estado compatible. No hay canal de lanzamiento, no hay política de retrocompatibilidad, no hay SLA.

**Puerta de envío.** [SHIP_GATE.md](SHIP_GATE.md) contiene las puertas estrictas A–D tal como están realmente, con cada línea verificada con su evidencia o omitida con la razón en función de sus méritos. Los elementos de identidad de la puerta flexible se enumeran honestamente, incluido el que aún está abierto.

## Licencia

MIT: consulte [LICENSE](LICENSE). La licencia de cualquier *modelo* utilizado a través de esta herramienta es una cuestión separada, rastreada en `docs/license-map.md`.
