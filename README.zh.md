<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.md">English</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
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

**你挡住了镜头。模型拍摄了它。**

**[登陆页面和手册 →](https://mcp-tool-shop-org.github.io/armature/)**

一个视频模型可以产生渲染器无法产生的运动、光线和生命。你无法分辨*屏幕上是谁以及他们站在哪里*。armature 恰好提供了这一点：一个规范的角色网格被放置并以无头 Blender 的形式进行动画处理，渲染结果成为每帧的**控制序列**，视频模型必须遵守该序列——因此，人工智能生成的视频可以呈现出一个持续存在的主要角色，并且每一帧都知道角色的位置和姿势。

**armature 是图像到视频的转换，使用 GLB 文件代替图像。** 所有空间元素都经过了设计，模型在其之上赋予生命。最终交付的是素材——电影、过场动画、角色姿势和动作，以及任何镜头。游戏只是该素材的一种应用方式，而不是该工具的边界。

在 Blender 中设置你的角色。渲染控制序列。让视频模型在其之上赋予生命。结构来自你拥有的几何体；生命来自模型；身份是一个命名的、版本化的事物，它存在于提示词和参考堆栈中——而不是某个幸运帧的偶然结果。

## 安装

```bash
pip install armature-studio
```

```bash
npm install -g @mcptoolshop/armature-studio   # the same command, as a launcher
```

```bash
armature check
```

可安装的软件包是 **`armature_core`** ——关卡、框架和旋转求解器、镜头规范合同、通道数学以及有效负载构建器。它们都以纯 CPython 的形式导入，这使得它们可以在没有 Blender 的情况下进行测试和打包。

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**渲染脚本不是控制台入口点，这是有意的。** `render_turnaround.py`、`stage_render.py`及其相关组件在 **Blender 自身的解释器**中运行——你的 Python 中的一个控制台脚本无法导入 `bpy`，并且会在第一行代码处失败，因此提供一个这样的脚本是不现实的：

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

它们停留在仓库中，其中有效的调用方式是记录的方式。`armature_core.blender_scene` 是导入 `bpy` 的唯一模块；`armature check` 将其报告为 `needs-blender`，而不是将其视为缺陷。

npm 包是一个**启动器，而不是一个端口**：在第二种语言中重新实现一个阈值，会导致阈值发生漂移，因此它会转发到包含真实数据的 Python 中，并拒绝——以响亮、非零的方式，使用唯一可以修复它的命令——而不是代表你安装任何东西。

---

## 状态：该论点在产品级别上得到衡量

成立于 **2026-08-10**。完成了 13 个实验，并且该论点已从*正在测试中*发展到**在产品级别上进行衡量**：角色在他的骨骼驱动下在屏幕上跳舞并自由活动；一个手工制作的世界保持到最后一帧，使用了两个种子（E12），并且**身份现在可以在托管的、由人类训练的分层系统中存活，该系统仅接收授权的参考资料**（E13）——所有这些都由导演进行判断。创始阶段审计位于 [docs/audit-first-arc.md](docs/audit-first-arc.md)；自 2026-08-12 以来的状态是一个学习型单仓库——实验证明了路径，没有路径可以通过惯性成为规范（CLAUDE.md）。

| | |
|---|---|
| 实验 | **E01–E14 已完成**（E05 因虚假前提而被撤回）——控制阶段（E01–E06）、骨骼修复 + 骨架批准（E07）、**第一个渲染的镜头**（E08）、干净链基线（E09）、密集化驱动采用（E10）、无控制路线，三个阶段导致了具有指导意义的失败（E11）、**自由路线获得了一个世界**以及 6.0 / uni_pc 基线（E12）、**组合路线回答了它的问题**（E13——已发布，在零花费下停止，由支持阶段进行修复、重新武装、运行并关闭，所有这些都在同一日期内完成：身份保持在导演的眼中；参考资料指导模型决定的世界）——**LoRA 场景杠杆定价实时**（E14——烘焙测试：两种风格 LoRA 都绑定到派生权重；角色保留在 `technically_color` 上并失败于照片级对；获胜者将携带一个无法解析的已服务文件层和一个信用义务，两者都已记录） |
| 路线 | **三种，已衡量**——**驱动路线**（骨骼渲染的 AAPose 贴纸 → Animate；在镜头级别上得到证明，暂停并获得许可以供重新使用）、**自由路线**（GLB 设计的起始帧 → 相机层位于 6.0 / uni_pc 基线上；身份保持未锚定状态，一个手工制作的世界保持到两个种子，并且 LoRA 场景杠杆被实时衡量——E14）、**组合路线**（授权的参考资料进入托管的身份锁定层——由 E13 完成：身份锁定的、模型决定的电影摄影，世界由参考资料携带的内容进行指导；其规范中包含披露说明） |
| 支出 | 创始阶段有 22 个探测器，每个探测器的费用为 4 个积分；E08–E12 阶段的支出为 **0 积分**（GPU 小时计费），并且在每个实验中都有上限；**E13 的四个生成是仓库中的第一个合作伙伴信用支出，其支出位于他们先前声明的 424–844 范围内**；E14 的两个生成支出为 **0 个合作伙伴积分**，达到两个生成的上限。 |
| 许可地图 | 每个采用的依赖项都包含一个**检索到的许可文档**；未验证的内容被视为“无”；通过第三方层进行的路线还包含**每条路线的披露信息**（由导演于 2026-08-12 确定）；该关卡的明确目的是发布工作室的艺术作品。 |
| 支出关卡 | **CANON 关卡**拒绝提交付费内容，如果无法根据机器可读的规范来命名其主题——表面是行，一个空占位符是一个**孔而不是缺失**，并且会检查两个方向（提示词涵盖了规范；提示词中的所有内容*都是*规范）。它会在创建输出目录之前，在七个有效负载构建器中的每一个中触发，因为此仓库拥有的不可逆步骤是写入有效负载。逃生方式以普查为后盾：如果某个主题*具有*规范，则拒绝 `--no-canon`，而不是接受。 |
| 测试 | **1351 在拍摄现场进行**（14 次跳过，测量于 2026-08-18），在 `-O` 中完全相同；CI 流程模拟了渲染器可以真正做到的事情——本地资产 **明显跳过**。 |
| 状态 | **v0.3.0** — 该记录增加了一个支出门控和一个自我验证的索引。`armature_core` 以 `armature-studio` 的形式发布到 PyPI，以 `@mcptoolshop/armature-studio` 的形式发布到 npm，并从一个标签中通过 OIDC 发布，且没有长期有效的令牌。 |

### 测量的是什么（当前阶段）

- **身份一致性**——既有驱动（E08：画面显示与双胞胎相似），又有非锚定状态（E11 波次 1：每个特征都保留到最后一帧，没有参考、没有剪辑视觉效果、没有驱动信号）。导演的视角是记录的最终判定标准。
- **相机严格遵循明确控制，精确到单个像素**（在相机层权重上，E11 波次 3），并且在没有明确指令的情况下进行推移（E11 波次 1）。
- **密度影响信号，而非性能**（E10）——重采样使步骤平滑了 41%，性能提升了 8.6%；尽管如此，仍然通过视觉效果来判断：更高的帧率看起来更好。
- **许可问题与线路连接无关**（E11 波次 2）——一个映射的 Apache 模型和一个从未加载该模型的图表，在每个门控都显示为绿色时，产生了 65 帧噪声。现在存在“门控对”功能。
- **场景构图具有种子敏感性**（E10 / E11）——相同的文本重新组合了整个世界，跨越不同的种子。**一个场景声明需要两个种子才能成为一个属性。**
- **一个稳定的世界得以保留**（E12）——起始帧中的真实房间在相机层上的两个种子上保留到最后一帧，并且通过字段差异将一个变量属性分配给起始图像。相同的层在一个预览空虚中保留了一个空虚（E11 波次 3）：世界是创作出来的，然后被保存下来。
- **目录的 6.0 / uni_pc 是相机层的基准**（E12）——继承的 3.5 / euler 前提落到了它自己的层级：在目录设置中，相同的种子既失去了一个头部又长出了一个肢体，使得人物保持到 f80。代价是明确的——更强的附着力将 **未限定身份条款**应用于两个种子上的人群；以主题为范围的提示是主要的控制杆。
- **身份在仅由授权参考资料提供的层级中得以保留**（E13）——在 wan2.7 的参考视频中，双臂、两个种子，风格化的木制表演者通过一个经过人工训练的模型呈现出与导演视角相同的角色。三个盲测预测表明该层级会覆盖非人类结构；但没有一个预测是正确的——现在将对这些模型的一方向性悲观情绪记录下来，作为校准原则。
- **参考资料引导模型决定的世界，并在该层级上主导种子混沌**（E13）——灰色板材产生了灰色的工作室，一段温暖的酒吧片段产生了温暖的内部空间，并且两个种子的手臂都一致了。机制归因（板材溢出与工作室默认值）在四个世代中可以明确地看到；一个属性级声明在一个设计的后续步骤中遵循双种子法则。
- **构建的视频到达视频插座**（E13）——没有上传路径用于剪辑，但 81 个授权帧以图形方式组装（`CreateVideo`），并被接受到参考视频插座。原则上，平台上所有 VIDEO 类型的输入都可以从授权帧中访问。

### 不包括的内容

- **高速运动的手臂和手**。在两个种子和两种设置下，仍然无法达到 f80（E12）。控制杆被重新限定为 **首先关注呈现效果**——腕部和相机布景，来自导演对 GLB 的诊断（爪子是一个投影伪像，而不是网格损坏），并以网格修复作为最后的手段，而不是第一步。
- **摄影世界中的相机声明**。在所有四个 E12 剪辑中，0/81 个地平线检测结果表明，检测器需要一个该世界没有的地缝——在提交之前进行注册盲测，并且从未转换为相机结果。在对真实房间进行任何相机编号读取之前，应该有一个 **无缝的相机仪器**。
- **叙事层**（请参阅 #7）：情节转折点、每个片段的提示、视频时间区域条件、相机嵌入——已采用，并在需要时获得许可，但尚未测试。

一个否定的答案仍然是一个完全成功的案例——E11 的严重失败带来了三个门控、两个法则以及下一个工作的确切形状，并且路线图在任何证据出现之前就说明了这一点。

## 此仓库的工作方式

- [CLAUDE.md](CLAUDE.md)——如何在此处工作：三个角色、每个座位遵循的规则以及不可谈判的内容（许可门控、有限额度，身份由视觉效果进行判断）。
- [docs/ROADMAP.md](docs/ROADMAP.md)——整个构建过程，按会话划分，并提前命名了漂移触发器。
- `docs/experiments/`——每个非平凡的更改都以编号实验的形式运行：**先制定规范，然后进行工作 → 工作完成后进行报告 → 最后由顾问做出裁决。**
- `docs/license-map.md`——经过验证的商业用途地图。没有任何内容可以在没有检索到的许可文档的情况下进入流水线。

该方法继承自 [facet](../facet)，在那里它得到了应用：在 facet 的初始会话中，六个继承的声明在几分钟内被证明是错误的，因为每个声明都与可运行的代码相邻。armature 是 facet 的下游产品——facet 雕刻并绘制人物；armature 进行布景和表演。

## 如何运行它

`armature_core` 可以从 PyPI 安装（如上所述）；**实验记录和渲染仪器**是此仓库，克隆并运行——没有服务，也没有守护进程。每个仪器都直接调用：

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| 平台 | 拍摄现场的 Windows 11（Omen 45L，RTX 5090）。在 CI 中，hermetic 测试也在 `ubuntu-latest` 上运行；依赖于 Blender 的测试会在没有 Blender 时 **明显跳过**，而不是静默地通过。 |
| Python | 3.13+——CI 运行 3.13，拍摄现场的 venv 运行 3.14。测试依赖项包括 numpy、pillow、pytest 和 opencv（固定到拍摄现场的版本，因为姿势栅格测试断言字节稳定的栅格化）以及 matplotlib。 |
| Blender | 5.2 版本，仅支持无头模式。在没有记录参数的情况下运行 GUI 会话会产生伪影，并且无法重现输出的配方就不是一个有效的配方。 |
| 节点 | 22，仅适用于 `site/` 中的站点 |
| 生成 | 在 Comfy Cloud 上运行，并由操作员提交；渲染和测量在本地进行。 |

许多工具和文档中都使用了绝对的设备路径——它们不是秘密，但这意味着大多数工具未经修改就无法在另一台机器上运行。

## 所有内容的基础规则

**永远不允许使用任何非商业模型，包括实验。** CC-BY-NC、仅用于研究和仅用于学术用途的许可被完全禁止。如果基于受禁用的模型得出的结论，则该结论必须被抛弃，因此它从一开始就不能开始。

**指标是诊断工具；由总监进行判断。** 屏幕上显示的图像是否为同一个角色才是关键，没有任何指标可以近似地表示这一点。每个生成实验都会在引用任何数字之前构建一个 **控制 | 输出 | 参考 | 出处** 表格。

**云端积分在使用前是有限制的。** 使用过的积分无法撤销，因此每个规范都提前说明了每个分支的上限。

**路径会显示与之相关的流程**（总监裁定，2026-08-12）。通过第三方层级的任何流程都会记录其提供商的数据使用和训练策略、AI 内容披露义务以及水印政策，这些都基于许可地图中获取的文档。完全本地化的流程表明没有任何数据会离开设备。如果缺少披露说明，则该流程不完整——首次应用将遵循 E13 的规范。

## 信任和威胁模型

完整的策略是 [SECURITY.md](SECURITY.md)，它不是断言而是根据树形结构进行衡量。简要说明如下：

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
- **Support status** — `main` is the only supported state. No release channel, no backport
  policy, no SLA.

**发布门控。** [SHIP_GATE.md](SHIP_GATE.md) 包含实际存在的 A–D 四个硬性门控，每一行都附带其证据或说明跳过该行的理由。软性门控标识项也如实列出，包括仍然开放的那个。

## 许可

MIT——请参阅 [LICENSE](LICENSE)。通过此工具使用的任何 *模型* 的许可证都是一个单独的问题，并在 `docs/license-map.md` 中进行跟踪。
