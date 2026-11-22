# Design

Play either game first as a normal adventure, then the other as a linked game.
The target is all collectibles and upgrades across the two saves, rather than
every mutually exclusive story variant or optional challenge in both orders.

The ordinary ten secrets per order remain. Ages' Plen and Mamamu quests give
Spin + Swimmer's and Snowshoe + Heart Ring L-1 respectively. Seasons' Diver and
Great Fairy give the reverse pairs. Each uses two native pickup sequences,
with the original quest completion flag recorded only after both. Appraise both
rings and transfer them using the ordinary ring secret. No additional password
protocol, dialogue entries, book rows, save fields or Game 2 receiver quests are
needed. Existing appraisal reminders use plural wording.

Game 2's ending save and peaceful world remain independent. The broad Game 1
completion flag stays unset in linked clears: the family, trades and original
linked secret givers retain their roles. The Diver returns home peacefully
using existing ordinary dialogue, without enabling his Game 1 secret quest.
The Room of Rites entrance closes after a saved linked final clear, preventing
the already-completed rescue sequence from reappearing during postgame play.
Both the portal decoration and the actual warp are removed. The existing
Ganon-clear flag controls this; no extra save fields or dialogue are added.

Other cumulative changes include Game 1's postgame heart chest and expanded
Hero's Cave access, Ages' sea passage, and the linked Victory Ring. Hero's Cave
is open from the start in Game 1. Native equipment puzzles gate progress.
Seasons uses the upper Game 1 door and matching exit throughout the adventure;
the original sword cave and native linked entrances retain their roles.
Advance rings keep the native hardware gate. Farore's book code and graphics
layout are restored to retail, with the unrelated chest graphics fix preserved.

Source changes are tracked in src/changes.patch against the pinned upstream.
Already-claimed quests are not migrated into new paired rewards.
