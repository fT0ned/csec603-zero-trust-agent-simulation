"""Small transparent statistical primitives; no third-party runtime is required.

Rank tests use exact enumeration when feasible and otherwise a documented normal
approximation with tie correction. Bootstrap uncertainty resamples runs, never
individual calls. Censored observations are never fed to ordinary time summaries.
"""
from __future__ import annotations

from collections import Counter
import itertools
import math
import random
import statistics


def quantile(values, p):
    values = sorted(values)
    if not values:
        return None
    i = (len(values) - 1) * p
    low = math.floor(i)
    high = math.ceil(i)
    return values[low] + (values[high] - values[low]) * (i - low)


def describe(values):
    values = [float(x) for x in values if x is not None and math.isfinite(float(x))]
    return {"n": len(values), "median": quantile(values, .5), "q1": quantile(values, .25),
            "q3": quantile(values, .75), "p95": quantile(values, .95)}


def wilson(successes, n, z=1.959963984540054):
    if n == 0:
        return {"successes": 0, "n": 0, "rate": None, "ci_low": None, "ci_high": None}
    if not 0 <= successes <= n:
        raise ValueError("Invalid binomial count")
    p = successes / n
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n))/denominator
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/denominator
    return {"successes": successes, "n": n, "rate": p,
            "ci_low": max(0., center-half), "ci_high": min(1., center+half)}


def fisher_exact(a, b, c, d):
    """Two-sided fixed-margin Fisher p-value (probability ordering)."""
    if min(a, b, c, d) < 0:
        raise ValueError("Negative contingency count")
    n = a+b+c+d
    if n == 0:
        return None
    row, col = a+b, a+c
    denom = math.comb(n, row)
    probability = lambda x: math.comb(col, x)*math.comb(n-col, row-x)/denom
    observed = probability(a)
    return min(1., sum(probability(x) for x in range(max(0, row-(n-col)), min(row, col)+1)
                       if probability(x) <= observed*(1+1e-12)))


def mcnemar(left, right):
    if len(left) != len(right) or not left:
        raise ValueError("Matched nonempty samples required")
    b = sum(bool(a) and not bool(b) for a, b in zip(left, right))
    c = sum(not bool(a) and bool(b) for a, b in zip(left, right))
    n = b+c
    p = 1. if n == 0 else min(1., 2*sum(math.comb(n, k) for k in range(min(b,c)+1))/2**n)
    return {"p_value": p, "discordant_left": b, "discordant_right": c,
            "method": "exact McNemar (two-sided binomial)"}


def ranks(values):
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.] * len(values)
    start = 0
    while start < len(order):
        end = start+1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start+1+end)/2
        for i in order[start:end]:
            result[i] = rank
        start = end
    return result


def wilcoxon(left, right):
    if len(left) != len(right) or not left:
        raise ValueError("Matched nonempty samples required")
    differences = [a-b for a,b in zip(left,right) if a != b]
    n = len(differences)
    if not n:
        return {"p_value": 1., "statistic": 0., "method": "Wilcoxon; all differences zero"}
    r = ranks([abs(x) for x in differences])
    total = sum(r)
    positive = sum(rank for rank, d in zip(r, differences) if d > 0)
    observed = abs(positive-total/2)
    if n <= 20:
        extreme = sum(abs(sum(v for v,b in zip(r,bits) if b)-total/2) >= observed-1e-12
                      for bits in itertools.product((0,1), repeat=n))
        p = extreme/2**n
        method = "exact Wilcoxon sign permutation; zeros discarded"
    else:
        variance = sum(x*x for x in r)/4
        z = max(0., observed-.5)/math.sqrt(variance)
        p = math.erfc(z/math.sqrt(2))
        method = "Wilcoxon normal approximation; ties corrected; continuity correction"
    return {"p_value": p, "statistic": min(positive,total-positive), "method": method}


def mann_whitney(left, right):
    if not left or not right:
        return {"p_value": None, "statistic": None, "method": "Not measured"}
    n1, n2 = len(left), len(right)
    combined = list(left)+list(right)
    r = ranks(combined)
    u = sum(r[:n1])-n1*(n1+1)/2
    observed = abs(u-n1*n2/2)
    possibilities = math.comb(n1+n2,n1)
    if possibilities <= 100000:
        extreme = sum(abs(sum(r[i] for i in idx)-n1*(n1+1)/2-n1*n2/2) >= observed-1e-12
                      for idx in itertools.combinations(range(n1+n2),n1))
        p = extreme/possibilities
        method = "exact Mann-Whitney label permutation (ties retained)"
    else:
        n = n1+n2
        correction = sum(t**3-t for t in Counter(combined).values())/(n*(n-1))
        variance = n1*n2/12*((n+1)-correction)
        p = 1. if variance == 0 else math.erfc(max(0., observed-.5)/math.sqrt(2*variance))
        method = "Mann-Whitney normal approximation; ties corrected; continuity correction"
    return {"p_value": p, "statistic": u, "method": method}


