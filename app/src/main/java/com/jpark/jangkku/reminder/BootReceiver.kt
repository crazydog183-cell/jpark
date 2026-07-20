package com.jpark.jangkku.reminder

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/** 재부팅 시 AlarmManager 알람이 사라지므로 미래 리마인더를 다시 등록한다. */
class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                ReminderManager(context.applicationContext).rescheduleAll()
            } finally {
                pendingResult.finish()
            }
        }
    }
}
