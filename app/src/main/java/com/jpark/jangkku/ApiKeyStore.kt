package com.jpark.jangkku

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** Claude API 키를 기기 내 암호화 저장소에 보관한다. */
object ApiKeyStore {

    private const val PREF_FILE = "jangkku_secure"
    private const val KEY_API = "anthropic_api_key"

    private fun prefs(context: Context) = EncryptedSharedPreferences.create(
        context,
        PREF_FILE,
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    fun save(context: Context, apiKey: String) {
        prefs(context).edit().putString(KEY_API, apiKey.trim()).apply()
    }

    fun load(context: Context): String? =
        prefs(context).getString(KEY_API, null)?.takeIf { it.isNotBlank() }

    fun clear(context: Context) {
        prefs(context).edit().remove(KEY_API).apply()
    }
}
