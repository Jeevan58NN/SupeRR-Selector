# Source audit (2026-11-17)

The folder has one ball-by-ball file: 180,723 rows, 33 columns, 779 matches. Match metadata has 883 rows; 104 have no ball-by-ball coverage. The source folder has no repaired ball copy for a hash comparison. The delivery file has zero exact duplicate rows.

The competition table has 134 T20I and 7 T20 records. T20 includes IPL 2022–2026 and two other T20 competitions. There are 31 knockout metadata rows, 25 covered by deliveries. Five matches contain innings numbered 3/4, consistent with Super Overs. Match 46249 (Nepal-West Indies, 2025-09-27) has only an innings-2 segment and no innings-1 rows.

extras1_runs is a category code, not an extra-run amount: 1 overstep, 2 wide, 3 legbyes, 4 byes, 5 other, 6 no extra, 7 penalty. Only 35 rows have nonzero extras_2_runs. Preserve separate exact and proxy score states. There are 20 disagreements between is_four and runs==4, and two between is_six and runs==6.

All observed player IDs join to the supplied mapping. playing_eleven.csv contains 40 repeated match/team/player keys with differing batting_order values. Two extra Excel workbooks exist in the folder but were not in the authorized input list and have not been inspected or used.

