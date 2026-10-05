"""Independent synthetic remittance quote experiment. Run: python run.py."""
from pathlib import Path
import json
import sqlite3
import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.optimize import minimize
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SEED = 20261001

def generate(n=24000, seed=SEED):
    rng = np.random.default_rng(seed)
    corridor = rng.choice(['Market-A', 'Market-B', 'Market-C'], n)
    new = rng.binomial(1, .4, n)
    amount = rng.choice([150., 300., 600.], n)
    # Assignment is independent of customer propensity, within all segments.
    arm = rng.choice(['low', 'current', 'high'], n)
    mult = pd.Series(arm).map({'low': .8, 'current': 1., 'high': 1.2}).to_numpy()
    base_fee = pd.Series(corridor).map({'Market-A': 2., 'Market-B': 3., 'Market-C': 4.}).to_numpy()
    fee = base_fee * mult
    spread_bps = 100 * mult
    # Spread revenue is defined on USD send principal in this toy model.
    price = fee + amount * spread_bps / 10000
    price_pct = 100 * price / amount
    beta = pd.Series(corridor).map({'Market-A': -1., 'Market-B': -1.4, 'Market-C': -.7}).to_numpy()
    probability = expit(2.3 + beta * price_pct - .4 * new + .15 * np.log(amount / 300))
    converted = rng.binomial(1, probability)
    cost = 1.0 + .001 * amount
    out = pd.DataFrame({'quote_id': np.arange(n), 'customer_id': np.arange(n), 'corridor': corridor,
                        'is_new': new, 'send_amount_usd': amount, 'arm': arm, 'fee_usd': fee,
                        'spread_bps': spread_bps, 'total_price_usd': price, 'price_pct': price_pct,
                        'variable_cost_usd': cost, 'converted': converted})
    out['revenue_usd'] = out.converted * out.total_price_usd
    out['contribution_usd'] = out.converted * (out.total_price_usd - out.variable_cost_usd)
    out['split'] = np.where(rng.random(n) < .75, 'train', 'validation')
    return out

def design(d):
    return np.column_stack([np.ones(len(d)), d.price_pct, d.is_new, np.log(d.send_amount_usd / 300)])

def fit(d):
    x, y = design(d), d.converted.to_numpy()
    def loss(b):
        z=x @ b
        return np.logaddexp(0, z).sum() - y @ z
    def grad(b): return x.T @ (expit(x @ b) - y)
    result = minimize(loss, [2., -1., -.3, .1], jac=grad, method='BFGS', options={'gtol': 1e-5})
    if not np.isfinite(result.fun) or np.linalg.norm(grad(result.x)) > .02:
        raise RuntimeError('Logistic estimation failed')
    return result.x

def optimize(d, b):
    candidates=[]
    # Evaluate ONLY the observed randomized price levels. No extrapolation.
    for mult in [.8, 1., 1.2]:
        scenario=d.copy()
        scenario['price_pct']=d.price_pct * mult  # d is fixed current-price population
        p=expit(design(scenario) @ b)
        price=d.total_price_usd * mult
        cm=(p * (price - d.variable_cost_usd)).mean()
        candidates.append((mult, float(p.mean()), float(cm)))
    base=candidates[1][1]
    feasible=[r for r in candidates if r[1] >= base - .03]
    return max(feasible, key=lambda r:r[2]), candidates

