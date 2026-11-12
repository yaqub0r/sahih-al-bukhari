"""Synthetic reciprocal-communication regression and adversarial cycle tests."""
import copy
import unittest
from scripts import hadith_structure as legacy
from scripts import hadith_structure_v2 as h
from tests.test_hadith_structure import fixture as legacy_fixture


def fixture():
    text = 'A tells B, replies. C invented event.'
    source = {'units': [{'id': 'u', 'kind': 'report', 'arabic': text}]}
    ledger = {'identities': [{'id': x.lower(), 'arabicForms': [x]} for x in ['A', 'B', 'C']]}
    nodes = [{'id': x.lower(), 'kind': 'narrator', 'start': text.index(x),
              'end': text.index(x)+1, 'nameId': x.lower(), 'status': 'resolved',
              'note': 'Invented physical occurrence.'} for x in ['A', 'B']]
    edges = [{'id': 'ab', 'from': 'a', 'to': 'b', 'start': 2, 'end': 7,
              'mode': 'explicit', 'note': 'Invented receipt.'},
             {'id': 'ba', 'from': 'b', 'to': 'a', 'start': 11, 'end': 18,
              'mode': 'explicit', 'note': 'Invented reply receipt.'}]
    paths = [{'id': e['id'], 'kind': 'embedded', 'nodeIds': [e['from'], e['to']],
              'edgeIds': [e['id']], 'status': 'complete', 'note': 'Separate textual receipt.'} for e in edges]
    unit = {'id': 'u', 'sha256': h.sha(text.encode()),
            'segments': [{'start': 0, 'end': len(text), 'kind': 'matn'}],
            'nodes': nodes, 'edges': edges, 'paths': paths,
            'reports': [{'id': 'r', 'start': 0, 'end': len(text), 'pathIds': ['ab', 'ba'],
                         'status': 'complete', 'note': 'Synthetic report.'}],
            'status': 'complete', 'note': 'Synthetic, no historical assertion.',
            'reciprocalCommunications': [{'id': 'reciprocal', 'edgeIds': ['ab', 'ba'],
                                          'note': 'Invented telling and explicit reply.'}]}
    return source, {'version': 2, 'units': [unit]}, ledger


class ReciprocalTests(unittest.TestCase):
    def test_truthful_reciprocal_passes_new_contract_only(self):
        s,g,l = fixture()
        self.assertEqual(h.validate(s,g,l), g)
        self.assertIn('RECIPROCAL', h.render(s,g))
        old = copy.deepcopy(g); old['version'] = 1
        del old['units'][0]['reciprocalCommunications']
        with self.assertRaisesRegex(ValueError, 'transmission cycle'):
            legacy.validate(s,old,l)

    def test_ordinary_legacy_graph_migrates_without_semantic_change(self):
        s,g,l = legacy_fixture(); before = copy.deepcopy(g['units'])
        g['version'] = 2
        h.validate(s,g,l)
        self.assertEqual(g['units'], before)
        self.assertNotEqual(h.contract_hash(), legacy.contract_hash())

    def test_undeclared_reciprocal_rejected(self):
        s,g,l = fixture(); g['units'][0]['reciprocalCommunications'] = []
        with self.assertRaisesRegex(ValueError, 'transmission cycle'):
            h.validate(s,g,l)

    def test_declaration_cannot_conceal_longer_cycle(self):
        s,g,l = fixture(); u = g['units'][0]; pos = s['units'][0]['arabic'].index('C')
        u['nodes'].append({'id':'c','kind':'narrator','start':pos,'end':pos+1,
                           'nameId':'c','status':'resolved','note':'Third invented actor.'})
        for eid, left, right in [('ac','a','c'),('cb','c','b')]:
            u['edges'].append({'id':eid,'from':left,'to':right,'start':2,'end':7,
                               'mode':'explicit','note':'Invented extra relation.'})
            u['paths'].append({'id':eid,'kind':'embedded','nodeIds':[left,right],
                               'edgeIds':[eid],'status':'complete','note':'Invented path.'})
            u['reports'][0]['pathIds'].append(eid)
        with self.assertRaisesRegex(ValueError, 'larger'):
            h.validate(s,g,l)

    def test_reciprocal_edge_cannot_appear_in_primary_or_multiple_paths(self):
        for duplicate in [False, True]:
            s,g,l = fixture(); u = g['units'][0]
            if duplicate:
                p = dict(u['paths'][0], id='copy'); u['paths'].append(p)
                u['reports'][0]['pathIds'].append('copy')
            else: u['paths'][0]['kind'] = 'primary'
            with self.assertRaisesRegex(ValueError, 'exclusive two-node'):
                h.validate(s,g,l)

    def test_reciprocal_predicates_cannot_be_implicit_reused_or_reversed(self):
        for case in ['implicit','reused','reversed']:
            s,g,l = fixture(); u = g['units'][0]
            if case == 'implicit': u['edges'][0].update(mode='implicit',start=None,end=None)
            elif case == 'reused': u['edges'][1].update(start=2,end=7)
            else: u['reciprocalCommunications'][0]['edgeIds'].reverse()
            with self.subTest(case=case), self.assertRaises(ValueError): h.validate(s,g,l)

    def test_no_extra_internal_edge_or_duplicate_declaration(self):
        for case in ['edge','declaration']:
            s,g,l = fixture(); u = g['units'][0]
            if case == 'declaration': u['reciprocalCommunications'].append(dict(u['reciprocalCommunications'][0],id='copy'))
            else:
                u['edges'].append(dict(u['edges'][0],id='extra'))
                u['paths'].append(dict(u['paths'][0],id='extra',edgeIds=['extra']))
                u['reports'][0]['pathIds'].append('extra')
            with self.subTest(case=case), self.assertRaises(ValueError): h.validate(s,g,l)


if __name__ == '__main__': unittest.main()
