import gzip
import hashlib
import json
import zipfile
from scripts.verify_bundle import verify


def bundle(tmp_path, *, recompress=False, omit_pdf=False, secret=False):
    sha=lambda b:hashlib.sha256(b).hexdigest()
    original=gzip.compress(b'{"message":"synthetic-secret-123456"}\n',mtime=0)
    exported=gzip.compress(gzip.decompress(original),mtime=1) if recompress else original
    pdf=b'%PDF-1.4\nfigure';source=b'# collected source\n'
    files={'results/runs/r1/actions.jsonl.gz':exported,
        'results/runs/r1/raw-manifest.json':json.dumps({'hash_scheme':'sha256-bytes','files':{'actions.jsonl.gz':sha(original)}}).encode(),
        'results/manifest.json':json.dumps({'source_sha256':{'testbed\\client.py':sha(source)}}).encode(),
        'source/testbed/client.py':source,
        'results/figures/figure-manifest.json':json.dumps({'exports':{'plot.pdf':sha(pdf)}}).encode(),
        'EXPORT_PROVENANCE.json':json.dumps({'batch_quality':{'passed':False}}).encode()}
    if not omit_pdf:files['results/figures/plot.pdf']=pdf
    path=tmp_path/'bundle.zip'
    with zipfile.ZipFile(path,'w') as archive:
        for name,data in files.items():archive.writestr(name,data)
        archive.writestr('SHA256SUMS.json',json.dumps({k:sha(v) for k,v in files.items()}))
    return verify(path,[b'synthetic-secret-123456'] if secret else [])


def test_valid_package_does_not_infer_scientific_quality(tmp_path):
    result=bundle(tmp_path)
    assert result['integrity_passed'] and result['original_raw_members_checked']==1
    assert result['figure_table_exports_checked']==1 and result['source_files_checked']==1
    assert result['batch_quality']['passed'] is False and not result['scientific_acceptance_inferred']


def test_export_checksums_cannot_hide_recompressed_raw_seal(tmp_path):
    result=bundle(tmp_path,recompress=True)
    assert not result['integrity_passed']
    assert any('Raw seal original hash mismatch' in e for e in result['errors'])


def test_missing_manifest_bound_pdf_fails(tmp_path):
    assert not bundle(tmp_path,omit_pdf=True)['integrity_passed']


def test_decoded_gzip_secret_is_detected_without_value_in_report(tmp_path):
    result=bundle(tmp_path,secret=True)
    assert not result['integrity_passed'] and result['secret_member_paths']
    assert 'synthetic-secret-123456' not in json.dumps(result)


def test_unlisted_members_and_intentional_metadata_are_also_secret_scanned(tmp_path):
    bundle(tmp_path)
    path=tmp_path/'bundle.zip'
    with zipfile.ZipFile(path,'a') as archive:
        archive.writestr('unexpected-unlisted.txt',b'synthetic-secret-123456')
        archive.writestr('BUNDLE_README.txt',b'synthetic-secret-123456')
    result=verify(path,[b'synthetic-secret-123456'])
    assert not result['integrity_passed']
    assert any('absent from export checksum manifest' in error for error in result['errors'])
    assert result['secret_member_paths']==['BUNDLE_README.txt','results/runs/r1/actions.jsonl.gz','unexpected-unlisted.txt']
    assert 'synthetic-secret-123456' not in json.dumps(result)


def test_secret_in_unlisted_member_name_is_not_echoed_in_diagnostics(tmp_path):
    bundle(tmp_path)
    path=tmp_path/'bundle.zip'
    with zipfile.ZipFile(path,'a') as archive:
        archive.writestr('synthetic-secret-123456.txt',b'ordinary content')
    result=verify(path,[b'synthetic-secret-123456'])
    assert not result['integrity_passed']
    assert 'synthetic-secret-123456' not in json.dumps(result)
