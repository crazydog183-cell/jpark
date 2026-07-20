package com.jpark.jangkku.ui

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.InputType
import android.view.Gravity
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/**
 * 버블을 탭하면 열리는 장꾸 채팅 패널 (오버레이 윈도우에 부착).
 */
@SuppressLint("ViewConstructor")
class ChatPanelView(
    context: Context,
    private val onSend: (String) -> Unit,
    private val onClose: () -> Unit,
) : LinearLayout(context) {

    private val messageList = LinearLayout(context).apply {
        orientation = VERTICAL
        setPadding(dp(10), dp(8), dp(10), dp(8))
    }
    private val scroll = ScrollView(context)
    private val input = EditText(context).apply {
        hint = "장꾸에게 말 걸기…"
        inputType = InputType.TYPE_CLASS_TEXT
        imeOptions = EditorInfo.IME_ACTION_SEND
        maxLines = 3
    }
    private val sendButton = Button(context).apply { text = "전송" }

    init {
        orientation = VERTICAL
        background = GradientDrawable().apply {
            setColor(Color.WHITE)
            cornerRadius = dp(16).toFloat()
            setStroke(dp(1), Color.rgb(255, 183, 77))
        }
        elevation = dp(8).toFloat()

        // 헤더
        addView(LinearLayout(context).apply {
            orientation = HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(14), dp(10), dp(6), dp(10))
            background = GradientDrawable().apply {
                setColor(Color.rgb(255, 224, 178))
                cornerRadii = floatArrayOf(
                    dp(16).toFloat(), dp(16).toFloat(), dp(16).toFloat(), dp(16).toFloat(),
                    0f, 0f, 0f, 0f,
                )
            }
            addView(TextView(context).apply {
                text = "🐹 장꾸"
                textSize = 16f
                setTypeface(typeface, Typeface.BOLD)
                layoutParams = LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f)
            })
            addView(TextView(context).apply {
                text = "✕"
                textSize = 18f
                setPadding(dp(10), 0, dp(10), 0)
                setOnClickListener { onClose() }
            })
        })

        // 메시지 목록
        scroll.addView(messageList)
        addView(scroll, LayoutParams(LayoutParams.MATCH_PARENT, 0, 1f))

        // 입력줄
        addView(LinearLayout(context).apply {
            orientation = HORIZONTAL
            setPadding(dp(8), dp(4), dp(8), dp(8))
            addView(input, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
            addView(sendButton)
        })

        val submit = {
            val text = input.text.toString().trim()
            if (text.isNotEmpty()) {
                input.setText("")
                onSend(text)
            }
        }
        sendButton.setOnClickListener { submit() }
        input.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_SEND) {
                submit(); true
            } else false
        }

        addMessage("안녕! 나는 장꾸야 🐹 뭐든 물어봐~\n(예: \"손전등 켜줘\", \"내일 9시에 회의 알려줘\")", fromUser = false)
    }

    /** 대화 말풍선을 추가한다. 반환된 TextView로 나중에 내용 갱신 가능(로딩 표시용). */
    fun addMessage(text: String, fromUser: Boolean): TextView {
        val bubble = TextView(context).apply {
            this.text = text
            textSize = 14f
            setTextColor(Color.BLACK)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            background = GradientDrawable().apply {
                cornerRadius = dp(12).toFloat()
                setColor(if (fromUser) Color.rgb(255, 236, 179) else Color.rgb(240, 240, 240))
            }
        }
        val wrapper = LinearLayout(context).apply {
            gravity = if (fromUser) Gravity.END else Gravity.START
            setPadding(0, dp(3), 0, dp(3))
            addView(bubble)
        }
        messageList.addView(wrapper)
        scrollToBottom()
        return bubble
    }

    fun setInputEnabled(enabled: Boolean) {
        input.isEnabled = enabled
        sendButton.isEnabled = enabled
    }

    fun scrollToBottom() {
        scroll.post { scroll.fullScroll(ScrollView.FOCUS_DOWN) }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
