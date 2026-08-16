# @mcptoolshop/armature

**You block the shot. The model shoots it.**

Node launcher for [`armature-previz`](https://pypi.org/project/armature-previz/) — GLB-authored
previz, control sequences and gates for video-diffusion generation.

A video model can produce motion, light and life that no renderer can. It cannot be told
*who is on screen and where they are standing*. armature supplies exactly that: a canonical
character mesh is staged and animated in headless Blender, and the render becomes a per-frame
**control sequence** the video model must obey — so AI-generated video can carry one
persistent main character whose position and pose are known every frame.

**armature is image-to-video with a GLB instead of an image.**

## Install

```bash
npm install -g @mcptoolshop/armature
```

The toolkit itself is Python, so install that too:

```bash
pip install armature-previz
```

```bash
armature check
```

## Why a launcher and not a port

armature's measured pieces — the gates, the framing solves, the channel maths — are Python.
Re-implementing any of them in Node would create a second copy of a threshold, which is how a
threshold drifts. This package installs the `armature` command and forwards it, verbatim, to
the Python that holds the truth.

**It will not install Python for you and will not `pip install` anything behind your back.**
When the toolkit is missing it says which of the two things is wrong — no interpreter, or an
interpreter without the package — prints the one command that fixes it, and exits non-zero.

Point it at a specific interpreter with `ARMATURE_PYTHON` if you keep several.

## Commands

```bash
armature check      # import every module and report what resolved
armature modules    # what each module is for  (--json for machine output)
armature where      # where the docs and the Blender-side scripts live
```

## The rendering scripts are not here, deliberately

`render_turnaround.py` and its siblings run inside **Blender's own interpreter**:

```bash
blender -b -P tools/render_turnaround.py -- --glb subject.glb --out renders --ortho
```

They live in the repository, where the invocation that works is the one written down.

- **Docs and handbook:** https://mcp-tool-shop-org.github.io/armature/
- **Repository and the full record:** https://github.com/mcp-tool-shop-org/armature

## License

MIT.
