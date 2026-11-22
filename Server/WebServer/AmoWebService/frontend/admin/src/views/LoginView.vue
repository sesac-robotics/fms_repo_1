<script setup>
import { nextTick, onMounted, ref, watch } from "vue";
import { api } from "../api";
import { announceBrowserSession, isStaff } from "../browserSession";
import { installGoogleButton } from "../google";
import { languages, preferences } from "../preferences";
import { t } from "../i18n";

defineProps({ desktop: Boolean });
const emit = defineEmits(["signed"]);
const register = ref(false);
const fullName = ref("");
const email = ref("");
const password = ref("");
const loading = ref(false);
const alerts = ref("");
const googleButton = ref(null);
const googleClient = ref("");
const googleFailed = ref(false);

async function accept(result) {
  const user = result?.user ?? result;
  if (!isStaff(user)) {
    await api("/auth/logout", { method: "POST" }).catch(() => {});
    alerts.value = "denied";
    announceBrowserSession();
    return;
  }
  emit("signed", user);
  announceBrowserSession();
}

async function submit() {
  loading.value = true;
  alerts.value = "";
  try {
    const body = { email: email.value.trim(), password: password.value };
    if (register.value) {
      await api("/auth/register/admin", {
        method: "POST",
        body: { ...body, name: fullName.value.trim() },
      });
      register.value = false;
      alerts.value = "pending";
    } else {
      await accept(await api("/auth/login", { method: "POST", body }));
    }
  } catch (error) {
    alerts.value = [401, 403].includes(error.status) ? "denied" : "error";
  } finally {
    password.value = "";
    loading.value = false;
  }
}

async function renderGoogle() {
  if (!googleClient.value || register.value) return;
  await nextTick();
  if (!googleButton.value) return;
  try {
    await installGoogleButton(googleButton.value, {
      clientId: googleClient.value,
      locale: preferences.locale,
      theme: preferences.theme,
      credential: async (credential) => {
        try {
          await accept(
            await api("/auth/google", {
              method: "POST",
              body: { credential },
            }),
          );
        } catch (error) {
          alerts.value = error.status === 403 ? "denied" : "googleError";
        }
      },
    });
    googleFailed.value = false;
  } catch {
    googleFailed.value = true;
  }
}

onMounted(async () => {
  const config = await api("/auth/google/config").catch(() => null);
  googleClient.value = config?.clientId ?? "";
  await renderGoogle();
});
watch(
  () => [preferences.locale, preferences.theme, register.value],
  renderGoogle,
);
</script>

<template>
  <main class="sign-in">
    <section class="sign-card" :aria-label="t('admin')">
      <div class="sign-controls">
        <span class="brand"
          ><img :src="'/amo-logo-' + preferences.theme + '.png'" alt="AMO"
        /></span>
        <select v-model="preferences.locale" :aria-label="t('language')">
          <option
            v-for="language in languages"
            :key="language.code"
            :value="language.code"
          >
            {{ language.label }}
          </option>
        </select>
      </div>
      <h1>{{ t(register ? "register" : "login") }}</h1>
      <p class="muted">
        {{ t(desktop ? "desktopLoginHelp" : "loginHelp") }}
      </p>
      <form class="stack" @submit.prevent="submit">
        <label v-if="register"
          >{{ t("name")
          }}<input v-model="fullName" autocomplete="name" required
        /></label>
        <label
          >{{ t("email")
          }}<input v-model="email" type="email" autocomplete="email" required
        /></label>
        <label
          >{{ t("password") }}
          <input
            v-model="password"
            type="password"
            :autocomplete="register ? 'new-password' : 'current-password'"
            required
          />
        </label>
        <button class="primary" :disabled="loading">
          {{ t(loading ? "busy" : register ? "register" : "login") }}
        </button>
      </form>
      <p v-if="alerts" role="status">{{ t(alerts) }}</p>
      <template v-if="!register">
        <div v-if="googleClient" ref="googleButton" class="google-button"></div>
        <p v-if="googleFailed || !googleClient" class="muted">
          {{ t(googleFailed ? "googleError" : "googleMissing") }}
        </p>
      </template>
      <button
        v-if="!desktop"
        class="quiet"
        type="button"
        @click="
          register = !register;
          alerts = '';
        "
      >
        {{ t(register ? "returnLogin" : "register") }}
      </button>
    </section>
  </main>
</template>
