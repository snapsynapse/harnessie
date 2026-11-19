"""Offline assurance-gap probes; no providers or external writes."""
import json, subprocess, tempfile
from pathlib import Path
from harness.evals import run_scenario
from harness.schema import validate_data
from harness.routing import Budget
from harness.blast_radius import PhaseBlastRadius, RunBlastRadius, BlastRadiusLimits
from harness.events import EventLog

def main():
    result = run_scenario({'id':'audit_unknown_assertion','kind':'loop','script':[{'tool':'task_complete','args':{'report':'done'}}], 'expect_stop':'complete','expect_impossible_security_property':False})
    print(json.dumps({'probe':'unknown_eval_assertion','silently_passed':result.passed}))
    config={'tiers':{'mid':{'provider':'mock','model_id':'mock'}},'routing':{'default':{'tier':'mid','effort':'medium'}},'budget':{'max_usd':float('nan'),'max_tokens':100000}}
    problems=validate_data(config,'models','synthetic')
    budget=Budget(max_usd=float('nan'),max_tokens=100000)
    budget.add_spend(1000000000,1)
    print(json.dumps({'probe':'nonfinite_budget','schema_accepted':not problems,'budget_not_exhausted':not budget.exhausted}))
    source=Path('scripts/check-search.mjs').read_text()
    start=source.index('function decode(value)')
    end=source.index('\n}',start)+2
    output=subprocess.check_output(['node','-e',source[start:end]+'; process.stdout.write(decode("&amp;lt;tag&amp;gt;"));'],text=True)
    print(json.dumps({'probe':'xml_double_decode','nested_escape_decoded_twice':output=='<tag>'}))
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw);ws=root/'workspace';ws.mkdir();log=EventLog(root/'run',echo=False)
        meter=PhaseBlastRadius('p','p',ws,BlastRadiusLimits(max_files_touched=0,max_edits_applied=0,max_bytes_written=0),RunBlastRadius(BlastRadiusLimits()),log)
        meter.apply('mkdir',lambda:(ws/'newdir').mkdir())
        print(json.dumps({'probe':'directory_accounting_scope','empty_directory_change_allowed_at_zero_limits':(ws/'newdir').exists(),'edits_accounted':meter.edits}))
        log.close()
if __name__=='__main__':main()
