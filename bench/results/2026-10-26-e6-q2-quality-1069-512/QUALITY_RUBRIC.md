# 1,069-token generation quality rubric

This is a task-level diagnostic for the existing 1,069-token prompt, extended to a 512-token output allowance so the requested 200 words are feasible. It is not a general model-quality benchmark or performance confirmation. Review both arms against the same checklist without ranking style.

Pass criteria:

1. The first substantive word is “Processor” (case-insensitive).
2. The completion contains at least 200 words.
3. It accurately describes processor instruction processing, including a fetch/decode/execute sequence.
4. It explains how memory (registers/cache/RAM and/or storage) supports execution.
5. It describes input/output or peripheral interaction.
6. It contains no material factual error that reverses or breaks the explanation.

Record each item separately for both arms. A pass here does not override persistent-state differences, does not qualify other tasks, and does not authorize a performance claim.
