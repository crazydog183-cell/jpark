package com.jpark.jangkku.reminder

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.Query

@Dao
interface ReminderDao {
    @Insert
    suspend fun insert(reminder: Reminder): Long

    @Query("SELECT * FROM reminders ORDER BY timeMillis ASC")
    suspend fun getAll(): List<Reminder>

    @Query("SELECT * FROM reminders WHERE id = :id")
    suspend fun getById(id: Long): Reminder?

    @Query("SELECT * FROM reminders WHERE timeMillis > :now ORDER BY timeMillis ASC")
    suspend fun getUpcoming(now: Long): List<Reminder>

    @Delete
    suspend fun delete(reminder: Reminder)

    @Query("DELETE FROM reminders WHERE id = :id")
    suspend fun deleteById(id: Long): Int
}
