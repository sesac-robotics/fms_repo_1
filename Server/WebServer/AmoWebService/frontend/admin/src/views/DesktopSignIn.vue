<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";
import { isStaff } from "../browserSession";
import { desktopCallback, desktopRequest } from "../desktopSignIn";
import { t } from "../i18n";
import { preferences } from "../preferences";
import LoginView from "./LoginView.vue";

const request = desktopRequest(window.location.search);
const initial = ref(Boolean(request));
const account = ref(null);
const busy = ref(false);
const error = ref("");

onMounted(async () => {
  if (!request) return;
  try {
    const existing = await api("/auth/me");
    account.value = isStaff(existing) ? existing : null;
  } catch (failure) {
    if (failure.status !== 401) error.value = "desktopConnectFailed";
  } finally {
    initial.value = false;
  }
});

function signed(user) {
  if (isStaff(user)) account.value = user;
}

async function connect() {
  if (!request || !isStaff(account.value) || busy.value) return;
  busy.value = true;
  error.value = "";
  try {
    const result = await api("/auth/desktop/authorize", {
      method: "POST",
      body: { port: request.port, challenge: request.challenge },
    });
    if (!result?.code) throw new Error("Authorization code unavailable");
    window.location.replace(desktopCallback(request, result.code));
  } catch (failure) {
    if (failure.status === 401 || failure.status === 403) account.value = null;
    error.value = "desktopConnectFailed";
    busy.value = false;
  }
}

function cancel() {
  window.location.replace(desktopCallback(request));
}
</script>

<template>
  <main v-if="initial" class="sign-in" aria-busy="true">{{ t("busy") }}</main>
  <LoginView v-else-if="request && !account" :desktop="true" @signed="signed" />
  <main v-else class="sign-in">
    <section class="sign-card">
      <span class="brand"
        ><img :src="'/amo-logo-' + preferences.theme + '.png'" alt="AMO"
      /></span>
      <h1>{{ t("desktopTitle") }}</h1>
      <template v-if="request">
        <p class="muted">{{ t("desktopConnectHelp") }}</p>
        <p>
          <strong>{{ account.name }}</strong
          ><br /><small>{{ account.email }}</small>
        </p>
        <p v-if="error" role="alert">{{ t(error) }}</p>
        <button class="primary" type="button" :disabled="busy" @click="connect">
          {{ t(busy ? "busy" : "desktopConnect") }}
        </button>
        <button class="quiet" type="button" :disabled="busy" @click="cancel">
          {{ t("cancel") }}
        </button>
      </template>
      <template v-else>
        <p role="alert">{{ t("desktopInvalid") }}</p>
        <a href="/">{{ t("returnLogin") }}</a>
      </template>
    </section>
  </main>
</template>
