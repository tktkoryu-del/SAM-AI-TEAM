package com.samteam.recovery

import android.Manifest

/** Keeps runtime media permissions aligned with the Android platform version. */
object MediaPermissionPolicy {
    fun requiredPermissions(sdk: Int): Array<String> = when {
        sdk >= 34 -> arrayOf(
            Manifest.permission.READ_MEDIA_IMAGES,
            Manifest.permission.READ_MEDIA_VIDEO,
            Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED
        )
        sdk >= 33 -> arrayOf(
            Manifest.permission.READ_MEDIA_IMAGES,
            Manifest.permission.READ_MEDIA_VIDEO
        )
        else -> arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
    }
}
