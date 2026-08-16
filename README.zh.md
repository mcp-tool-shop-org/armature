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

一个视频模型可以产生渲染器无法产生的动态、光线和生命感。它不能告诉我们*屏幕上是谁，以及他们站在哪里*。armature 正好提供了这一点：一个规范的角色网格被放置并以无头 Blender 形式进行动画处理，然后渲染结果成为每帧的**控制序列**，视频模型必须遵守该序列——因此，人工智能生成的视频可以呈现出一个持续存在的主要角色，并且每一帧都知道角色的位置和姿势。

**armature 是将图像转换为视频，使用 GLB 文件而不是图像。** 所有空间元素都经过了设计，模型在其之上赋予生命。最终交付的是素材——电影、过场动画、角色姿势和动作，以及任何镜头。游戏只是这些素材的消费者之一，而不是该工具的边界。

在 Blender 中设置你的角色。渲染控制序列。让视频模型在其之上赋予生命。结构来自你拥有的几何体；生命来自模型；身份是一个命名的、版本化的事物，它存在于提示和参考堆栈中——而不是某个幸运帧的偶然结果。

## 安装

```bash
pip install armature-previz
```

```bash
npm install -g @mcptoolshop/armature   # the same command, as a launcher
```

```bash
armature check
```

可安装的软件包是 **`armature_core`** ——包括门控、框架和转弯求解器，镜头规格合同、通道数学以及有效载荷构建器。它们中的每一个都以纯 CPython 的形式导入，这使得它们可以在没有 Blender 的情况下进行测试和打包。

```python
from armature_core import turnaround, framing

plan = turnaround.projection_plan(ortho=True, ortho_scale=1.1235359256161628)
```

**渲染脚本不是控制台入口点，这是有意的。**
`render_turnaround.py`、`stage_render.py` 及其相关模块在 **Blender 自身的解释器**中运行——如果你的 Python 中的一个控制台脚本尝试导入 `bpy`，它会在第一行就失败，因此提供这样的脚本是不现实的：

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

它们会保留在此仓库中，其中有效的调用方式是记录的方式。
`armature_core.blender_scene` 是唯一导入 `bpy` 的模块；`armature check` 将其报告为 `needs-blender`，而不是将其视为缺陷。

npm 包是一个**启动器，而不是一个移植版本**：在第二种语言中重新实现阈值会导致阈值发生漂移，因此它会转发到包含真实数据的 Python 代码，并拒绝——以响亮、非零的方式，使用唯一可以修复它的命令——而不是在你不知情的情况下安装任何东西。

---

## 状态：该论点在产品层面进行衡量

成立于 **2026-08-10**。完成了 13 个实验，并且该论点已经从*测试中*发展到**在产品层面上进行衡量**：角色在他的骨骼驱动下在屏幕上跳舞，并且自由地活动；一个手工制作的世界保持到最后一帧，使用了两个种子（E12），并且**身份现在可以在托管的、由人类训练的分层系统中生存，该系统只接收设计好的参考资料**（E13）——所有这些都由导演来判断。创始阶段的审计报告位于
[docs/audit-first-arc.md](docs/audit-first-arc.md)；自 2026-08-12 以来的状态是一个学习型的单一代码仓库——实验证明了路径，没有哪条路径会因为惯性而成为规范（CLAUDE.md）。

