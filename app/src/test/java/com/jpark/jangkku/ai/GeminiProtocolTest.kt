package com.jpark.jangkku.ai

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GeminiProtocolTest {

    @Test
    fun `요청 본문에 시스템 프롬프트, 대화, 도구가 모두 들어간다`() {
        val history = listOf(GeminiProtocol.userTurn("안녕!"))
        val request = GeminiProtocol.buildRequest(
            history = history,
            systemPrompt = "너는 장꾸야",
            functionDeclarations = ToolDefinitions.functionDeclarations(),
            maxOutputTokens = 1024,
        )

        assertEquals(
            "너는 장꾸야",
            request.getJSONObject("systemInstruction").getJSONArray("parts").getJSONObject(0).getString("text"),
        )
        val contents = request.getJSONArray("contents")
        assertEquals(1, contents.length())
        assertEquals("user", contents.getJSONObject(0).getString("role"))
        assertEquals(
            ToolNames.ALL.size,
            request.getJSONArray("tools").getJSONObject(0).getJSONArray("functionDeclarations").length(),
        )
        assertEquals(1024, request.getJSONObject("generationConfig").getInt("maxOutputTokens"))
    }

    @Test
    fun `텍스트 응답을 해석한다`() {
        val response = JSONObject(
            """
            {"candidates":[{"content":{"role":"model","parts":[{"text":"안녕! 나는 장꾸야 🐹"}]},"finishReason":"STOP"}]}
            """
        )
        val turn = GeminiProtocol.parseResponse(response)
        assertNotNull(turn.content)
        assertEquals("안녕! 나는 장꾸야 🐹", turn.text)
        assertTrue(turn.functionCalls.isEmpty())
        assertNull(turn.blockReason)
    }

    @Test
    fun `functionCall 응답을 해석한다`() {
        val response = JSONObject(
            """
            {"candidates":[{"content":{"role":"model","parts":[
              {"text":"손전등 켤게!"},
              {"functionCall":{"name":"toggle_flashlight","args":{"on":true}}}
            ]}}]}
            """
        )
        val turn = GeminiProtocol.parseResponse(response)
        assertEquals("손전등 켤게!", turn.text)
        assertEquals(1, turn.functionCalls.size)
        assertEquals("toggle_flashlight", turn.functionCalls[0].name)
        assertEquals(true, turn.functionCalls[0].args["on"])
    }

    @Test
    fun `thought 파트는 사용자 텍스트에서 제외된다`() {
        val response = JSONObject(
            """
            {"candidates":[{"content":{"role":"model","parts":[
              {"text":"내부 추론 요약","thought":true},
              {"text":"최종 답변"}
            ]}}]}
            """
        )
        assertEquals("최종 답변", GeminiProtocol.parseResponse(response).text)
    }

    @Test
    fun `차단된 응답은 blockReason을 담는다`() {
        val response = JSONObject(
            """
            {"promptFeedback":{"blockReason":"SAFETY"},"candidates":[]}
            """
        )
        val turn = GeminiProtocol.parseResponse(response)
        assertNull(turn.content)
        assertEquals("SAFETY", turn.blockReason)
    }

    @Test
    fun `functionResponse 턴을 올바른 구조로 만든다`() {
        val turn = GeminiProtocol.functionResponseTurn(listOf("toggle_flashlight" to "손전등을 켰습니다."))
        assertEquals("user", turn.getString("role"))
        val part = turn.getJSONArray("parts").getJSONObject(0).getJSONObject("functionResponse")
        assertEquals("toggle_flashlight", part.getString("name"))
        assertEquals("손전등을 켰습니다.", part.getJSONObject("response").getString("result"))
    }

    @Test
    fun `jsonToMap은 널과 기본 타입을 처리한다`() {
        val map = GeminiProtocol.jsonToMap(JSONObject("""{"a":1,"b":"x","c":true,"d":null}"""))
        assertEquals(1, map["a"])
        assertEquals("x", map["b"])
        assertEquals(true, map["c"])
        assertNull(map["d"])
    }
}
