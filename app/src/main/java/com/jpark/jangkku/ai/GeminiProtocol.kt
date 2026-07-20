package com.jpark.jangkku.ai

import org.json.JSONArray
import org.json.JSONObject

/**
 * Gemini generateContent REST API의 요청/응답 JSON을 만들고 해석한다.
 * 순수 JVM 코드 — 단위 테스트 대상.
 *
 * https://ai.google.dev/gemini-api/docs (generateContent + function calling)
 */
object GeminiProtocol {

    data class FunctionCall(val name: String, val args: Map<String, Any?>)

    /** 모델 응답 한 턴의 해석 결과 */
    data class ModelTurn(
        /** 히스토리에 그대로 되돌려 넣을 model content (없으면 응답이 차단된 것) */
        val content: JSONObject?,
        val text: String,
        val functionCalls: List<FunctionCall>,
        val blockReason: String?,
    )

    /** 사용자 텍스트 턴 */
    fun userTurn(text: String): JSONObject = JSONObject()
        .put("role", "user")
        .put("parts", JSONArray().put(JSONObject().put("text", text)))

    /** 도구 실행 결과(functionResponse) 턴 — (도구 이름, 결과 문자열) 목록 */
    fun functionResponseTurn(results: List<Pair<String, String>>): JSONObject {
        val parts = JSONArray()
        results.forEach { (name, result) ->
            parts.put(
                JSONObject().put(
                    "functionResponse",
                    JSONObject()
                        .put("name", name)
                        .put("response", JSONObject().put("result", result)),
                )
            )
        }
        return JSONObject().put("role", "user").put("parts", parts)
    }

    /** generateContent 요청 본문 */
    fun buildRequest(
        history: List<JSONObject>,
        systemPrompt: String,
        functionDeclarations: JSONArray,
        maxOutputTokens: Int,
    ): JSONObject {
        val contents = JSONArray()
        history.forEach { contents.put(it) }
        return JSONObject()
            .put(
                "systemInstruction",
                JSONObject().put("parts", JSONArray().put(JSONObject().put("text", systemPrompt))),
            )
            .put("contents", contents)
            .put("tools", JSONArray().put(JSONObject().put("functionDeclarations", functionDeclarations)))
            .put("generationConfig", JSONObject().put("maxOutputTokens", maxOutputTokens))
    }

    /** generateContent 응답 해석 */
    fun parseResponse(response: JSONObject): ModelTurn {
        val candidate = response.optJSONArray("candidates")?.optJSONObject(0)
        val content = candidate?.optJSONObject("content")
        if (content == null) {
            val blockReason = response.optJSONObject("promptFeedback")?.optString("blockReason")
                ?.takeIf { it.isNotBlank() }
                ?: candidate?.optString("finishReason")?.takeIf { it.isNotBlank() }
                ?: "UNKNOWN"
            return ModelTurn(content = null, text = "", functionCalls = emptyList(), blockReason = blockReason)
        }

        val texts = StringBuilder()
        val calls = mutableListOf<FunctionCall>()
        val parts = content.optJSONArray("parts") ?: JSONArray()
        for (i in 0 until parts.length()) {
            val part = parts.optJSONObject(i) ?: continue
            // thought=true 파트는 내부 추론 요약이므로 사용자에게 보여주지 않는다
            if (part.has("text") && !part.optBoolean("thought", false)) {
                if (texts.isNotEmpty()) texts.append('\n')
                texts.append(part.getString("text"))
            }
            part.optJSONObject("functionCall")?.let { call ->
                calls.add(
                    FunctionCall(
                        name = call.getString("name"),
                        args = jsonToMap(call.optJSONObject("args") ?: JSONObject()),
                    )
                )
            }
        }
        return ModelTurn(content = content, text = texts.toString().trim(), functionCalls = calls, blockReason = null)
    }

    /** 얕은 JSONObject → Map 변환 (도구 인자는 평면 구조만 사용) */
    fun jsonToMap(obj: JSONObject): Map<String, Any?> {
        val map = mutableMapOf<String, Any?>()
        val keys = obj.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val value = obj.get(key)
            map[key] = if (value == JSONObject.NULL) null else value
        }
        return map
    }
}
