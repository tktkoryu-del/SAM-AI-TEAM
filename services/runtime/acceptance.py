import os
import re

MEDIA_EXTENSIONS = {
    ".mp4": "video", ".mov": "video", ".mkv": "video", ".webm": "video",
    ".png": "image", ".jpg": "image", ".jpeg": "image", ".webp": "image",
    ".wav": "audio", ".mp3": "audio", ".m4a": "audio", ".aac": "audio",
}


def required_media_types(task_text):
    text = str(task_text or "").lower()
    patterns = {
        "video": r"\b(actual|real|rendered|exported|generated)\s+(?:video|mp4)|video\s+file|mp4\b|ملف\s+فيديو|فيديو\s+(?:فعلي|جاهز|مصدّر)",
        "image": r"\b(actual|real|generated|rendered)\s+image|image\s+file|png\b|ملف\s+صورة|صورة\s+(?:فعلية|جاهزة)",
        "audio": r"\b(actual|real|generated|rendered)\s+audio|audio\s+file|wav\b|mp3\b|ملف\s+صوت|صوت\s+(?:فعلي|جاهز)",
    }
    return {
        media_type for media_type, pattern in patterns.items()
        if re.search(pattern, text, flags=re.IGNORECASE)
    }


def validate_role_outputs(results, requested_roles, task_text, evidence):
    violations = []
    verified = []
    for record in evidence or []:
        if (
            record.get("verified")
            and record.get("sha256")
            and int(record.get("size_bytes", 0) or 0) > 0
            and record.get("type") in ("video", "image", "audio")
        ):
            verified.append(record)

    evidence_names = {
        os.path.basename(record.get("path", "")).lower()
        for record in verified
        if record.get("path")
    }
    evidence_by_type = {}
    for record in verified:
        evidence_by_type.setdefault(record["type"], []).append(record)

    missing_roles = []
    malformed_roles = []
    unverified_file_claims = []
    for role in requested_roles:
        if role == "quality":
            continue
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

    required_media = required_media_types(task_text)
    missing_media = sorted(
        media_type for media_type in required_media
        if not evidence_by_type.get(media_type)
    )
    probe_errors = []
    text = str(task_text or "").lower()
    video_records = evidence_by_type.get("video", [])
    if "vertical" in text or "9:16" in text or "عمودي" in text:
        for record in video_records:
            probe = record.get("media_probe") or {}
            width = probe.get("width")
            height = probe.get("height")
            if not width or not height:
                probe_errors.append("vertical video has no verified width/height probe")
            elif int(height) <= int(width):
                probe_errors.append("video is not portrait/vertical")
    duration_match = re.search(r"(\d{1,3})\s*(?:seconds?|secs?|ثانية|ثواني)", text)
    if duration_match and video_records:
        expected = int(duration_match.group(1))
        for record in video_records:
            duration = (record.get("media_probe") or {}).get("duration_seconds")
            if duration is None:
                probe_errors.append("video has no verified duration probe")
            elif abs(float(duration) - expected) > 0.75:
                probe_errors.append(
                    "video duration {}s does not match {}s".format(duration, expected)
                )

    if missing_roles:
        violations.append("Missing roles: " + ", ".join(sorted(set(missing_roles))))
    if malformed_roles:
        violations.append(
            "Malformed or non-deliverable outputs: " + ", ".join(sorted(set(malformed_roles)))
        )
    if unverified_file_claims:
        violations.append(
            "Unverified media filenames: " + ", ".join(sorted(set(unverified_file_claims)))
        )
    if missing_media:
        violations.append("Required media files not evidenced: " + ", ".join(missing_media))
    if probe_errors:
        violations.append("Media probe failures: " + "; ".join(probe_errors))
    return violations
