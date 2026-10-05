import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run import generate,fit,optimize

class PricingTests(unittest.TestCase):
    def test_price_and_contribution_accounting(self):
        d=generate(5000)
        self.assertEqual(d.customer_id.nunique(),len(d))
        np.testing.assert_allclose(d.total_price_usd,d.fee_usd+d.send_amount_usd*d.spread_bps/10000)
        np.testing.assert_allclose(d.contribution_usd,d.converted*(d.total_price_usd-d.variable_cost_usd))
        self.assertEqual(float(d.loc[d.converted==0,'revenue_usd'].sum()),0.)
    def test_randomized_response_recovery(self):
        d=generate(24000)
        for c,true_slope in [('Market-A',-1.),('Market-B',-1.4),('Market-C',-.7)]:
            b=fit(d[d.corridor==c])
            self.assertLess(abs(b[1]-true_slope),.35)
    def test_recommendation_is_supported_and_guardrailed(self):
        d=generate(8000)
        for _,g in d.groupby('corridor'):
            b=fit(g);best,candidates=optimize(g[g.arm=='current'],b)
            self.assertIn(best[0],[.8,1.,1.2])
            self.assertGreaterEqual(best[1],candidates[1][1]-.03)
            self.assertGreater(candidates[0][1],candidates[2][1])
if __name__=='__main__':unittest.main()
