/* Artificial ordinary-C development input; not Linux source or a defect. */
int select_relation_2(int target, int m0, int m1, int m2, int r0, int r1, int r2)
{
  int members[3] = {m0, m1, m2};
  int owners[3] = {r0, r1, r2};
  const int limit = 2;
  int witness = -1;
  int mismatch = 0;
  int pos;

  if (limit == 1)
    return 10;
  for (pos = 0; pos < limit; pos++) {
    int member = members[pos];
    if (member == target)
      continue;
    if (owners[member] == member) {
      witness = member;
      break;
    }
  }
  if (witness < 0)
    return 20;
  for (pos = 0; pos < limit; pos++) {
    int member = members[pos];
    if (member == target)
      owners[member] = witness;
    if (owners[member] != witness)
      mismatch = 1;
  }
  if (mismatch)
    return 30;
  return 0;
}
