# TICKET-055 — parse_merge_commits + MergeCommit (git merge-commit half of §8 "Done")

## Capability
`MergeCommit(cycle, sha, raw)` dataclass + `parse_merge_commits(text, *, merge_pattern=None) -> list[MergeCommit]`.

## Spec
- Parse git log text into per-cycle merge commits in FILE ORDER — position is the only order, never reordered, never deduped (a cycle may have more than one merge across restarts).
- `merge_pattern` is an overridable seam: default a compiled regex with ONE capture group (the cycle number) matching a merge-commit line that names the cycle — the repo's `Merge pull request #N from <owner>/build<cycle>/...` convention, capturing the cycle from the branch name.
- Each match -> `MergeCommit(cycle=int(group1), sha=<sha>, raw=<line>)`. The sha is the leading token of the line (the commit hash); when a line has no leading sha token, sha is the empty string.
- Pure, deterministic, stdlib-only; no I/O. Empty text / no match -> empty list.

## Acceptance
- single commit, multiple commits, file order preserved, no reorder/dedupe, empty text, custom merge_pattern seam, no-match -> empty.
