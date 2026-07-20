package com.jpark.jangkku.reminder

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

/** 리마인더 저장(Room)과 알람(AlarmManager) 예약을 담당한다. */
class ReminderManager(private val context: Context) {

    private val dao get() = ReminderDatabase.get(context).reminderDao()
    private val alarmManager get() = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager

    suspend fun add(content: String, timeMillis: Long): Reminder {
        val id = dao.insert(Reminder(content = content, timeMillis = timeMillis))
        val reminder = Reminder(id = id, content = content, timeMillis = timeMillis)
        scheduleAlarm(reminder)
        return reminder
    }

    suspend fun list(): List<Reminder> = dao.getAll()

    suspend fun delete(id: Long): Boolean {
        val deleted = dao.deleteById(id) > 0
        if (deleted) cancelAlarm(id)
        return deleted
    }

    /** 재부팅 후 미래 리마인더의 알람을 다시 등록한다. */
    suspend fun rescheduleAll() {
        dao.getUpcoming(System.currentTimeMillis()).forEach { scheduleAlarm(it) }
    }

    fun scheduleAlarm(reminder: Reminder) {
        val pendingIntent = buildPendingIntent(reminder.id, reminder.content)
        val canExact = Build.VERSION.SDK_INT < 31 || alarmManager.canScheduleExactAlarms()
        if (canExact) {
            alarmManager.setExactAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP, reminder.timeMillis, pendingIntent,
            )
        } else {
            // 정확한 알람 권한이 없으면 근사 알람으로라도 등록
            alarmManager.setAndAllowWhileIdle(
                AlarmManager.RTC_WAKEUP, reminder.timeMillis, pendingIntent,
            )
        }
    }

    private fun cancelAlarm(id: Long) {
        alarmManager.cancel(buildPendingIntent(id, ""))
    }

    private fun buildPendingIntent(id: Long, content: String): PendingIntent {
        val intent = Intent(context, ReminderReceiver::class.java).apply {
            putExtra(ReminderReceiver.EXTRA_ID, id)
            putExtra(ReminderReceiver.EXTRA_CONTENT, content)
        }
        return PendingIntent.getBroadcast(
            context,
            id.toInt(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}
