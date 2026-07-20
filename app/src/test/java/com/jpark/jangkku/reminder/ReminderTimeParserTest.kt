package com.jpark.jangkku.reminder

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.Calendar

class ReminderTimeParserTest {

    @Test
    fun `유효한 형식을 파싱한다`() {
        val millis = ReminderTimeParser.parse("2026-07-21 09:30")
        assertNotNull(millis)

        val cal = Calendar.getInstance().apply { timeInMillis = millis!! }
        assertEquals(2026, cal.get(Calendar.YEAR))
        assertEquals(Calendar.JULY, cal.get(Calendar.MONTH))
        assertEquals(21, cal.get(Calendar.DAY_OF_MONTH))
        assertEquals(9, cal.get(Calendar.HOUR_OF_DAY))
        assertEquals(30, cal.get(Calendar.MINUTE))
    }

    @Test
    fun `앞뒤 공백은 무시한다`() {
        assertNotNull(ReminderTimeParser.parse("  2026-01-01 00:00  "))
    }

    @Test
    fun `잘못된 형식은 null을 반환한다`() {
        assertNull(ReminderTimeParser.parse("내일 아침"))
        assertNull(ReminderTimeParser.parse("2026/07/21 09:30"))
        assertNull(ReminderTimeParser.parse("2026-07-21"))
        assertNull(ReminderTimeParser.parse(""))
    }

    @Test
    fun `존재하지 않는 날짜는 null을 반환한다`() {
        assertNull(ReminderTimeParser.parse("2026-02-30 10:00"))
        assertNull(ReminderTimeParser.parse("2026-13-01 10:00"))
        assertNull(ReminderTimeParser.parse("2026-07-21 25:00"))
    }

    @Test
    fun `포맷과 파싱은 왕복 가능하다`() {
        val original = "2026-12-25 18:45"
        val millis = ReminderTimeParser.parse(original)!!
        assertEquals(original, ReminderTimeParser.format(millis))
    }

    @Test
    fun `미래 여부를 판단한다`() {
        val now = ReminderTimeParser.parse("2026-07-20 12:00")!!
        assertTrue(ReminderTimeParser.isFuture(ReminderTimeParser.parse("2026-07-20 12:01")!!, now))
        assertFalse(ReminderTimeParser.isFuture(ReminderTimeParser.parse("2026-07-20 12:00")!!, now))
        assertFalse(ReminderTimeParser.isFuture(ReminderTimeParser.parse("2026-07-20 11:59")!!, now))
    }
}