def main():
    for f in ['data','outputs']: (ROOT/f).mkdir(exist_ok=True)
    d=generate(); d.to_csv(ROOT/'data/quotes.csv', index=False)
    connection=sqlite3.connect(ROOT/'outputs/analytics.sqlite')
    d.to_sql('quotes', connection, if_exists='replace', index=False)
    sql=(ROOT/'sql/01_experiment_metrics.sql').read_text()
    pd.read_sql_query(sql, connection).to_csv(ROOT/'outputs/experiment_metrics.csv',index=False)
    connection.close()
    results=[]; curves=[]; uncertainty=[]
    rng=np.random.default_rng(SEED+1)
    for corridor,g in d.groupby('corridor'):
        train=g[g.split=='train']; valid=g[g.split=='validation']; b=fit(train)
        pred=expit(design(valid)@b)
        population=train[train.arm=='current'].copy()
        best,candidates=optimize(population,b)
        # Elasticity wrt total effective price: d log p / d log price.
        elasticity=float(np.mean(b[1] * population.price_pct * (1-expit(design(population)@b))))
        boot=[]
        for i in range(80):
            sample=train.iloc[rng.integers(0,len(train),len(train))]
            bb=fit(sample); boot.append(bb[1])
        lo,hi=np.quantile(boot,[.025,.975])
        # Validation contains randomized observations; report observed means at the fixed recommendation.
        selected_arm={.8:'low',1.:'current',1.2:'high'}[best[0]]
        v=valid[valid.arm==selected_arm]
        results.append({'corridor':corridor,'price_slope':float(b[1]),'slope_ci_low':float(lo),
                        'slope_ci_high':float(hi),'average_price_elasticity':elasticity,
                        'recommended_multiplier':best[0],'predicted_conversion':best[1],
                        'predicted_contribution_per_quote_usd':best[2],
                        'validation_brier':float(np.mean((pred-valid.converted)**2)),
                        'validation_selected_arm_quotes':len(v),
                        'validation_selected_arm_conversion':float(v.converted.mean()),
                        'validation_selected_arm_contribution_usd':float(v.contribution_usd.mean())})
        for mult,p,cm in candidates: curves.append({'corridor':corridor,'multiplier':mult,'conversion':p,'contribution':cm})
        # Coefficient bootstrap CI is uncertainty conditional on this synthetic design, not recommendation regret.
        uncertainty.append((corridor,lo,hi))
    pd.DataFrame(results).to_csv(ROOT/'outputs/pricing_recommendations.csv',index=False)
    curves=pd.DataFrame(curves); curves.to_csv(ROOT/'outputs/price_scenarios.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for corridor,g in curves.groupby('corridor'):
        axes[0].plot(g.multiplier,g.conversion,marker='o',label=corridor)
        axes[1].plot(g.multiplier,g.contribution,marker='o',label=corridor)
    axes[0].set(xlabel='Price multiplier vs current',ylabel='Predicted conversion')
    axes[1].set(xlabel='Price multiplier vs current',ylabel='Predicted contribution / quote (USD)')
    axes[0].legend(); fig.suptitle('Synthetic remittance price experiment'); fig.savefig(ROOT/'outputs/pricing_tradeoff.png',dpi=160); plt.close(fig)
    summary={'seed':SEED,'quotes':len(d),'recommendations':results,
             'scope':'Synthetic simulation only; not an employer result',
             'guardrail':'Predicted conversion no more than 3 percentage points below current within each corridor',
             'limitations':['Fee and spread co-vary; separate fee and FX sensitivities are not identifiable.',
                            'One quote per user, short-term conversion only; no retention/LTV claim.',
                            'Model assumes logit linearity in total price percent and fixed variable costs.',
                            'Bootstrap CIs are pointwise slope CIs, not simultaneous decision guarantees.',
                            'No claim of optimized policy uplift without a prospective confirmatory test.']}
    (ROOT/'outputs/summary.json').write_text(json.dumps(summary,indent=2))
    lines=['# Synthetic pricing decision memo','',f'{len(d):,} independent quotes; train/validation split fixed before analysis.','',
           '| Corridor | Selected multiplier | Price elasticity | Predicted CM / quote | Held-out selected-arm CM / quote |',
           '|---|---:|---:|---:|---:|']
    for r in results:
        lines.append(f"| {r['corridor']} | {r['recommended_multiplier']:.1f} | {r['average_price_elasticity']:.2f} | ${r['predicted_contribution_per_quote_usd']:.2f} | ${r['validation_selected_arm_contribution_usd']:.2f} |")
    lines+=['','The recommendation maximizes immediate contribution within observed price support, subject to the model conversion guardrail. This is a hypothesis for a follow-up test, not a production rollout decision.','',
            'Next experiment: randomize eligible customers between current and selected total price; freeze allocation and exclusions, size on contribution variance, cluster on customer if repeated quotes exist, and monitor conversion, complaints and 30-day retention. No horizon or LTV extrapolation is justified by this dataset.']
    (ROOT/'outputs/decision_memo.md').write_text('\n'.join(lines)+'\n')
    print('Pricing analysis complete:',len(d),'synthetic quotes')

if __name__=='__main__': main()
