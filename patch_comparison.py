"""Each patch's embedding beside the same patch's embedding after identification.

The left plot is umap_patch_<P>_all.npy, fitted on every bin of the trials at
patch P's ports. The right is umap_patch_<P>_identified.npy, fitted on only the
bins of those trials that came after their block's patch was identified -- see
run_umap.py. Both are coloured by port, as port_figure colours every embedding,
so a port keeps its hue across the pair. Run from the project root, after
embedding_and_labels.m and run_umap.py:

    python patch_comparison.py

and for each patch with both embeddings it writes
figures/<session>/prediscovery_patch_comparison/patch_<P>.html. Each side keeps
the camera its own embedding has in parameters.yaml, and can be orbited apart.
"""

import numpy as np
from plotly.subplots import make_subplots

import umap_plots as plots
import video
from paths import load_params, session_paths

PARAMS = load_params()
PATHS = session_paths(PARAMS)
LABEL_DIR = PATHS.label_dir
EMB_DIR = PATHS.emb_dir

SIDE = 600                                       # width and height of each plot, in pixels
LEGEND_WIDTH = 120                               # right margin the legend sits in


def side_by_side(patch, sides, colours):
    """One figure, the two port figures in its two scenes, sharing one legend.

    sides is (name, title, points, ports) for the left plot then the right.
    port_figure draws each, so the colouring is exactly the other port plots';
    its traces and scene layout are then moved into this figure's scene and
    scene2. A port present on both sides gets one legend entry, which toggles
    it on both.
    """
    figure = make_subplots(rows=1, cols=2, specs=[[{'type': 'scene'}] * 2],
                           subplot_titles=[title for _, title, _, _ in sides],
                           horizontal_spacing=0.02)

    shown = set()
    for col, (name, title, points, ports) in enumerate(sides, start=1):
        camera = video.read_camera(PARAMS['vid'], f'{name}_camera')
        single = plots.port_figure(points, ports, colours, title, camera, SIDE)
        for trace in single.data:
            trace.update(legendgroup=trace.name, showlegend=trace.name not in shown)
            shown.add(trace.name)
            figure.add_trace(trace, row=1, col=col)
        figure.update_layout({'scene' if col == 1 else f'scene{col}': single.layout.scene})

    # The legend in a margin of its own, so it covers neither plot.
    plots.show_category_legend(figure)
    figure.update_layout(
        legend=dict(x=1.0, xanchor='left'),
        title=dict(text=f'Patch {patch}', x=0.01, xanchor='left'),
        width=2 * SIDE + LEGEND_WIDTH, height=SIDE,
        margin=dict(l=0, r=LEGEND_WIDTH, t=60, b=0),
        paper_bgcolor=plots.BACKGROUND)
    return figure


patch_id = np.loadtxt(LABEL_DIR / 'patch_id.csv')
patch_identified = np.loadtxt(LABEL_DIR / 'patch_identified.csv').astype(bool)
port_ids = np.loadtxt(LABEL_DIR / 'port_ids.csv')

PATHS.patch_comparison_dir.mkdir(parents=True, exist_ok=True)

for patch in range(1, video.PATCHES + 1):
    in_patch = patch_id == patch
    selections = [(f'patch_{patch}_all', 'Every trial', in_patch),
                  (f'patch_{patch}_identified', 'After identification',
                   in_patch & patch_identified)]

    sides = []
    for name, title, mask in selections:
        path = EMB_DIR / f'umap_{name}.npy'
        if not path.exists():
            break
        points = np.load(path)
        assert len(points) == mask.sum(), (
            f'{path.name} has {len(points)} rows but its mask selects '
            f'{int(mask.sum())} bins -- re-run run_umap.py')
        sides.append((name, f'{title} ({len(points)} bins)', points, port_ids[mask]))

    if len(sides) < 2:
        print(f'no {path.name}; patch {patch} skipped')
        continue

    out_path = PATHS.patch_comparison_dir / f'patch_{patch}.html'
    side_by_side(patch, sides, PARAMS['port_colors']).write_html(out_path)
    print(f'wrote {out_path}')
