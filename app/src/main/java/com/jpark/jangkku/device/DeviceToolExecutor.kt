package com.jpark.jangkku.device

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.media.AudioManager
import android.net.Uri
import android.os.BatteryManager
import android.provider.Settings
import com.jpark.jangkku.ai.ToolExecutor
import com.jpark.jangkku.ai.ToolNames
import com.jpark.jangkku.notification.JangkkuNotificationListener
import com.jpark.jangkku.reminder.ReminderManager
import com.jpark.jangkku.reminder.ReminderTimeParser
import kotlinx.coroutines.runBlocking

/**
 * Claude가 호출한 도구를 안드로이드 시스템 API로 실제 실행한다.
 * 반환 문자열은 모델에게 tool_result로 전달된다.
 */
class DeviceToolExecutor(private val context: Context) : ToolExecutor {

    private val reminderManager = ReminderManager(context)

    override fun execute(name: String, input: Map<String, Any?>): String = when (name) {
        ToolNames.TOGGLE_FLASHLIGHT -> toggleFlashlight(bool(input, "on"))
        ToolNames.SET_BRIGHTNESS -> setBrightness(int(input, "level"))
        ToolNames.SET_VOLUME -> setVolume(str(input, "stream"), int(input, "level"))
        ToolNames.SET_RING_MODE -> setRingMode(str(input, "mode"))
        ToolNames.LAUNCH_APP -> launchApp(str(input, "app_name"))
        ToolNames.OPEN_URL -> openUrl(str(input, "url"))
        ToolNames.OPEN_SETTINGS -> openSettings(str(input, "section"))
        ToolNames.GET_DEVICE_STATUS -> getDeviceStatus()
        ToolNames.CREATE_REMINDER -> createReminder(str(input, "time"), str(input, "content"))
        ToolNames.LIST_REMINDERS -> listReminders()
        ToolNames.DELETE_REMINDER -> deleteReminder(int(input, "id").toLong())
        ToolNames.GET_RECENT_NOTIFICATIONS -> getRecentNotifications()
        else -> "알 수 없는 도구: $name"
    }

    // ── 기기 제어 ─────────────────────────────────────────

    private fun toggleFlashlight(on: Boolean): String {
        val cameraManager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
        val cameraId = cameraManager.cameraIdList.firstOrNull { id ->
            cameraManager.getCameraCharacteristics(id)
                .get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
        } ?: return "이 기기에는 플래시가 없습니다."
        return try {
            cameraManager.setTorchMode(cameraId, on)
            if (on) "손전등을 켰습니다." else "손전등을 껐습니다."
        } catch (e: Exception) {
            "손전등 제어 실패: ${e.message}"
        }
    }

