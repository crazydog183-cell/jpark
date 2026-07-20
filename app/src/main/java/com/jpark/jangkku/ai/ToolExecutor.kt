package com.jpark.jangkku.ai

/**
 * Claude가 호출한 도구를 실제로 실행하는 역할.
 * (안드로이드 구현체: [com.jpark.jangkku.device.DeviceToolExecutor])
 */
interface ToolExecutor {
    /** 도구를 실행하고 모델에게 돌려줄 결과 문자열을 반환한다. */
    fun execute(name: String, input: Map<String, Any?>): String
}
