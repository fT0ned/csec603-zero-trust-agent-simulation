# Publish the extension DOI

The GitHub release is the formal versioned archive prepared by this task. A DOI is not invented, and account login/author and license confirmation remain with the repository owner. `.zenodo.json` and `CITATION.cff` use the public owner handle `fT0ned`; replace it with the intended publication creator names if appropriate. The original repo has no LICENSE file; no license for historical contributors' material has been invented in this task. Verify the intended deposit license before publication.

## GitHub-linked route

1. Open [Zenodo login](https://zenodo.org/login/) and sign in with the GitHub account that owns the repository. Complete GitHub authorization if prompted.
2. Open the profile menu, select **GitHub**, locate `fT0ned/csec603-zero-trust-agent-simulation`, and enable its switch. If the repo is absent, grant Zenodo access in GitHub's application permissions and refresh the Zenodo repository list.
3. In the repository's Zenodo view, select **Create release**, then create/publish the GitHub release from the archive commit. If the task's release was published before linking, use a new archival release tag pointing at that same commit (for example `extension-study-001-doi`); do not move `extension-study-freeze-v1` and do not rerun experiments for a DOI.
4. Wait for processing in Zenodo's GitHub view, then click the record DOI. If processing fails, open the failed release and expand **Errors**. Review creator metadata, version, software type, license, file list and source commit before relying on the deposit.
5. On the record page, verify the DOI resolves, the experimental config/freeze and results are present, and **External resources → Archived in** shows archival status. Record the DOI in `CITATION.cff` and the completion report as a later metadata-only commit.

## Manual route for the already published release

If the release predates enabling GitHub integration, download the extension-only archive asset from the GitHub release. In Zenodo create a new upload/software record, upload that archive, enter the version and creator metadata from `.zenodo.json`, select the intended license, link the repository/release, review and publish. Use the archive checksum from the release to verify the uploaded file. Do not upload `.env`, `.runtime`, provider credentials, model weights or private signing keys.

Official guides consulted 2026-11-17: [enable a repository](https://help.zenodo.org/docs/github/enable-repository/), [archive a GitHub release](https://help.zenodo.org/docs/github/archive-software/github-upload/). The DOI is complete only after a published, resolvable Zenodo record exists; a GitHub tag or prepared metadata alone is not a minted DOI.