    private fun setBrightness(level: Int): String {
        if (!Settings.System.canWrite(context)) {
            return "실패: '시스템 설정 변경' 권한이 없습니다. 설정 앱에서 권한을 켜달라고 사용자에게 안내하세요."
        }
        val clamped = level.coerceIn(0, 100)
        val value = (clamped * 255 / 100).coerceIn(1, 255)
        Settings.System.putInt(
            context.contentResolver,
            Settings.System.SCREEN_BRIGHTNESS_MODE,
            Settings.System.SCREEN_BRIGHTNESS_MODE_MANUAL,
        )
        Settings.System.putInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS, value)
        return "화면 밝기를 ${clamped}%로 설정했습니다."
    }

    private fun setVolume(stream: String, level: Int): String {
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val streamType = when (stream) {
            "ring" -> AudioManager.STREAM_RING
            else -> AudioManager.STREAM_MUSIC
        }
        val max = audio.getStreamMaxVolume(streamType)
        val clamped = level.coerceIn(0, 100)
        return try {
            audio.setStreamVolume(streamType, clamped * max / 100, 0)
            val label = if (streamType == AudioManager.STREAM_RING) "벨소리" else "미디어"
            "$label 볼륨을 ${clamped}%로 설정했습니다."
        } catch (e: SecurityException) {
            // 방해 금지 모드 중 벨소리 변경 등은 SecurityException이 날 수 있음
            "볼륨 변경 실패: 방해 금지 모드 설정 때문에 변경할 수 없습니다."
        }
    }

    private fun setRingMode(mode: String): String {
        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        return try {
            audio.ringerMode = when (mode) {
                "vibrate" -> AudioManager.RINGER_MODE_VIBRATE
                "silent" -> AudioManager.RINGER_MODE_SILENT
                else -> AudioManager.RINGER_MODE_NORMAL
            }
            val label = when (mode) {
                "vibrate" -> "진동"
                "silent" -> "무음"
                else -> "소리"
            }
            "벨소리 모드를 '$label'으로 변경했습니다."
        } catch (e: SecurityException) {
            "실패: 무음/진동 전환에는 '방해 금지 접근' 권한이 필요할 수 있습니다."
        }
    }

    private fun launchApp(query: String): String {
        val pm = context.packageManager
        val launchables = pm.queryIntentActivities(
            Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER),
            PackageManager.MATCH_ALL,
        )
        val match = launchables.firstOrNull {
            it.loadLabel(pm).toString().contains(query, ignoreCase = true)
        } ?: return "'$query' 이름의 앱을 찾지 못했습니다. 설치된 앱 이름을 다시 확인해 주세요."

        val packageName = match.activityInfo.packageName
        val intent = pm.getLaunchIntentForPackage(packageName)
            ?: return "'$query' 앱을 실행할 수 없습니다."
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        context.startActivity(intent)
        return "'${match.loadLabel(pm)}' 앱을 실행했습니다."
    }

    private fun openUrl(url: String): String {
        val uri = Uri.parse(if (url.startsWith("http")) url else "https://$url")
        return try {
            context.startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            "브라우저로 열었습니다: $uri"
        } catch (e: Exception) {
            "URL 열기 실패: ${e.message}"
        }
    }

    private fun openSettings(section: String): String {
        val action = when (section) {
            "wifi" -> Settings.ACTION_WIFI_SETTINGS
            "bluetooth" -> Settings.ACTION_BLUETOOTH_SETTINGS
            "display" -> Settings.ACTION_DISPLAY_SETTINGS
            "sound" -> Settings.ACTION_SOUND_SETTINGS
            "battery" -> Settings.ACTION_BATTERY_SAVER_SETTINGS
            "apps" -> Settings.ACTION_APPLICATION_SETTINGS
            else -> Settings.ACTION_SETTINGS
        }
        return try {
            context.startActivity(Intent(action).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            "설정 화면($section)을 열었습니다."
        } catch (e: Exception) {
            "설정 화면 열기 실패: ${e.message}"
        }
    }

    private fun getDeviceStatus(): String {
        val battery = context.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val level = battery.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val charging = battery.isCharging

        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        val mediaVol = audio.getStreamVolume(AudioManager.STREAM_MUSIC) * 100 /
            audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        val ringMode = when (audio.ringerMode) {
            AudioManager.RINGER_MODE_VIBRATE -> "진동"
            AudioManager.RINGER_MODE_SILENT -> "무음"
            else -> "소리"
        }
        val brightness = try {
            Settings.System.getInt(context.contentResolver, Settings.System.SCREEN_BRIGHTNESS) * 100 / 255
        } catch (e: Exception) {
            -1
        }

        return buildString {
            append("배터리: ${level}%")
            append(if (charging) " (충전 중)" else "")
            append(", 미디어 볼륨: ${mediaVol}%")
            append(", 벨소리 모드: $ringMode")
            if (brightness >= 0) append(", 화면 밝기: ${brightness}%")
        }
    }

    // ── 리마인더 ─────────────────────────────────────────

    private fun createReminder(time: String, content: String): String {
        val timeMillis = ReminderTimeParser.parse(time)
            ?: return "실패: 시간 형식이 잘못되었습니다. 'yyyy-MM-dd HH:mm' 형식으로 다시 시도하세요. (받은 값: $time)"
        if (!ReminderTimeParser.isFuture(timeMillis)) {
            return "실패: 과거 시각입니다 ($time). 미래 시각으로 다시 시도하세요."
        }
        val reminder = runBlocking { reminderManager.add(content, timeMillis) }
        return "리마인더 등록 완료 (ID ${reminder.id}): ${ReminderTimeParser.format(timeMillis)} — $content"
    }

    private fun listReminders(): String {
        val reminders = runBlocking { reminderManager.list() }
        if (reminders.isEmpty()) return "등록된 리마인더가 없습니다."
        return reminders.joinToString("\n") {
            "ID ${it.id}: ${ReminderTimeParser.format(it.timeMillis)} — ${it.content}"
        }
    }

    private fun deleteReminder(id: Long): String {
        val deleted = runBlocking { reminderManager.delete(id) }
        return if (deleted) "리마인더(ID $id)를 삭제했습니다." else "ID $id 리마인더를 찾지 못했습니다."
    }

    // ── 알림 ─────────────────────────────────────────

    private fun getRecentNotifications(): String {
        if (!JangkkuNotificationListener.connected) {
            return "알림 읽기 권한이 없습니다. 설정 앱의 '알림 읽기' 권한을 켜달라고 사용자에게 안내하세요."
        }
        val notifications = JangkkuNotificationListener.snapshot()
        if (notifications.isEmpty()) return "최근 수신된 알림이 없습니다."
        return notifications.joinToString("\n") { it.summary() }
    }

    // ── 입력 파싱 헬퍼 ─────────────────────────────────────

    private fun str(input: Map<String, Any?>, key: String): String =
        input[key]?.toString().orEmpty()

    private fun int(input: Map<String, Any?>, key: String): Int = when (val v = input[key]) {
        is Number -> v.toInt()
        is String -> v.toIntOrNull() ?: 0
        else -> 0
    }

    private fun bool(input: Map<String, Any?>, key: String): Boolean = when (val v = input[key]) {
        is Boolean -> v
        is String -> v.equals("true", ignoreCase = true)
        else -> false
    }
}
