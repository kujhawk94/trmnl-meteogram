#!/usr/bin/env python 

import argparse
import configparser
import math
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import pandas as pd
import requests
import sys
import zoneinfo

from datetime import datetime
from datetime import timedelta
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import FancyBboxPatch

# E-ink friendly settings
plt.style.use("grayscale")
plt.rcParams["font.size"] = 24
plt.rcParams["axes.titlesize"] = 24
plt.rcParams["axes.labelsize"] = 24
plt.rcParams["xtick.labelsize"] = 24
plt.rcParams["ytick.labelsize"] = 24

# Parse command-line argument for config file
parser = argparse.ArgumentParser(description="Generate weather forecast graph.")
parser.add_argument("--config", required=True, help="Path to .ini config file")
args = parser.parse_args()

if not os.path.isfile(args.config):
    sys.stderr.write(f"Error: Config file not found: {args.config}\n")
    sys.exit(1)

config = configparser.ConfigParser()
config.read(args.config)

LAT = float(config.get("location", "latitude", fallback="40.5804"))
LON = float(config.get("location", "longitude", fallback="-105.072"))
LOCALTZ  = zoneinfo.ZoneInfo(config.get( "output", "timezone", fallback="America/Denver"))
OUTPUT_PATH = config.get("output", "filepath", fallback="trmnl_meteogram.png")

HOURS_AHEAD = 48  # Can be adjusted to 12, 24, 48, etc.

def one_letter_day_formatter_with_skip(x, pos):
    # if pos == 0:
    #     return ""  # Skip first label
    dt = mdates.num2date(x, tz=LOCALTZ)
    day = dt.strftime('%a')
    one_letter = "R" if day == "Thu" else day[0]
    hour = dt.strftime('%I').lstrip('0')  # Remove leading 0 from hour
    ampm = dt.strftime('%p').rstrip('M')
    if hour == '12' and ampm == 'A':
        return f"{one_letter}"
    elif hour == '12' and ampm == 'P':
        return "12"
    return ""

def get_forecast_url(lat, lon):
    url = f"https://api.weather.gov/points/{lat},{lon}"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()["properties"]["forecastHourly"]

def fetch_hourly_forecast(forecast_url):
    r = requests.get(forecast_url)
    r.raise_for_status()
    data = r.json()["properties"]["periods"]
    df = pd.DataFrame(data)
    df["startTime"] = pd.to_datetime(df["startTime"])

    # Truncate to only the next HOURS_AHEAD
    now = pd.Timestamp.now(tz="UTC")
    df = df[df["startTime"] <= now + timedelta(hours=HOURS_AHEAD)]
    return df

