package com.jpark.jangkku.ai

import org.json.JSONArray
import org.json.JSONObject

/** Gemini function calling에 전달하는 스마트폰 제어 도구(함수) 선언. */
object ToolDefinitions {

    fun functionDeclarations(): JSONArray {
        val declarations = JSONArray()

        declarations.put(
            declaration(
                ToolNames.TOGGLE_FLASHLIGHT,
                "스마트폰 손전등(플래시)을 켜거나 끈다. 사용자가 손전등/플래시를 켜달라거나 꺼달라고 하면 호출한다.",
                mapOf("on" to prop("boolean", "true면 켜기, false면 끄기")),
                required = listOf("on"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.SET_BRIGHTNESS,
                "화면 밝기를 조절한다 (0~100 퍼센트).",
                mapOf("level" to prop("integer", "밝기 퍼센트 (0~100)")),
                required = listOf("level"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.SET_VOLUME,
                "미디어 또는 벨소리 볼륨을 조절한다 (0~100 퍼센트).",
                mapOf(
                    "stream" to enumProp("조절할 볼륨 종류", listOf("media", "ring")),
                    "level" to prop("integer", "볼륨 퍼센트 (0~100)"),
                ),
                required = listOf("stream", "level"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.SET_RING_MODE,
                "전화 벨소리 모드를 소리/진동/무음으로 바꾼다.",
                mapOf("mode" to enumProp("벨소리 모드", listOf("normal", "vibrate", "silent"))),
                required = listOf("mode"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.LAUNCH_APP,
                "설치된 앱을 이름으로 찾아 실행한다. 예: '유튜브 켜줘' → app_name='유튜브'.",
                mapOf("app_name" to prop("string", "실행할 앱 이름 (부분 일치 허용)")),
                required = listOf("app_name"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.OPEN_URL,
                "웹 브라우저로 URL을 연다. 검색 요청이면 검색 엔진 URL을 만들어 전달한다.",
                mapOf("url" to prop("string", "열려는 전체 URL (https:// 포함)")),
                required = listOf("url"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.OPEN_SETTINGS,
                "시스템 설정 화면을 연다. 와이파이/블루투스 등은 직접 토글할 수 없으므로 해당 설정 화면을 열어준다.",
                mapOf(
                    "section" to enumProp(
                        "열려는 설정 화면",
                        listOf("wifi", "bluetooth", "display", "sound", "battery", "apps", "main"),
                    )
                ),
                required = listOf("section"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.GET_DEVICE_STATUS,
                "배터리 잔량, 충전 여부, 볼륨, 밝기, 벨소리 모드 등 현재 기기 상태를 조회한다.",
                emptyMap(),
            )
        )
        declarations.put(
            declaration(
                ToolNames.CREATE_REMINDER,
                "지정한 시각에 알림을 울리는 리마인더를 등록한다. 시간은 반드시 'yyyy-MM-dd HH:mm' 형식의 기기 현지 시각이어야 한다. " +
                    "상대적 표현('내일 3시', '30분 뒤')은 시스템 프롬프트의 현재 시각을 기준으로 계산해서 절대 시각으로 변환해 전달한다.",
                mapOf(
                    "time" to prop("string", "알림 시각, 'yyyy-MM-dd HH:mm' 형식 (예: 2026-07-21 09:00)"),
                    "content" to prop("string", "알림 내용 (예: 팀 회의)"),
                ),
                required = listOf("time", "content"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.LIST_REMINDERS,
                "등록된 리마인더 목록을 조회한다.",
                emptyMap(),
            )
        )
        declarations.put(
            declaration(
                ToolNames.DELETE_REMINDER,
                "리마인더를 ID로 삭제한다. ID는 list_reminders 결과에서 확인한다.",
                mapOf("id" to prop("integer", "삭제할 리마인더 ID")),
                required = listOf("id"),
            )
        )
        declarations.put(
            declaration(
                ToolNames.GET_RECENT_NOTIFICATIONS,
                "최근에 도착한 다른 앱의 알림 목록을 조회한다 (알림 읽기 권한 필요).",
                emptyMap(),
            )
        )
        return declarations
    }

    private fun prop(type: String, description: String): JSONObject =
        JSONObject().put("type", type).put("description", description)

    private fun enumProp(description: String, values: List<String>): JSONObject =
        JSONObject()
            .put("type", "string")
            .put("description", description)
            .put("enum", JSONArray(values))

    private fun declaration(
        name: String,
        description: String,
        properties: Map<String, JSONObject>,
        required: List<String> = emptyList(),
    ): JSONObject {
        val declaration = JSONObject()
            .put("name", name)
            .put("description", description)
        // 파라미터가 없는 함수는 parameters를 생략한다
        if (properties.isNotEmpty()) {
            val props = JSONObject()
            properties.forEach { (key, schema) -> props.put(key, schema) }
            val parameters = JSONObject()
                .put("type", "object")
                .put("properties", props)
            if (required.isNotEmpty()) parameters.put("required", JSONArray(required))
            declaration.put("parameters", parameters)
        }
        return declaration
    }
}
