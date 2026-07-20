package com.jpark.jangkku.ai

/** 도구 이름 상수 — 정의(ToolDefinitions)와 실행(ToolExecutor 구현)이 공유한다. */
object ToolNames {
    const val TOGGLE_FLASHLIGHT = "toggle_flashlight"
    const val SET_BRIGHTNESS = "set_brightness"
    const val SET_VOLUME = "set_volume"
    const val SET_RING_MODE = "set_ring_mode"
    const val LAUNCH_APP = "launch_app"
    const val OPEN_URL = "open_url"
    const val OPEN_SETTINGS = "open_settings"
    const val GET_DEVICE_STATUS = "get_device_status"
    const val CREATE_REMINDER = "create_reminder"
    const val LIST_REMINDERS = "list_reminders"
    const val DELETE_REMINDER = "delete_reminder"
    const val GET_RECENT_NOTIFICATIONS = "get_recent_notifications"

    val ALL: Set<String> = setOf(
        TOGGLE_FLASHLIGHT, SET_BRIGHTNESS, SET_VOLUME, SET_RING_MODE,
        LAUNCH_APP, OPEN_URL, OPEN_SETTINGS, GET_DEVICE_STATUS,
        CREATE_REMINDER, LIST_REMINDERS, DELETE_REMINDER, GET_RECENT_NOTIFICATIONS,
    )
}
