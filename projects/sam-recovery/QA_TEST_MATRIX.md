# SAM Recovery — QA Test Matrix

## Android
- [ ] Android 13: accept images and videos separately.
- [ ] Android 14+: grant full access.
- [ ] Android 14+: grant selected photos only; verify no crash and accurate count.
- [ ] Deny permission; verify explanation and retry path.
- [ ] Empty library; verify empty state.
- [ ] Open image/video; verify URI permission handoff.
- [ ] Export image/video to user-selected document location.
- [ ] Cancel export; verify no false success message.
- [ ] Revoke permission from Settings while app is backgrounded; relaunch and scan.
- [ ] Confirm no network traffic during scan/export.

## iOS
- [ ] Fresh install: request read/write authorization only after user action.
- [ ] Full library authorization: list images and videos.
- [ ] Limited authorization: list only selected assets.
- [ ] Denied/restricted authorization: show actionable explanation.
- [ ] Confirm Recently Deleted is not presented as accessible recovery data.
- [ ] Confirm no network traffic or asset upload.

## Cross-platform
- [ ] Arabic RTL layout, long filenames, and date formatting.
- [ ] Accessibility labels and dynamic text sizing.
- [ ] Large media library performance and cancellation.
- [ ] Privacy notice matches actual runtime behavior.
- [ ] No marketing claim of guaranteed permanent-deletion recovery.

## Release gate
All applicable checks must be executed on real devices and recorded with OS version, device model, test result, and evidence. A successful compile alone is not a functional recovery test.