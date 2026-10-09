<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import { PERSONAS, otherPersona } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const switching = ref(false)

const partner = computed(() => otherPersona(auth.user?.id))
const mePersona = computed(() => PERSONAS.find((p) => p.id === auth.user?.id))

const links = [
  {
    to: '/settings',
    title: '设置',
    desc: '昵称 · 基础代谢 · 积分结算',
    tone: 'primary',
    mark: '设',
  },
  {
    to: '/mall-admin',
    title: '商城管理',
    desc: '积分价 · 上下架',
    tone: 'workout',
    mark: '商',
  },
  {
    to: '/achievements',
    title: '成就',
    desc: '完成挑战 · 领取积分',
    tone: 'workout',
    mark: '成',
  },
  {
    to: '/body',
    title: '身体数据',
    desc: '体重趋势 · BMI · 体脂',
    tone: 'water',
    mark: '体',
  },
  {
    to: '/report',
    title: 'AI 报告',
    desc: '日终与周报洞察',
    tone: 'cal',
    mark: '报',
  },
  {
    to: '/chat',
    title: '智能聊天',
    desc: '教练随时答疑',
    tone: 'primary',
    mark: '聊',
  },
  {
    to: '/push',
    title: '推送提醒',
    desc: 'PushPlus 绑定与时段',
    tone: 'muted',
    mark: '推',
  },
] as const

async function switchToPartner() {
  if (!partner.value || switching.value) return
  switching.value = true
  showLoadingToast({ message: '切换中…', forbidClick: true, duration: 0 })
  try {
    await auth.select(partner.value.id)
    closeToast()
    await router.replace(router.currentRoute.value.fullPath)
  } catch {
    closeToast()
    showFailToast('切换失败')
  } finally {
    switching.value = false
  }
}

function backToPick() {
  auth.clearSession()
  void router.push({ name: 'login' })
}
</script>

<template>
  <div class="mine">
    <section class="mine-hero" :class="`mine-hero--${auth.user?.id ?? 'leaf'}`">
      <div class="mine-hero__glow" aria-hidden="true" />
      <p class="fit-section-label">Profile</p>
      <div class="mine-hero__who">
        <span class="mine-hero__emoji">{{ mePersona?.emoji }}</span>
        <div>
          <h1>{{ auth.user?.display_name ?? '—' }}</h1>
          <p>健康space · {{ mePersona?.label ?? '成员' }}</p>
        </div>
      </div>
      <button
        type="button"
        class="mine-hero__switch"
        :disabled="switching"
        @click="switchToPartner"
      >
        切换为 {{ partner.emoji }} {{ partner.label }}
      </button>
    </section>

    <p class="fit-section-label mine-label">Space</p>
    <nav class="mine-grid">
      <router-link
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="mine-tile"
        :class="`mine-tile--${link.tone}`"
      >
        <span class="mine-tile__mark" aria-hidden="true">{{ link.mark }}</span>
        <strong>{{ link.title }}</strong>
        <span>{{ link.desc }}</span>
      </router-link>
    </nav>

    <button type="button" class="mine-logout" @click="backToPick">重新选人</button>
  </div>
</template>

<style scoped>
.mine {
  padding: 12px 14px 36px;
}

.mine-hero {
  position: relative;
  overflow: hidden;
  padding: 22px 18px 18px;
  margin-bottom: 22px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background:
    linear-gradient(150deg, color-mix(in srgb, var(--primary) 18%, var(--card)), var(--card) 60%);
  box-shadow: var(--shadow);
  animation: mine-in 0.45s ease both;
}

.mine-hero__glow {
  position: absolute;
  width: 200px;
  height: 200px;
  right: -48px;
  top: -60px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--hero-glow), transparent 70%);
  pointer-events: none;
}

.mine-hero__who {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 4px;
}

.mine-hero__emoji {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: 1.7rem;
  background: var(--surface-elevated);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.mine-hero h1 {
  margin: 0;
  font-size: 1.7rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.mine-hero__who p {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.mine-hero__switch {
  position: relative;
  margin-top: 16px;
  width: 100%;
  height: 46px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--surface-elevated);
  color: var(--ink);
  font-weight: 800;
  cursor: pointer;
  backdrop-filter: blur(8px);
}

.mine-hero__switch:disabled {
  opacity: 0.6;
}

.mine-label {
  margin-bottom: 10px;
}

.mine-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 20px;
}

.mine-tile {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 100px;
  padding: 16px 14px;
  border-radius: 20px;
  text-decoration: none;
  color: var(--ink);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  background: var(--card);
  overflow: hidden;
  transition: transform 0.15s ease, border-color 0.2s;
  animation: mine-in 0.5s ease both;
}

.mine-tile__mark {
  position: absolute;
  right: 10px;
  top: 10px;
  width: 28px;
  height: 28px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  font-family: var(--font-display);
  opacity: 0.7;
  background: color-mix(in srgb, var(--ink) 6%, transparent);
}

.mine-tile:nth-child(1) {
  animation-delay: 0.04s;
}
.mine-tile:nth-child(2) {
  animation-delay: 0.08s;
}
.mine-tile:nth-child(3) {
  animation-delay: 0.12s;
}
.mine-tile:nth-child(4) {
  animation-delay: 0.16s;
}
.mine-tile:nth-child(5) {
  animation-delay: 0.2s;
}
.mine-tile:nth-child(6) {
  animation-delay: 0.24s;
}

.mine-tile:active {
  transform: scale(0.98);
}

.mine-tile strong {
  font-size: 15px;
  font-weight: 800;
}

.mine-tile span {
  font-size: 11px;
  line-height: 1.4;
  font-weight: 600;
  color: var(--muted);
}

.mine-tile--primary {
  background: linear-gradient(160deg, color-mix(in srgb, var(--primary) 14%, var(--card)), var(--card));
  border-color: color-mix(in srgb, var(--primary) 28%, var(--line));
}

.mine-tile--workout {
  background: linear-gradient(160deg, color-mix(in srgb, var(--workout) 16%, var(--card)), var(--card));
  border-color: color-mix(in srgb, var(--workout) 30%, var(--line));
}

.mine-tile--water {
  background: linear-gradient(160deg, color-mix(in srgb, var(--water) 14%, var(--card)), var(--card));
  border-color: color-mix(in srgb, var(--water) 28%, var(--line));
}

.mine-tile--cal {
  background: linear-gradient(160deg, color-mix(in srgb, var(--cal) 14%, var(--card)), var(--card));
  border-color: color-mix(in srgb, var(--cal) 28%, var(--line));
}

.mine-tile--muted {
  background: color-mix(in srgb, var(--line) 35%, var(--card));
}

.mine-logout {
  width: 100%;
  height: 48px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: transparent;
  font-weight: 800;
  color: var(--muted);
  cursor: pointer;
}

@keyframes mine-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 360px) {
  .mine-grid {
    grid-template-columns: 1fr;
  }
}
</style>
