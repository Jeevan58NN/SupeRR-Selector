import React from "react";

const fmt=(v,d=1)=>v==null||Number.isNaN(Number(v))?"—":Number(v).toLocaleString(undefined,{maximumFractionDigits:d});

function DataTable({rows,columns}){
  if(!rows?.length)return <p className="empty">No recorded data for this role.</p>;
  return <div className="table-wrap"><table><thead><tr>{columns.map(c=><th key={c.key}>{c.label}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i}>{columns.map(c=><td key={c.key}>{c.format?c.format(row[c.key]):row[c.key]??"—"}</td>)}</tr>)}</tbody></table></div>;
}

export default function PlayerProfile({profile,breakdowns,role,setRole,scenario}){
  const player=profile?.player??{};
  const isBatter=role==="batter";
  const stats=isBatter?profile?.batting:profile?.bowling;
  const rating=(player.ratings??[]).find(x=>x.player_role===role)??{};
  const contexts=(breakdowns?.[role]??[]).slice().sort((a,b)=>(b.matches_in_sample??0)-(a.matches_in_sample??0));
  const situations=(profile?.situations??[]).filter(x=>x.player_role===role);
  const statsCards=isBatter?[
    ["Innings",stats?.batter_innings],["Runs",stats?.runs],["Balls faced",stats?.balls],
    ["Strike rate",stats?.strike_rate,2],["Average",stats?.average,2],["Fours",stats?.fours],
    ["Sixes",stats?.sixes],["Dot balls",stats?.dot_pct,"percent"],["Boundary balls",stats?.boundary_pct,"percent"]
  ]:[
    ["Innings",stats?.bowler_innings],["Legal balls",stats?.legal_balls],["Runs conceded",stats?.runs_proxy],
    ["Wickets",stats?.wickets],["Economy",stats?.economy_proxy,2],["Dot balls",stats?.dot_pct,"percent"],
    ["Wides",stats?.wides],["No-balls",stats?.no_balls]
  ];
  const situationColumns=[{key:"situation_id",label:"Situation"},{key:"situation_score",label:"Rating",format:v=>fmt(v,2)},
    {key:"matches_in_sample",label:"Matches"},{key:"episodes",label:"Episodes"},{key:"deliveries",label:"Deliveries"}];
  const contextColumns=isBatter?
    [{key:"context_dimension",label:"Context"},{key:"context_value",label:"Value"},{key:"matches_in_sample",label:"Matches"},{key:"innings_in_sample",label:"Innings"},{key:"runs",label:"Runs"},{key:"balls",label:"Balls faced"},{key:"strike_rate",label:"Strike rate",format:v=>fmt(v,2)}]:
    [{key:"context_dimension",label:"Context"},{key:"context_value",label:"Value"},{key:"matches_in_sample",label:"Matches"},{key:"innings_in_sample",label:"Innings"},{key:"runs",label:"Runs conceded"},{key:"balls",label:"Legal balls"},{key:"economy_proxy",label:"Economy",format:v=>fmt(v,2)}];
  return <>
    <section className="hero profile-hero"><div><small>PLAYER PROFILE · ID {player.player_id}</small><h2>{player.player_name}</h2><p><strong>{player.player_type??"Role unavailable"}</strong> · Proxy-inclusive estimate</p></div></section>
    <section className="cards profile-ranks">
      <article className="rank-card"><span>Batting rank</span><b>{player.batting_rank?`#${player.batting_rank}`:"—"}</b><small>{fmt(player.normal_batting_innings,0)} normal batting innings</small></article>
      <article className="rank-card"><span>Bowling rank</span><b>{player.bowling_rank?`#${player.bowling_rank}`:"—"}</b><small>{fmt(player.normal_bowling_innings,0)} normal bowling innings</small></article>
    </section>
    <section className="panel profile-role-panel"><h3>Role statistics</h3><div className="tabs profile-role-toggle">
      <button className={isBatter?"selected":""} onClick={()=>setRole("batter")}>Batting</button>
      <button className={!isBatter?"selected":""} onClick={()=>setRole("bowler")}>Bowling</button>
    </div>
    <div className="cards profile-stat-cards">{statsCards.map(([label,value,format])=><article key={label}><span>{label}</span><b>{format==="percent"?`${fmt(value,2)}%`:fmt(value,format??0)}</b></article>)}</div>
    {rating.rank==null&&<p className="explain">No {role} pressure rank is available for this player in this scenario. Their general role statistics may still be available.</p>}</section>
    <section className="cards profile-rating-cards">
      {[ ["Pressure rating",rating.ranking_score,2],["Normal rating",rating.normal_rating,2],["Pressure matches",rating.pressure_matches,0],
         ["Normal innings",rating.normal_innings,0],["Consistency",rating.consistency_score,1],["Evidence",rating.confidence_label] ].map(([label,value,d])=><article key={label}><span>{label}</span><b>{typeof value==="string"?value:fmt(value,d??1)}</b></article>)}
    </section>
    <section className="panel"><h3>{isBatter?"Batting":"Bowling"} pressure situations</h3><DataTable rows={situations} columns={situationColumns}/></section>
    {contexts.length>0&&<section className="panel"><h3>{isBatter?"Batting":"Bowling"} by context</h3><DataTable rows={contexts.slice(0,24)} columns={contextColumns}/></section>}
  </>;
}
