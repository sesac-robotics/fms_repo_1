<script setup>
import { useAdminWorkspace } from "./adminWorkspace";
import { t } from "./i18n";
import { preferences } from "./preferences";
import Sidebar from "./views/Sidebar.vue";
import LoginView from "./views/LoginView.vue";
import OperationsView from "./views/OperationsView.vue";
import SettingsView from "./views/SettingsView.vue";
import TutorialDialog from "./views/TutorialDialog.vue";
import MenuView from "./views/MenuView.vue";
import MembersView from "./views/MembersView.vue";

const {
  user,
  initial,
  busy,
  error,
  view,
  operations,
  menus,
  members,
  tutorial,
  admin,
  menuItems,
  refresh,
  signed,
  signOut,
  show,
} = useAdminWorkspace();
</script>

<template>
  <main v-if="initial" class="sign-in" aria-busy="true">{{ t("busy") }}</main>
  <LoginView v-else-if="!user" @signed="signed" />
  <div v-else class="shell">
    <Sidebar
      :menu-items="menuItems"
      :active-item="view"
      :user="user"
      @navigate="show"
      @logout="signOut"
    />
    <main class="workspace" :aria-busy="busy">
      <div class="topbar">
        <span>{{ t("tenant") }}</span>
        <div class="actions">
          <span v-if="operations.demo" class="state">{{ t("demo") }}</span>
          <button
            type="button"
            @click="
              preferences.theme =
                preferences.theme === 'dark' ? 'light' : 'dark'
            "
          >
            {{ t(preferences.theme === "dark" ? "light" : "dark") }}
          </button>
          <button
            v-if="view !== 'settings'"
            type="button"
            :disabled="busy"
            @click="refresh"
          >
            {{ t("refresh") }}
          </button>
        </div>
      </div>
      <div class="content">
        <h1 v-if="view !== 'settings'">{{ t(view) }}</h1>
        <p v-if="error" role="alert">{{ t(error) }}</p>
        <SettingsView
          v-if="view === 'settings'"
          :admin="admin"
          @replay="tutorial = true"
          @menus="show('menu')"
        />
        <MenuView
          v-else-if="view === 'menu' && admin"
          :items="menus"
          @changed="refresh"
        />
        <MembersView
          v-else-if="view === 'members' && admin"
          :items="members"
          @changed="refresh"
        />
        <OperationsView
          v-else
          :data="operations"
          :view="view"
          :demo="operations.demo === true"
        />
      </div>
    </main>
    <TutorialDialog
      v-if="tutorial"
      @finish="
        tutorial = false;
        preferences.tutorialSeen = true;
      "
    />
  </div>
</template>