def bootstrap_difference(left, right, paired=False, statistic="median", seed=603, samples=2000):
    """Right minus left. Percentile interval; observational unit is one run."""
    if not left or not right:
        return {"estimate": None, "ci_low": None, "ci_high": None}
    if paired and len(left) != len(right):
        raise ValueError("Unequal paired samples")
    fn = statistics.mean if statistic == "mean" else statistics.median
    rng = random.Random(seed)
    differences = []
    for _ in range(samples):
        if paired:
            idx = [rng.randrange(len(left)) for _ in left]
            a,b = [left[i] for i in idx], [right[i] for i in idx]
        else:
            a,b = rng.choices(left,k=len(left)), rng.choices(right,k=len(right))
        differences.append(fn(b)-fn(a))
    return {"estimate": fn(right)-fn(left), "ci_low": quantile(differences,.025),
            "ci_high": quantile(differences,.975), "bootstrap_samples": samples, "seed": seed,
            "interval": "percentile bootstrap; right minus left"}


def cluster_ratio(counts,seed=603,samples=2000):
    """Ratio of aggregate counts with run-cluster percentile uncertainty."""
    n=sum(total for successes,total in counts)
    k=sum(successes for successes,total in counts)
    result={"numerator":k,"denominator":n,"rate":k/n if n else None,
            "ci_low":None,"ci_high":None,"measured_runs":len(counts),
            "uncertainty":"Run-cluster percentile bootstrap; degenerate samples do not establish zero risk"}
    if not n:return result
    rng=random.Random(seed);ratios=[]
    for _ in range(samples):
        sample=rng.choices(counts,k=len(counts))
        denominator=sum(total for successes,total in sample)
        if denominator:ratios.append(sum(successes for successes,total in sample)/denominator)
    result.update(ci_low=quantile(ratios,.025),ci_high=quantile(ratios,.975),
                  bootstrap_samples=samples,seed=seed)
    return result


def holm(p_values):
    """Preserve missing hypotheses in family size (conservative incomplete family)."""
    adjusted = [None]*len(p_values)
    ordered = sorted((p,i) for i,p in enumerate(p_values) if p is not None)
    previous = 0.
    for rank,(p,i) in enumerate(ordered):
        previous = min(1.,max(previous,p*(len(p_values)-rank)))
        adjusted[i] = previous
    return adjusted


def kaplan_meier(observations):
    """(time, observed event) -> curve; event processed before tied censoring."""
    observations = [(float(t),bool(e)) for t,e in observations]
    risk = len(observations)
    survival = 1.
    curve = [{"time": 0., "survival": 1., "at_risk": risk, "events": 0, "censored": 0}]
    for t in sorted(set(t for t,_ in observations)):
        events = sum(t == time and event for time,event in observations)
        censored = sum(t == time and not event for time,event in observations)
        if risk:
            survival *= 1-events/risk
        curve.append({"time": t, "survival": survival, "at_risk": risk,
                      "events": events, "censored": censored})
        risk -= events+censored
    return curve


def logrank(left, right):
    """Two-group log-rank; chi-square(1), no event means no test information."""
    oe,variance = 0.,0.
    for t in sorted({t for t,e in list(left)+list(right) if e}):
        n1,n2 = sum(x >= t for x,e in left),sum(x >= t for x,e in right)
        d1,d2 = sum(x == t and e for x,e in left),sum(x == t and e for x,e in right)
        n,d = n1+n2,d1+d2
        if n:
            oe += d1-d*n1/n
        if n > 1:
            variance += n1*n2*d*(n-d)/(n*n*(n-1))
    if variance == 0:
        return {"p_value": None, "statistic": None, "method": "log-rank; no informative events"}
    statistic = oe*oe/variance
    return {"p_value": math.erfc(math.sqrt(statistic/2)), "statistic": statistic,
            "method": "two-group log-rank chi-square(1); tied events supported"}