def plot_forecast(df):
    fig, ax1 = plt.subplots(figsize=(7.6, 4.56), dpi=100)
    ax2 = ax1.twinx()

    # Plot temperature
    ax1.plot(
        df["startTime"], 
        df["temperature"], 
        label="Temp (°F)", 
        color="black", 
        linewidth=6
    )

    # 1) Compute raw min/max
    tmin, tmax = df["temperature"].min(), df["temperature"].max()
    
    # 2) Round bounds out to multiples of 5 °F
    ylim_min = math.floor(tmin / 5) * 5
    ylim_max = math.ceil(tmax  / 5) * 5
    ax1.set_ylim(ylim_min, ylim_max)
    
    # 3) Major ticks at every 10 °F (these get labels)
    maj_start = math.ceil(ylim_min / 10) * 10
    maj_end   = math.floor(ylim_max / 10) * 10
    maj_ticks = list(range(maj_start, maj_end + 1, 10))
    ax1.set_yticks(maj_ticks)
    
    # 4) Minor ticks at every 5 °F (grid lines only)
    min_ticks = list(range(ylim_min, ylim_max + 1, 5))
    ax1.set_yticks(min_ticks, minor=True)
    
    # 5) Draw grid: light dashed at 5°, solid at 10°
    ax1.grid(which='minor', linestyle='--', linewidth=0.5, alpha=0.5)
    ax1.grid(which='major', linestyle='-',  linewidth=0.8)

    # Plot wind speed
    # Extract sustained wind speeds
    wind_speeds = df["windSpeed"].str.extract(r"(\d+)").astype(float)
    ax2.plot(df["startTime"], wind_speeds[0], label="Wind (mph)", color="black", linestyle='--', linewidth=4)
    max_w = wind_speeds[0].max()
    if max_w <= 40:
        y2lim_max = 40
    else:
        y2lim_max = math.ceil(max_w / 5.0) * 5
    ax2.set_ylim(0, y2lim_max)
    ticks = [i for i in range (10, int(y2lim_max)+1, 10) if i < max_w + 10]
    ax2.set_yticks(ticks)
    ax2.set_yticklabels([str(i) for i in ticks], fontweight='bold')

    # Add wind direction labels at the top of the graph every N hours
    compass_labels = df["windDirection"]
    times = df["startTime"]

    label_spacing = 3  # every 3 hours
    selected = df.iloc[::label_spacing]

    direction_to_arrow = {
        "N": "↓", "NNE": "↙", "NE": "↙", "ENE": "↙",
        "E": "←", "ESE": "↖", "SE": "↖", "SSE": "↖",
        "S": "↑", "SSW": "↗", "SW": "↗", "WSW": "↗",
        "W": "→", "WNW": "↘", "NW": "↘", "NNW": "↘",
        "VRB": "◦", "CALM": "·"
    }

    for i, row in selected.iterrows():
        time = row["startTime"]
        direction = row["windDirection"]
        if pd.notnull(direction):
            arrow = direction_to_arrow.get(direction.upper(), "?")
            x_frac = mdates.date2num(row["startTime"])
            x_pixel = ax1.transData.transform((x_frac, 0))[0]
            x_fig = fig.transFigure.inverted().transform((x_pixel, 0))[0]

            # Place label in figure coordinates
            fig.text(
                x_fig,
                0.92,  # height in figure coordinates (near top)
                arrow,
                ha="center",
                va="bottom",
                fontsize=24,
                fontweight="bold"
            )


    # Plot precipitation probability
    if "probabilityOfPrecipitation" in df.columns:
        pop = (
            df["probabilityOfPrecipitation"]
            .apply(lambda x: x.get("value") if isinstance(x, dict) else 0)
            .fillna(0) / 100.0
        )
        total_height = ylim_max - ylim_min
        bar_heights = total_height * pop
        ax1.bar(
            df["startTime"], 
            bar_heights, 
            bottom=ylim_min,
            width=0.03,
            label="Precip %", 
            color="black", 
            alpha=0.2
        )
    # Plot nighttime with bar at bottom of chart
    if "isDaytime" in df.columns:
        daytime = df["isDaytime"].apply(lambda x: 0.015 if not x else 0.00).fillna(0.00)
        total_height = ylim_max - ylim_min
        bar_heights = total_height * daytime
        ax1.bar( df["startTime"], bar_heights, bottom=ylim_min, width=0.05, color="black")

    # Formatting
    ax1.xaxis.set_major_formatter( FuncFormatter(one_letter_day_formatter_with_skip))
    ax1.xaxis.set_major_locator(mdates.HourLocator(byhour=[0,6,12,18]))
    plt.setp(
        ax1.get_xticklabels(),
        rotation=0,
        ha='center',
        fontweight="bold"
    )
    plt.setp(ax1.get_yticklabels(), rotation=0, ha='right', fontweight="bold")
    plt.setp(ax2.get_yticklabels(), rotation=0, ha='left', fontweight="bold")
    ax1.grid(True, linestyle='--', linewidth=0.5)

    # customize these four margins in figure‐fraction units:
    pad_left   = 0.00
    pad_right  = 0.00
    pad_bottom = 0.07   # more room below
    pad_top    = -0.01   # tighter at the top
    
    # corner rounding radius (also in fig‐fraction units)
    rounding_size = 0.03
    
    # compute the width/height of the inner rectangle
    fig_width  = 1 - pad_left - pad_right
    fig_height = 1 - pad_bottom - pad_top
    
    rect = FancyBboxPatch(
        (pad_left, pad_bottom),        # (x0, y0) in fig‐fraction coords
        fig_width,                     # total width
        fig_height,                    # total height
        boxstyle=f"round,pad=0,rounding_size={rounding_size}",
        linewidth=1,
        linestyle="--",
        edgecolor="black",
        facecolor="none",
        transform=fig.transFigure,
        clip_on=False
    )
    fig.patches.append(rect)

    fig.tight_layout()
    plt.savefig(OUTPUT_PATH, dpi=100, bbox_inches="tight")

if __name__ == "__main__":
    forecast_url = get_forecast_url(LAT, LON)
    df = fetch_hourly_forecast(forecast_url)
    plot_forecast(df)
