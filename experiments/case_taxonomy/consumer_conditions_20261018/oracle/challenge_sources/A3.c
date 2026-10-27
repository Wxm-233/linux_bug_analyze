/* Artificial ordinary-C development input; not Linux source or a defect. */
int bind_actor_group(int focus, int m0, int m1, int m2, int r0, int r1, int r2)
{
  int actors[3] = {m0, m1, m2};
  int backref[3] = {r0, r1, r2};
  const int span = 3;
  int chosen = -1;
  int inconsistent = 0;
  int slot;

  if (span == 1)
    return 10;
  for (slot = 0; slot < span; slot++) {
    int actor = actors[slot];
    if (actor == focus)
      continue;
    if (backref[actor] == actor) {
      chosen = actor;
      break;
    }
  }
  if (chosen < 0)
    return 20;
  for (slot = 0; slot < span; slot++) {
    int actor = actors[slot];
    if (actor == focus)
      backref[actor] = chosen;
    if (backref[actor] != chosen)
      inconsistent = 1;
  }
  if (inconsistent)
    return 30;
  return 0;
}
