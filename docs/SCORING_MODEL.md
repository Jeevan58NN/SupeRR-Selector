# Scoring model

## Outcome signals

All signals are calculated separately by batter/bowler role and within the situation and context benchmark fallback hierarchy. The batting blend weights scoring efficiency (strike rate and batter dots) at 45%, pressure runs contributed at 15%, boundary rate at 20%, and chase RRR reduction at 20%. When RRR cannot be calculated (for example, a first innings), the available metric weights are renormalized; missing chase evidence is not scored as zero. The bowling blend weights economy/control at 45%, bowler-credited wickets per 100 balls at 30%, boundary prevention at 15%, and increasing chase RRR at 10%. This keeps the rating tied to whether the player changed the pressure state, not only to being present in an episode.

- Batter scoring: `strike rate − 0.35 × batter dot-ball percentage`.
- Batter survival: `− dismissal rate`.
- Bowler control: `−0.70 × economy + 0.30 × legal-ball dot percentage`.
- Bowler wicket: bowler-credited wickets per 100 eligible balls.

Each signal is robustly normalized using median/MAD (with interquartile/standard-deviation fallback when the MAD is zero), transformed to `clip(50 + 10z, 0, 100)`, and combined with the situation-specific weights above. Missing chase-only signals are excluded and the remaining weights are renormalized. Batter dots use batter runs; bowling dots use exact bowler-conceded runs in strict mode and proxy-lower-bound conceded runs in proxy mode. Strict bowling economy only uses legal balls with known exact bowler runs. Wickets are independently available where dismissal type supports attribution.

Peer groups use a minimum of five distinct players, with fallback ordered from situation + role + competition + opponent tier + phase + batting position, progressively broader same-role groups, then role population. The benchmark level is saved per observation.

## Context, opportunity and evidence

Situation severity and dynamic pressure intensity set opportunity weights; overlapping candidate clusters share rather than multiply contribution. Opponent factors scale the context-adjusted score departure from neutral 50: factor 1.0 preserves it, lower values reduce the magnitude. Opponent factor does not change match count. A sensitivity variant recomputes scores without this factor.

Observations are consolidated to player-match scores. Episodes and deliveries from the same match are not independent evidence units. Pressure match evidence is weighted by the configured opponent tier, so a match against a weaker pool contributes less evidence. Normal batting/bowling innings are combined with weighted pressure matches using their harmonic mean: both evidence sources must be present, and a large sample in one cannot mask a tiny sample in the other. Both the observed pressure score and match-consistency score are shrunk toward 50 using `k=30` effective match-equivalents. Sensitivity reports `k=3`, `5`, `8`, `12`, `20`, `30`, and `40`. Match consistency uses weighted above-neutral frequency, exceptional frequency, and dispersion. A player's single-match consistency therefore stays close to neutral instead of being inferred as perfect. The final rating is 50% adjusted pressure performance, 20% match consistency, and 30% role-aware normal performance. Normal performance is standardized within a player's primary batting-position or bowling-phase group, then its departure from neutral is scaled by the opponent factor. This gives sustained normal performance a meaningful supporting role while keeping pressure performance the largest component. There is no hard minimum-match cutoff. Sensitivity varies consistency weight from 20% through 50%, with the normal component held at 30%. Evidence confidence and a match-bootstrap interval are reported separately. Batting and bowling evidence are scored independently, so a bowling spell cannot affect a player's batting rank.

## Known limits

The current composite is an explainable first model, not a validated probability of future success. Its component weights and robust baseline fallback should be evaluated with cricket analysts. Ranking sensitivity provides weight comparisons but the current acceptance suite does not yet independently test all 31 triggers and every end condition. The confidence interval is a 300-resample match bootstrap. Knockout evidence is capped to ±0.50 only when base ratings are within the configured 0.50-point band.
