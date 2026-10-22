"""Analyze measured summaries: python -m analysis.run RESULTS --output OUTPUT.

Every output carries source file hashes. Raw files are opened read-only. Mixed
agents, pilot/full runs, scenarios, lifetimes and revocation modes never pool.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import html
import json
import math
from pathlib import Path
import statistics

from .statistics import (bootstrap_difference, cluster_ratio, describe, fisher_exact, holm,
                         kaplan_meier, logrank, mann_whitney, mcnemar, wilcoxon, wilson)

CONDITIONS = ("C0", "C1", "C2", "C2-noWF", "C2-RS")
PAIRS = (("C0","C1"),("C1","C2"),("C0","C2"),("C2","C2-noWF"),("C2","C2-RS"))
STRATA = ("mode", "phase", "model", "model_snapshot", "scenario", "ttl_seconds",
          "revocation_mode", "approval_dependent")
TIME_METRICS = ("run_median_latency_ms", "run_median_authorization_ms", "reachable_authority",
                "cumulative_ratio", "approval_count", "approval_delay_ms",
                "revocation_propagation_ms", "revocation_to_denial_ms", "cost_usd")
RATE_METRICS = ("unauthorized_outcome", "injection_followed", "task_completed", "attribution_correct")
INFRA_FAILURES = {"infrastructure_error", "infra_error", "infrastructure_failure", "crashed"}
PENDING_STATUSES = {"running", "pending", "queued"}


def finite_number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def normalize(raw):
    run = dict(raw)
    metadata = run.get("metadata") or {}
    for field in ("model","model_snapshot","approval_dependent"):
        if field not in run:
            run[field] = metadata.get(field)
    for field in ("mode","phase","model","model_snapshot"):
        if run.get(field) is None:
            run[field] = "Not reported"
    for source,target in (("latencies_ms","run_median_latency_ms"),
                          ("authorization_ms","run_median_authorization_ms")):
        values = run.get(source)
        if isinstance(values,list):
            values = [x for x in values if finite_number(x)]
            run[target] = statistics.median(values) if values else None
        elif finite_number(values):
            run[target] = values
        else:
            run[target] = None
    if run.get("scenario") == "S1" and run.get("task_outcome") is not None:
        run["task_completed"] = run["task_outcome"] == "completed"
    else:
        run["task_completed"] = None
    true,predicted = run.get("attribution_true"),run.get("attribution_predicted")
    run["attribution_correct"] = true == predicted if true is not None and predicted is not None else None
    if run.get("event_observed") is False:
        # Censored waits are not completed revocation-to-denial measurements.
        run["revocation_to_denial_ms"] = None
    return run


def survival_observation(run):
    """Use first-denial endpoint, not nominal expiry or last-success lower bound."""
    event = run.get("event_observed")
    if not isinstance(event,bool):
        return None
    duration = run.get("first_denial_seconds") if event else run.get("observation_window_seconds")
    if duration is None:
        # A harness may supply a separate explicitly defined KM endpoint.
        duration = run.get("survival_duration_seconds")
    if not finite_number(duration) or duration < 0:
        return None
    return duration,event


def load_runs(root):
    paths = sorted(Path(root).rglob("summary.json"))
    records,sources,errors = [],[],[]
    for path in paths:
        try:
            data = path.read_bytes()
            raw = json.loads(data)
            if not isinstance(raw,dict) or "condition" not in raw or "scenario" not in raw:
                continue
            run = normalize(raw)
            run["source_path"] = str(path.resolve())
            run["source_sha256"] = hashlib.sha256(data).hexdigest()
            records.append(run)
            sources.append({"path":str(path.resolve()),"sha256":run["source_sha256"]})
        except (OSError,ValueError,TypeError) as exc:
            errors.append({"path":str(path),"error":str(exc)})
    return records,sources,errors


def key(run):
    return tuple(run.get(field) for field in STRATA)


def rate(run_values):
    values = [v for v in run_values if isinstance(v,bool)]
    return wilson(sum(values),len(values))


def summarize(records):
    groups = defaultdict(list)
    for run in records:
        groups[(key(run),run["condition"])].append(run)
    output,confusion,survival = [],[],[]
    for (stratum,condition),runs in sorted(groups.items(),key=lambda x: str(x[0])):
        labels = dict(zip(STRATA,stratum),condition=condition)
        valid = [r for r in runs if r.get("status") not in INFRA_FAILURES|PENDING_STATUSES]
        row = dict(labels, runs=len(runs), analyzed_runs=len(valid),
                   infrastructure_failures=sum(r.get("status") in INFRA_FAILURES for r in runs),
                   pending_runs=sum(r.get("status") in PENDING_STATUSES for r in runs),
                   status_counts=dict(Counter(r.get("status","Not reported") for r in runs)),
                   task_outcome_counts=dict(Counter(r.get("task_outcome","Not measured") for r in valid)))
        for metric in RATE_METRICS:
            row[metric] = rate([r.get(metric) for r in valid])
        for metric in TIME_METRICS:
            row[metric] = describe([r.get(metric) for r in valid if finite_number(r.get(metric))])
        for numerator,denominator,label in (("harmful_executed","harmful_attempts","harmful_action_success"),
                                             ("audit_complete","audit_total","audit_completeness"),
                                             ("tamper_detected","tamper_total","tamper_detection")):
            measured = [r for r in valid if finite_number(r.get(numerator)) and finite_number(r.get(denominator))]
            row[label] = cluster_ratio([(r[numerator],r[denominator]) for r in measured])
        # Exposure values are listed as interval-censored observations. No average.
        row["exposure_observations"] = [
            {"run_id":r.get("run_id"),"last_success_seconds":r.get("last_success_seconds",r.get("exposure_seconds")),
             "first_denial_seconds":r.get("first_denial_seconds"),
             "right_censored":not r["event_observed"],"observation_window_seconds":r.get("observation_window_seconds"),
             "nominal_remaining_seconds":r.get("nominal_remaining_seconds")}
            for r in valid if isinstance(r.get("event_observed"),bool)]
        observations = [o for r in valid if (o := survival_observation(r)) is not None]
        for point in kaplan_meier(observations) if observations else []:
            survival.append(dict(labels,**point))
        row["survival_measured_runs"] = len(observations)
        row["still_valid_at_end"] = rate([not o[1] for o in observations])
        for (true,predicted),count in Counter((r.get("attribution_true"),r.get("attribution_predicted"))
                                            for r in valid if r.get("attribution_true") is not None
                                            and r.get("attribution_predicted") is not None).items():
            confusion.append(dict(labels,true=true,predicted=predicted,count=count))
        output.append(row)
    return output,confusion,survival


def paired_samples(left,right,metric):
    """No invented pairing. Duplicate pair IDs or differing fixtures invalidate it."""
    def index(runs):
        indexed = {}
        for r in runs:
            if r.get("pair_id") is None or r.get(metric) is None:
                continue
            k = (r["pair_id"],r.get("seed"),r.get("payload_id"))
            if k in indexed:
                return None
            indexed[k] = r[metric]
        return indexed
    a,b = index(left),index(right)
    if a and b and a.keys() == b.keys():
        order = sorted(a,key=str)
        return [a[k] for k in order],[b[k] for k in order]
    return None


def compare(records,bootstrap_samples=2000):
    strata = defaultdict(lambda:defaultdict(list))
    for r in records:
        if r.get("status") not in INFRA_FAILURES|PENDING_STATUSES:
            strata[key(r)][r["condition"]].append(r)
    output = []
    for stratum,groups in sorted(strata.items(),key=lambda x:str(x[0])):
        labels = dict(zip(STRATA,stratum))
        for left_name,right_name in PAIRS:
            # Retain placeholders to preserve the planned family size even when a
            # condition is absent. Cut-down pairs only exist on S2/S5.
            if right_name in ("C2-noWF","C2-RS") and labels["scenario"] not in ("S2","S5"):
                continue
            left,right = groups[left_name],groups[right_name]
            for metric in RATE_METRICS+TIME_METRICS:
                binary = metric in RATE_METRICS
                valid = lambda x: isinstance(x,bool) if binary else finite_number(x)
                a,b = [r[metric] for r in left if valid(r.get(metric))],[r[metric] for r in right if valid(r.get(metric))]
                row = dict(labels,left=left_name,right=right_name,metric=metric,n_left=len(a),n_right=len(b))
                paired = paired_samples(left,right,metric)
                if not a or not b:
                    row.update(p_value=None,method="Not measured",paired=False,effect=None)
                else:
                    if paired:
                        a,b = paired
                    row["paired"] = bool(paired)
                    if binary:
                        test = mcnemar(a,b) if paired else {"p_value":fisher_exact(sum(a),len(a)-sum(a),sum(b),len(b)-sum(b)),"method":"Fisher exact (two-sided)"}
                    else:
                        test = wilcoxon(a,b) if paired else mann_whitney(a,b)
                    row.update(test)
                    row["effect"] = bootstrap_difference(a,b,paired=bool(paired),statistic="mean" if binary else "median",samples=bootstrap_samples)
                output.append(row)
            a = [o for r in left if (o:=survival_observation(r)) is not None]
            b = [o for r in right if (o:=survival_observation(r)) is not None]
            for metric in ("survival_logrank","still_valid_at_end"):
                row = dict(labels,left=left_name,right=right_name,metric=metric,n_left=len(a),n_right=len(b),paired=False,effect=None)
                if not a or not b:
                    row.update(p_value=None,method="Not measured")
                elif metric == "survival_logrank":
                    row.update(logrank(a,b))
                else:
                    ca,cb = sum(not e for t,e in a),sum(not e for t,e in b)
                    row.update(p_value=fisher_exact(ca,len(a)-ca,cb,len(b)-cb),method="Fisher exact, still valid at window end")
                output.append(row)
    # H1b contrasts immediate revocation with waiting for expiry within the same
    # condition/lifetime. Ordinary denial times are omitted for censored waits.
    revocation_groups = defaultdict(lambda:defaultdict(list))
    for run in records:
        if run.get("scenario") != "S4" or run.get("status") in INFRA_FAILURES|PENDING_STATUSES:
            continue
        rev_mode = run.get("revocation_mode")
        canonical = {"now":"now","revoke_now":"now","expiry":"expiry","wait_expiry":"expiry"}.get(rev_mode)
        if canonical:
            group_key=tuple(run.get(x) for x in STRATA if x != "revocation_mode")+(run["condition"],)
            revocation_groups[group_key][canonical].append(run)
    for group_key,groups in revocation_groups.items():
        fields=tuple(x for x in STRATA if x != "revocation_mode")+("condition",)
        labels=dict(zip(fields,group_key));condition=labels.pop("condition")
        labels["revocation_mode"]="now-vs-expiry"
        left,right=groups["now"],groups["expiry"]
        for metric in ("revocation_to_denial_ms","survival_logrank","still_valid_at_end"):
            row=dict(labels,left=condition+":now",right=condition+":expiry",metric=metric,paired=False,effect=None)
            if metric == "revocation_to_denial_ms":
                a=[r[metric] for r in left if finite_number(r.get(metric))]
                b=[r[metric] for r in right if finite_number(r.get(metric))]
                row.update(n_left=len(a),n_right=len(b))
                if a and b:
                    paired=paired_samples(left,right,metric)
                    if paired:a,b=paired
                    row["paired"]=bool(paired)
                    row.update(wilcoxon(a,b) if paired else mann_whitney(a,b))
                    row["effect"]=bootstrap_difference(a,b,paired=bool(paired),samples=bootstrap_samples)
                else:row.update(p_value=None,method="Not measured; censored waits cannot enter ordinary time tests")
            else:
                a=[o for r in left if (o:=survival_observation(r)) is not None]
                b=[o for r in right if (o:=survival_observation(r)) is not None]
                row.update(n_left=len(a),n_right=len(b))
                if not a or not b:row.update(p_value=None,method="Not measured")
                elif metric == "survival_logrank":row.update(logrank(a,b))
                else:
                    ca,cb=sum(not e for t,e in a),sum(not e for t,e in b)
                    row.update(p_value=fisher_exact(ca,len(a)-ca,cb,len(b)-cb),method="Fisher exact, still valid at window end")
            output.append(row)
    # One conservative confirmatory family contains all planned contrasts and
    # metrics in each independently analyzed agent/phase/model partition.
    families=defaultdict(list)
    for i,row in enumerate(output):
        families[tuple(row[x] for x in ("mode","phase","model","model_snapshot"))].append(i)
    for family,indices in families.items():
        adjusted=holm([output[i]["p_value"] for i in indices])
        for i,p in zip(indices,adjusted):
            output[i]["p_holm"]=p
            output[i]["family_size"]=len(indices)
            output[i]["interpretation"]="Exploratory until frozen full-run manifest and practical threshold are verified"
    return output


def flatten(value,prefix=""):
    result={}
    for k,v in value.items():
        name=f"{prefix}.{k}" if prefix else k
        if isinstance(v,dict): result.update(flatten(v,name))
        elif isinstance(v,list): result[name]=json.dumps(v,ensure_ascii=False)
        else: result[name]=v
    return result


def write_csv(path,rows):
    rows=[flatten(r) for r in rows]
    fields=list(dict.fromkeys(k for r in rows for k in r)) or ["status"]
    with path.open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def plot_rates(path,rows):
    """Standalone SVG with Wilson intervals, explicit strata and mode labels."""
    measured=[r for r in rows if r["unauthorized_outcome"]["n"]]
    height=max(160,100+len(measured)*38)
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<g font-family="Arial,sans-serif" font-size="12" fill="#152238">',
           '<text x="24" y="28" font-size="18">Fig. 2. Unauthorized outcomes measured in this testbed (authors’ work)</text>',
           '<text x="24" y="49">Run proportions and Wilson 95% intervals. Scripted checks are separate from real-LLM findings.</text>']
    if not measured:
        parts.append('<text x="24" y="90">Not measured. No eligible attack-run outcomes are present.</text>')
    for i,row in enumerate(measured):
        y=85+i*38;r=row["unauthorized_outcome"]
        label=" | ".join(str(row.get(x,"")) for x in ("mode","phase","scenario","condition","ttl_seconds","revocation_mode","approval_dependent"))
        parts.append(f'<text x="24" y="{y+4}">{html.escape(label)}</text>')
        x=lambda p:760+280*p
        parts.extend([f'<line x1="{x(r["ci_low"])}" y1="{y}" x2="{x(r["ci_high"])}" y2="{y}" stroke="#2458a6" stroke-width="3"/>',
                      f'<circle cx="{x(r["rate"])}" cy="{y}" r="5" fill="#2458a6"/>',
                      f'<text x="1060" y="{y+4}">{r["successes"]}/{r["n"]} ({r["rate"]:.1%})</text>'])
    parts.extend(['</g></svg>']);path.write_text('\n'.join(parts),encoding="utf-8")


def plot_survival(path,rows):
    groups=defaultdict(list)
    for row in rows:
        groups[tuple(row.get(x) for x in STRATA+("condition",))].append(row)
    height=max(180,110+len(groups)*34)
    p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}"><rect width="100%" height="100%" fill="white"/>',
       '<g font-family="Arial,sans-serif" font-size="12" fill="#152238"><text x="20" y="26" font-size="18">Fig. 3. Replay validity survival (authors’ work)</text>',
       '<text x="20" y="48">Step curves use first observed denial; probe intervals bound timing precision. Censor marks are vertical ticks.</text>']
    if not groups:p.append('<text x="20" y="90">Not measured. No observed or censored replay endpoints are present.</text>')
    max_time=max((r["time"] for r in rows),default=1) or 1
    for i,(labels,curve) in enumerate(groups.items()):
        y=80+i*34
        label=" | ".join(str(x) for x in labels)
        p.append(f'<text x="20" y="{y+12}">{html.escape(label)}</text>')
        points=[];last=1.
        for point in curve:
            x=760+280*point["time"]/max_time
            points.extend([f'{x},{y+24*(1-last)}',f'{x},{y+24*(1-point["survival"])}'])
            last=point["survival"]
            if point["censored"]:p.append(f'<line x1="{x}" x2="{x}" y1="{y+24*(1-last)-4}" y2="{y+24*(1-last)+4}" stroke="#b54921"/>')
        p.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="#2458a6" stroke-width="2"/>')
    p.extend([f'<text x="760" y="{height-12}">0 seconds</text><text x="1000" y="{height-12}">{max_time:.1f} seconds</text>','</g></svg>'])
    path.write_text('\n'.join(p),encoding="utf-8")


def analyze(root,output=None,bootstrap_samples=2000):
    root=Path(root)
    output=Path(output) if output else root/"analysis"
    if root.resolve()==output.resolve():
        raise ValueError("Analysis output must not overwrite the raw results directory")
    output.mkdir(parents=True,exist_ok=True)
    records,sources,errors=load_runs(root)
    tables,confusion,survival=summarize(records)
    comparisons=compare(records,bootstrap_samples)
    report={"schema_version":1,"context":"Measured in this testbed only; no production-enterprise inference",
            "runs":len(records),"load_errors":errors,"sources":sources,"tables":tables,
            "comparisons":comparisons,"attribution_confusion":confusion,"survival":survival,
            "censoring":"First-denial KM endpoints; last-success exposure is a lower bound. No average of censored times.",
            "bootstrap_seed":603,"bootstrap_samples":bootstrap_samples,
            "hypothesis_support":"Not adjudicated automatically: verify frozen manifest, full-run completion and practical thresholds."}
    (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    for name,rows in (("metrics",tables),("comparisons",comparisons),("attribution-confusion",confusion),("survival",survival),("source-manifest",sources)):
        write_csv(output/f"{name}.csv",rows)
    plot_rates(output/"unauthorized-outcomes.svg",tables)
    plot_survival(output/"replay-survival.svg",survival)
    lines=["# Results measured in this testbed", "",f"Preserved input runs: {len(records)}. Read errors: {len(errors)}.","",
           "Table I. Run outcomes with Wilson 95% intervals (authors’ work). Each row is a separate experimental stratum.","",
           "| Agent mode | Phase | Scenario | Condition | Lifetime s | Revocation | Outcomes/n | Wilson interval |",
           "| --- | --- | --- | --- | ---: | --- | ---: | --- |"]
    for r in tables:
        v=r["unauthorized_outcome"]
        interval=f'{v["ci_low"]:.1%}–{v["ci_high"]:.1%}' if v["n"] else "Not measured"
        lines.append(f'| {r["mode"]} | {r["phase"]} | {r["scenario"]} | {r["condition"]} | {r["ttl_seconds"]} | {r["revocation_mode"]} | {v["successes"]}/{v["n"]} | {interval} |')
    lines.extend(["","Inference is restricted to this single-machine testbed, these payloads and the recorded model/date. Configuration-guaranteed denials and tamper checks are sanity checks. Scripted runs do not establish real-LLM findings.","",
                  "Comparisons are in comparisons.csv, including missing contrasts, exact test names, right-minus-left effects, deterministic bootstrap intervals and Holm-adjusted p-values. No hypothesis is declared supported until the frozen design and minimum practical difference are verified.","",
                  "Replay times remain censored where validity outlasted observation. No mean or ordinary median is computed for those times. Kaplan–Meier curves use first observed denial and must be interpreted at the recorded probe resolution."])
    (output/"results.md").write_text('\n'.join(lines)+'\n',encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results",type=Path)
    parser.add_argument("--output",type=Path)
    parser.add_argument("--bootstrap-samples",type=int,default=2000)
    args=parser.parse_args()
    if args.bootstrap_samples < 100:
        parser.error("Use at least 100 bootstrap resamples")
    report=analyze(args.results,args.output,args.bootstrap_samples)
    print(json.dumps({"runs":report["runs"],"load_errors":len(report["load_errors"]),"output":str(args.output or args.results/'analysis')}))


if __name__ == "__main__":main()
