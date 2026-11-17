from pathlib import Path
import hashlib
import pandas as pd

FILES = ["ball_by_ball.csv","competition_team_player_mapping.csv","competitions.csv","matches.csv","playing_eleven.csv","teams.csv"]

def project_root():
    return Path(__file__).resolve().parents[3]

def load(root=None):
    root = Path(root or project_root())
    missing = [f for f in FILES if not (root/f).is_file()]
    if missing:
        raise FileNotFoundError("Missing source CSVs: " + ", ".join(missing))
    return {f: pd.read_csv(root/f, low_memory=False) for f in FILES}

def manifest(root=None):
    root = Path(root or project_root())
    rows=[]
    for f in FILES + ["Round 1 Problem Statement _ SupeRR Selector Season 2.docx.pdf"]:
        p=root/f
        rows.append({"file_name":f,"exists":p.is_file(),"bytes":p.stat().st_size if p.is_file() else None,
                     "sha256":hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None})
    return pd.DataFrame(rows)

def validate(t):
    required={"ball_by_ball.csv":{"match_id","innings","overid","striker_id","bowler_id","runs","extras1_runs"},
              "matches.csv":{"match_id","comp_id","match_date","revised_target"},
              "competitions.csv":{"comp_id","comp_name","match_format"},
              "playing_eleven.csv":{"match_id","team_id","player_id","is_played","is_impact"},
              "competition_team_player_mapping.csv":{"comp_id","team_id","player_id","player_name"},
              "teams.csv":{"comp_id","team_id","team_name"}}
    rows=[]
    for name, cols in required.items():
        df=t[name]; miss=sorted(cols-set(df.columns))
        rows.append({"file_name":name,"rows":len(df),"columns":len(df.columns),"missing_required":"|".join(miss),
                     "exact_duplicate_rows":int(df.duplicated().sum()),"valid":not miss})
    out=pd.DataFrame(rows)
    if not out.valid.all(): raise ValueError(out.loc[~out.valid].to_string(index=False))
    return out