| | |
|---|---|
| 实验 | **E01–E14 closed** (E05 withdrawn on a falsified premise) — the control arc (E01–E06) · rig repair + skeleton approval (E07) · **the first painted shot** (E08) · the clean-chain baseline (E09) · densified driving adopted (E10) · the no-control route, three waves to an instructive hard fail (E11) · **the free route gains a world** and the 6.0 / uni_pc baseline (E12) · **the composed route answers its question** (E13 — dispatched, halted at zero spend, repaired by a support arc, re-armed, run, and closed inside one date: identity holds at the Director's eye; reference grounds steer model-decided worlds) · **the LoRA scene-lever priced live** (E14 — the bake-off: both style LoRAs bind on the derivative weights; the character holds on `technically_color` and fails on the photo-real pair; the winner carries an unresolvable served-file tier and a credit obligation, both recorded) |
| 路线 | **三种，已衡量**——**驱动路线**（渲染骨骼 AAPose 贴纸 → 动画；在镜头层面得到证明，暂停，并且可以用于其重新启动）；**自由路线**（使用 GLB 设计的起始帧 → 相机层位于 6.0 / uni_pc 基线；身份保持未锚定状态，一个手工制作的世界保持两个种子，并且 LoRA 场景杠杆被实时衡量——E14）；**组合路线**（将设计好的参考资料输入到托管的身份锁定层中——由 E13 完成：身份锁定的、模型决定的电影拍摄，世界由参考资料所包含的内容进行指导；其规范中有披露说明）。 |
| 花费 | 创始阶段有 22 个测试，每个测试花费 4 个积分；E08–E12 阶段的实际花费为 **0 积分**（GPU 小时计费），低于每个实验设定的上限；**E13 的四个生成是该代码仓库中第一个合作伙伴积分支出，并且在他们之前声明的 424-844 范围内**；E14 的两个生成实际花费了 **0 个合作伙伴积分**，达到其两个生成的上限。 |
| 许可地图 | 每个采用的依赖项都包含一个**检索到的许可文档**；未验证的内容被视为“无”；通过第三方层进行的路线还包含**每条路线的披露说明**（由导演于 2026-08-12 决定）；该门户网站的既定目的是发布工作室的艺术作品。 |
| 测试 | **1311 个测试通过（在骨架上），跳过 13 个（测量于 2026-08-15，v0.2.0 版本），同样适用于 `-O`；CI 测试了运行器可以真正执行的内容——本地骨架资源会**明显地被跳过**。 |
| 状态 | **v0.2.0 于 2026-08-15 发布**——记录变成了一个可安装的工具包：`armature_core` 在 PyPI 上作为 `armature-previz`，在 npm 上作为 `@mcptoolshop/armature`，由 OIDC 从一个标签发布，并且没有长期存在的令牌。该记录仍然是文档树，并且它仍然是完整的。 |

### 正在衡量的内容（当前的阶段）

- **身份一致性**——通过驱动（E08：在整个镜头中，面部看起来像双胞胎）*并且*不锚定（E11 wave 1：最后一帧的每个特征都没有参考、没有剪辑视角、没有驱动信号）。导演的观察是记录的最终裁决。
- **相机严格遵循指令，精确控制到单个像素**（相机层权重，E11 wave 3），并且在没有指令的情况下进行调整（E11 wave 1）。
- **密度影响信号，而非性能**（E10）——重采样使步骤平滑了41%，性能提升了8.6%；尽管如此，仍然通过视觉判断采用：更高的帧率看起来更好。
- **许可证问题不是线路连接问题**（E11 wave 2）——一个映射的Apache模型和一个从未加载它的图表，每次都产生65帧噪声，并且所有门控信号均为绿色。现在存在“门控对”功能。
- **场景构图具有种子敏感性**（E10 / E11）——相同的文本重新构建了整个世界，跨越不同的种子。**一个场景声明需要两个种子才能成为其属性。**
- **一个稳定的世界得以保留**（E12）——起始帧中的真实房间在相机层上的两个种子上保留到最后一帧，并且通过场差将一个变量属性分配给起始图像。相同的层在一个预览空白中保留了一个空白（E11 wave 3）：世界是创作出来的，然后被保存下来。
- **目录的6.0 / uni_pc 是相机层的基准**（E12）——继承的3.5 / euler 前提落到了它自己的等级：在目录设置中，相同的种子既失去了头部又长出了肢体，使得图像保持到f80。代价是明确的——更强的附着力将**未限定身份条款**应用于两个种子上的人群；以主题为范围的提示是主要的控制因素。
- **身份在一个仅接收授权参考输入的托管层中得以保留**（E13）——在wan2.7的参考视频中，双臂、两个种子，程式化的木制表演者通过一个经过人工训练的模型呈现出相同的角色，这符合导演的期望。在两个座位上进行的三个盲测预测该层会覆盖非人类结构；但没有一个预测是正确的——对这些模型的一种单向悲观情绪现在被记录下来作为校准原则。
- **参考依据引导模型决定的世界，并控制该层上的种子混乱**（E13）——灰色板产生了灰色的工作室，一段温暖的酒吧片段产生了一个温暖的内部空间，并且两个种子的结果一致。机制归因（板材溢出与工作室默认值）在四个世代中可以清晰地观察；一种基于属性的声明遵循两个种子的规则，并在一个设计好的后续步骤中进行。
- **构建的视频到达视频接口**（E13）——没有上传路径用于剪辑片段，但 81 个授权帧在图表中组装在一起 (`CreateVideo`)，并被接受到参考视频接口。原则上，平台上所有 VIDEO 类型的输入都可以从授权帧中访问。

### 不符合要求的是什么

- **高速运动的手臂和手**。在两个种子和两种设置下，仍然无法达到 f80（E12）。控制因素被重新设定为**首先考虑呈现效果**——腕部和相机布景，来自导演对 GLB 的诊断（爪子是一种投影伪像，而不是网格损坏），并且以网格修复作为最后的手段，而不是第一步。
- **摄影世界中的相机声明**。在所有四个 E12 剪辑中，0/81 个地平线检测结果表明，检测器需要一个该世界没有的缝隙——在提交之前进行注册盲测，并且从未转换为相机结果。在真实房间上读取任何相机编号之前，应该有一个**无缝的相机工具**。
- **叙事层**（请参考#7）：节拍端点、每个片段的提示、视频时间区域条件、相机嵌入——已采用，并在需要时获得许可，但未经测试。

一个否定答案仍然是一个完全成功的案例——E11 的严重失败带来了三个门控信号、两个规则以及下一个作品的确切形状，并且路线图在任何证据出现之前就说明了这一点。

## 这个仓库的工作方式

- [CLAUDE.md](CLAUDE.md)——如何在这里工作：三个角色、每个座位遵循的规则以及不可谈判的内容（许可证门控信号、有限的积分、身份由视觉判断）。
- [docs/ROADMAP.md](docs/ROADMAP.md)——整个构建过程，按会话划分，并提前命名了漂移触发点。
- `docs/experiments/`——每个非平凡的更改都以编号实验的形式运行：**先进行规范说明，然后进行工作 → 完成报告 → 最后由顾问做出裁决。**
- `docs/license-map.md`——经过验证的商业用途地图。没有任何内容可以在没有检索到许可证文档的情况下进入流水线。

该方法继承自 [facet](../facet)，在那里它得到了应用：在 facet 的初始会话中，六个继承的声明在几分钟内被证明是错误的，因为每个声明都与可运行的代码相邻。armature 是 facet 的下游产品——facet 剪切和绘制图像；armature 对其进行分阶段处理并呈现。

## 如何运行它

无需安装任何东西。这是一个你可以克隆并运行的仓库——没有在任何注册表中存在的软件包，也没有服务或守护进程。每个工具都直接调用：

```
python tools/<name>.py --help                       # measurement, sheets, payload builders
blender -b -P tools/stage_render.py -- <args>       # staging and render, headless only
pwsh -NoProfile -File .\verify.ps1                  # tests, tests under -O, site build
```

| | |
|---|---|
| 平台 | 在机器上使用 Windows 11（Omen 45L，RTX 5090）。hermetic 测试也在 `ubuntu-latest` 中以 CI 的形式运行；依赖于 Blender 的测试会在没有 Blender 时**明显跳过**，而不是静默地通过。 |
| Python | 3.13+——CI 使用 3.13，机器 venv 使用 3.14。测试依赖项包括 numpy、pillow、pytest 和 opencv（固定到机器的版本，因为姿势栅格化测试断言字节稳定的栅格化）以及 matplotlib。 |
| Blender | 5.2，仅限无头模式。一个实时的 GUI 会话会产生没有记录参数的伪像，并且无法重现其输出的配方就不是一个配方。 |
| Node | 22，仅用于 `site/` 下的站点。 |
| 生成 | 在 Comfy Cloud 上运行，并由操作员提交；渲染和测量在本地进行。 |

许多工具和文档都使用了绝对路径——这些不是秘密，但这意味着大多数程序在其他机器上运行时都需要进行修改。

## 所有内容都遵循既定的规则

**绝不允许使用任何非商业模型，包括实验中使用的模型。** CC-BY-NC、仅供研究和仅供学术用途的许可协议均被明确禁止。如果结论是基于一个被禁止的模型得出的，那么这个结论就必须被抛弃，因此它一开始就不应该存在。

**指标用于诊断；最终由主管进行判断。** 屏幕上显示的图像是否与原始角色相同，才是衡量标准，没有任何指标可以近似地达到这一点。每个生成实验都会在引用任何数据之前，先构建一个“控制 | 输出 | 参考 | 出处”表格。

**云端积分在使用前会被限制。** 已使用的积分无法撤销，因此每个配置都预先规定了每个分支的上限。

**路径会显示与之相关的内容（主管裁定，2026-08-12）。** 任何通过第三方渠道进行的流程，都会记录其提供商的数据使用和训练策略、人工智能内容披露义务以及水印政策，这些都基于许可地图中获取的文档。完全本地化的流程会声明没有任何数据会离开系统。如果缺少披露说明，则该流程不完整——首次应用将遵循 E13 的规范。

## 信任和威胁模型

完整的策略在 [SECURITY.md](SECURITY.md) 中，它不是基于断言，而是根据实际情况进行衡量。简要说明如下：

- **涉及的数据**——本地磁盘上的网格、渲染、视频、图像和 JSON 文件，以及您通过命令行传递的路径，此外还有 `docs/index/armature.db`，这是一个从该仓库自身的 Markdown 文档中*派生*出的 SQLite 索引。规范资产仅以只读方式从同级目录读取，绝不会写入。
- **不涉及的数据**——任何类型的凭据：既不读取、也不存储或传输，并且对每个已跟踪的文件进行扫描，以查找提供商前缀的密钥、令牌、私钥块和内联密钥赋值，结果都为零。**不收集或发送任何遥测数据、分析数据或使用情况统计信息；** 因为没有任何内容需要选择退出，所以根本不需要提供选择退出的选项。
- **网络输出**——在 `tools/` 或 `tests/` 中的任何位置都不会导入任何 Python 网络库。两个工具会通过 shell 命令调用 `curl.exe` 来下载您粘贴的转储文件中列出的文件，这些文件来自您提交的生成内容。除此之外，没有任何其他组件会进行网络调用。
- **权限**——普通用户权限。不进行权限提升、不安装服务、不写入注册表或系统设置。
- **潜在风险，公开披露而不是隐瞒**——文件操作不会在沙盒中运行；工具会将数据写入其参数指定的任何位置。意外错误会打印原始回溯信息。有意的拒绝则不会：每个安全检查都会引发一个带有触发该检查的测量值的类型化错误，并且**其中没有任何一个是 `assert`**——该套件会在 CI 中第二次运行 `-O`，以证明它们仍然会引发错误。
- **支持状态**——`main` 是唯一受支持的状态。没有发布渠道、没有回溯策略、也没有 SLA（服务级别协议）。

**发布门控。** [SHIP_GATE.md](SHIP_GATE.md) 包含了实际存在的 A–D 四个硬性门控，每一行都附带了相应的证据或说明其被跳过的理由。软性门控项目也如实列出，包括仍然开放的项目。

## 许可协议

MIT——请参阅 [LICENSE](LICENSE)。通过此工具使用的任何*模型*的许可协议是另一个问题，它在 `docs/license-map.md` 中进行跟踪。
