package com.jpark.jangkku.service

import android.animation.ValueAnimator
import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.graphics.PixelFormat
import android.os.IBinder
import android.view.Gravity
import android.view.WindowManager
import android.view.animation.OvershootInterpolator
import com.jpark.jangkku.ApiKeyStore
import com.jpark.jangkku.JangkkuApp
import com.jpark.jangkku.MainActivity
import com.jpark.jangkku.ai.ChatEngine
import com.jpark.jangkku.device.DeviceToolExecutor
import com.jpark.jangkku.ui.ChatPanelView
import com.jpark.jangkku.ui.PetBubbleView
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * 장꾸의 본체. 포그라운드 서비스로 상주하며
 * WindowManager 오버레이로 플로팅 버블과 채팅 패널을 띄운다.
 */
class PetOverlayService : Service() {

    private lateinit var windowManager: WindowManager
    private var bubble: PetBubbleView? = null
    private var bubbleParams: WindowManager.LayoutParams? = null
    private var chatPanel: ChatPanelView? = null
    private var snapAnimator: ValueAnimator? = null

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var chatEngine: ChatEngine? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        startForeground(NOTIFICATION_ID, buildNotification())

        val apiKey = ApiKeyStore.load(this)
        if (apiKey != null) {
            chatEngine = ChatEngine(apiKey, DeviceToolExecutor(applicationContext))
        }
        addBubble()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        scope.cancel()
        removeChatPanel()
        bubble?.let { runCatching { windowManager.removeView(it) } }
        bubble = null
        super.onDestroy()
    }

    // ── 버블 ─────────────────────────────────────────────

    private fun addBubble() {
        val params = WindowManager.LayoutParams(
            dp(64), dp(64),
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = screenWidth() - dp(72)
            y = screenHeight() / 3
        }
        bubbleParams = params

        val view = PetBubbleView(
            this,
            onTap = { toggleChatPanel() },
            onDrag = { dx, dy ->
                snapAnimator?.cancel()
                params.x += dx
                params.y += dy
                bubble?.let { windowManager.updateViewLayout(it, params) }
            },
            onRelease = { snapToEdge() },
        )
        bubble = view
        windowManager.addView(view, params)

        if (chatEngine == null) view.setState(PetBubbleView.PetState.ERROR)
    }

    /** 손을 떼면 가까운 좌/우 가장자리로 스냅 */
    private fun snapToEdge() {
        val params = bubbleParams ?: return
        val view = bubble ?: return
        val targetX = if (params.x + dp(32) < screenWidth() / 2) dp(8) else screenWidth() - dp(72)
        val startX = params.x
        val maxY = screenHeight() - dp(80)
        val targetY = params.y.coerceIn(dp(8), maxY)
        val startY = params.y

        snapAnimator?.cancel()
        snapAnimator = ValueAnimator.ofFloat(0f, 1f).apply {
            duration = 250
            interpolator = OvershootInterpolator()
            addUpdateListener { anim ->
                val f = anim.animatedValue as Float
                params.x = (startX + (targetX - startX) * f).toInt()
                params.y = (startY + (targetY - startY) * f).toInt()
                runCatching { windowManager.updateViewLayout(view, params) }
            }
            start()
        }
    }

    // ── 채팅 패널 ─────────────────────────────────────────

    private fun toggleChatPanel() {
        if (chatPanel != null) removeChatPanel() else showChatPanel()
    }

    private fun showChatPanel() {
        val panel = ChatPanelView(
            this,
            onSend = { text -> handleUserMessage(text) },
            onClose = { removeChatPanel() },
        )
        val params = WindowManager.LayoutParams(
            dp(300), dp(400),
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.CENTER
            softInputMode = WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE
        }
        chatPanel = panel
        windowManager.addView(panel, params)

        if (chatEngine == null) {
            panel.addMessage("API 키가 설정되지 않았어… 설정 앱에서 Gemini API 키를 저장해 줘! 😢", fromUser = false)
            panel.setInputEnabled(false)
        }
    }

    private fun removeChatPanel() {
        chatPanel?.let { runCatching { windowManager.removeView(it) } }
        chatPanel = null
    }

    private fun handleUserMessage(text: String) {
        val engine = chatEngine ?: return
        val panel = chatPanel ?: return
        panel.addMessage(text, fromUser = true)
        val pending = panel.addMessage("생각 중… 🤔", fromUser = false)
        panel.setInputEnabled(false)
        bubble?.setState(PetBubbleView.PetState.THINKING)

        scope.launch {
            val reply = withContext(Dispatchers.IO) {
                runCatching { engine.send(text) }
                    .getOrElse { e -> "앗, 문제가 생겼어 😵 (${e.message ?: e.javaClass.simpleName})" }
            }
            pending.text = reply.ifBlank { "…(할 말을 잃은 장꾸)" }
            chatPanel?.setInputEnabled(true)
            chatPanel?.scrollToBottom()
            bubble?.setState(PetBubbleView.PetState.TALKING)
            delay(1500)
            bubble?.setState(PetBubbleView.PetState.IDLE)
        }
    }

    // ── 기타 ─────────────────────────────────────────────

    private fun buildNotification(): Notification {
        val contentIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE,
        )
        return Notification.Builder(this, JangkkuApp.CHANNEL_PET_SERVICE)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("장꾸가 활동 중이에요 🐹")
            .setContentText("버블을 탭하면 대화할 수 있어요")
            .setContentIntent(contentIntent)
            .setOngoing(true)
            .build()
    }

    private fun screenWidth(): Int = resources.displayMetrics.widthPixels
    private fun screenHeight(): Int = resources.displayMetrics.heightPixels
    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    companion object {
        private const val NOTIFICATION_ID = 1
    }
}
