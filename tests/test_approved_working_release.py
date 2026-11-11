"""Verify the explicitly owner-approved public working proposal."""
import unittest
from pathlib import Path
from scripts import release_distribution as d
ROOT=Path(__file__).resolve().parents[1]
class ApprovedWorkingReleaseTests(unittest.TestCase):
    def test_public_proposal_and_owner_approval(self):
        config=d.read(ROOT/'release/distribution.config.json');schema,adapter=d.load_contract(ROOT,config)
        p=d.read(ROOT/'release/proposals/bukhari-opening-faith-working-1.json')
        d.validate_proposal(p,config,schema,adapter)
        a=d.read(ROOT/'release/approvals/bukhari-opening-faith-working-1.json')
        self.assertTrue(config['publicationEnabled']);self.assertEqual(p['rights']['originalContentLicense'],'CC-BY-4.0')
        self.assertEqual(p['rights']['status'],'approved');self.assertEqual(len(p['records']),110)
        self.assertEqual(sum(r['printedHadithNumber'] is not None for r in p['records']),58)
        self.assertTrue(all(r['humanReview']=='unreviewed' for r in p['records']))
        self.assertEqual(sum(len(r['uncertainties']) for r in p['records']),49)
        self.assertEqual(a['proposalSha256'],d.digest(p));self.assertEqual(a['schemaSha256'],d.digest(schema))
        self.assertTrue(a['authorized']);self.assertIn(a['approvedBy'],config['approverIds'])
        self.assertEqual(a['decisionId'],p['rights']['decisionId']);self.assertEqual(a['releaseId'],p['releaseId'])
