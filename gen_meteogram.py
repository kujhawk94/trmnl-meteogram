import argparse
import configparser
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import pandas as pd
import requests
import sys

from datetime import datetime
from datetime import timedelta
from matplotlib.ticker import FuncFormatter

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
OUTPUT_PATH = config.get(
    "output", "filepath", fallback="/var/www/html/trmnl_meteogram.png"
)

HOURS_AHEAD = 48  # Can be adjusted to 12, 24, 48, etc.

def one_letter_day_formatter_with_skip(x, pos):
    # if pos == 0:
    #     return ""  # Skip first label
    dt = mdates.num2date(x)
    day = dt.strftime('%a')
    one_letter = "R" if day == "Thu" else day[0]
    hour = dt.strftime('%I').lstrip('0')  # Remove leading 0 from hour
    ampm = dt.strftime('%p').rstrip('M')
    return f"{one_letter} {hour}{ampm}"
    
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
    fig, ax1 = plt.subplots(figsize=(8, 4.8), dpi=100)
    ax2 = ax1.twinx()

    # Plot temperature
    ax1.plot(
        df["startTime"], 
        df["temperature"], 
        label="Temp (°F)", 
        color="black", 
        linewidth=6
    )
    # ax1.set_ylabel("Temperature (°F)", color="black")
    ax1.tick_params(axis='y', labelcolor="black")

    # Plot wind speed
    # Extract sustained wind speeds
    wind_speeds = df["windSpeed"].str.extract(r"(\d+)").astype(float)
    ax2.plot(df["startTime"], wind_speeds[0], label="Wind (mph)", color="black", linestyle='--', linewidth=4)
    
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
        pop = df["probabilityOfPrecipitation"].apply(lambda x: x.get("value") if isinstance(x, dict) else None)
        ax1.bar(df["startTime"], pop, width=0.03, label="Precip %", color="black", alpha=0.3)

    # Formatting
    ax1.xaxis.set_major_formatter(
        FuncFormatter(one_letter_day_formatter_with_skip)
    )
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    plt.setp(
        ax1.get_xticklabels(),
        rotation=0,
        ha='center',
        fontweight="bold"
    )
    plt.setp(ax1.get_yticklabels(), rotation=0, ha='right', fontweight="bold")
    plt.setp(ax2.get_yticklabels(), rotation=0, ha='left', fontweight="bold")
    ax1.grid(True, linestyle='--', linewidth=0.5)
    
    fig.tight_layout()
    plt.savefig("hourly_forecast_eink.png", dpi=100, bbox_inches="tight")

if __name__ == "__main__":
    forecast_url = get_forecast_url(LAT, LON)
    df = fetch_hourly_forecast(forecast_url)
    plot_forecast(df)