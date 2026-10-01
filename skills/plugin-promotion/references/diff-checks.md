# Diff checks: hunk arithmetic

How to check the **plugin-promotion** skill's diff rule 6 (no hunk touches frontmatter) by hand.

- In each `git diff -U0` hunk `@@ -a,n +b,m @@` (an omitted count is 1), the removed lines are old
  lines a…a+n−1 and the added lines are new lines b…b+m−1.
- Each must be strictly after the closing frontmatter `---` on its own side (old or new file).
- On a saved patch with context, count from the header past context lines to each hunk's first
  `+`/`-` line.
