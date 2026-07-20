package com.jpark.jangkku.reminder

import java.text.ParseException
import java.text.SimpleDateFormat
import java.util.Locale

/**
 * AI가 전달한 'yyyy-MM-dd HH:mm' 형식의 시각 문자열을 epoch millis로 변환한다.
 * 순수 JVM 코드 — 단위 테스트 대상.
 */
object ReminderTimeParser {

    private const val PATTERN = "yyyy-MM-dd HH:mm"

    /** 파싱 실패 시 null. 기기 기본 시간대를 사용한다. */
    fun parse(text: String): Long? {
        val format = SimpleDateFormat(PATTERN, Locale.US).apply { isLenient = false }
        return try {
            format.parse(text.trim())?.time
        } catch (e: ParseException) {
            null
        }
    }

    fun format(timeMillis: Long): String =
        SimpleDateFormat(PATTERN, Locale.US).format(timeMillis)

    fun isFuture(timeMillis: Long, now: Long = System.currentTimeMillis()): Boolean =
        timeMillis > now
}
