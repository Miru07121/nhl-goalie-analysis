"""Reproduce a season-level goalie EDA using MoneyPuck's public CSV."""
from pathlib import Path
import json
import hashlib
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent

def main():
    source = ROOT / 'data/goalies_2024.csv'
    raw = pd.read_csv(source)
    columns = ['playerId', 'name', 'season', 'situation', 'icetime', 'xGoals', 'goals', 'ongoal']
    if not set(columns).issubset(raw.columns):
        raise ValueError('Missing required source columns')
    df = raw.loc[(raw.season == 2024) & (raw.situation == 'all'), columns].copy()
    if df.empty or df.playerId.duplicated().any() or df.isna().any().any():
        raise ValueError('Empty sample, duplicate goalies, or missing values')
    if (df[['icetime', 'xGoals', 'goals', 'ongoal']] < 0).any().any() or (df.goals > df.ongoal).any():
        raise ValueError('Invalid time, count, or expected-goal value')
    df = df.loc[(df.icetime > 0) & (df.ongoal > 0)].copy()
    df['minutes'] = df.icetime / 60
    df['gsax'] = df.xGoals - df.goals
    df['gsax_per60'] = df.gsax * 3600 / df.icetime
    df['save_pct'] = 1 - df.goals / df.ongoal
    df['gaa'] = df.goals * 3600 / df.icetime
    df['xga_per60'] = df.xGoals * 3600 / df.icetime
    eligible = df.loc[df.minutes >= 1000].copy()
    if len(eligible) < 3:
        raise ValueError('Insufficient eligible goalies')
    eligible['total_rank'] = eligible.gsax.rank(ascending=False, method='min')
    eligible['rate_rank'] = eligible.gsax_per60.rank(ascending=False, method='min')
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    eligible.sort_values('gsax', ascending=False).to_csv(out / 'goalie_metrics.csv', index=False)
    sensitivity = []
    for threshold in (500, 1000, 1500, 2000):
        sample = df.loc[df.minutes >= threshold]
        leader = sample.loc[sample.gsax_per60.idxmax()]
        sensitivity.append({'minimum_minutes': threshold, 'goalies': len(sample),
                            'rate_leader': leader['name'], 'leader_gsax_per60': leader.gsax_per60})
    pd.DataFrame(sensitivity).to_csv(out / 'threshold_sensitivity.csv', index=False)
    total = eligible.loc[eligible.gsax.idxmax()]
    rate = eligible.loc[eligible.gsax_per60.idxmax()]
    summary = {'season': '2024-25 regular season', 'situation': 'all',
               'source_rows': len(raw), 'goalies_before_time_filter': len(df),
               'minimum_minutes': 1000, 'eligible_goalies': len(eligible),
               'total_leader': total['name'], 'total_leader_gsax': total.gsax,
               'rate_leader': rate['name'], 'rate_leader_gsax_per60': rate.gsax_per60,
               'pearson_save_pct_vs_gsax_per60': eligible.save_pct.corr(eligible.gsax_per60),
               'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    (out / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), layout='constrained')
    top = eligible.nlargest(10, 'gsax').sort_values('gsax')
    axes[0].barh(top['name'], top.gsax, color='#137c85')
    axes[0].set(xlabel='Goals saved above expected', title='Top 10 by total GSAx')
    axes[1].scatter(eligible.save_pct * 100, eligible.gsax_per60, color='#137c85', alpha=.75)
    axes[1].axhline(0, color='gray', linestyle='--', linewidth=1)
    for _, row in eligible.nlargest(3, 'gsax_per60').iterrows():
        axes[1].annotate(row['name'], (row.save_pct*100, row.gsax_per60), xytext=(-5, 7),
                         textcoords='offset points', ha='right', fontsize=9)
    axes[1].set(xlabel='Save percentage (%)', ylabel='GSAx per 60 minutes',
                title='Save percentage and quality-adjusted results')
    fig.suptitle('NHL goalies | 2024–25 regular season\nAll situations · minimum 1,000 minutes · Source: MoneyPuck.com', fontsize=14)
    fig.savefig(out / 'goalie_performance.png', dpi=160)
    plt.close(fig)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
