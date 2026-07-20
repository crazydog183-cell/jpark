package com.jpark.jangkku.ai

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * 장꾸의 두뇌. Gemini API(generateContent)를 호출하고, 모델이 요청한
 * 함수(도구)를 [ToolExecutor]로 실행해 결과를 돌려주는 에이전트 루프를 돈다.
 *
 * 순수 JVM 코드로 유지한다 (안드로이드 의존성 금지 — JVM 단위 테스트/검증 대상).
 */
class ChatEngine(
    private val apiKey: String,
    private val toolExecutor: ToolExecutor,
    private val model: String = DEFAULT_MODEL,
) {
    private val http = OkHttpClient.Builder()
        .connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .build()

    private val history = mutableListOf<JSONObject>()

    /** 사용자 메시지를 보내고 최종 답변 텍스트를 반환한다. (블로킹 — IO 스레드에서 호출할 것) */
    fun send(userText: String): String {
        history.add(GeminiProtocol.userTurn(userText))
        trimHistoryIfNeeded()

        val reply = StringBuilder()
        var rounds = 0
        while (true) {
            val requestBody = GeminiProtocol.buildRequest(
                history = history,
                systemPrompt = buildSystemPrompt(),
                functionDeclarations = ToolDefinitions.functionDeclarations(),
                maxOutputTokens = MAX_OUTPUT_TOKENS,
            )
            val turn = GeminiProtocol.parseResponse(post(requestBody))

            if (turn.content == null) {
                return reply.toString().trim().ifEmpty {
                    "미안, 그 요청에는 답할 수 없어 😢 (사유: ${turn.blockReason})"
                }
            }
            history.add(turn.content)

            if (turn.text.isNotBlank()) {
                if (reply.isNotEmpty()) reply.append('\n')
                reply.append(turn.text)
            }

            if (turn.functionCalls.isEmpty() || ++rounds >= MAX_TOOL_ROUNDS) {
                return reply.toString().trim().ifEmpty { "…(할 말을 잃은 장꾸)" }
            }

            val results = turn.functionCalls.map { call ->
                val result = runCatching { toolExecutor.execute(call.name, call.args) }
                    .getOrElse { e -> "도구 실행 오류: ${e.message ?: e.javaClass.simpleName}" }
                call.name to result
            }
            history.add(GeminiProtocol.functionResponseTurn(results))
        }
    }

    fun resetConversation() {
        history.clear()
    }

    private fun post(body: JSONObject): JSONObject {
        val request = Request.Builder()
            .url("$BASE_URL/models/$model:generateContent")
            .header("x-goog-api-key", apiKey)
            .post(body.toString().toRequestBody("application/json; charset=utf-8".toMediaType()))
            .build()
        http.newCall(request).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                val message = runCatching {
                    JSONObject(text).getJSONObject("error").getString("message")
                }.getOrDefault(text.take(200))
                throw IOException("Gemini API 오류 (HTTP ${response.code}): $message")
            }
            return JSONObject(text)
        }
    }

    /** 대화가 너무 길어지면 앞부분을 잘라 토큰 사용을 제한한다. */
    private fun trimHistoryIfNeeded() {
        while (history.size > MAX_HISTORY_MESSAGES) {
            history.removeAt(0)
        }
        // 히스토리는 반드시 user 텍스트 턴으로 시작해야 자연스럽다.
        while (history.isNotEmpty() &&
            !(history.first().optString("role") == "user" &&
                history.first().optJSONArray("parts")?.optJSONObject(0)?.has("text") == true)
        ) {
            history.removeAt(0)
        }
    }

    private fun buildSystemPrompt(): String {
        val now = SimpleDateFormat("yyyy-MM-dd HH:mm (EEEE)", Locale.KOREAN).format(Date())
        return """
            너는 '장꾸'라는 이름의 스마트폰 요정 펫이야. 사용자의 홈 화면 위에 떠서 함께 지내.

            성격과 말투:
            - 밝고 장난기 많은 반말을 써. 이모지를 적당히 섞어 귀엽게 말해.
            - 답변은 짧고 경쾌하게. 화면이 작으니 3~4문장을 넘기지 마.

            능력:
            - 제공된 함수로 사용자의 스마트폰을 직접 조작할 수 있어 (손전등, 밝기, 볼륨, 앱 실행 등).
            - 리마인더를 등록/조회/삭제해서 일정을 챙겨줄 수 있어.
            - 사용자가 기기 조작을 부탁하면 망설이지 말고 바로 해당 함수를 호출해.
            - 함수 실행 결과를 받으면 결과를 짧게 요약해서 알려줘.
            - 상대 시간 표현(내일, 30분 뒤 등)은 아래 현재 시각을 기준으로 계산해.

            현재 시각: $now
        """.trimIndent()
    }

    companion object {
        const val DEFAULT_MODEL = "gemini-2.5-flash"
        private const val BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
        private const val MAX_OUTPUT_TOKENS = 2048
        private const val MAX_TOOL_ROUNDS = 8
        private const val MAX_HISTORY_MESSAGES = 40
    }
}
