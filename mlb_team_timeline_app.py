import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from rapidfuzz import process, fuzz

# Load datasets
@st.cache_data
def load_data():
    people = pd.read_csv("data/People.csv")
    batting = pd.read_csv("data/Batting.csv")
    teams = pd.read_csv("data/Teams.csv")
    return people, batting, teams

people, batting, teams = load_data()

# Team color mapping (franchise ID → HEX)
TEAM_COLORS = {
    "ARI": "#A71930", "ATL": "#CE1141", "BAL": "#DF4601", "BOS": "#BD3039",
    "CHC": "#0E3386", "CHW": "#27251F", "CIN": "#C6011F", "CLE": "#0C2340",
    "COL": "#33006F", "DET": "#0C2340", "HOU": "#EB6E1F", "KCR": "#004687",
    "LAA": "#BA0021", "LAD": "#005A9C", "MIA": "#00A3E0", "MIL": "#12284B",
    "MIN": "#002B5C", "NYM": "#002D72", "NYY": "#003087", "OAK": "#003831",
    "PHI": "#E81828", "PIT": "#FDB827", "SDP": "#2F241D", "SEA": "#0C2C56",
    "SFG": "#FD5A1E", "STL": "#C41E3A", "TBR": "#092C5C", "TEX": "#003278",
    "TOR": "#134A8E", "WSN": "#AB0003"
}

# Official team names → franchise code
OFFICIAL_TEAM_NAMES = {
    "Arizona Diamondbacks": "ARI",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KCR",
    "Los Angeles Angels": "ANA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "FLA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Oakland Athletics": "OAK",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SDP",
    "Seattle Mariners": "SEA",
    "San Francisco Giants": "SFG",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TBR",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSN"
}

# Franchise code → full team name
TEAM_NAMES = {v: k for k, v in OFFICIAL_TEAM_NAMES.items()}

def get_player_team_blocks(player_first, player_last, people_df, batting_df, teams_df):
    people_df.columns = people_df.columns.str.lower()
    batting_df.columns = batting_df.columns.str.lower()
    teams_df.columns = teams_df.columns.str.lower()

    player = people_df[
        (people_df['namefirst'] == player_first) & (people_df['namelast'] == player_last)
    ]
    if player.empty:
        return []

    player_id = player['playerid'].values[0]
    player_batting = batting_df[batting_df['playerid'] == player_id]

    merged = player_batting.merge(
        teams_df[['teamid', 'yearid', 'franchid']],
        on=['teamid', 'yearid'],
        how='left'
    ).sort_values('yearid')

    blocks = []
    last_team = None
    start_year = None

    for _, row in merged.iterrows():
        year, team = row['yearid'], row['franchid']
        if team != last_team:
            if last_team is not None:
                blocks.append((start_year, year - 1, last_team))
            last_team = team
            start_year = year

    if last_team is not None:
        blocks.append((start_year, year, last_team))

    return blocks

def get_franchise_code_from_input(user_input):
    match = process.extractOne(user_input, OFFICIAL_TEAM_NAMES.keys(), scorer=fuzz.WRatio)
    if match and match[1] >= 70:
        return OFFICIAL_TEAM_NAMES[match[0]], match[0]
    else:
        return None, None

def plot_multiple_timelines_plotly(player_list, people, batting, teams):
    fig = go.Figure()
    seen_legends = set()

    for first, last in player_list:
        blocks = get_player_team_blocks(first, last, people, batting, teams)
        player_name = f"{first} {last}"

        for start, end, team in blocks:
            color = TEAM_COLORS.get(team, "#888888")
            team_full_name = TEAM_NAMES.get(team, "Unknown Team")
            legend_label = f"{team} ({team_full_name})"

            fig.add_trace(go.Bar(
                x=[end - start + 1],
                y=[player_name],
                base=start,
                orientation='h',
                name=legend_label,
                marker=dict(color=color),
                text=team,
                textposition='inside',
                insidetextanchor='middle',
                hovertemplate=f"<b>{player_name}</b><br>Team: {team_full_name}<br>Years: {start}-{end}<extra></extra>",
                showlegend=(legend_label not in seen_legends)
            ))
            seen_legends.add(legend_label)

    fig.update_layout(
        barmode='stack',
        title="MLB Player Team Timelines",
        xaxis_title="Year",
        yaxis=dict(autorange="reversed"),
        height=max(800, len(player_list) * 40),
        legend_title="Team",
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    st.plotly_chart(fig, use_container_width=True)

def main():
    st.set_page_config(
    page_title="MLB Team Timeline",  # This changes the tab title
    page_icon="⚾️"                     # Optional: changes the favicon
    )
    st.title("MLB Active Players Team Timeline")

    people.columns = people.columns.str.lower()
    batting.columns = batting.columns.str.lower()
    teams.columns = teams.columns.str.lower()

    people['finalyear'] = pd.to_datetime(people['finalgame'], errors='coerce').dt.year
    active_players_df = people[people['finalyear'].isna()].copy()

    active_batting = batting[batting['playerid'].isin(active_players_df['playerid'])]

    latest_years = active_batting.groupby('playerid')['yearid'].max().reset_index()
    latest_batting = active_batting.merge(latest_years, on=['playerid', 'yearid'], how='inner')
    latest_batting = latest_batting.merge(
        teams[['teamid', 'yearid', 'franchid']],
        on=['teamid', 'yearid'],
        how='left'
    )

    team_name_input = st.text_input("Enter MLB team name:", value="")

    if team_name_input:
        franchise_code, matched_name = get_franchise_code_from_input(team_name_input)
        if franchise_code is None:
            st.error(f"No close match found for '{team_name_input}'. Try a different name.")
            return
        else:
            st.success(f"Matched team name: {matched_name} → Franchise code: {franchise_code}")

        teams_per_player_year = latest_batting.groupby(['playerid', 'yearid'])['franchid'].unique().reset_index()
        only_team_players = teams_per_player_year[
            teams_per_player_year['franchid'].apply(lambda teams: len(teams) == 1 and teams[0] == franchise_code)
        ]['playerid'].values

        team_player_names = people[
            people['playerid'].isin(only_team_players)
        ][['namefirst', 'namelast']].dropna().values.tolist()

        if len(team_player_names) == 0:
            st.warning(f"No active players found who only played for {matched_name} in their latest year.")
        else:
            plot_multiple_timelines_plotly(team_player_names, people, batting, teams)

if __name__ == "__main__":
    main()
