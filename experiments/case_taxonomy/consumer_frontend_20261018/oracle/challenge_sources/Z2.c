/* Assistant-synthesized component input: not Linux or an expert gold standard.
 * Markers inside this comment: // and the word alpha; no executable evidence.
 */
int noncanonical_lookup(int focus, int p0, int p1, int p2, int q0, int q1, int q2, int nomination)
{
  int sequence[3] = {p0, p1, p2}; // bounded local sequence
  int parent[3] = {q0, q1, q2};
  const /* immutable local bound */ int extent = 3;
  int selected = -1;
  int scan;
  int walk;

  if (extent == 1)
    return 13;
  scan = 0;
  while (scan < extent) {
    int entry = sequence[scan];
    int earlier_relation = parent[entry];
    if (entry == focus)
      continue;
    if (earlier_relation == entry) {
      selected = entry;
      break;
    }
    scan++;
  }
  if (selected < 0)
    return 29;
  // The following check is a neutral predicate, not a bug label.
  for (walk = 0; walk < extent; walk++) {
    int unit = sequence[walk];
    int inspected_unit = unit;
    if (inspected_unit == focus)
      parent[inspected_unit] = selected;
    if (parent[inspected_unit] != selected)
      return 37;
  }
  return 5;
}
