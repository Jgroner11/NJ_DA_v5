"""Time warping of each trial's UMAP trajectory onto WARP_BINS bins, split at
the lick, and the mean warped trajectory of each trial type.

Every trial is taken to end LICK_BEFORE_END_S after its lick -- rewarded
trials end a fixed ~2 s after reward onset, and unrewarded ones look the same
from port arrival on -- so the lick is placed there rather than read from
anything. A trial then runs from its start to the lick, a stretch that varies
a lot from trial to trial, and the fixed LICK_BEFORE_END_S after. The warp
gives each of the two sections its own share of the bins, in proportion to
the average trial: the cutoff is the mean lick time in trial over the mean
trial length, over every trial of the session. Bins 0 to pre_bins - 1 then
span start to lick and the rest lick to end, so the lick sits at the same
warped bin in every trial.

Each trial's trajectory is linearly interpolated, one coordinate at a time,
at the real times of its warped bin centres, through each of these embeddings:

    full            every trial, through umap_full.npy
    patch_<P>_all   only the trials at patch P's ports, through umap_patch_<P>_all.npy

A patch embedding was fitted on every bin of exactly those trials, so each
trial it warps is made of fitted points alone, never ones placed by
UMAP.transform. Every embedding shares the session's one cutoff, worked out
over every trial, so a warped bin means the same point in a trial in all of
them. Every trial type appears -- codes as in trial_type.csv, named in
video.TRIAL_TYPES -- bar a trial no longer than LICK_BEFORE_END_S, which has no
time before its lick and is left out. Run from the project root, after
embedding_and_labels.m and run_umap.py:

    python warp.py

and for each embedding <name> it writes data/<session>/embeddings/warped_<name>.npz:

    warped       (n_trials, WARP_BINS, n_components)  each trial's warped trajectory
    trial_ids    (n_trials,)                          its SessionTrial
    trial_type   (n_trials,)                          its trial_type.csv code
    real_times   (n_trials, WARP_BINS)                seconds from trial start each bin was read at
    pre_bins     ()                                   warped bins before the lick
    type_codes   (n_types,)                           the trial types present, ascending
    type_counts  (n_types,)                           trials of each
    type_means   (n_types, WARP_BINS, n_components)   their mean warped trajectory

and figures/<session>/umap/umap_<name>_trial_type_means.html: the embedding,
uncoloured and faded, with each type's mean trajectory drawn through it and
the lick marked on each.

Everything is read off the per-bin csvs, so trial edges, and with them the
lick, are only as fine as a bin: a trial runs from half a bin before its first
bin's centre to half a bin after its last. A warped bin in the first or last
half bin of a trial lies outside its bin centres, and takes the nearest one's
value.
"""

import numpy as np
import plotly.graph_objects as go

import umap_plots as plots
import video
from paths import load_params, session_paths

WARP_BINS = 100                                  # bins each warped trial is resampled onto
LICK_BEFORE_END_S = 2.0                          # every trial's lick, this long before it ends

FIGURE_SIZE = 900                                # side of the html plot, in pixels
CLOUD_OPACITY = 0.15                             # the faded embedding under the means
MEAN_WIDTH = 6                                   # mean trajectory line width
LICK_SIZE = 7                                    # lick marker on each mean
PATCHES = 4                                      # patch embeddings, patch_1_all to this
TYPE_COLOURS = {                                 # trial_type.csv code -> mean trajectory colour
    1: '#A6CC5C', 2: '#8C564B', 3: '#D4B44A',
    4: '#E07A1F', 5: '#2A7FA8', 6: '#7B5EA7', 7: '#5B5A57', 8: '#E6A1C0', 9: '#B8336A'}

PARAMS = load_params()
PATHS = session_paths(PARAMS)
LABEL_DIR = PATHS.label_dir
EMB_DIR = PATHS.emb_dir


def session_trials(times, trial_ids):
    """Each trial's rows, and its start, lick and end in session seconds, the
    lick LICK_BEFORE_END_S before the end. A trial no longer than that is left
    out, and returned separately as a count."""
    half_bin = (times[1] - times[0]) / 2

    trials, too_short = [], 0
    for trial in np.unique(trial_ids[~np.isnan(trial_ids)]):
        rows = np.flatnonzero(trial_ids == trial)
        start = times[rows[0]] - half_bin
        end = times[rows[-1]] + half_bin
        if end - start <= LICK_BEFORE_END_S:
            too_short += 1
            continue
        trials.append((trial, rows, start, end - LICK_BEFORE_END_S, end))
    return trials, too_short


def warped_bin_times(start, lick, end, pre_bins):
    """Session times of one trial's WARP_BINS warped bin centres: pre_bins
    evenly across start to lick, the rest evenly across lick to end."""
    post_bins = WARP_BINS - pre_bins
    pre = start + (np.arange(pre_bins) + 0.5) / pre_bins * (lick - start)
    post = lick + (np.arange(post_bins) + 0.5) / post_bins * (end - lick)
    return np.concatenate([pre, post])


def warp_trials(coords, times, trials, pre_bins):
    """Each trial's trajectory through `coords`, one row per bin of the
    session, read at its warped bin centres; and the seconds from its start
    each warped bin was read at."""
    warped = np.empty((len(trials), WARP_BINS, coords.shape[1]))
    real_times = np.empty((len(trials), WARP_BINS))
    for k, (_, rows, start, lick, end) in enumerate(trials):
        sample_times = warped_bin_times(start, lick, end, pre_bins)
        for c in range(coords.shape[1]):
            warped[k, :, c] = np.interp(sample_times, times[rows], coords[rows, c])
        real_times[k] = sample_times - start
    return warped, real_times


