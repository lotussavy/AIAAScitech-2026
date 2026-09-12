"""Recreate the four result-figure families for all three airports."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .model import BOROUGHS, COSTS, PHASES

COLORS = ["#2479ad", "#e88924", "#37975c", "#c74747"]


def bars(ax, table, label):
    x = np.arange(len(table))
    for i, col in enumerate(COSTS):
        ax.bar(x + (i - 1.5) * .2, table[col], .2, color=COLORS[i],
               label="Taxi" if i == 0 else f"UAM {PHASES[i - 1]}")
    ax.set_xticks(x, table[label].astype(str), rotation=25 if label == "borough" else 0)
    ax.set_ylabel("Trip-weighted GCT (USD-equivalent)")
    ax.set_xlabel("Pickup borough" if label == "borough" else "Pickup taxi zone ID")
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=.2)
    ax.set_axisbelow(True)
    for i, count in enumerate(table["total_trips"]):
        if count == 0:
            ax.text(i, .03, "No data", transform=ax.get_xaxis_transform(), ha="center", fontsize=8)


def switch_lines(ax, table, group, values, phase):
    for value in values:
        rows = table.loc[table[group].eq(value)].sort_values("pickup_hour")
        # Reindex to avoid drawing continuous lines across unobserved hours.
        rows = rows.set_index("pickup_hour").reindex(range(24))
        ax.plot(rows.index, rows[f"Switch_{phase}_pct"], marker=".", ms=3, label=str(value))
    ax.set(xlim=(0, 23), ylim=(0, 100), xlabel="Pickup hour (local NYC time)",
           ylabel="Expected switching to UAM (%)")
    ax.set_xticks([0, 6, 12, 18, 23])
    ax.grid(alpha=.2)


def save(fig, path):
    fig.savefig(path.with_suffix(".png"), dpi=180, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def generate_figures(results, output, mode):
    output.mkdir(parents=True, exist_ok=True)
    airports = list(results)
    note = "Airport-specific costs" if mode == "corrected" else "Archived CSV costs (EWR uses LGA distances)"
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    for name, table_name, label in [
        ("fig4_top10_zone_gct", "zone_gct", "PULocationID"),
        ("fig6_borough_gct", "borough_gct", "borough"),
    ]:
        fig, axes = plt.subplots(1, len(airports), figsize=(6 * len(airports), 4.8), squeeze=False)
        for ax, airport in zip(axes[0], airports):
            table = results[airport][table_name]
            bars(ax, table.head(10) if label == "PULocationID" else table, label)
            ax.set_title(f"Trips to {airport}")
        axes[0, 0].legend(fontsize=8)
        fig.suptitle(note)
        fig.tight_layout()
        save(fig, output / name)
    fig, axes = plt.subplots(len(airports), 3, figsize=(15, 3.8 * len(airports)), squeeze=False)
    for row, airport in enumerate(airports):
        top = results[airport]["zone_gct"].head(3)["PULocationID"].tolist()
        for col, phase in enumerate(PHASES):
            ax = axes[row, col]
            switch_lines(ax, results[airport]["hourly_zone_switching"], "PULocationID", top, phase)
            ax.set_title(f"{airport} — {phase}")
            ax.legend(title="Pickup zone", fontsize=8)
    fig.suptitle(f"Top three pickup zones — {note}")
    fig.tight_layout()
    save(fig, output / "fig5_hourly_top3_switching")
    # Paper Figure 7 focuses on these three boroughs. A five-borough extension is also saved.
    for boroughs, filename in [
        (["Manhattan", "Brooklyn", "Queens"], "fig7_hourly_borough_switching"),
        (BOROUGHS, "hourly_all5_borough_switching"),
    ]:
        fig, axes = plt.subplots(len(airports), len(boroughs),
                                 figsize=(4.5 * len(boroughs), 3.8 * len(airports)), squeeze=False)
        for row, airport in enumerate(airports):
            table = results[airport]["hourly_borough_switching"]
            for col, borough in enumerate(boroughs):
                ax = axes[row, col]
                rows = table.loc[table["borough"].eq(borough)].set_index("pickup_hour").reindex(range(24))
                for i, phase in enumerate(PHASES):
                    ax.plot(rows.index, rows[f"Switch_{phase}_pct"], color=COLORS[i + 1], label=phase)
                ax.set(title=f"{airport} — {borough}", ylim=(0, 100), xlim=(0, 23),
                       xlabel="Pickup hour (local NYC time)", ylabel="Expected switching to UAM (%)")
                ax.set_xticks([0, 6, 12, 18, 23])
                ax.grid(alpha=.2)
                if rows["total_trips"].isna().all():
                    ax.text(.5, .5, "No data", transform=ax.transAxes, ha="center")
                ax.legend(fontsize=8)
        fig.suptitle(note)
        fig.tight_layout()
        save(fig, output / filename)
