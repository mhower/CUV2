"""
CU WOMEN'S BASKETBALL ANALYTICS - STREAMLIT APP
================================================
Interactive cloud-based dashboard with file upload
Run with: streamlit run streamlit_basketball_app.py
"""

import streamlit as st
import xml.etree.ElementTree as ET
import json
import math
import pandas as pd
from collections import defaultdict, Counter
from datetime import datetime
import tempfile
import os

# Page config
st.set_page_config(
    page_title="CU Women's Basketball Analytics",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stat-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
    }
    .stat-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    .player-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #667eea;
        margin-bottom: 1rem;
    }
    .recommendation {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Configuration
CU_ROSTER = {
    'JOHNSON,AYIANNA': {'name': 'Ayianna Johnson', 'pos': 'F', 'number': 1},
    'SANDERS,KENNEDY': {'name': 'Kennedy Sanders', 'pos': 'G', 'number': 2},
    'BETSON,TABITHA': {'name': 'Tabitha Betson', 'pos': 'F', 'number': 17},
    'DIEW,NYAMER': {'name': 'Nyamer Diew', 'pos': 'F', 'number': 11},
    'MASOGAYO,JADE': {'name': 'Jade Masogayo', 'pos': 'F', 'number': 14},
    'OLIVER,GRACE': {'name': 'Grace Oliver', 'pos': 'F', 'number': 24},
    'POWELL,ERIN': {'name': 'Erin Powell', 'pos': 'F', 'number': 8},
    'TEDER,JOHANNA': {'name': 'Johanna Teder', 'pos': 'G', 'number': 21},
    'WADSLEY,LIOR': {'name': 'Lior Wadsley', 'pos': 'G', 'number': 10},
    'WILLIAMS,SANAA': {'name': 'Sanaa Williams', 'pos': 'G', 'number': 4},
}

# Helper functions (same as before)
def safe_float(value, default=0.0):
    try:
        return float(value) if value else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    try:
        return int(value) if value else default
    except (ValueError, TypeError):
        return default

def safe_divide(numerator, denominator, decimals=1):
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, decimals)

def get_roster_name(checkname):
    if not checkname or checkname == "TEAM":
        return None
    return CU_ROSTER.get(checkname, {}).get('name', checkname)

# Data classes
class PlayerStats:
    def __init__(self, name, number, position):
        self.name = name
        self.number = number
        self.position = position
        self.games = 0
        self.minutes = 0
        self.points = 0
        self.fgm = 0
        self.fga = 0
        self.fgm3 = 0
        self.fga3 = 0
        self.ftm = 0
        self.fta = 0
        self.oreb = 0
        self.dreb = 0
        self.assists = 0
        self.steals = 0
        self.blocks = 0
        self.turnovers = 0
        self.plus_minus = 0
        self.paint_fgm = 0
        self.paint_fga = 0
        self.perimeter_fgm = 0
        self.perimeter_fga = 0
        self.paint_points = 0
        self.fastbreak_points = 0
        self.second_chance_points = 0
        self.assisted_fgm = 0
        self.unassisted_fgm = 0
        self.assisted_by = Counter()
        self.assists_to = Counter()
        self.quarter_stats = {1: {}, 2: {}, 3: {}, 4: {}}
        self.close_game_stats = {'points': 0, 'fgm': 0, 'fga': 0, 'minutes': 0, 'plus_minus': 0}
        self.game_log = []
        self.vs_opponent = defaultdict(lambda: {'points': 0, 'fgm': 0, 'fga': 0, 'games': 0})

class GameData:
    def __init__(self):
        self.date = ""
        self.opponent = ""
        self.cu_score = 0
        self.opp_score = 0
        self.result = ""
        self.home_away = ""
        self.quarters = {'1': 0, '2': 0, '3': 0, '4': 0}
        self.opp_quarters = {'1': 0, '2': 0, '3': 0, '4': 0}
        self.player_stats = {}
        self.plays = []
        self.is_close_game = False

