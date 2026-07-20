# Anthropic SDK / Jackson은 리플렉션을 사용하므로 minify 활성화 시 keep 규칙 필요
-keep class com.anthropic.** { *; }
-keep class com.fasterxml.jackson.** { *; }
-dontwarn com.fasterxml.jackson.**
