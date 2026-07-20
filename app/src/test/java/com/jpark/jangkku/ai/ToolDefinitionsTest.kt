package com.jpark.jangkku.ai

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ToolDefinitionsTest {

    @Test
    fun `정의된 도구 이름이 ToolNames와 정확히 일치한다`() {
        val definedNames = ToolDefinitions.all().map { it.name() }.toSet()
        assertEquals(ToolNames.ALL, definedNames)
    }

    @Test
    fun `도구 이름은 중복이 없다`() {
        val names = ToolDefinitions.all().map { it.name() }
        assertEquals(names.size, names.toSet().size)
    }

    @Test
    fun `모든 도구에 설명이 있다`() {
        ToolDefinitions.all().forEach { tool ->
            assertTrue(
                "도구 ${tool.name()}에 설명이 없습니다",
                tool.description().isPresent && tool.description().get().isNotBlank(),
            )
        }
    }

    @Test
    fun `직렬화 시 유효한 스키마 구조를 가진다`() {
        // Tool 객체가 SDK 검증을 통과하는지 확인 (잘못된 스키마면 예외 발생)
        ToolDefinitions.all().forEach { it.validate() }
    }
}
