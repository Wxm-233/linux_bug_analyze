/* Assistant-synthesized component input: not Linux or an expert gold standard.
 * Markers inside this comment: // and the word alpha; no executable evidence.
 */
int revocable_recording(int pivot, int p0, int p1, int p2, int q0, int q1, int q2, int nomination)
{
  int items[3] = {p0, p1, p2}; // bounded local sequence
  int route[3] = {q0, q1, q2};
  const /* immutable local bound */ int ceiling = 3;
  int nominee = -1;
  int marked = 0;
  int cursor;
  int ordinal;

  if (ceiling == 1)
    return 13;
  for (cursor = 0; cursor < ceiling; cursor++) {
    int element = items[cursor];
    int earlier_relation = route[element];
    if (element == pivot)
      continue;
    if (earlier_relation == element) {
      nominee = element;
      break;
    }
  }
  if (nominee < 0)
    return 29;
  // The following check is a neutral predicate, not a bug label.
  for (ordinal = 0; ordinal < ceiling; ordinal++) {
    int subject = items[ordinal];
    int inspected_unit = subject;
    if (inspected_unit == pivot)
      route[inspected_unit] = nominee;
    if (route[inspected_unit] != nominee)
      marked = 1;
    if (inspected_unit == pivot)
      marked = 0;
  }
  if (marked)
    return 37;
  return 5;
}
