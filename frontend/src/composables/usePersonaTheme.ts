import { watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

/** Apply dragon (dark) / leaf (pink) theme on <html data-persona>. */
export function usePersonaTheme() {
  const auth = useAuthStore()

  function apply(id: string | undefined | null) {
    const root = document.documentElement
    if (id === 'dragon' || id === 'leaf') {
      root.dataset.persona = id
    } else {
      delete root.dataset.persona
    }
  }

  apply(auth.user?.id)
  watch(
    () => auth.user?.id,
    (id) => apply(id),
    { immediate: true },
  )
}
