import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from light_ids import assign_ids
from records import Neighbours, distance, interpretation, key


class LightRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads((Path(__file__).resolve().parents[1] / 'web/data/lights.json').read_text())['lights']

    def test_sorted_latitude_search_matches_brute_force(self):
        tree = Neighbours(self.rows)
        for q in self.rows[::810]:
            expected = sorted((distance(q,r),r['id']) for r in self.rows if r['id']!=q['id'])[:3]
            self.assertEqual([(d,r['id']) for d,r in tree.closest(q,3)], expected)

    def test_duplicate_list_number_can_appear_and_disappear_without_moving_profiles(self):
        one = [{'id':'atl-110','number':'110','name':'Original'}]
        two = [dict(one[0]), dict(one[0],name='Additional buoy')]
        assign_ids(two, one)
        self.assertEqual(two[0]['id'], 'atl-110')
        other = two[1]['id']
        self.assertNotEqual(other, 'atl-110')
        survivor = [dict(two[1], id='atl-110')]
        assign_ids(survivor, two)
        self.assertEqual(survivor[0]['id'], other)

    def test_stable_ids_and_compound_signal_interpretation(self):
        self.assertEqual(len({key(r) for r in self.rows}),len(self.rows))
        self.assertEqual(key({'id':'pac-387.2'}),'pac-387-d-2')
        syntax = {'rhythm':'Q(6) + LFl','colour':'W','period':15}
        self.assertIn('Six quick white flashes followed by a long flash',interpretation(syntax))
        self.assertIn('colour indications',interpretation({**syntax,'colour':'R G'}))
