package com.jpark.jangkku.ai

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ToolDefinitionsTest {

    private fun declarations(): List<JSONObject> {
        val array = ToolDefinitions.functionDeclarations()
        return (0 until array.length()).map { array.getJSONObject(it) }
    }

    @Test
    fun `정의된 함수 이름이 ToolNames와 정확히 일치한다`() {
        val definedNames = declarations().map { it.getString("name") }.toSet()
        assertEquals(ToolNames.ALL, definedNames)
    }

    @Test
    fun `함수 이름은 중복이 없다`() {
        val names = declarations().map { it.getString("name") }
        assertEquals(names.size, names.toSet().size)
    }

    @Test
    fun `모든 함수에 설명이 있다`() {
        declarations().forEach { declaration ->
            assertTrue(
                "함수 ${declaration.getString("name")}에 설명이 없습니다",
                declaration.getString("description").isNotBlank(),
            )
        }
    }

    @Test
    fun `parameters가 있으면 object 타입이고 required 키는 properties에 존재한다`() {
        declarations().forEach { declaration ->
            val parameters = declaration.optJSONObject("parameters") ?: return@forEach
            assertEquals("object", parameters.getString("type"))
            val properties = parameters.getJSONObject("properties")
            val required = parameters.optJSONArray("required")
            if (required != null) {
                for (i in 0 until required.length()) {
                    val key = required.getString(i)
                    assertTrue(
                        "${declaration.getString("name")}의 required '$key'가 properties에 없습니다",
                        properties.has(key),
                    )
                }
            }
        }
    }
}
