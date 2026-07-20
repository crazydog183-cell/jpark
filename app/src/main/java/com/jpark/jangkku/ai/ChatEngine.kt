package com.jpark.jangkku.ai

import com.anthropic.client.AnthropicClient
import com.anthropic.client.okhttp.AnthropicOkHttpClient
import com.anthropic.models.messages.ContentBlockParam
import com.anthropic.models.messages.MessageCreateParams
import com.anthropic.models.messages.MessageParam
import com.anthropic.models.messages.StopReason
import com.anthropic.models.messages.ToolResultBlockParam
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 장꾸의 두뇌. Claude API를 호출하고, 모델이 요청한 도구를
 * [ToolExecutor]로 실행해 결과를 돌려주는 에이전트 루프를 돈다.
 *
 * 순수 JVM 코드로 유지한다 (안드로이드 의존성 금지 — JVM 단위 테스트/검증 대상).
 */
class ChatEngine(
    apiKey: String,
    private val toolExecutor: ToolExecutor,
) {
    private val client: AnthropicClient = AnthropicOkHttpClient.builder().apiKey(apiKey).build()
    private val history = mutableListOf<MessageParam>()

    /** 사용자 메시지를 보내고 최종 답변 텍스트를 반환한다. (블로킹 — IO 스레드에서 호출할 것) */
    fun send(userText: String): String {
        history.add(
            MessageParam.builder().role(MessageParam.Role.USER).content(userText).build()
        )
        trimHistoryIfNeeded()

        val reply = StringBuilder()
        var rounds = 0
        while (true) {
            val builder = MessageCreateParams.builder()
                .model(MODEL)
                .maxTokens(2048L)
                .system(buildSystemPrompt())
                .messages(history.toList())
            ToolDefinitions.all().forEach { builder.addTool(it) }

            val response = client.messages().create(builder.build())
            history.add(response.toParam())

            val toolResults = mutableListOf<ContentBlockParam>()
            for (block in response.content()) {
                block.text().ifPresent { text ->
                    if (reply.isNotEmpty()) reply.append('\n')
                    reply.append(text.text())
                }
                block.toolUse().ifPresent { toolUse ->
                    val input: Map<String, Any?> = runCatching {
                        @Suppress("UNCHECKED_CAST")
                        toolUse._input().convert(Map::class.java) as Map<String, Any?>
                    }.getOrElse { emptyMap() }

                    val result = runCatching { toolExecutor.execute(toolUse.name(), input) }
                        .getOrElse { e -> "도구 실행 오류: ${e.message ?: e.javaClass.simpleName}" }

                    toolResults.add(
                        ContentBlockParam.ofToolResult(
                            ToolResultBlockParam.builder()
                                .toolUseId(toolUse.id())
                                .content(result)
                                .build()
                        )
                    )
                }
            }

            val stop = response.stopReason().orElse(null)
            if (stop != StopReason.TOOL_USE || toolResults.isEmpty() || ++rounds >= MAX_TOOL_ROUNDS) {
                return reply.toString().trim()
            }
            history.add(
                MessageParam.builder()
                    .role(MessageParam.Role.USER)
                    .contentOfBlockParams(toolResults)
                    .build()
            )
        }
    }

    fun resetConversation() {
        history.clear()
    }

    /** 대화가 너무 길어지면 앞부분을 잘라 토큰 사용을 제한한다. */
    private fun trimHistoryIfNeeded() {
        while (history.size > MAX_HISTORY_MESSAGES) {
            history.removeAt(0)
        }
        // 히스토리 첫 메시지는 반드시 user 텍스트여야 하므로,
        // 잘린 뒤 assistant/tool_result로 시작하면 계속 제거한다.
        while (history.isNotEmpty() && history.first().role() != MessageParam.Role.USER) {
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
            - 제공된 도구로 사용자의 스마트폰을 직접 조작할 수 있어 (손전등, 밝기, 볼륨, 앱 실행 등).
            - 리마인더를 등록/조회/삭제해서 일정을 챙겨줄 수 있어.
            - 사용자가 기기 조작을 부탁하면 망설이지 말고 바로 해당 도구를 호출해.
            - 도구 실행 결과를 받으면 결과를 짧게 요약해서 알려줘.
            - 상대 시간 표현(내일, 30분 뒤 등)은 아래 현재 시각을 기준으로 계산해.

            현재 시각: $now
        """.trimIndent()
    }

    companion object {
        const val MODEL = "claude-opus-4-8"
        private const val MAX_TOOL_ROUNDS = 8
        private const val MAX_HISTORY_MESSAGES = 40
    }
}
