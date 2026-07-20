package com.jpark.jangkku.ui

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.MotionEvent
import android.widget.FrameLayout
import android.widget.TextView
import kotlin.math.abs

/**
 * 화면 위를 떠다니는 장꾸 버블.
 * 드래그로 이동하고, 손을 떼면 가까운 화면 가장자리에 붙는다.
 * 짧게 탭하면 채팅창이 열린다.
 */
@SuppressLint("ViewConstructor")
class PetBubbleView(
    context: Context,
    private val onTap: () -> Unit,
    private val onDrag: (dx: Int, dy: Int) -> Unit,
    private val onRelease: () -> Unit,
) : FrameLayout(context) {

    enum class PetState(val emoji: String) {
        IDLE("🐹"),
        THINKING("🤔"),
        TALKING("😆"),
        SLEEPING("😴"),
        ERROR("😵"),
    }

    private val face = TextView(context).apply {
        text = PetState.IDLE.emoji
        textSize = 34f
        gravity = Gravity.CENTER
    }

    private var downRawX = 0f
    private var downRawY = 0f
    private var lastRawX = 0f
    private var lastRawY = 0f
    private var dragging = false

    init {
        background = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(Color.argb(235, 255, 224, 178)) // 연한 주황 배경
            setStroke(dp(2), Color.rgb(255, 167, 38))
        }
        elevation = dp(6).toFloat()
        addView(face, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
    }

    fun setState(state: PetState) {
        face.text = state.emoji
    }

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                downRawX = event.rawX
                downRawY = event.rawY
                lastRawX = event.rawX
                lastRawY = event.rawY
                dragging = false
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                val dx = (event.rawX - lastRawX).toInt()
                val dy = (event.rawY - lastRawY).toInt()
                lastRawX = event.rawX
                lastRawY = event.rawY
                if (dragging ||
                    abs(event.rawX - downRawX) > TOUCH_SLOP ||
                    abs(event.rawY - downRawY) > TOUCH_SLOP
                ) {
                    dragging = true
                    onDrag(dx, dy)
                }
                return true
            }
            MotionEvent.ACTION_UP -> {
                if (dragging) onRelease() else onTap()
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    companion object {
        private const val TOUCH_SLOP = 20f
    }
}
