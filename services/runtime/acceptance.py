import os
import re

MEDIA_EXTENSIONS = {
    ".mp4": "video", ".mov": "video", ".mkv": "video", ".webm": "video",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
    ".wav": "audio", ".mp3": "audio", ".m4a": "audio", ".aac": "audio",
}


def required_media_types(task_text):
    text = str(task_text or "").lower()
    required = set()
    explicit = {
        "video": r"\b(actual|real|rendered|exported|generated)\s+(?:video|mp4)|video\s+file|mp4\b|ملف\s+فيديو|فيديو\s+(?:فعلي|جاهز|مصدّر)",
        "image": r"\b(actual|real|generated|rendered)\s+image|image\s+file|png\b|ملف\s+صورة|صورة\s+(?:فعلية|جاهزة)",
        "audio": r"\b(actual|real|generated|rendered)\s+audio|audio\s+file|wav\b|mp3\b|ملف\s+صوت|صوت\s+(?:فعلي|جاهز)",
    }
    for media_type, pattern in explicit.items():
        if re.search(pattern, text, flags=re.IGNORECASE):
            required.add(media_type)
    return required


def validate_role_outputs(results, requested_roles, task_text, evidence):
    violations = []
    evidence_by_type = {}
    evidence_names = set()
    for record in evidence or []:
        if not record.get("verified") or not record.get("sha256") or record.get("size_bytes", 0) <= 0:
            continue
        media_type = record.get("type")
        if media_type in ("video", "image", "audio"):
            evidence_by_type.setdefault(media_type, []).append(record)
        basename = os.path.basename(record.get("path", "")).lower()
        if basename:
            evidence_names.add(basename)

    missing_roles = []
    malformed_roles = []
    unverified_file_claims = []
    required_roles = [role for role in requested_roles if role != "quality"]
    for role in required_roles:
        result = next(
            (
                entry for entry in results
                if entry.get("service") == role
                and entry.get("ok")
                and str(entry.get("output", "")).strip()
            ),
            None,
        )
        if result is None:
            missing_roles.append(role)
            continue
        output = str(result.get("output", ""))
        if len(output.strip()) < 80 or "DELIVERABLE" not in output.upper():
            malformed_roles.append(role)
        for match in re.findall(
            r"(?i)\b[A-Za-z0-9_ -]+\.(?:mp4|mov|mkv|webm|png|jpe?g|webp|wav|mp3|m4a|aac)\b",
            output,
        ):
            filename = os.path.basename(match.strip()).lower()
            if filename not in evidence_names:
                unverified_file_claims.append(role + ":" + filename)

    missing_media = sorted(
        media_type for media_type in required_media_types(task_text)
        if not evidence_by_type.get(media_type)
    )
    if missing_roles:
        violations.append("Missing roles: " + ", ".join(sorted(missing_roles)))
    if malformed_roles:
        violations.append("Malformed or non-deliverable outputs: " + ", ".join(sorted(malformed_roles)))
    if unverified_file_claims:
        violations.append("Unverified media filenames: " + ", ".join(sorted(set(unverified_file_claims))))
    if missing_media:
        violations.append("Required media files not evidenced: " + ", ".join(missing_media))
    return violations
