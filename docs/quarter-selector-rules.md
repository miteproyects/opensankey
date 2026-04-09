# Quarter Selector Rules

## Display
- Always show exactly 8 quarter buttons: 4 from the selected year (Period A) and 4 from the previous year.
- Sorted by closest to present at the top, oldest at the bottom.
- Each button shows: `FY{year} - Q{n} ({Mon YY} · {Mon YY} · {Mon YY})`
- Unavailable quarters (not yet completed) show: `FY{year} - Q{n} — in {X}d`

## Default State
- On load, the available quarter closest to the present must be ON.
- All other quarters default to OFF.

## Selection Constraints
1. **Minimum 1**: At least one quarter selector must always be ON. User cannot turn off the last active quarter.
2. **Maximum 4**: User can select at most 4 quarter selectors. Selecting a 5th is blocked.
3. **Maximum span of 3**: The chronological distance between the topmost (newest) selected quarter and the bottommost (oldest) selected quarter cannot exceed 3 quarter periods. For example, if Q3 FY2025 is selected, the furthest allowed selection downward is Q4 FY2024 (3 periods apart). Selecting Q3 FY2024 (4 periods apart) would be blocked.

## Toggle Behavior
- Click an OFF button to turn it ON (if constraints allow).
- Click an ON button to turn it OFF (if at least 1 remains ON).
- If a toggle would violate max-4 or max-span-3, the toggle is ignored (button stays OFF).

## State Validation
- On every rerun, existing state is validated against all constraints.
- If the span between the newest and oldest selected quarter exceeds 3 periods, the oldest selections are dropped until the span fits.
- If more than 4 quarters are selected, the oldest are dropped.
- This handles stale state from before the rules were deployed or edge cases from year switching.