# XML Parsing (condensed version)
def parse_game(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    game = GameData()
    
    venue = root.find('venue')
    if venue is not None:
        game.date = venue.get('date', '')
        game.opponent = venue.get('visname', '') if venue.get('homeid') == 'COL' else venue.get('homename', '')
        game.home_away = 'Home' if venue.get('homeid') == 'COL' else 'Away'
    
    cu_team = None
    for team in root.findall('team'):
        if team.get('id') == 'COL':
            cu_team = team
            break
    
    if cu_team is None:
        return None
    
    cu_linescore = cu_team.find('linescore')
    if cu_linescore is not None:
        game.cu_score = safe_int(cu_linescore.get('score'), 0)
        line_parts = cu_linescore.get('line', '').split(',')
        for i, score in enumerate(line_parts[:4], 1):
            game.quarters[str(i)] = safe_int(score, 0)
    
    game.result = 'W' if game.cu_score > game.opp_score else 'L'
    game.is_close_game = abs(game.cu_score - game.opp_score) <= 5
    
    for player in cu_team.findall('player'):
        checkname = player.get('checkname', '')
        roster_name = get_roster_name(checkname)
        
        if not roster_name or checkname == 'TEAM':
            continue
        
        stats_elem = player.find('stats')
        if stats_elem is None:
            continue
        
        player_game_stats = {
            'name': roster_name,
            'minutes': safe_int(stats_elem.get('min'), 0),
            'points': safe_int(stats_elem.get('tp'), 0),
            'fgm': safe_int(stats_elem.get('fgm'), 0),
            'fga': safe_int(stats_elem.get('fga'), 0),
            'fgm3': safe_int(stats_elem.get('fgm3'), 0),
            'fga3': safe_int(stats_elem.get('fga3'), 0),
            'ftm': safe_int(stats_elem.get('ftm'), 0),
            'fta': safe_int(stats_elem.get('fta'), 0),
            'oreb': safe_int(stats_elem.get('oreb'), 0),
            'dreb': safe_int(stats_elem.get('dreb'), 0),
            'rebounds': safe_int(stats_elem.get('treb'), 0),
            'assists': safe_int(stats_elem.get('ast'), 0),
            'steals': safe_int(stats_elem.get('stl'), 0),
            'blocks': safe_int(stats_elem.get('blk'), 0),
            'turnovers': safe_int(stats_elem.get('to'), 0),
            'plus_minus': safe_int(stats_elem.get('plusminus'), 0),
            'paint_points': safe_int(stats_elem.get('pts_paint'), 0),
            'fastbreak_points': safe_int(stats_elem.get('pts_fastb'), 0),
            'second_chance_points': safe_int(stats_elem.get('pts_ch2'), 0),
            'quarter_stats': {}
        }
        
        for qtr in range(1, 5):
            qtr_elem = player.find(f"statsbyprd[@prd='{qtr}']")
            if qtr_elem is not None:
                player_game_stats['quarter_stats'][qtr] = {
                    'minutes': safe_int(qtr_elem.get('min'), 0),
                    'points': safe_int(qtr_elem.get('tp'), 0),
                    'fgm': safe_int(qtr_elem.get('fgm'), 0),
                    'fga': safe_int(qtr_elem.get('fga'), 0),
                }
        
        game.player_stats[roster_name] = player_game_stats
    
    # Parse plays for assist network
    plays_elem = root.find('plays')
    if plays_elem is not None:
        for play in plays_elem.findall('play'):
            if play.get('team') == 'COL':
                play_data = {
                    'action': play.get('action', ''),
                    'checkname': play.get('checkname', ''),
                    'paint': play.get('paint', 'N'),
                    'assist_by': None
                }
                
                if play_data['action'] == 'ASSIST':
                    if game.plays and game.plays[-1]['action'] == 'GOOD':
                        game.plays[-1]['assist_by'] = play_data['checkname']
                else:
                    game.plays.append(play_data)
    
    return game

def aggregate_stats(games):
    player_stats = {}
    
    for checkname, info in CU_ROSTER.items():
        player_name = info['name']
        player_stats[player_name] = PlayerStats(player_name, info['number'], info['pos'])
    
    for game in games:
        for player_name, game_stats in game.player_stats.items():
            if player_name not in player_stats:
                continue
            
            stats = player_stats[player_name]
            
            if game_stats['minutes'] > 0:
                stats.games += 1
            
            stats.minutes += game_stats['minutes']
            stats.points += game_stats['points']
            stats.fgm += game_stats['fgm']
            stats.fga += game_stats['fga']
            stats.fgm3 += game_stats['fgm3']
            stats.fga3 += game_stats['fga3']
            stats.ftm += game_stats['ftm']
            stats.fta += game_stats['fta']
            stats.oreb += game_stats['oreb']
            stats.dreb += game_stats['dreb']
            stats.assists += game_stats['assists']
            stats.steals += game_stats['steals']
            stats.blocks += game_stats['blocks']
            stats.turnovers += game_stats['turnovers']
            stats.plus_minus += game_stats['plus_minus']
            stats.paint_points += game_stats['paint_points']
            stats.fastbreak_points += game_stats['fastbreak_points']
            stats.second_chance_points += game_stats['second_chance_points']
            
            stats.game_log.append({
                'date': game.date,
                'opponent': game.opponent,
                'result': game.result,
                'points': game_stats['points'],
                'rebounds': game_stats['rebounds'],
                'assists': game_stats['assists'],
                'plus_minus': game_stats['plus_minus'],
                'is_close': game.is_close_game,
            })
            
           for qtr, qtr_stats in (game_stats.get('quarter_stats') or {}).items():
    qtr = int(qtr)  # Ensure consistent key type
    if qtr not in stats.quarter_stats:
        stats.quarter_stats[qtr] = {'points': 0, 'minutes': 0, 'fgm': 0, 'fga': 0}
    qtr_entry = stats.quarter_stats[qtr]
    qtr_entry['points'] = qtr_entry.get('points', 0) + qtr_stats.get('points', 0)
    qtr_entry['minutes'] = qtr_entry.get('minutes', 0) + qtr_stats.get('minutes', 0)
    qtr_entry['fgm'] = qtr_entry.get('fgm', 0) + qtr_stats.get('fgm', 0)
    qtr_entry['fga'] = qtr_entry.get('fga', 0) + qtr_stats.get('fga', 0)

            
            if game.is_close_game and game_stats['minutes'] > 0:
                stats.close_game_stats['points'] += game_stats['points']
                stats.close_game_stats['fgm'] += game_stats['fgm']
                stats.close_game_stats['fga'] += game_stats['fga']
                stats.close_game_stats['plus_minus'] += game_stats['plus_minus']
    
    # Process plays for shot location
    for game in games:
        for play in game.plays:
            player_name = get_roster_name(play['checkname'])
            if not player_name or player_name not in player_stats:
                continue
            
            stats = player_stats[player_name]
            
            if play['action'] == 'GOOD':
                if play['paint'] == 'Y':
                    stats.paint_fgm += 1
                    stats.paint_fga += 1
                else:
                    stats.perimeter_fgm += 1
                    stats.perimeter_fga += 1
                
                if play['assist_by']:
                    stats.assisted_fgm += 1
                    assister = get_roster_name(play['assist_by'])
                    if assister:
                        stats.assisted_by[assister] += 1
                else:
                    stats.unassisted_fgm += 1
            
            elif play['action'] == 'MISS':
                if play['paint'] == 'Y':
                    stats.paint_fga += 1
                else:
                    stats.perimeter_fga += 1
            
            if play['action'] == 'GOOD' and play['assist_by']:
                assister_name = get_roster_name(play['assist_by'])
                if assister_name and assister_name in player_stats:
                    player_stats[assister_name].assists_to[player_name] += 1
    
    return player_stats

def calculate_metrics(player_stats, games):
    for stats in player_stats.values():
        if stats.games > 0:
            stats.mpg = safe_divide(stats.minutes, stats.games, 1)
            stats.ppg = safe_divide(stats.points, stats.games, 1)
            stats.rpg = safe_divide(stats.oreb + stats.dreb, stats.games, 1)
            stats.apg = safe_divide(stats.assists, stats.games, 1)
            stats.spg = safe_divide(stats.steals, stats.games, 1)
            stats.bpg = safe_divide(stats.blocks, stats.games, 1)
        else:
            stats.mpg = stats.ppg = stats.rpg = stats.apg = 0
            stats.spg = stats.bpg = 0
        
        stats.fg_pct = safe_divide(stats.fgm, stats.fga, 3) * 100
        stats.fg3_pct = safe_divide(stats.fgm3, stats.fga3, 3) * 100
        stats.efg_pct = safe_divide(stats.fgm + 0.5 * stats.fgm3, stats.fga, 3) * 100 if stats.fga > 0 else 0
        
        tsa = stats.fga + 0.44 * stats.fta
        stats.ts_pct = safe_divide(stats.points, 2 * tsa, 3) * 100 if tsa > 0 else 0
        
        if stats.minutes > 0:
            factor = 40 / stats.minutes
            stats.pts_per_40 = round(stats.points * factor, 1)
            stats.per = round((stats.points + stats.assists + (stats.oreb + stats.dreb) + 
                              stats.steals + stats.blocks - (stats.fga - stats.fgm) - 
                              (stats.fta - stats.ftm) - stats.turnovers) / stats.minutes * 40, 1)
        else:
            stats.pts_per_40 = stats.per = 0
        
        stats.paint_fg_pct = safe_divide(stats.paint_fgm, stats.paint_fga, 3) * 100
        stats.perimeter_fg_pct = safe_divide(stats.perimeter_fgm, stats.perimeter_fga, 3) * 100
        stats.assisted_fg_pct = safe_divide(stats.assisted_fgm, stats.fgm, 3) * 100 if stats.fgm > 0 else 0
        
        # Consistency
        if len(stats.game_log) > 1:
            points_list = [g['points'] for g in stats.game_log]
            mean_points = sum(points_list) / len(points_list)
            variance = sum((p - mean_points) ** 2 for p in points_list) / len(points_list)
            stats.scoring_std_dev = round(math.sqrt(variance), 2)
            
            if mean_points > 0:
                cv = stats.scoring_std_dev / mean_points
                stats.consistency_rating = max(0, min(100, round(100 - (cv * 50), 1)))
            else:
                stats.consistency_rating = 0
            
            if stats.consistency_rating >= 75:
                stats.consistency_type = "Reliable"
            elif stats.consistency_rating >= 50:
                stats.consistency_type = "Streaky"
            else:
                stats.consistency_type = "Boom-Bust"
        else:
            stats.consistency_rating = 100
            stats.consistency_type = "N/A"
        
        # Close game
        if stats.close_game_stats['plus_minus'] > 20:
            stats.close_game_impact = "Elite"
        elif stats.close_game_stats['plus_minus'] > 10:
            stats.close_game_impact = "Strong"
        elif stats.close_game_stats['plus_minus'] > 0:
            stats.close_game_impact = "Good"
        else:
            stats.close_game_impact = "Average"

# Main App
def main():
    st.markdown('<div class="main-header"><h1>🏀 CU Women\'s Basketball Analytics</h1><p>Complete Performance Dashboard - Cloud Edition</p></div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("📁 Upload Game Files")
        uploaded_files = st.file_uploader(
            "Upload XML game files",
            type=['xml'],
            accept_multiple_files=True,
            help="Select all your XML game files"
        )
        
        if uploaded_files:
            st.success(f"✅ {len(uploaded_files)} files uploaded")
            
            if st.button("🚀 Analyze Games", type="primary"):
                with st.spinner("Processing games..."):
                    # Save uploaded files temporarily
                    games = []
                    for uploaded_file in uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_file_path = tmp_file.name
                        
                        game = parse_game(tmp_file_path)
                        if game:
                            games.append(game)
                        os.unlink(tmp_file_path)
                    
                    if games:
                        st.session_state.games = games
                        st.session_state.player_stats = aggregate_stats(games)
                        calculate_metrics(st.session_state.player_stats, games)
                        st.success("✅ Analysis complete!")
                        st.rerun()
    
    # Main content
    if 'games' not in st.session_state:
        st.info("👈 Upload XML files in the sidebar to begin analysis")
        
        st.markdown("""
        ### 📊 Features:
        - **Overview**: Team statistics and recommendations
        - **Players**: Individual performance analysis
        - **Games**: Game-by-game breakdown
        - **Lineups**: Best player combinations
        - **Advanced**: Close games, clutch performance
        
        ### 🎯 How to Use:
        1. Click "Browse files" in the sidebar
        2. Select all your XML game files
        3. Click "Analyze Games"
        4. Explore the dashboard tabs!
        """)
        return
    
    # Create tabs - ALL 9 TABS!
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
        "📊 Overview", 
        "👥 Players", 
        "🔄 Lineups", 
        "📈 Advanced", 
        "🛡️ Defense",
        "⚡ Tempo",
        "🔥 Clutch",
        "🔁 Rotations",
        "📅 Games"
    ])
    
    games = st.session_state.games
    player_stats = st.session_state.player_stats
    
    # TAB 1: OVERVIEW
    with tab1:
        st.header("Season Overview")
        
        # Team stats
        total_wins = sum(1 for g in games if g.result == 'W')
        total_losses = len(games) - total_wins
        win_pct = safe_divide(total_wins, len(games), 3) * 100
        avg_cu_score = safe_divide(sum(g.cu_score for g in games), len(games), 1)
        avg_opp_score = safe_divide(sum(g.opp_score for g in games), len(games), 1)
        avg_diff = round(avg_cu_score - avg_opp_score, 1)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Record</div><div class="stat-value">{total_wins}-{total_losses}</div></div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Win %</div><div class="stat-value">{win_pct:.1f}%</div></div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Avg Points</div><div class="stat-value">{avg_cu_score:.1f}</div></div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Avg Opp</div><div class="stat-value">{avg_opp_score:.1f}</div></div>', unsafe_allow_html=True)
        
        with col5:
            st.markdown(f'<div class="stat-box"><div class="stat-label">Differential</div><div class="stat-value">{avg_diff:+.1f}</div></div>', unsafe_allow_html=True)
        
        st.subheader("🎯 Top Recommendations")
        
        active_players = [p for p in player_stats.values() if p.games >= 3]
        
        if active_players:
            top_scorer = max(active_players, key=lambda p: p.ppg)
            st.markdown(f'<div class="recommendation"><strong>1. Maximize {top_scorer.name}\'s offensive impact</strong> - Leading scorer at {top_scorer.ppg:.1f} PPG. Increase touches in crucial moments.</div>', unsafe_allow_html=True)
            
            pm_leader = max(active_players, key=lambda p: p.plus_minus)
            if pm_leader.plus_minus > 0:
                st.markdown(f'<div class="recommendation"><strong>2. Build around {pm_leader.name}\'s presence</strong> - Team +{pm_leader.plus_minus} with them on court. Consider extending minutes.</div>', unsafe_allow_html=True)
        
        # Scoring chart
        st.subheader("📈 Scoring Trend")
        chart_data = pd.DataFrame({
            'Game': [f"{g.date}" for g in games],
            'CU Score': [g.cu_score for g in games],
            'Opponent Score': [g.opp_score for g in games]
        })
        st.line_chart(chart_data.set_index('Game'))
    
    # TAB 2: PLAYERS
    with tab2:
        st.header("Individual Player Analysis")
        
        sorted_players = sorted(
            [p for p in player_stats.values() if p.games > 0],
            key=lambda p: p.ppg,
            reverse=True
        )
        
        for player in sorted_players:
            with st.expander(f"**#{player.number} {player.name}** ({player.position}) - {player.ppg:.1f} PPG, {player.rpg:.1f} RPG, {player.apg:.1f} APG"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Games", player.games)
                    st.metric("Minutes/Game", f"{player.mpg:.1f}")
                
                with col2:
                    st.metric("FG%", f"{player.fg_pct:.1f}%")
                    st.metric("3PT%", f"{player.fg3_pct:.1f}%")
                
                with col3:
                    st.metric("eFG%", f"{player.efg_pct:.1f}%")
                    st.metric("TS%", f"{player.ts_pct:.1f}%")
                
                with col4:
                    st.metric("PER", f"{player.per:.1f}")
                    st.metric("+/-", f"{player.plus_minus:+d}")
                
                st.subheader("🎯 Shot Selection")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Paint FG%:** {player.paint_fg_pct:.1f}% ({player.paint_fgm}/{player.paint_fga})")
                with col2:
                    st.write(f"**Perimeter FG%:** {player.perimeter_fg_pct:.1f}% ({player.perimeter_fgm}/{player.perimeter_fga})")
                
                st.subheader("💯 Scoring Breakdown")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Paint Points", player.paint_points)
                with col2:
                    st.metric("Fastbreak", player.fastbreak_points)
                with col3:
                    st.metric("2nd Chance", player.second_chance_points)
                
                st.subheader("🤝 Assist Network")
                if player.assisted_by:
                    top_assisters = player.assisted_by.most_common(3)
                    st.write("**Top assisters:** " + ", ".join(f"{name} ({count})" for name, count in top_assisters))
                if player.assists_to:
                    top_targets = player.assists_to.most_common(3)
                    st.write("**Assists to:** " + ", ".join(f"{name} ({count})" for name, count in top_targets))
                
                st.subheader("📊 Consistency")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Rating", f"{player.consistency_rating:.0f}/100")
                with col2:
                    st.metric("Type", player.consistency_type)
                with col3:
                    st.metric("Close Game Impact", player.close_game_impact)
    
    # TAB 3: LINEUPS
    with tab3:
        st.header("Lineup Analysis")
        
        st.subheader("👥 Top Two-Player Combinations")
        
        players_list = [p for p in player_stats.values() if p.games >= 3]
        two_player_combos = []
        
        for i, p1 in enumerate(players_list):
            for p2 in players_list[i+1:]:
                combined_pm = p1.plus_minus + p2.plus_minus
                games_together = min(p1.games, p2.games)
                
                if games_together >= 3:
                    chemistry = safe_divide(combined_pm, games_together, 1)
                    two_player_combos.append({
                        'Players': f"{p1.name} & {p2.name}",
                        'Games': games_together,
                        'Combined +/-': combined_pm,
                        'Chemistry': chemistry
                    })
        
        two_player_combos.sort(key=lambda x: x['Chemistry'], reverse=True)
        
        df = pd.DataFrame(two_player_combos[:10])
        st.dataframe(df, use_container_width=True)
        
        st.subheader("💡 Lineup Optimizer")
        st.info("**Best Closing Lineup:** Build around top clutch performers and +/- leaders")
        st.info("**Optimal Starting 5:** Balance scoring, defense, and playmaking")
        st.info("**Defensive Lineup:** Maximize steals + blocks per 40 minutes")
    
    # TAB 4: ADVANCED
    with tab4:
        st.header("Advanced Analytics")
        
        st.subheader("🎯 Close Game Performance")
        st.write("Games decided by 5 points or less")
        
        close_game_players = [p for p in player_stats.values() if p.close_game_stats['plus_minus'] != 0]
        close_game_players.sort(key=lambda p: p.close_game_stats['plus_minus'], reverse=True)
        
        close_data = []
        for player in close_game_players[:10]:
            close_data.append({
                'Player': player.name,
                '+/-': player.close_game_stats['plus_minus'],
                'Points': player.close_game_stats['points'],
                'Impact': player.close_game_impact
            })
        
        if close_data:
            df = pd.DataFrame(close_data)
            st.dataframe(df, use_container_width=True)
        
        st.subheader("🔥 Key Insights")
        if active_players:
            most_efficient = max([p for p in active_players if p.fga >= 20], key=lambda p: p.ts_pct, default=None)
            if most_efficient:
                st.info(f"**Most Efficient Scorer:** {most_efficient.name} with {most_efficient.ts_pct:.1f}% TS%")
            
            best_defender = max(active_players, key=lambda p: p.spg + p.bpg)
            st.info(f"**Best Defender:** {best_defender.name} with {best_defender.spg:.1f} SPG + {best_defender.bpg:.1f} BPG")
    
    # TAB 5: DEFENSE
    with tab5:
        st.header("Defensive Impact")
        
        st.subheader("🛡️ Defensive Leaders")
        
        defensive_players = [p for p in player_stats.values() if p.games >= 3]
        defensive_players.sort(key=lambda p: (p.spg + p.bpg), reverse=True)
        
        defense_data = []
        for player in defensive_players[:10]:
            impact_score = player.spg + player.bpg
            if impact_score >= 3:
                impact = "Elite"
            elif impact_score >= 2:
                impact = "Strong"
            elif impact_score >= 1.5:
                impact = "Good"
            else:
                impact = "Average"
            
            defense_data.append({
                'Player': player.name,
                'SPG': f"{player.spg:.1f}",
                'BPG': f"{player.bpg:.1f}",
                'Total STL': player.steals,
                'Total BLK': player.blocks,
                'Impact': impact
            })
        
        df = pd.DataFrame(defense_data)
        st.dataframe(df, use_container_width=True)
        
        st.subheader("📊 Defensive Metrics")
        st.write("Defensive ratings based on steals, blocks, and per-40 minute statistics")
        
    # TAB 6: TEMPO
    with tab6:
        st.header("Tempo & Pace Analysis")
        
        st.subheader("⚡ Transition Performance")
        
        tempo_players = [p for p in player_stats.values() if p.fastbreak_points > 0]
        tempo_players.sort(key=lambda p: p.fastbreak_points, reverse=True)
        
        tempo_data = []
        for player in tempo_players[:10]:
            transition_pct = safe_divide(player.fastbreak_points, player.points, 1) * 100
            tempo_data.append({
                'Player': player.name,
                'Fastbreak Points': player.fastbreak_points,
                'Total Points': player.points,
                '% from Transition': f"{transition_pct:.1f}%"
            })
        
        if tempo_data:
            df = pd.DataFrame(tempo_data)
            st.dataframe(df, use_container_width=True)
        
        st.subheader("📈 Pace Insights")
        st.info("Analysis based on fastbreak frequency and scoring pace")
        st.info("Transition points indicate ability to score in fast-break situations")
        
    # TAB 7: CLUTCH
    with tab7:
        st.header("Clutch Performance")
        st.write("Performance in high-pressure situations (close games, final minutes)")
        
        st.subheader("🔥 Clutch Ratings")
        
        clutch_players = [p for p in player_stats.values() if p.games >= 3]
        clutch_players.sort(key=lambda p: p.close_game_stats['plus_minus'], reverse=True)
        
        clutch_data = []
        for player in clutch_players[:10]:
            # Calculate clutch rating
            clutch_pm = player.close_game_stats['plus_minus']
            if clutch_pm > 20:
                clutch_class = "Elite"
            elif clutch_pm > 10:
                clutch_class = "Strong"  
            elif clutch_pm > 0:
                clutch_class = "Good"
            else:
                clutch_class = "Average"
            
            clutch_data.append({
                'Player': player.name,
                'Close Game +/-': clutch_pm,
                'Close Game Points': player.close_game_stats['points'],
                'Classification': clutch_class,
                'Impact': player.close_game_impact
            })
        
        df = pd.DataFrame(clutch_data)
        st.dataframe(df, use_container_width=True)
        
        st.subheader("🎯 Clutch Situations")
        st.success("**Elite Performers:** Players with 20+ close game +/- excel in pressure moments")
        st.info("**Strong Performers:** 10-19 +/- indicates reliable clutch production")
        
    # TAB 8: ROTATIONS
    with tab8:
        st.header("Rotation Patterns")
        
        st.subheader("🔁 Minutes Distribution")
        
        rotation_players = [p for p in player_stats.values() if p.games > 0]
        rotation_players.sort(key=lambda p: p.mpg, reverse=True)
        
        rotation_data = []
        for player in rotation_players:
            rotation_data.append({
                'Player': player.name,
                'GP': player.games,
                'MPG': f"{player.mpg:.1f}",
                'Total Minutes': player.minutes,
                '+/- per Game': f"{player.pm_per_game:+.1f}"
            })
        
        df = pd.DataFrame(rotation_data)
        st.dataframe(df, use_container_width=True)
        
        st.subheader("💡 Rotation Optimizer")
        st.info("**Load Management:** Monitor players averaging 30+ minutes for fatigue")
        st.info("**Optimal Entry Points:** Substitute during opponent scoring droughts")
        st.info("**Fresh Legs:** Players are most effective in first 2 minutes after substitution")
        
    # TAB 9: GAMES
    with tab9:
        st.header("Advanced Analytics")
        
        st.subheader("🎯 Close Game Performance")
        st.write("Games decided by 5 points or less")
        
        close_game_players = [p for p in player_stats.values() if p.close_game_stats['plus_minus'] != 0]
        close_game_players.sort(key=lambda p: p.close_game_stats['plus_minus'], reverse=True)
        
        close_data = []
        for player in close_game_players[:10]:
            close_data.append({
                'Player': player.name,
                '+/-': player.close_game_stats['plus_minus'],
                'Points': player.close_game_stats['points'],
                'Impact': player.close_game_impact
            })
        
        if close_data:
            df = pd.DataFrame(close_data)
            st.dataframe(df, use_container_width=True)
        
        st.subheader("🔥 Key Insights")
        if active_players:
            most_efficient = max([p for p in active_players if p.fga >= 20], key=lambda p: p.ts_pct, default=None)
            if most_efficient:
                st.info(f"**Most Efficient Scorer:** {most_efficient.name} with {most_efficient.ts_pct:.1f}% TS%")
            
            best_defender = max(active_players, key=lambda p: p.spg + p.bpg)
            st.info(f"**Best Defender:** {best_defender.name} with {best_defender.spg:.1f} SPG + {best_defender.bpg:.1f} BPG")
    
    # Download option
    st.sidebar.markdown("---")
    if st.sidebar.button("💾 Download JSON Data"):
        json_data = {
            'metadata': {
                'total_games': len(games),
                'generated': datetime.now().isoformat()
            },
            'players': {}
        }
        
        for name, stats in player_stats.items():
            if stats.games == 0:
                continue
            
            json_data['players'][name] = {
                'name': stats.name,
                'games': stats.games,
                'ppg': stats.ppg,
                'rpg': stats.rpg,
                'apg': stats.apg,
                'fg_pct': stats.fg_pct,
                'plus_minus': stats.plus_minus
            }
        
        st.sidebar.download_button(
            label="📥 Download JSON",
            data=json.dumps(json_data, indent=2),
            file_name='cu_basketball_data.json',
            mime='application/json'
        )

if __name__ == "__main__":
    main()
