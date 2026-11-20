package com.samteam.recovery

import android.Manifest
import android.app.Activity
import android.content.ContentUris
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.Gravity
import android.view.View
import android.widget.*
import java.text.DateFormat
import java.util.Date

/** Local media discovery MVP. It does not recover permanently deleted storage blocks. */
class MainActivity : Activity() {
    private lateinit var results: LinearLayout
    private lateinit var status: TextView
    private val permissionRequest = 4102

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            layoutDirection = View.LAYOUT_DIRECTION_RTL
            setPadding(24, 30, 24, 20)
            setBackgroundColor(0xFFF7F8FC.toInt())
        }
        root.addView(TextView(this).apply {
            text = "SAM Recovery"
            textSize = 28f
            gravity = Gravity.RIGHT
            setTextColor(0xFF172554.toInt())
        })
        root.addView(TextView(this).apply {
            text = "العثور على الصور والفيديوهات المتاحة"
            textSize = 17f
            gravity = Gravity.RIGHT
            setPadding(0, 8, 0, 14)
        })
        root.addView(TextView(this).apply {
            text = "تنبيه: لا يمكن ضمان استعادة الملفات المحذوفة نهائياً. يفحص هذا الإصدار الوسائط التي يتيحها Android فقط، ولا يرفع ملفاتك إلى الإنترنت."
            textSize = 14f
            gravity = Gravity.RIGHT
            setPadding(14, 14, 14, 14)
            setTextColor(0xFF7C2D12.toInt())
            setBackgroundColor(0xFFFFEDD5.toInt())
        })
        root.addView(Button(this).apply {
            text = "ابدأ الفحص المحلي"
            setOnClickListener { requestMediaAccess() }
        })
        status = TextView(this).apply {
            text = "امنح الإذن لبدء الفحص."
            textSize = 14f
            gravity = Gravity.RIGHT
            setPadding(0, 16, 0, 12)
        }
        root.addView(status)
        results = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; layoutDirection = View.LAYOUT_DIRECTION_RTL }
        root.addView(ScrollView(this).apply { addView(results) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    private fun permissions(): Array<String> = when {
        Build.VERSION.SDK_INT >= 34 -> arrayOf(Manifest.permission.READ_MEDIA_IMAGES, Manifest.permission.READ_MEDIA_VIDEO, Manifest.permission.READ_MEDIA_VISUAL_USER_SELECTED)
        Build.VERSION.SDK_INT >= 33 -> arrayOf(Manifest.permission.READ_MEDIA_IMAGES, Manifest.permission.READ_MEDIA_VIDEO)
        else -> arrayOf(Manifest.permission.READ_EXTERNAL_STORAGE)
    }

    private fun requestMediaAccess() {
        val missing = permissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) scanMedia() else requestPermissions(missing.toTypedArray(), permissionRequest)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != permissionRequest) return
        if (permissions().any { checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }) scanMedia()
        else status.text = "لم تمنح إذن الوصول. يمكنك إعادة المحاولة أو تعديل الإذن من إعدادات الجهاز."
    }

    private data class Item(val uri: Uri, val name: String, val type: String, val date: Long)

    private fun scanMedia() {
        results.removeAllViews()
        val items = mutableListOf<Item>()
        query(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, "صورة", items)
        query(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, "فيديو", items)
        items.sortByDescending { it.date }
        status.text = "عُثر على ${items.size} عنصر متاح. هذه ليست قائمة بالملفات المحذوفة نهائياً."
        if (items.isEmpty()) {
            addMessage("لا توجد وسائط متاحة ضمن الأذونات الحالية.")
            return
        }
        items.forEach { item ->
            val date = if (item.date > 0) DateFormat.getDateTimeInstance().format(Date(item.date * 1000)) else ""
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(12, 10, 12, 10)
                setBackgroundColor(0xFFFFFFFF.toInt())
            }
            row.addView(TextView(this).apply {
                text = "${item.type}: ${item.name}\n$date"
                textSize = 15f
                gravity = Gravity.RIGHT
                setOnClickListener { openItem(item) }
            })
            row.addView(Button(this).apply {
                text = "حفظ نسخة في مجلد أختاره"
                setOnClickListener { chooseExportDestination(item) }
            })
            results.addView(row, LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, 0, 0, 8) })
        }
    }

    private fun query(collection: Uri, type: String, output: MutableList<Item>) {
        val projection = arrayOf(MediaStore.MediaColumns._ID, MediaStore.MediaColumns.DISPLAY_NAME, MediaStore.MediaColumns.DATE_ADDED)
        try {
            contentResolver.query(collection, projection, null, null, "${MediaStore.MediaColumns.DATE_ADDED} DESC")?.use { c ->
                val id = c.getColumnIndexOrThrow(MediaStore.MediaColumns._ID)
                val name = c.getColumnIndexOrThrow(MediaStore.MediaColumns.DISPLAY_NAME)
                val date = c.getColumnIndexOrThrow(MediaStore.MediaColumns.DATE_ADDED)
                while (c.moveToNext()) output.add(Item(ContentUris.withAppendedId(collection, c.getLong(id)), c.getString(name) ?: "ملف بدون اسم", type, c.getLong(date)))
            }
        } catch (_: SecurityException) { /* Partial media access is supported. */ }
    }

    private var pendingExportUri: Uri? = null
    private var pendingExportName: String = "SAM-Recovery-media"

    private fun chooseExportDestination(item: Item) {
        pendingExportUri = item.uri
        pendingExportName = item.name
        val mime = contentResolver.getType(item.uri) ?: if (item.type == "صورة") "image/jpeg" else "video/mp4"
        startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = mime
            putExtra(Intent.EXTRA_TITLE, item.name)
        }, 4103)
    }

    @Deprecated("Uses the platform document picker result callback")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 4103 || resultCode != RESULT_OK) return
        val destination = data?.data ?: return
        val source = pendingExportUri ?: return
        try {
            contentResolver.openInputStream(source).use { input ->
                contentResolver.openOutputStream(destination, "w").use { output ->
                    requireNotNull(input) { "تعذر قراءة الملف الأصلي" }
                    requireNotNull(output) { "تعذر إنشاء النسخة" }
                    input.copyTo(output)
                }
            }
            Toast.makeText(this, "تم حفظ نسخة من الملف في المكان الذي اخترته.", Toast.LENGTH_LONG).show()
        } catch (_: Exception) {
            Toast.makeText(this, "تعذر حفظ النسخة. تحقق من المساحة والأذونات.", Toast.LENGTH_LONG).show()
        } finally {
            pendingExportUri = null
        }
    }

    private fun openItem(item: Item) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW).apply {
                setDataAndType(item.uri, if (item.type == "صورة") "image/*" else "video/*")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            })
        } catch (_: Exception) { Toast.makeText(this, "تعذرت معاينة الملف.", Toast.LENGTH_SHORT).show() }
    }

    private fun addMessage(message: String) {
        results.addView(TextView(this).apply { text = message; gravity = Gravity.RIGHT; setPadding(12, 18, 12, 18) })
    }
}