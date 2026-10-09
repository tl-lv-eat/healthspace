<script setup lang="ts">
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { usePersonaTheme } from '@/composables/usePersonaTheme'

const auth = useAuthStore()
usePersonaTheme()
</script>

<template>
  <RouterView :key="auth.user?.id ?? 'anon'" />
</template>
