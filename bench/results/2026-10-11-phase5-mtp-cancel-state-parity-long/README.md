# Excluded MTP cancellation-state attempt — early EOS

This attempt also failed to reach cancellation. Although the prepared fixture
allows up to 128 output tokens, the model emitted the same 11-token
early-EOS response as the 512/64 fixture before the client cutoff. No canceled
state comparison was produced. The raw engine log and supervisor record are
retained. The next attempt uses an explicit open-ended integer-list prompt and
records it in the result JSON.
