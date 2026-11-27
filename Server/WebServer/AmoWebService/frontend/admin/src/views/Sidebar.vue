<script setup>
import { preferences } from "../preferences";
import { t } from "../i18n";
defineProps({
  menuItems: { type: Array, required: true },
  activeItem: { type: String, required: true },
  user: { type: Object, required: true },
});
defineEmits(["navigate", "logout"]);
</script>
<template>
  <aside class="sidebar">
    <span class="brand"
      ><img :src="'/amo-logo-' + preferences.theme + '.png'" alt="AMO"
    /></span>
    <p class="muted">{{ t("admin") }}</p>
    <nav :aria-label="t('admin')">
      <button
        v-for="item in menuItems"
        :key="item.key"
        type="button"
        :aria-current="activeItem === item.key ? 'page' : undefined"
        @click="$emit('navigate', item.key)"
      >
        {{ item.label }}
      </button>
    </nav>
    <section class="account">
      <strong>{{ user.name }}</strong>
      <small>{{ t(user.role) }}</small>
      <button class="quiet" type="button" @click="$emit('logout')">
        {{ t("logout") }}
      </button>
    </section>
  </aside>
</template>
