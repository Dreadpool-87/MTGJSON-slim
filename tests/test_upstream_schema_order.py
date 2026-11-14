"""Explicitly authorized MTGJSON sets-column reordering without data loss."""
import copy
import json
from pathlib import Path
import unittest

import slim

ROOT = Path(__file__).resolve().parents[1]


class OfficialSchemaCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads((ROOT / "profiles" / "v2_3.json").read_text())
        cls.pinned = cls.profile["source_schema"]
        cls.set_index = next(i for i,x in enumerate(cls.pinned) if x[:2] == ["table", "sets"])

    def reorder_sets(self):
        observed = copy.deepcopy(self.pinned)
        ddl = observed[self.set_index][3]
        prefix = 'CREATE TABLE "sets" ('
        self.assertTrue(ddl.startswith(prefix))
        bits = ddl[len(prefix):-1].split(", ")
        self.assertGreater(len(bits), 8)
        observed[self.set_index][3] = prefix + ", ".join(reversed(bits)) + ")"
        return observed

    def test_profile_still_locked(self):
        slim.check_profile(self.profile)
        self.assertTrue(slim.source_schema_compatible(self.pinned, self.pinned))

    def test_set_column_order_change_only_is_allowed(self):
        self.assertTrue(slim.source_schema_compatible(self.reorder_sets(), self.pinned))

    def test_added_or_removed_field_fails_closed(self):
        observed = self.reorder_sets()
        observed[self.set_index][3] = observed[self.set_index][3][:-1] + ', "danger" TEXT)'
        self.assertFalse(slim.source_schema_compatible(observed, self.pinned))

    def test_type_change_fails_closed(self):
        observed = self.reorder_sets()
        observed[self.set_index][3] = observed[self.set_index][3].replace('"mcmId" INTEGER', '"mcmId" TEXT')
        self.assertFalse(slim.source_schema_compatible(observed, self.pinned))

    def test_other_table_or_index_reordering_fails_closed(self):
        altered = copy.deepcopy(self.pinned)
        item = next(i for i,x in enumerate(altered) if x[0] == "index")
        altered[item][3] += " "
        self.assertFalse(slim.source_schema_compatible(altered, self.pinned))

    def test_no_unreviewed_constraints(self):
        altered = self.reorder_sets()
        altered[self.set_index][3] = altered[self.set_index][3][:-1] + ", CHECK(1=1))"
        self.assertFalse(slim.source_schema_compatible(altered, self.pinned))


if __name__ == "__main__":
    unittest.main()
