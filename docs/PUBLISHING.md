# Publishing Auto TTS

## GitHub releases

The source repository is https://github.com/hamid7780/Auto-TTS-for-NVDA. Installable
packages are attached to releases rather than committed to source history.

For a new stable version:

1. Update the version, description/changelog and compatibility fields in
   `manifest.ini`, keeping `updateChannel = stable`.
2. Update `README.md` if the behaviour changed, then run `python tools/make_help.py`
   to rebuild the bundled help page. Update the third-party notice heading,
   `CHANGELOG.md`, and the "What's new" part of `RELEASE_NOTES.md`. The release
   page shows `RELEASE_NOTES.md` as it is.
3. Run the regression suite and test the add-on in the intended NVDA versions.
4. Commit and push the changes to `main`.
5. Create an annotated tag matching the manifest, for example:

   ```powershell
   git tag -a v1.0.2 -m "Auto TTS 1.0.2"
   git push origin v1.0.2
   ```

GitHub Actions tests all three bundled runtime generations, builds the package
and publishes a normal release with the `.nvda-addon` and SHA-256 checksum.
The workflow refuses a tag whose version differs from the manifest. See Actions
for failures before retrying. Re-running the tagged workflow updates the release
notes and replaces its package attachments. Use a new version for functional changes.

## NVDA Add-on Store

A GitHub release does not automatically list the add-on in NVDA's Add-on Store.
Follow the [official submission guide](https://github.com/nvaccess/addon-datastore/blob/master/docs/submitters/submissionGuide.md)
and its [registration form](https://github.com/nvaccess/addon-datastore/issues/new?template=registerAddon.yml).
First submissions require NV Access publisher approval and validation.

Values to enter for the current release (replace the version with the one in `manifest.ini`):

| Field | Value |
| --- | --- |
| Add-on ID | `autoTTS` |
| Display name | Auto TTS for NVDA |
| Version | `1.0.2` |
| Channel | `stable` |
| Publisher account | `hamid7780` |
| Author | Raja Hamid |
| Source URL | https://github.com/hamid7780/Auto-TTS-for-NVDA |
| Homepage | https://github.com/hamid7780/Auto-TTS-for-NVDA |
| Direct download | https://github.com/hamid7780/Auto-TTS-for-NVDA/releases/download/v1.0.2/autoTTS-1.0.2.nvda-addon |
| License | GPL-2.0, with bundled MIT and CC-BY-SA-3.0 components |
| Minimum NVDA | `2023.3` |
| Last tested NVDA | `2026.2` |

Use the checksum attached to the release if the form requests it. Verify that
the compatibility versions are accepted in the store's current API list.
Publisher approval and NVDA compatibility testing are required for store submissions.
