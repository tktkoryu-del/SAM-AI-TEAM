package com.samteam.recovery

import org.junit.Assert.assertArrayEquals
import org.junit.Test

class MediaPermissionPolicyTest {
    @Test fun android14RequestsPartialSelectionPermission() {
        assertArrayEquals(
            arrayOf("android.permission.READ_MEDIA_IMAGES", "android.permission.READ_MEDIA_VIDEO", "android.permission.READ_MEDIA_VISUAL_USER_SELECTED"),
            MediaPermissionPolicy.requiredPermissions(34)
        )
    }

    @Test fun android13RequestsImageAndVideoPermissions() {
        assertArrayEquals(
            arrayOf("android.permission.READ_MEDIA_IMAGES", "android.permission.READ_MEDIA_VIDEO"),
            MediaPermissionPolicy.requiredPermissions(33)
        )
    }

    @Test fun android12AndEarlierUseLegacyReadPermission() {
        assertArrayEquals(
            arrayOf("android.permission.READ_EXTERNAL_STORAGE"),
            MediaPermissionPolicy.requiredPermissions(32)
        )
    }
}
