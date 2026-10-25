"""Persist functional evidence, separately from unvalidated research quality."""
import argparse
import hashlib
import io
import json
import platform
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from pfa.assurance import RUNNING_KERNEL
from pfa.service import doctor, probe


def source_manifest():
    paths=[]
    for directory in ('pfa','scripts','tests','static'):
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file()
                     and p.suffix in ('.py','.sh','.html','.js','.css'))
    paths += [ROOT/'fixtures/companies.json',ROOT/'requirements.txt',ROOT/'quality/features.json']
    paths += list((ROOT/'knowledge').glob('*.json'))
    site=ROOT/'sites/personal-financial-analyses'
    for directory in ('app','client','lib','tests','db','drizzle'):
        paths.extend(p for p in (site/directory).rglob('*') if p.is_file()
                     and p.suffix in ('.ts','.tsx','.mjs','.js','.sql','.json')
                     and p.name!='terminal-html.ts')
    paths += [site/p for p in ('package.json','package-lock.json',
              '.openai/hosting.json','scripts/prepare-terminal.mjs','vite.config.ts') if (site/p).is_file()]
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


class EvidenceResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.evidence=[]

    def addSuccess(self,test):
        super().addSuccess(test);self.evidence.append(dict(test=test.id(),result='passed'))

    def addFailure(self,test,err):
        super().addFailure(test,err);self.evidence.append(dict(test=test.id(),result='failed',detail=self._exc_info_to_string(err,test)))

    def addError(self,test,err):
        super().addError(test,err);self.evidence.append(dict(test=test.id(),result='error',detail=self._exc_info_to_string(err,test)))

    def addSkip(self,test,reason):
        super().addSkip(test,reason);self.evidence.append(dict(test=test.id(),result='not_run',reason=reason))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default=str(ROOT/'quality/latest-functional.json'))
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args()
    contract=json.loads((ROOT/'quality/features.json').read_text())
    required_fields=('id','name','status','decision','inputs','output','automated_tests',
                     'failure_modes','implementation_paths','acceptance','next_work','references')
    seen=set()
    for feature in contract['features']:
        if any(key not in feature for key in required_fields) or feature['id'] in seen:
            raise SystemExit('功能合同字段不完整或编号重复')
        seen.add(feature['id'])
        if any(not (ROOT/p).is_file() for p in feature['implementation_paths']):
            raise SystemExit('功能实现/规划位置不存在：'+feature['id'])
        if not feature['failure_modes'] or not feature['references']:
            raise SystemExit('功能缺少失败模式或参考依据：'+feature['id'])
    manifest=source_manifest()
    output=Path(args.output)
    if args.verify_only:
        prior=json.loads(output.read_text())
        matched=prior['source_manifest']==manifest
        live=doctor(args.port) if args.live else None
        health=probe(args.port) if args.live else None
        runtime_matches=bool(health and health.get('kernel_digest')==RUNNING_KERNEL) if args.live else True
        previously_passed=prior.get('functional_passed') is True
        print(json.dumps(dict(source_manifest_matches=matched,previous_functional_passed=previously_passed,
                              runtime_kernel_matches=runtime_matches,live=live or 'not_requested')))
        return 0 if matched and previously_passed and runtime_matches and (not args.live or live['passed']) else 1
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=stream,resultclass=EvidenceResult,verbosity=2).run(suite)
    statuses={t['test']:t['result'] for t in result.evidence}
    feature_checks=[]
    for feature in contract['features']:
        required=feature['automated_tests']
        absent=[name for name in required if name not in statuses]
        checks=bool(required) and not absent and all(statuses.get(name)=='passed' for name in required)
        feature_checks.append(dict(id=feature['id'],implementation_status=feature['status'],
            functional_checks='passed' if checks else 'not_implemented' if not required else 'failed',
            missing_test_ids=absent,research_decision_ready=False,method_review=feature['method_review']))
    package=json.loads((ROOT/'fixtures/companies.json').read_text())
    documents=[]
    for company in package['companies']:
        for doc in company['documents']:
            path=Path(doc['local_path'])
            if not path.is_absolute():path=ROOT/path
            matched=path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==doc['sha256']
            documents.append(dict(issuer=company['id'],title=doc['title'],sha256_match=matched))
    live=doctor(args.port) if args.live else dict(passed=None,reason='not_requested')
    health=probe(args.port) if args.live else None
    runtime_matches=bool(health and health.get('kernel_digest')==RUNNING_KERNEL) if args.live else None
    cloud=subprocess.run(['node','--test','tests/cloud-policy.test.mjs'],cwd=ROOT/'sites/personal-financial-analyses',
                         text=True,capture_output=True)
    passed=(result.wasSuccessful() and not result.skipped
            and all(f['functional_checks']!='failed' for f in feature_checks)
            and all(d['sha256_match'] for d in documents) and cloud.returncode==0
            and (not args.live or live['passed'] and runtime_matches))
    revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,text=True,capture_output=True).stdout.strip()
    dirty=bool(subprocess.run(['git','status','--porcelain'],cwd=ROOT,text=True,capture_output=True).stdout.strip())
    report=dict(run_at=datetime.now(timezone.utc).isoformat(),command=' '.join(sys.argv),
        tested_base_commit=revision,working_tree_dirty=dirty,python=platform.python_version(),
        source_manifest=manifest,kernel_digest=RUNNING_KERNEL,tests_run=result.testsRun,
        test_results=result.evidence,feature_checks=feature_checks,source_checks=documents,
        local_runtime=live,runtime_kernel_matches=runtime_matches,functional_passed=bool(passed),
        cloud_policy_checks=dict(passed=cloud.returncode==0,output=cloud.stdout+cloud.stderr),
        permitted_use='local_evidence_and_illustrative_scenarios',research_decision_ready=False,
        research_quality='not_validated',prediction_calibration='not_evaluated',
        limitations=['测试不等于语义、行业方法或投资效果验收','六家公司及公开题已用于开发，不属于真正盲测',
                     '资料哈希不证明提取、口径、机制和预测正确','持续来源更新、独立专家与前瞻效果尚未验证'])
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(tests=result.testsRun,functional_passed=bool(passed),
                         research_decision_ready=False,output=str(output)),ensure_ascii=False))
    if not passed:print(stream.getvalue())
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
