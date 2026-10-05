"""Where each port is on each session's maze image, side by side.

One panel per session listed in parameters.yaml: the blackout frame, every bin
labelled at a port drawn as a faint dot in that port's colour, and each port's
centre -- the mean of those bins' head positions -- marked and numbered. The
port numbers are the rig's own, as recorded in each trial's Port and carried
into port_ids.csv by embedding_and_labels.m, so this shows where the data puts
each port in the camera's view, not where the physical labels on the rig are.

    python port_locations.py      # writes figures/port_locations.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from PIL import Image

from paths import RAW_DIR

params = yaml.safe_load(Path('parameters.yaml').read_text())
colours = params['port_colors']
sessions = params['sessions']

figure, axes = plt.subplots(1, len(sessions), figsize=(6.5 * len(sessions), 6),
                            squeeze=False)

for ax, (name, session) in zip(axes[0], sessions.items()):
    stem = Path(session['data_file']).stem
    labels = Path('data') / stem / 'binned_labels'
    positions = np.loadtxt(labels / 'head_positions.csv', delimiter=',')
    ports = np.loadtxt(labels / 'port_ids.csv')

    ax.imshow(Image.open(RAW_DIR / session['maze_png']))
    for port in range(1, len(colours) + 1):
        at = ports == port
        if not at.any():
            continue
        ax.scatter(*positions[at].T, s=2, color=colours[port - 1], alpha=0.25,
                   linewidths=0)
        x, y = np.nanmean(positions[at], axis=0)
        ax.scatter(x, y, s=500, color=colours[port - 1], edgecolors='white',
                   linewidths=2, zorder=3)
        ax.text(x, y, str(port), ha='center', va='center', color='white',
                fontsize=13, fontweight='bold', zorder=4)

    ax.set_title(f'{name}  ({stem})', fontsize=11)
    ax.axis('off')

figure.suptitle('Port centres in camera view: mean head position of bins at each port',
                fontsize=13)
figure.tight_layout()

out_path = Path('figures') / 'port_locations.png'
out_path.parent.mkdir(exist_ok=True)
figure.savefig(out_path, dpi=120)
print(f'wrote {out_path}')