def means_figure(points, title, type_codes, type_counts, type_means, pre_bins, camera):
    """The embedding as the plain panel draws it, faded, with one line per
    trial type's mean warped trajectory and a diamond at its lick.

    The lick falls between warped bins pre_bins - 1 and pre_bins, so the
    diamond sits at their midpoint.
    """
    figure = plots.plain_figure(points, f'{title} - mean warped trajectory per trial type',
                                camera, FIGURE_SIZE)
    figure.update_traces(marker_opacity=CLOUD_OPACITY, hoverinfo='skip',
                         name='every bin', showlegend=False)

    for code, count, mean in zip(type_codes, type_counts, type_means):
        colour = TYPE_COLOURS.get(code, plots.POINT_COLOUR)
        name = f'{video.TRIAL_TYPES[code]} ({count})'
        figure.add_trace(go.Scatter3d(
            x=mean[:, 0], y=mean[:, 1], z=mean[:, 2], mode='lines',
            line=dict(color=colour, width=MEAN_WIDTH), name=name, legendgroup=name,
            customdata=np.arange(WARP_BINS),
            hovertemplate=f'{name}<br>warped bin %{{customdata}}<extra></extra>'))

        lick = mean[pre_bins - 1:pre_bins + 1].mean(axis=0)
        figure.add_trace(go.Scatter3d(
            x=[lick[0]], y=[lick[1]], z=[lick[2]], mode='markers',
            marker=dict(color=colour, size=LICK_SIZE, symbol='diamond',
                        line=dict(color=plots.POINT_COLOUR, width=1)),
            legendgroup=name, showlegend=False,
            hovertemplate=f'{name}<br>lick<extra></extra>'))

    return plots.show_category_legend(figure)


def warp_embedding(name, title, points, mask, times, trials, trial_type, pre_bins):
    """Warp `trials` through one embedding, average them per trial type, and
    write the npz and the html plot.

    `points` is the embedding as run_umap.py wrote it and `mask` the bins it
    was fitted on, its row i being the i-th True. Every trial handed in must
    lie wholly inside the mask.
    """
    coords = np.full((len(times), points.shape[1]), np.nan)
    coords[mask] = points
    assert all(mask[rows].all() for _, rows, *_ in trials), \
        f'a trial warped through {name} has bins it was not fitted on'

    warped, real_times = warp_trials(coords, times, trials, pre_bins)
    warped_ids = np.array([trial for trial, *_ in trials])
    warped_types = np.array([trial_type[rows[0]] for _, rows, *_ in trials])

    type_codes, type_counts = np.unique(warped_types, return_counts=True)
    type_means = np.stack([warped[warped_types == code].mean(axis=0)
                           for code in type_codes])

    print(f'{title}: {len(trials)} trials, '
          + ', '.join(f'{code}: {count}' for code, count in zip(type_codes, type_counts)))

    out_path = EMB_DIR / f'warped_{name}.npz'
    np.savez(out_path, warped=warped, trial_ids=warped_ids, trial_type=warped_types,
             real_times=real_times, pre_bins=pre_bins, type_codes=type_codes,
             type_counts=type_counts, type_means=type_means)
    print(f'  wrote {out_path}  warped {warped.shape}, type_means {type_means.shape}')

    camera_key = f'{name}_camera'
    camera = video.read_camera(PARAMS['vid'], camera_key)
    figure = means_figure(points, title, type_codes, type_counts, type_means, pre_bins, camera)
    html_path = PATHS.umap_dir / f'umap_{name}_trial_type_means.html'
    print(f'  wrote {plots.write_html(figure, html_path, camera_key, video.CAMERA_ZOOM)}')


if __name__ == '__main__':
    times = np.loadtxt(LABEL_DIR / 'bin_times.csv')
    trial_ids = np.loadtxt(LABEL_DIR / 'trial_ids.csv')
    trial_type = np.loadtxt(LABEL_DIR / 'trial_type.csv').astype(int)
    patch_id = np.loadtxt(LABEL_DIR / 'patch_id.csv').astype(int)
    trials, too_short = session_trials(times, trial_ids)

    # The cutoff: the mean trial's share of time before the lick, over every
    # trial, and shared by every embedding.
    lengths = np.array([end - start for _, _, start, _, end in trials])
    lick_times = lengths - LICK_BEFORE_END_S
    cutoff = lick_times.mean() / lengths.mean()
    pre_bins = round(cutoff * WARP_BINS)

    print(f'{len(trials)} trials, {too_short} left out as no longer than '
          f'{LICK_BEFORE_END_S:g} s: mean length {lengths.mean():.2f} s, '
          f'mean lick time {lick_times.mean():.2f} s')
    print(f'cutoff {cutoff:.3f}: {pre_bins} of {WARP_BINS} bins before the lick, '
          f'{WARP_BINS - pre_bins} after')

    PATHS.umap_dir.mkdir(parents=True, exist_ok=True)

    full = np.load(EMB_DIR / 'umap_full.npy')
    assert len(full) == len(times), \
        f'{len(full)} embedded bins but {len(times)} in bin_times.csv'
    warp_embedding('full', 'Full session', full, np.ones(len(times), dtype=bool),
                   times, trials, trial_type, pre_bins)

    for patch in range(1, PATCHES + 1):
        path = EMB_DIR / f'umap_patch_{patch}_all.npy'
        if not path.exists():
            print(f'no {path.name}; patch {patch} skipped')
            continue
        mask = patch_id == patch
        at_patch = [trial for trial in trials if patch_id[trial[1][0]] == patch]
        warp_embedding(f'patch_{patch}_all', f'Patch {patch}', np.load(path), mask,
                       times, at_patch, trial_type, pre_bins)
