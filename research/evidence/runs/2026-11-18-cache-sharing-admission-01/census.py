import hashlib
import json
from pathlib import Path


RUN = Path(__file__).resolve().parent
ROOT = RUN.parents[3]
baseline = ROOT / 'research/evidence/runs/2026-11-18-cache-transaction-fixture-01/baseline-dentry.rs'
source = baseline.read_text().splitlines()
original = '\n'.join(source[830:845] + source[932:949])
proposal = (RUN / 'proposal.rs').read_text()


def counts(text):
    return {
        'nonblank_lines': sum(bool(line.strip()) for line in text.splitlines()),
        'method_declarations': text.count('fn '),
        'children_lock_sites': text.count('self.0.children.lock()'),
        'live_upgrade_sites': text.count('entry.upgrade().map(Dentry)'),
        'weak_insert_sites': text.count('Arc::downgrade('),
        'retention_call_sites': text.count('super_block.cache_dentry('),
    }


proposal_methods = '\n'.join(proposal.splitlines()[1:-1])
report = {
    'baseline_sha256': hashlib.sha256(baseline.read_bytes()).hexdigest(),
    'proposal_sha256': hashlib.sha256((RUN / 'proposal.rs').read_bytes()).hexdigest(),
    'baseline_ranges_1based_inclusive': [[831, 845], [933, 949]],
    'original': counts(original),
    'proposal_excluding_impl_shell': counts(proposal_methods),
    'limits': 'Literal source inventory, not AST/type proof, quality score, machine-code cost or allocation measurement',
}
print(json.dumps(report, indent=2))
