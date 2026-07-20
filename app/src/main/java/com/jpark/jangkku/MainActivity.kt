package com.jpark.jangkku

import android.app.Activity
import android.app.AlarmManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import com.jpark.jangkku.service.PetOverlayService

/**
 * 온보딩/설정 화면.
 * - Claude API 키 입력
 * - 필요한 권한 안내 및 설정 화면 이동
 * - 장꾸(플로팅 펫) 시작/중지
 */
class MainActivity : Activity() {

    private lateinit var apiKeyInput: EditText
    private val permissionRows = mutableListOf<Pair<TextView, () -> Boolean>>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(24), dp(20), dp(24))
        }

        root.addView(TextView(this).apply {
            text = "🐹 장꾸 AI"
            textSize = 28f
            setTypeface(typeface, Typeface.BOLD)
        })
        root.addView(TextView(this).apply {
            text = "바탕화면 위를 떠다니는 AI 펫이에요.\n대화하고, 폰을 조작하고, 일정을 챙겨줘요!"
            textSize = 14f
            setTextColor(Color.DKGRAY)
            setPadding(0, dp(4), 0, dp(16))
        })

        // ── API 키 ──────────────────────────────
        root.addView(sectionTitle("1. Claude API 키"))
        apiKeyInput = EditText(this).apply {
            hint = "sk-ant-... 형식의 API 키"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            if (ApiKeyStore.load(this@MainActivity) != null) hint = "저장된 키가 있어요 (변경하려면 입력)"
        }
        root.addView(apiKeyInput)
        root.addView(Button(this).apply {
            text = "키 저장"
            setOnClickListener {
                val key = apiKeyInput.text.toString().trim()
                if (key.isEmpty()) {
                    Toast.makeText(context, "API 키를 입력해 주세요", Toast.LENGTH_SHORT).show()
                } else {
                    ApiKeyStore.save(this@MainActivity, key)
                    apiKeyInput.setText("")
                    apiKeyInput.hint = "저장된 키가 있어요 (변경하려면 입력)"
                    Toast.makeText(context, "저장했어요! 🎉", Toast.LENGTH_SHORT).show()
                }
            }
        })

        // ── 권한 ──────────────────────────────
        root.addView(sectionTitle("2. 권한 설정"))
        addPermissionRow(root, "다른 앱 위에 표시 (필수)",
            { Settings.canDrawOverlays(this) },
            {
                startActivity(
                    Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName"))
                )
            })
        addPermissionRow(root, "알림 표시 (리마인더용)",
            { Build.VERSION.SDK_INT < 33 || checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) == android.content.pm.PackageManager.PERMISSION_GRANTED },
            {
                if (Build.VERSION.SDK_INT >= 33) {
                    requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 100)
                }
            })
        addPermissionRow(root, "정확한 알람 (리마인더용)",
            {
                val am = getSystemService(Context.ALARM_SERVICE) as AlarmManager
                Build.VERSION.SDK_INT < 31 || am.canScheduleExactAlarms()
            },
            {
                if (Build.VERSION.SDK_INT >= 31) {
                    startActivity(Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM, Uri.parse("package:$packageName")))
                }
            })
        addPermissionRow(root, "알림 읽기 (선택)",
            { isNotificationListenerEnabled() },
            { startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)) })
        addPermissionRow(root, "시스템 설정 변경 — 밝기 제어 (선택)",
            { Settings.System.canWrite(this) },
            { startActivity(Intent(Settings.ACTION_MANAGE_WRITE_SETTINGS, Uri.parse("package:$packageName"))) })

        // ── 시작/중지 ──────────────────────────────
        root.addView(sectionTitle("3. 장꾸 깨우기"))
        root.addView(Button(this).apply {
            text = "🐹 장꾸 시작!"
            setOnClickListener { startPet() }
        })
        root.addView(Button(this).apply {
            text = "😴 장꾸 재우기"
            setOnClickListener {
                stopService(Intent(this@MainActivity, PetOverlayService::class.java))
                Toast.makeText(context, "장꾸가 잠들었어요", Toast.LENGTH_SHORT).show()
            }
        })

        setContentView(ScrollView(this).apply { addView(root, MATCH_PARENT, WRAP_CONTENT) })
    }

    override fun onResume() {
        super.onResume()
        refreshPermissionStatuses()
    }

    private fun startPet() {
        if (ApiKeyStore.load(this) == null) {
            Toast.makeText(this, "먼저 Claude API 키를 저장해 주세요!", Toast.LENGTH_LONG).show()
            return
        }
        if (!Settings.canDrawOverlays(this)) {
            Toast.makeText(this, "'다른 앱 위에 표시' 권한이 필요해요!", Toast.LENGTH_LONG).show()
            return
        }
        startForegroundService(Intent(this, PetOverlayService::class.java))
        Toast.makeText(this, "장꾸가 깨어났어요! 홈 화면을 확인해 보세요 🐹", Toast.LENGTH_SHORT).show()
    }

    private fun isNotificationListenerEnabled(): Boolean {
        val flat = Settings.Secure.getString(contentResolver, "enabled_notification_listeners") ?: return false
        return flat.split(":").any {
            ComponentName.unflattenFromString(it)?.packageName == packageName
        }
    }

    private fun addPermissionRow(
        parent: LinearLayout,
        label: String,
        isGranted: () -> Boolean,
        onRequest: () -> Unit,
    ) {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(0, dp(4), 0, dp(4))
        }
        val status = TextView(this).apply {
            textSize = 14f
            layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
        }
        permissionRows += status to isGranted
        row.addView(status)
        row.addView(Button(this).apply {
            text = "설정"
            setOnClickListener { onRequest() }
        })
        parent.addView(row)
        // 라벨을 상태 TextView에 함께 표기
        status.tag = label
    }

    private fun refreshPermissionStatuses() {
        permissionRows.forEach { (view, isGranted) ->
            val label = view.tag as String
            val ok = isGranted()
            view.text = (if (ok) "✅ " else "⬜ ") + label
            view.setTextColor(if (ok) Color.rgb(46, 125, 50) else Color.DKGRAY)
        }
    }

    private fun sectionTitle(text: String) = TextView(this).apply {
        this.text = text
        textSize = 17f
        setTypeface(typeface, Typeface.BOLD)
        setPadding(0, dp(16), 0, dp(6))
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
