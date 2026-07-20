package com.jpark.jangkku.reminder

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "reminders")
data class Reminder(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val content: String,
    val timeMillis: Long,
)
