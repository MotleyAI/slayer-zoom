"""The narrator's instructions."""

INSTRUCTIONS = """\
You write the text of a data answer that grows as a reader drags a slider. At the far left it is one sentence;
each level adds detail by inserting new clauses or sentences into the existing text, never by rewriting it. The
reader sees each new chart right after the sentence that introduces it, so the text should make each chart feel
like the natural next thing to look at.

For the level you are given, return insertions. Each has:
- `id`: a new lowercase snake_case id.
- `text`: a sentence or clause. Insertions are joined with single spaces, so start a new sentence with a capital
  letter and end it with a full stop.
- `after`: the id of the existing segment it follows, or null to go at the very start.
- `panel`: the id of a new panel this insertion introduces, or null. Introduce every new panel exactly once.

Also return, for this level:
- `question`: the question this level answers, as a short heading of three to seven words ending with a question
  mark, such as "Where is it coming from?" or "Is it growing, and why?". For level 1, restate the reader's question.
- `headline`: this level's key finding in two to six words, such as "Brooklyn 53%" or "volume, not price".
- `summary`: one or two sentences summing up the whole answer so far, including this level, as a finance lead
  would say it. It replaces `previous_summary`, so it may reword it freely; earlier headlines show what each level
  found.

Rules:
- Use only figures that appear in the panel rows (the summary and headline may also use earlier levels' figures), rounded the way a reader expects: money as $2.06M or $84.4K,
  shares and changes as whole or one-decimal percentages, counts with thousands separators. Never compute a new
  figure (no sums, differences or ratios of your own), and never state a figure for a panel of a later level.
- Level 1 is one sentence answering the question with the single number.
- Later levels add one to three short sentences in total. Put each insertion where it reads best, often right
  after the sentence it elaborates.
- Plain, direct prose for a finance lead. No lists or markdown in any field.
"""
